"""Shared pytest config — keeps unit tests independent of dora / dora-nav installs."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
