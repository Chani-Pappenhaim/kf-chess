"""Slice piece sprite sheets into the per-state / per-frame PNGs the game loads.

Drop one sprite sheet per piece into ``assets/sheets/``, named by its piece
code with a .png extension (e.g. ``PW.png`` for the white pawn). Each sheet is
a grid of ROWS x COLS cells:

    row    = animation state, top to bottom: idle, move, jump, long_rest, short_rest
    column = frame, left to right:           1, 2, 3, 4, 5

A 5x5 grid of 64x64 cells is a 320x320 sheet, but any evenly-divisible size
works - each cell is resized to CELL x CELL on the way out so the result always
matches the game's existing 64x64 sprites.

Run:  python slice_sprites.py            # slice every sheet in assets/sheets/
      python slice_sprites.py PW KB      # slice only these codes
      python slice_sprites.py --dry-run  # show what would be written, write nothing
"""
from __future__ import annotations

import os
import sys

from PIL import Image

# Grid layout of every sheet. Row order MUST match the state folders on disk.
STATE_ORDER = ["idle", "move", "jump", "long_rest", "short_rest"]
FRAMES_PER_STATE = 5
CELL = 64  # output tile size in pixels (matches the existing assets)

_HERE = os.path.dirname(os.path.abspath(__file__))
SHEETS_DIR = os.path.join(_HERE, "assets", "sheets")
PIECES_DIR = os.path.join(_HERE, "assets", "pieces")

# The 12 valid piece codes: type letter (K/Q/R/B/N/P) + color (W/B).
VALID_CODES = {
    t + c for t in ("K", "Q", "R", "B", "N", "P") for c in ("W", "B")
}


def slice_sheet(code: str, dry_run: bool = False) -> int:
    """Cut one sheet into its 25 frames. Returns the number of files written."""
    sheet_path = os.path.join(SHEETS_DIR, code + ".png")
    if not os.path.exists(sheet_path):
        print(f"  ! {code}: no sheet at {sheet_path} - skipped")
        return 0

    sheet = Image.open(sheet_path).convert("RGBA")
    rows, cols = len(STATE_ORDER), FRAMES_PER_STATE
    if sheet.width < cols or sheet.height < rows:
        print(
            f"  ! {code}: {sheet.width}x{sheet.height} is too small for a "
            f"{cols}x{rows} grid - skipped"
        )
        return 0

    # Integer-divide so any sheet size works; a few leftover edge pixels are
    # harmless because every tile is resized to CELL x CELL below anyway.
    cell_w, cell_h = sheet.width // cols, sheet.height // rows
    written = 0
    for row, state in enumerate(STATE_ORDER):
        out_dir = os.path.join(PIECES_DIR, code, "states", state, "sprites")
        for col in range(cols):
            box = (col * cell_w, row * cell_h, (col + 1) * cell_w, (row + 1) * cell_h)
            tile = sheet.crop(box)
            if tile.size != (CELL, CELL):
                # NEAREST keeps pixel-art edges crisp instead of blurring them.
                tile = tile.resize((CELL, CELL), Image.NEAREST)
            out_path = os.path.join(out_dir, f"{col + 1}.png")
            if dry_run:
                print(f"    would write {os.path.relpath(out_path, _HERE)}")
            else:
                os.makedirs(out_dir, exist_ok=True)
                tile.save(out_path)
            written += 1
    print(f"  + {code}: {written} frames -> assets/pieces/{code}/states/*/sprites/")
    return written


def main(argv: list[str]) -> int:
    dry_run = "--dry-run" in argv
    requested = [a.upper() for a in argv if not a.startswith("-")]

    if not os.path.isdir(SHEETS_DIR):
        os.makedirs(SHEETS_DIR, exist_ok=True)
        print(f"Created {SHEETS_DIR}. Drop your sheets there (PW.png, KB.png, ...).")
        return 0

    if requested:
        unknown = [c for c in requested if c not in VALID_CODES]
        if unknown:
            print(f"Unknown piece codes: {', '.join(unknown)}")
            print(f"Valid codes: {', '.join(sorted(VALID_CODES))}")
            return 1
        codes = requested
    else:
        codes = sorted(
            os.path.splitext(f)[0].upper()
            for f in os.listdir(SHEETS_DIR)
            if f.lower().endswith(".png")
            and os.path.splitext(f)[0].upper() in VALID_CODES
        )
        if not codes:
            print(f"No piece sheets found in {SHEETS_DIR}.")
            print(f"Add files named by piece code, e.g. PW.png, KB.png.")
            return 0

    print(("Dry run - " if dry_run else "") + f"slicing {len(codes)} sheet(s):")
    total = sum(slice_sheet(code, dry_run) for code in codes)
    print(f"Done: {total} frames {'planned' if dry_run else 'written'}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
