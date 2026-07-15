"""Window - the cv2 window + input adapter.

One of the graphics/ modules that import cv2 (alongside Img and the asset
loader). Drawing never happens here: a
fully composed canvas Img is handed to show(). Presentation and input sit in
one class because cv2 binds them to a single window handle - waitKey both
refreshes the imshow buffer and returns keystrokes, and the mouse callback is
registered per window - so splitting them would only share that handle around.

Raw device events are returned as small tuples for the input layer to
translate; Window itself decides no game semantics:
    ("left",   x, y)   left mouse button pressed at pixel (x, y)
    ("double", x, y)   left mouse button double-clicked
    ("quit",)          ESC / q pressed, or the window was closed
"""
from __future__ import annotations

import cv2  # noqa: F401 - the sole window/input dependency; drawing stays in Img

_QUIT_KEYS = {27, ord("q")}  # ESC or 'q'


class Window:  # pragma: no cover - thin GUI shell, exercised only at runtime
    def __init__(self, title, poll_delay_ms=1):
        self._title = title
        self._poll_delay = poll_delay_ms
        self._pending = []
        self._closed = False
        cv2.namedWindow(title, cv2.WINDOW_AUTOSIZE)
        cv2.setMouseCallback(title, self._on_mouse)

    def _on_mouse(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDBLCLK:
            self._pending.append(("double", x, y))
        elif event == cv2.EVENT_LBUTTONDOWN:
            self._pending.append(("left", x, y))

    def show(self, canvas):
        """Present a fully composed canvas Img in the window."""
        cv2.imshow(self._title, canvas.img)

    def poll_events(self):
        """Pump the window (refresh + gather input) and return raw events."""
        events = self._pending
        self._pending = []
        key = cv2.waitKey(self._poll_delay) & 0xFF
        if key in _QUIT_KEYS:
            events.append(("quit",))
        elif cv2.getWindowProperty(self._title, cv2.WND_PROP_VISIBLE) < 1:
            events.append(("quit",))
        return events

    def close(self):
        if not self._closed:
            cv2.destroyWindow(self._title)
            self._closed = True
