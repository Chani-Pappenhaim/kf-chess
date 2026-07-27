"""Hud - the board "chrome": everything drawn around the board itself.

A view component like GraphicsRenderer: it reads the render model and draws onto
the canvas through Img, touching neither the engine nor cv2. It owns the title
strip ("Name: ..."), the per-side score strips (from the model's scores), the
a-h / 1-8 coordinate labels in the gutter around the board, and the game-over
banner - and it composes two MoveTablePanels (Black on the left, White on the
right) so the move-list drawing lives in one reusable place. The board and its
pieces are drawn separately by GraphicsRenderer; the Hud only frames them.

What the banner says and how long it lasts belongs to the BannerAnimation it is
handed; the Hud only asks what to draw at the current clock.
"""
from __future__ import annotations

from graphics.assets import solid
from ui.move_table_panel import MoveTablePanel

_TEXT = (35, 35, 35, 255)          # near-black title / score / label text (BGRA)
_BANNER_BG = (0, 0, 0, 180)        # translucent black
_BANNER_TEXT = (0, 0, 255, 255)    # red
_APPROX_CHAR_PX = 10               # rough per-character width, for centering text
_BANNER_CHAR_PX = 46               # the same, at the banner's larger text scale


class Hud:
    def __init__(self, config, banner, own_color=None, room_id=None, spectator=False):
        self._config = config
        self._bx = config.BOARD_ORIGIN_X
        self._by = config.BOARD_ORIGIN_Y
        self._cell = config.CELL_SIZE
        self._board_px = config.BOARD_PX
        self._gutter = config.COORD_GUTTER
        self._title = config.WINDOW_TITLE
        self._own_color = own_color  # which side is this player's; None in local play
        self._room_id = room_id      # shown on top; None in local play
        self._spectator = spectator  # this screen only watches; marked beside the room id
        self._rating_label = config.RATING_LABEL
        self._you_marker = config.YOU_MARKER
        self._title_baseline = config.TITLE_HEIGHT - 16
        self._top_score_baseline = config.TITLE_HEIGHT + config.SCORE_HEIGHT - 12
        self._bottom_score_baseline = (
            self._by + self._board_px + self._gutter + config.SCORE_HEIGHT - 12
        )
        self._banner = solid(self._board_px, 90, _BANNER_BG)
        self._animation = banner
        # Black is at the top of the board (left panel); White at the bottom (right).
        self._black_panel = MoveTablePanel(
            "Black", "b", 10, self._by, config.PANEL_WIDTH - 20, self._board_px
        )
        self._white_panel = MoveTablePanel(
            "White", "w", self._bx + self._board_px + self._gutter + 10, self._by,
            config.PANEL_WIDTH - 20, self._board_px,
        )

    def draw(self, canvas, model):
        self._draw_title(canvas)
        self._draw_room_id(canvas)
        self._draw_scores(canvas, model)
        self._draw_coordinates(canvas, model)
        self._draw_viewers(canvas, model)
        self._black_panel.draw(canvas, model)
        self._white_panel.draw(canvas, model)
        self._draw_countdown(canvas, model)
        self._draw_banner(canvas, model.clock)

    def _draw_room_id(self, canvas):
        # The room id, written on top of the screen, so players know which room
        # to tell each other to join. Absent in local play.
        if self._room_id is None:
            return
        text = self._config.ROOM_ID_LABEL.format(room_id=self._room_id)
        # A viewer's own screen says so, next to the room id, since the state
        # names the players but never marks the watcher as one.
        if self._spectator:
            text = f"{text}  {self._config.SPECTATOR_LABEL}"
        canvas.put_text(text, 12, self._title_baseline, 0.7, _TEXT, 2)

    def _draw_countdown(self, canvas, model):
        # While a disconnected player's grace runs down, the one who stayed sees
        # the seconds left before the game resigns in the other's name.
        if model.countdown is None:
            return
        text = self._config.DISCONNECT_NOTICE.format(seconds=model.countdown)
        canvas.put_text(text, self._centered(text, 14), self._by + 40, 0.9, _BANNER_TEXT, 2)

    def _draw_viewers(self, canvas, model):
        # Who is watching this room, listed under the board.
        if not model.viewers:
            return
        text = self._config.VIEWERS_LABEL.format(names=", ".join(model.viewers))
        canvas.put_text(text, 12, self._by + self._board_px + 40, 0.6, _TEXT, 1)

    def _draw_title(self, canvas):
        canvas.put_text(
            self._title, self._centered(self._title), self._title_baseline, 0.8, _TEXT, 2
        )

    def _draw_scores(self, canvas, model):
        # Each player's name and score sit on their side of the board: Black
        # above, White below. The name is blank until a player has that colour
        # (empty in local play, and for a colour nobody has joined as yet).
        black = self._name_and_score("b", model)
        white = self._name_and_score("w", model)
        canvas.put_text(black, self._centered(black), self._top_score_baseline, 0.9, _TEXT, 2)
        canvas.put_text(white, self._centered(white), self._bottom_score_baseline, 0.9, _TEXT, 2)

    def _name_and_score(self, color, model):
        # "dana  Rating 1516  Score: 5" networked; "Score: 5" alone in a local
        # game, where there is no player account and so no name or rating. The
        # player's own strip is tagged so a glance tells which side is theirs.
        name = model.players.get(color, "")
        rating = model.ratings.get(color)
        who = (
            f"{name}  {self._rating_label} {rating}  "
            if name and rating is not None
            else (f"{name}  " if name else "")
        )
        line = f"{who}Score: {model.scores.get(color, 0)}"
        return line + self._you_marker if color == self._own_color else line

    def _draw_coordinates(self, canvas, model):
        """The a-h files above and below the board, and the ranks down each side
        (row 0 is the top rank = model.height, matching the coordinate notation)."""
        for col in range(model.width):
            file = chr(ord("a") + col)
            x = self._bx + col * self._cell + self._cell // 2 - 5
            canvas.put_text(file, x, self._by - 8, 0.6, _TEXT, 1)
            canvas.put_text(file, x, self._by + self._board_px + 20, 0.6, _TEXT, 1)
        for row in range(model.height):
            rank = str(model.height - row)
            y = self._by + row * self._cell + self._cell // 2 + 6
            canvas.put_text(rank, self._bx - 20, y, 0.6, _TEXT, 1)
            canvas.put_text(rank, self._bx + self._board_px + 10, y, 0.6, _TEXT, 1)

    def _draw_banner(self, canvas, clock):
        text = self._animation.text_at(clock)
        if text is None:
            return
        self._banner.draw_on(canvas, self._bx, self._by + self._board_px // 2 - 45)
        canvas.put_text(text, self._centered(text, _BANNER_CHAR_PX),
                        self._by + self._board_px // 2 + 15, 2.0, _BANNER_TEXT, 4)

    def _centered(self, text, char_px=_APPROX_CHAR_PX):
        """Approximate x so `text` is roughly centered over the board (Img exposes
        no text-measuring, so this estimates the width from the character count).
        `char_px` is the per-character width at the scale the text is drawn."""
        return self._bx + self._board_px // 2 - len(text) * char_px // 2
