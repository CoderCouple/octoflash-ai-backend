"""
Primitive registry, populated by side-effect imports below.

Primitives are organized into subpackages by category to keep the tree
manageable as the library grows toward ~50 primitives. Each subpackage's
`__init__.py` imports all its primitive modules, registering them via the
`@register` decorator in `app.templates.primitives.registry`.

Subpackage layout:
  utility/   — cross-cutting helpers (background, hold, fade)
  text/      — text & titles primitives (text_reveal, text_pop, typewriter, …)
  math/      — math & equations (to be added)
  chart/     — data & charts (to be added)
  diagram/   — diagrams (to be added)
  compare/   — compare & contrast (to be added)
  emphasis/  — emphasis & reveals (to be added)
  motion/    — motion & geometry (to be added)
  camera/    — camera & transitions (to be added)
  outro/     — outros & CTAs (to be added)
  media/     — media (to be added)
  reactions/ — reactions / shorts vernacular (to be added)

To add a new primitive: create `<group>/<name>.py` with `@register` on its
Primitive subclass, then import it in `<group>/__init__.py`.
"""

# Importing each subpackage triggers its primitive modules' @register calls.
from app.templates.primitives import text, utility  # noqa: F401
