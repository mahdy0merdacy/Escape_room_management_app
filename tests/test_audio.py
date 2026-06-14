"""Headless smoke test for erm.audio sound generation. Run with plain python3."""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from erm import audio


def main():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "alert.wav"
        assert not path.exists()
        audio.ensure_alert_sound(path)
        assert path.exists()
        assert path.stat().st_size > 0
        # Idempotent - shouldn't error or rewrite if called again
        size = path.stat().st_size
        audio.ensure_alert_sound(path)
        assert path.stat().st_size == size

    print("audio.py smoke test: OK")


if __name__ == "__main__":
    main()
