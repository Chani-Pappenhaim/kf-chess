"""AudioPlayer - plays a sound file without blocking, via the OS.

The single place the winsound dependency lives, mirroring how cv2 stays inside
the graphics layer. Playback is asynchronous so the frame loop never stalls, and
a missing or unplayable file is ignored so absent sound assets never crash the
game.
"""
from __future__ import annotations

import winsound


class AudioPlayer:  # pragma: no cover - thin OS shell, exercised only at runtime
    def play(self, path):
        try:
            winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
        except RuntimeError:
            pass
