import sys
from pathlib import Path

# Ensure backend/ (project backend dir) is on sys.path so we can import main.py
_here = Path(__file__).resolve().parent
_backend_root = _here.parent
if str(_backend_root) not in sys.path:
    sys.path.insert(0, str(_backend_root))

try:
    # main.py defines FastAPI app as `app`
    from main import app  # type: ignore
except Exception:
    # Fallback: try importing as package
    try:
        from . import main as _m  # type: ignore
        app = getattr(_m, "app", None)
    except Exception:
        app = None


