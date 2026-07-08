"""utils/ — Re-export from core.utils for flat import compatibility.

The structured repo has core/utils.py with shared utilities. Some modules
import via `from utils import ...`. This __init__.py re-exports everything
from core.utils so both import paths work.
"""
import sys
import os

# Ensure core/ is on sys.path so we can import core.utils
_core = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "core")
if _core not in sys.path:
    sys.path.insert(0, _core)

from core.utils import *  # noqa: F401,F403,E402
from core.utils import sampling_kwargs, format_code_block, wrap_text  # noqa: F401,E402
