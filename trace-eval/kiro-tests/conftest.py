"""Put trace-eval/ on the import path, so `traceeval` and the demo modules import from here as from the root."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
