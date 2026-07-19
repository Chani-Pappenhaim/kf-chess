from game.models import MoveResult
from rules.reasons import Reason
from view.snapshot import GameSnapshot
from view.render_model import RenderModel, RenderPiece


class GameEngine:
    """Application-service coordinator and public command boundary.

    It owns none of the details it coordinates: legality lives in RuleEngine,
    real-time motion in RealTimeArbiter, the win rule in an injected
    WinCondition, and selection/pixel handling in the Controller. The engine
    only sequences them - applying application-level guards (game over, one
    motion at a time), delegating validation, starting validated motions,
    advancing time, and exposing a read-only snapshot.

    What should HAPPEN when a move completes is not its business either: it
    announces each event to its observers (see game/observers.py) without
    knowing who they are. `move_log` and `scoreboard` are still held here, but
    only as read handles for the view - the observers are what write to them.

    All collaborators are injected through the constructor - no module-level
    state, no hidden globals - so the engine is straightforward to unit test
    with fakes/stubs instead of monkeypatching.
    """

    def __init__(self, board, rule_engine, arbiter, win_condition, config,
                 move_log, scoreboard, observers=()):
        self._board = board
        self._rule_engine = rule_engine
        self._arbiter = arbiter
        self._win_condition = win_condition
        self._config = config
        self._move_log = move_log
        self._scoreboard = scoreboard
        self._observers = list(observers)
        self._game_over = False

    def subscribe(self, observer):
        """Register a GameObserver to receive events from here on."""
        self._observers.append(observer)

    @property
    def game_over(self):
        return self._game_over

    @property
    def move_log(self):
        """Read-only handle on the recorded moves (for the read model / view)."""
        return self._move_log

    @property
    def scoreboard(self):
        """Read-only handle on the running score (for the read model / view)."""
        return self._scoreboard

    @property
    def clock(self):
        return self._arbiter.clock

    def is_busy(self, cell):
        return self._arbiter.is_moving_from(cell) or self._arbiter.is_jumping_on(cell)

    def can_select(self, cell):
        """Whether `cell` can be picked as a move source right now."""
        self._apply_events(self._arbiter.resolve())
        if self._game_over:
            return False
        return (
            not self.is_busy(cell)
            and not self._arbiter.is_resting(cell)
            and not self._board.is_empty(*cell)
        )

    def legal_targets(self, cell):
        """Cells the piece on `cell` may currently move to, for the UI's move
        hints. A read-only query on the public command boundary: it delegates
        legality to the RuleEngine and returns nothing once the game is over."""
        if self._game_over:
            return ()
        return self._rule_engine.legal_targets(self._board, cell)

    def request_move(self, start, end):
        self._apply_events(self._arbiter.resolve())
        if self._game_over:
            return MoveResult(False, Reason.GAME_OVER)
        if self.is_busy(start):
            return MoveResult(False, Reason.BUSY_SOURCE)
        if self._arbiter.is_resting(start):
            return MoveResult(False, Reason.RESTING)

        validation = self._rule_engine.validate_move(self._board, start, end)
        if not validation.is_valid:
            return MoveResult(False, validation.reason)

        # Real-time policy: by default (ALLOW_CONCURRENT_MOVES) any number of
        # moves may be in flight at once, so both players act simultaneously and
        # one player may start further moves while an earlier one travels - each
        # piece is gated only by its own busy/resting state, checked above. Set
        # the flag False for the strict variant, where a single move is allowed
        # at a time and whoever started first wins a contested route.
        if not self._config.ALLOW_CONCURRENT_MOVES and self._arbiter.has_active_motion():
            return MoveResult(False, Reason.MOTION_IN_PROGRESS)

        # Turn the validated request into a stepping recipe (path + whether a
        # capture on the final cell is legal) via the rules layer, then hand it
        # to the arbiter. The arbiter walks the plan cell by cell and never
        # consults the rules layer itself - all piece knowledge stays here.
        plan = self._rule_engine.build_plan(self._board, start, end)
        self._arbiter.start_move(
            self._board.get(*start), start, plan.path, plan.may_capture_final
        )
        return MoveResult(True, Reason.OK)

    def request_jump(self, cell):
        self._apply_events(self._arbiter.resolve())
        if self._game_over:
            return MoveResult(False, Reason.GAME_OVER)
        if self.is_busy(cell):
            return MoveResult(False, Reason.BUSY_CELL)
        if self._arbiter.is_resting(cell):
            return MoveResult(False, Reason.RESTING)
        if self._board.is_empty(*cell):
            return MoveResult(False, Reason.EMPTY_CELL)

        self._arbiter.start_jump(self._board.get(*cell), cell)
        return MoveResult(True, Reason.OK)

    def wait(self, dt):
        self._apply_events(self._arbiter.advance_time(dt))

    def snapshot(self):
        return GameSnapshot.from_board(self._board, self._game_over)

    def render_model(self):
        """Rich read model for the graphical UI: every piece with its
        animation/domain state. This is the authoritative view a networked
        server would serialise; the client only draws it."""
        motions = {motion.start: motion for motion in self._arbiter.active_motions()}
        pieces = tuple(
            self._render_piece(self._board.get(r, c), (r, c), motions)
            for r in range(self._board.height)
            for c in range(self._board.width)
            if not self._board.is_empty(r, c)
        )
        return RenderModel(
            pieces=pieces,
            width=self._board.width,
            height=self._board.height,
            game_over=self._game_over,
            clock=self._arbiter.clock,
            moves=self._move_log.entries(),
            scores=self._scoreboard.as_dict(),
        )

    def _render_piece(self, token, cell, motions):
        # An in-flight piece still sits on its source cell on the board; render
        # it sliding towards its destination. A jumping piece stays put but plays
        # its jump animation. Otherwise the piece is idle.
        motion = motions.get(cell)
        if motion is not None:
            return RenderPiece(
                token=token,
                cell=motion.end,
                state="move",
                origin=cell,
                progress=motion.progress,
            )
        if self._arbiter.is_jumping_on(cell):
            return RenderPiece(
                token=token,
                cell=cell,
                state="jump",
                progress=self._arbiter.jump_progress(cell) or 0.0,
            )
        rest_state = self._arbiter.cooldown_of(cell)
        if rest_state is not None:
            return RenderPiece(
                token=token,
                cell=cell,
                state=rest_state,
                cooldown_progress=self._arbiter.cooldown_progress(cell) or 0.0,
            )
        return RenderPiece(token=token, cell=cell)

    def render(self, renderer):
        self._apply_events(self._arbiter.resolve())
        return renderer.render(self.snapshot())

    # -- internal helpers -------------------------------------------------

    def _apply_events(self, events):
        """React to arrivals reported by the arbiter.

        Anything that merely records what happened (the move log, the score, a
        future broadcast to remote clients) is an observer's job, so the engine
        just announces. Game over stays here: it is not a side effect but a
        guard the engine itself enforces on every later command.
        """
        for event in events:
            for observer in self._observers:
                observer.on_event(event)
            if self._win_condition.is_game_over(event.captured):
                self._game_over = True
