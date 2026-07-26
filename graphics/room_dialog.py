"""The Room dialog: a small native window to create or join a room by id.

cv2 draws no text box, so the one place a player types - which room - uses a
tkinter dialog instead, a thin shell like graphics.Window around cv2. It offers
Create, Join, and Cancel; the pure outcome (which button, and any id typed) is
all it hands back, for the caller to turn into a message. Nothing here decides
what a room is or talks to the server.
"""
from __future__ import annotations


def ask_room(config):  # pragma: no cover - native dialog, exercised only at runtime
    """Open the dialog and return (action, room_id): action is "create",
    "join", or None (cancelled); room_id is what was typed (blank for create)."""
    import tkinter as tk

    chosen = {"action": None, "room_id": ""}
    root = tk.Tk()
    root.title(config.ROOM_DIALOG_TITLE)

    tk.Label(root, text=config.ROOM_DIALOG_PROMPT).pack(padx=12, pady=(12, 4))
    entry = tk.Entry(root)
    entry.pack(padx=12, pady=4)
    entry.focus_set()

    def choose(action):
        chosen["action"] = action
        chosen["room_id"] = entry.get().strip()
        root.destroy()

    buttons = tk.Frame(root)
    buttons.pack(padx=12, pady=12)
    tk.Button(buttons, text=config.ROOM_DIALOG_CREATE,
              command=lambda: choose("create")).pack(side=tk.LEFT, padx=4)
    tk.Button(buttons, text=config.ROOM_DIALOG_JOIN,
              command=lambda: choose("join")).pack(side=tk.LEFT, padx=4)
    tk.Button(buttons, text=config.ROOM_DIALOG_CANCEL,
              command=lambda: choose(None)).pack(side=tk.LEFT, padx=4)

    root.mainloop()
    return chosen["action"], chosen["room_id"]
