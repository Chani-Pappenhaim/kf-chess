class Controller:
    """Translates user clicks/jumps into game commands and owns the selected-cell
    state. It decides nothing about chess legality - it only turns pixels into
    cells (via BoardMapper) and drives the gateway's public command path.

    A command is sent and not waited on: what a click does to the selection is
    decided from the render model the view already holds, never from a reply.
    That is what lets the same controller drive a remote game, where a reply
    could not arrive in time to matter.

    Both collaborators are injected. Selection is deliberately kept here (not on
    the engine) so the engine stays a pure application service.

    `own_color` is the colour this player may pick up, or None for a local game
    where one person moves both. It only gates selection - a UI courtesy so you
    cannot lift the opponent's piece; the server, not this, is what actually
    refuses an out-of-turn move.

    `spectator` is a viewer who may pick up nothing at all. It is distinct from
    `own_color=None`: that means local play (any piece), whereas a viewer of a
    networked game must be locked out of every piece.
    """

    def __init__(self, engine, board_mapper, own_color=None, spectator=False):
        self._engine = engine
        self._mapper = board_mapper
        self._own_color = own_color
        self._spectator = spectator
        self._selected = None

    @property
    def selected(self):
        return self._selected

    @property
    def legal_targets(self):
        """Cells the currently-selected piece may move to - the move hints the
        view highlights next to the selection. Empty when nothing is selected.
        Derived from the selection (a UI concern) and kept here with it, so the
        engine stays a pure application service."""
        if self._selected is None:
            return ()
        return self._engine.legal_targets(self._selected)

    def click(self, x, y):
        cell = self._mapper.pixel_to_cell(x, y)
        if cell is None:
            # Outside the board: leave selection untouched (a no-op click).
            return

        model = self._engine.render_model()
        if self._selected is None:
            # First click selects a piece if that cell can be a move source.
            if self._can_select(model, cell):
                self._selected = cell
            return

        # Second click: send the move, then re-select or clear. Clicking another
        # of your own free pieces picks that one up instead; every other second
        # click clears the selection, whether the move was accepted or refused.
        # The selected piece is already this player's, so "same colour as the
        # selection" is also the ownership check - no need to repeat own_color.
        self._engine.request_move(self._selected, cell)
        own_free_piece = self._same_color_as_selection(model, cell) and model.selectable(cell)
        self._selected = cell if own_free_piece else None

    def jump(self, x, y):
        # A jump ends any pending selection first.
        self._selected = None
        cell = self._mapper.pixel_to_cell(x, y)
        if cell is None:
            return
        self._engine.request_jump(cell)

    def _can_select(self, model, cell):
        """Whether `cell` may be picked up: a free piece there, and - in a
        networked game - one of this player's own colour. A viewer picks up
        nothing."""
        if self._spectator:
            return False
        if not model.selectable(cell):
            return False
        if self._own_color is None:
            return True
        piece = model.piece_at(cell)
        return piece is not None and piece.token[0] == self._own_color

    def _same_color_as_selection(self, model, cell):
        """Whether `cell` holds a piece of the selected piece's own color. The
        selected piece can be gone by now - captured while it sat selected - so
        both squares are looked up rather than assumed occupied."""
        selected = model.piece_at(self._selected)
        target = model.piece_at(cell)
        if selected is None or target is None:
            return False
        return target.token[0] == selected.token[0]
