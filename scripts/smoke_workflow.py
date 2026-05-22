"""
End-to-end test of the new Temporal pipeline:

    POST /projects/from-source     → AnalyzeProjectWorkflow
    poll /jobs/{analyze_job_id}    → wait for status=done
    POST /projects/{id}/generate   → GenerateVideoWorkflow (plan → fan-out → concat)
    poll /jobs/{gen_job_id}        → wait for status=done
    GET  /projects/{id}            → verify final_video_url + N scenes with video_urls

Usage:
    poetry run python scripts/smoke_workflow.py [url]
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

API = "http://localhost:8008/api/v1"
DEFAULT_URL = "https://www.youtube.com/shorts/6gcC6mBGj8s"
POLL_INTERVAL = 3.0  # seconds
ANALYZE_TIMEOUT = 300  # 5 min
GENERATE_TIMEOUT = 1200  # 20 min


def step(name: str) -> None:
    print(f"\n{'━' * 70}\n  {name}\n{'━' * 70}")


def must_succeed(resp: requests.Response) -> dict:
    try:
        body = resp.json()
    except Exception:
        print(f"  HTTP {resp.status_code}: {resp.text[:500]}")
        sys.exit(1)
    if not body.get("success", False):
        print(f"  HTTP {resp.status_code} success=False: {body.get('message')}")
        sys.exit(1)
    return body["result"]


def poll_job(job_id: str, timeout: int) -> dict:
    """Poll /jobs/{id} until status in (done, failed) or timeout. Returns last body."""
    start = time.time()
    last_status = None
    last_progress = None
    last_logs_count = 0
    while time.time() - start < timeout:
        body = requests.get(f"{API}/jobs/{job_id}").json()
        if not body.get("success"):
            print(f"  poll error: {body}")
            time.sleep(POLL_INTERVAL)
            continue
        job = body["result"]
        status = job["status"]
        progress = job.get("progress", 0)
        logs = job.get("logs") or []
        if status != last_status or progress != last_progress or len(logs) != last_logs_count:
            elapsed = int(time.time() - start)
            print(f"  [{elapsed:>4}s] status={status:<10} progress={progress:>3}  logs={len(logs)}")
            for entry in logs[last_logs_count:]:
                step_name = entry.get("step", "?")
                detail = {k: v for k, v in entry.items() if k != "step"}
                print(f"            └─ {step_name}: {detail}")
            last_status, last_progress, last_logs_count = status, progress, len(logs)
        if status in ("done", "failed"):
            return job
        time.sleep(POLL_INTERVAL)
    print(f"  ✗ timed out after {timeout}s")
    sys.exit(1)


def main(url: str) -> int:
    t_start = time.time()

    step(f"1. POST /projects/from-source  url={url}")
    body = requests.post(f"{API}/projects/from-source", json={"source_url": url})
    result = must_succeed(body)
    project_id = result["project"]["id"]
    analyze_job_id = result["job"]["id"]
    print(f"  project_id:      {project_id}")
    print(f"  source_type:     {result['source_type']}")
    print(f"  analyze job_id:  {analyze_job_id}")

    step(f"2. Poll analyze job {analyze_job_id}")
    analyze_job = poll_job(analyze_job_id, ANALYZE_TIMEOUT)
    if analyze_job["status"] != "done":
        print(f"  ✗ analyze failed: {analyze_job}")
        return 1
    analyze_elapsed = int(time.time() - t_start)
    print(f"  ✓ analyze done in {analyze_elapsed}s")

    step(f"3. Project after analyze (GET /projects/{project_id})")
    proj = requests.get(f"{API}/projects/{project_id}").json()["result"]
    print(f"  title:               {proj['title']}")
    print(f"  status:              {proj['status']}")
    print(f"  source_duration:     {proj.get('source_duration')}")
    print(f"  transcript chars:    {len(proj.get('transcript') or '')}")
    print(f"  description chars:   {len(proj.get('description') or '')}")
    print(f"  manim_prompt chars:  {len(proj.get('manim_prompt') or '')}")

    step(f"4. POST /projects/{project_id}/generate?max_clips=5")
    body = requests.post(f"{API}/projects/{project_id}/generate?max_clips=5")
    gen_job = must_succeed(body)
    gen_job_id = gen_job["id"]
    print(f"  generate job_id: {gen_job_id}")

    step(f"5. Poll generate job {gen_job_id}")
    final = poll_job(gen_job_id, GENERATE_TIMEOUT)
    if final["status"] != "done":
        print(f"  ✗ generate failed: {final}")
        return 1

    step("6. Project after generate")
    proj = requests.get(f"{API}/projects/{project_id}").json()["result"]
    print(f"  status:           {proj['status']}")
    print(f"  final_video_url:  {proj.get('final_video_url')}")
    print(f"  scenes:           {len(proj.get('scenes', []))}")
    for s in proj.get("scenes", []):
        print(
            f"    [n={s['n']}] {s['title'][:40]:<40}  status={s['status']:<8}"
            f"  render_method={(s.get('render_method') or '?'):<22}"
            f"  video={'yes' if s.get('video_url') else 'NO'}"
        )

    if proj.get("final_video_url"):
        path = Path(proj["final_video_url"])
        if path.exists():
            print(f"\n  ✓ final video: {path}  ({path.stat().st_size:,} bytes)")
            print(f"  Open:  open {path}")
        else:
            print(f"\n  ✗ final_video_url points at non-existent file: {path}")

    total = int(time.time() - t_start)
    print(f"\n  TOTAL: {total}s  (analyze {analyze_elapsed}s + generate {total - analyze_elapsed}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL))
