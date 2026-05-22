"""
ArticleScraperService — fetch readable article text from Medium + Substack.

Medium:
  - Public articles only (paywalled posts return a truncated preview)
  - Standard HTTP GET with a desktop UA; parse via BeautifulSoup
  - Body lives in <article>...</article> for most modern post layouts

Substack:
  - Prefer the RSS feed at https://<subdomain>.substack.com/feed — it bundles
    the full HTML body of each post, no scraping needed
  - Fall back to HTML scrape if the post isn't in the feed (deep archive)

Both are synchronous (network-bound). Callers should wrap in
`asyncio.to_thread(...)` from async code.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


# Real-browser UA — Medium serves a stripped fallback to default `python-requests` UAs.
_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15"
)


@dataclass
class ArticleContent:
    title: str
    text: str
    author: str | None = None
    published_at: str | None = None  # ISO 8601 when known


class ArticleFetchError(RuntimeError):
    """Article couldn't be fetched / parsed."""


class ArticleScraperService:
    # ── Medium ─────────────────────────────────────────────────────────────

    def fetch_medium(self, url: str) -> ArticleContent:
        import requests
        from bs4 import BeautifulSoup

        try:
            resp = requests.get(
                url, headers={"User-Agent": _UA, "Accept-Language": "en-US,en;q=0.9"},
                timeout=20, allow_redirects=True,
            )
        except Exception as e:
            raise ArticleFetchError(f"Medium GET failed: {e}") from e
        if resp.status_code != 200:
            raise ArticleFetchError(
                f"Medium returned HTTP {resp.status_code} for {url!r}"
            )

        soup = BeautifulSoup(resp.text, "lxml")
        title = (
            (soup.find("h1") and soup.find("h1").get_text(strip=True))
            or (soup.find("meta", property="og:title") or {}).get("content")
            or "Untitled"
        )

        # Modern Medium layouts use <article>; the body is a sequence of <p>,
        # <h2>, <pre>, <ul> etc. inside it.
        article_tag = soup.find("article")
        if article_tag is None:
            # Old layout / paywalled fallback.
            article_tag = soup.find("section") or soup.find("body")
        if article_tag is None:
            raise ArticleFetchError("Medium: could not locate article body")

        # Drop noisy elements before text extraction.
        for noise in article_tag.select(
            "script, style, noscript, footer, header, "
            "[data-test-id*='clap'], [data-testid*='clap'], [class*='clap'], [class*='Footer']"
        ):
            noise.decompose()

        # Collect paragraph/heading text, dedupe runs of whitespace.
        chunks: list[str] = []
        for el in article_tag.find_all(["h1", "h2", "h3", "p", "li", "pre", "blockquote"]):
            t = el.get_text(" ", strip=True)
            if t:
                chunks.append(t)
        text = "\n\n".join(chunks)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        if not text:
            raise ArticleFetchError("Medium: article body parsed empty")

        author_tag = soup.find("meta", attrs={"name": "author"})
        author = author_tag.get("content") if author_tag else None

        # `og:published_time` or `<time datetime=...>`
        pub_meta = soup.find("meta", property="article:published_time")
        published_at = (
            pub_meta.get("content")
            if pub_meta
            else (soup.find("time") or {}).get("datetime")
            if soup.find("time")
            else None
        )

        return ArticleContent(title=title, text=text, author=author, published_at=published_at)

    # ── Substack ───────────────────────────────────────────────────────────

    def fetch_substack(self, url: str) -> ArticleContent:
        # Try RSS first — gives clean HTML bodies, no scraping.
        try:
            return self._substack_via_rss(url)
        except ArticleFetchError as e:
            logger.info("Substack RSS path failed (%s); falling back to HTML", e)
        return self._substack_via_html(url)

    def _substack_via_rss(self, url: str) -> ArticleContent:
        import feedparser
        import requests
        from bs4 import BeautifulSoup

        parsed = urlparse(url)
        host = parsed.hostname or ""
        if not host:
            raise ArticleFetchError("Substack: missing hostname")

        feed_url = f"https://{host}/feed"
        try:
            resp = requests.get(
                feed_url, headers={"User-Agent": _UA}, timeout=15
            )
        except Exception as e:
            raise ArticleFetchError(f"Substack RSS GET failed: {e}") from e
        if resp.status_code != 200:
            raise ArticleFetchError(f"Substack RSS HTTP {resp.status_code}")

        feed = feedparser.parse(resp.content)
        # Find the entry whose link matches the requested URL (path comparison
        # is robust to trailing slashes / utm params).
        target_path = parsed.path.rstrip("/")
        entry = None
        for e in feed.entries:
            link = (e.get("link") or "").rstrip("/")
            if link.endswith(target_path):
                entry = e
                break
        if entry is None:
            raise ArticleFetchError("Substack: post not in RSS feed")

        # `content` is the rich HTML body; fall back to `summary`.
        html = (
            entry.get("content", [{}])[0].get("value") if entry.get("content") else None
        ) or entry.get("summary") or ""
        soup = BeautifulSoup(html, "lxml")
        for noise in soup.select("script, style, .button-wrapper, .image-link-expand"):
            noise.decompose()
        chunks = [el.get_text(" ", strip=True) for el in soup.find_all(["h1", "h2", "h3", "p", "li", "pre", "blockquote"])]
        text = "\n\n".join(c for c in chunks if c).strip()
        if not text:
            raise ArticleFetchError("Substack RSS body parsed empty")

        published_at = entry.get("published")
        if published_at:
            # feedparser emits RFC 822 strings; normalize to ISO 8601 when possible.
            try:
                published_at = datetime(*entry.published_parsed[:6]).isoformat()
            except Exception:
                pass

        return ArticleContent(
            title=entry.get("title") or "Untitled",
            text=text,
            author=entry.get("author"),
            published_at=published_at,
        )

    def _substack_via_html(self, url: str) -> ArticleContent:
        import requests
        from bs4 import BeautifulSoup

        try:
            resp = requests.get(url, headers={"User-Agent": _UA}, timeout=20)
        except Exception as e:
            raise ArticleFetchError(f"Substack HTML GET failed: {e}") from e
        if resp.status_code != 200:
            raise ArticleFetchError(f"Substack HTML HTTP {resp.status_code}")

        soup = BeautifulSoup(resp.text, "lxml")
        title = (
            (soup.find("h1") and soup.find("h1").get_text(strip=True))
            or (soup.find("meta", property="og:title") or {}).get("content")
            or "Untitled"
        )
        body = soup.select_one("div.available-content") or soup.find("article") or soup.find("body")
        if body is None:
            raise ArticleFetchError("Substack: could not locate post body")
        for noise in body.select("script, style, .button-wrapper, .subscribe-widget"):
            noise.decompose()
        chunks = [el.get_text(" ", strip=True) for el in body.find_all(["h1", "h2", "h3", "p", "li", "pre", "blockquote"])]
        text = "\n\n".join(c for c in chunks if c).strip()
        if not text:
            raise ArticleFetchError("Substack: post body parsed empty")

        pub_meta = soup.find("meta", property="article:published_time")
        return ArticleContent(
            title=title,
            text=text,
            author=(soup.find("meta", attrs={"name": "author"}) or {}).get("content"),
            published_at=pub_meta.get("content") if pub_meta else None,
        )
