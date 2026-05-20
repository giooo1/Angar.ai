"""Path shim so `from canonical import CanonicalInvoice` works.

The canonical Pydantic schema lives at `project foundation/canonical.py` at
the repo root. The folder name has a space, so a normal package import is
not possible. Importing this module (anywhere, once) prepends the foundation
path to sys.path; subsequent `from canonical import ...` calls then resolve.

Usage in every eval submodule that needs the schema:

    from eval import canonical_path  # noqa: F401  -- side-effect import
    from canonical import CanonicalInvoice, Money, Party  # etc.

When the backend service lands and canonical.py moves into a proper package
(e.g. `backend/angar/schema/canonical.py`), this shim becomes the single
file that needs updating across the eval harness.
"""

from __future__ import annotations

import pathlib
import sys

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
_FOUNDATION = _REPO_ROOT / "project foundation"

if not _FOUNDATION.is_dir():
    raise RuntimeError(
        f"Cannot locate canonical schema: expected '{_FOUNDATION}' to exist. "
        f"The eval harness must run from a checkout that includes the "
        f"`project foundation/` directory."
    )

_FOUNDATION_STR = str(_FOUNDATION)
if _FOUNDATION_STR not in sys.path:
    sys.path.insert(0, _FOUNDATION_STR)
