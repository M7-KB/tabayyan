"""Put the repository root on sys.path so tests can import the eval package.

api and corpus are installed by `pip install -e .`; the eval harness is a
development tool and is not part of the installed distribution.
"""

import sys
from pathlib import Path

ROOT = str(Path(__file__).resolve().parent)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
