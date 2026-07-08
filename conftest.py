"""conftest.py — Make flat imports work with structured repo layout.

The upstream repo organizes modules into subdirectories (core/, api/,
agents/, utils/) but the test suite uses flat imports (e.g.,
`from claude_thinking import ...`). This conftest adds all subdirectories
to sys.path so flat imports resolve correctly.
"""
import sys
import os

# Add all package subdirectories to sys.path for flat imports
_root = os.path.dirname(__file__)
for subdir in ("core", "api", "agents", "utils"):
    path = os.path.join(_root, subdir)
    if os.path.isdir(path) and path not in sys.path:
        sys.path.insert(0, path)

# Also add root for main.py, artifacts.py, etc.
if _root not in sys.path:
    sys.path.insert(0, _root)
