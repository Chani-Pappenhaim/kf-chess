from __future__ import annotations

from dataclasses import dataclass, replace

from realtime.models import Move, Jump, MotionView


@dataclass(frozen=True)
class ArrivalEvent:
    """What the arbiter reports back when a moving piece terminates a step.

    The arbiter mutates the board itself, but it does not decide the win
    condition - it only reports which token (if any) was captured, so the
    GameEngine can apply its injected WinCondition. `piece` is the token as
    placed at the destination (already promoted if a promotion applied),
    `origin` is the move's ORIGINAL source (notation "from" - the board has
    already cleared it), and `destination` is where the move actually stopped
    (which may be short of the requested target if it was blocked in flight).
    """

    piece: str
    origin: tuple
    destination: tuple
    captured: str | None


class RealTimeArbiter:
    """Owns all real-time motion: active Moves/Jumps, the simulated clock,
    per-cell step timing, and step/settlement/interception resolution.

    It is a PURE STEPPING MECHANISM. It walks a precomputed ``path`` (built by
    the rules layer and handed in via ``start_move``) one cell per step, and
    obeys a single ``may_capture_final`` flag; it never imports or queries the
    rules layer, so it can be tested against a bare fake board. All piece
    knowledge (who may capture how, what the geometry is) stays upstream.

    Kept separate from GameEngine so the real-time model can be tested in
    isolation, and so Board keeps representing only logical occupancy while
    in-flight motion state lives here. Time never advances from the wall clock:
    it only moves when `advance_time` is called with a delta.

    Promotion happens on arrival, so the promotion rule is injected here (into
    the layer that owns arrival), not into the engine.
    """

    def __init__(self, board, promotion_rule, config):
        self._board = board
        self._promotion_rule = promotion_rule
        self._config = config
        self._clock = 0
        self._active_moves = []
        self._active_jumps = []
        self._cooldowns = {}  # cell -> (rest_state, start_clock, expiry_clock)

    @property
    def clock(self):
        return self._clock

    def has_active_motion(self):
        return bool(self._active_moves)

    def is_moving_from(self, cell):
        """Keyed off each move's CURRENT cell (where the piece now sits), so
        busy-checks and the renderer find the piece at its live position rather
        than at the source it has already stepped off."""
        return any(move.current == cell for move in self._active_moves)

    def is_jumping_on(self, cell):
        return any(jump.cell == cell for jump in self._active_jumps)

    def jump_progress(self, cell):
        """How far a jumping piece is through its hop (0.0 at take-off, 1.0 on
        landing), or None if nothing is airborne on `cell`. Lets the view lift
        the piece along an arc so the jump is visible."""
        total = self._config.JUMP_DURATION
        for jump in self._active_jumps:
            if jump.cell == cell:
                if total <= 0:
                    return 1.0
                elapsed = total - (jump.end_time - self._clock)
                return max(0.0, min(1.0, elapsed / total))
        return None

    def cooldown_of(self, cell):
        """The rest state a piece on `cell` is in ('short_rest' after a jump,
        'long_rest' after a move), or None if it is free to act. Checks the
        expiry against the current clock, so an elapsed cooldown reads as None
        even before resolve() prunes it."""
        entry = self._cooldowns.get(cell)
        if entry is None:
            return None
        rest_state, _start, expiry = entry
        return None if self._clock >= expiry else rest_state

    def cooldown_progress(self, cell):
        """How far a resting piece is through its cooldown: 0.0 the instant the
        rest begins, rising to 1.0 as it ends (None once free to act again).
        Lets the view drain the rest veil from the top down as time elapses.

        A live entry always satisfies ``start <= clock < expiry`` - resolve()
        prunes an entry the moment its expiry passes (and a zero-length rest is
        pruned before it is ever observed) - so the ratio is a well-defined
        0..1 with no elapsed-or-degenerate-duration guard needed here."""
        entry = self._cooldowns.get(cell)
        if entry is None:
            return None
        _rest_state, start, expiry = entry
        return max(0.0, min(1.0, (self._clock - start) / (expiry - start)))

    def is_resting(self, cell):
        return self.cooldown_of(cell) is not None

    def active_motions(self):
        """Read-only views of the in-flight moves, each with its progress (0..1)
        through its CURRENT sub-step - for the renderer to interpolate a piece
        sliding from its current cell to the next."""
        return [self._motion_view(move) for move in self._active_moves]

    def _motion_view(self, move):
        step = self._move_total(move.current, move.next_cell)
        travelled = step - (move.arrival - self._clock)
        progress = 1.0 if step <= 0 else max(0.0, min(1.0, travelled / step))
        return MotionView(move.piece, move.current, move.next_cell, progress)

    def start_move(self, piece, source, path, may_capture_final):
        """Begin stepping ``piece`` from ``source`` along ``path`` (which
        EXCLUDES source and ENDS at the final cell). ``may_capture_final`` says
        whether an enemy sitting on the final cell may be captured. The first
        step's arrival is scheduled off the current clock; every later step is
        scheduled off the previous step's arrival (see ``resolve``), so there is
        no clock drift over a multi-cell slide."""
        path = tuple(path)
        arrival = self._clock + self._move_total(source, path[0])
        self._active_moves.append(
            Move(piece, source, path, 0, may_capture_final, arrival)
        )

    def start_jump(self, piece, cell):
        self._active_jumps.append(Jump(piece, cell, self._clock + self._config.JUMP_DURATION))

    def advance_time(self, dt):
        """Advance simulated time and resolve whatever became due."""
        self._clock += dt
        return self.resolve()

    def resolve(self):
        """Advance every move that has become due, one cell at a time.

        A single ``advance_time`` may cross several step boundaries, and several
        moves may be in flight, so this loops: it repeatedly picks the due move
        (arrival <= clock) with the SMALLEST arrival - tie-broken by insertion
        order in ``_active_moves`` (whoever started first) - advances it exactly
        ONE step, and recomputes. It never drains one move fully before the next,
        so cross-traffic contention for a cell resolves deterministically:
        whoever reaches the cell earlier (or, on a tie, started earlier) claims
        it, and the other sees it occupied and stops.
        """
        events = []
        while True:
            due = [
                (order, move)
                for order, move in enumerate(self._active_moves)
                if self._clock >= move.arrival
            ]
            if not due:
                break
            order, move = min(due, key=lambda pair: (pair[1].arrival, pair[0]))
            next_move, event = self._step_move(move)
            if event is not None:
                events.append(event)
            if next_move is None:
                self._active_moves.pop(order)
            else:
                self._active_moves[order] = next_move
        self._resolve_jumps()
        self._prune_cooldowns()
        return events

    # -- internal helpers -------------------------------------------------

    def _move_total(self, start, end):
        """Time to travel from `start` to the adjacent-or-leaped `end`:
        MOVE_DURATION per square of Chebyshev distance. Consecutive path cells
        are adjacent (1x); a knight's atomic ``(end,)`` L-jump has Chebyshev
        distance 2 (2x) - so leapers cost the right time with NO knight
        special-case anywhere in the stepping code."""
        distance = max(abs(end[0] - start[0]), abs(end[1] - start[1]))
        return distance * self._config.MOVE_DURATION

    def _step_move(self, move):
        """Advance ``move`` by EXACTLY ONE cell and report what happened.

        Returns ``(next_move, event)``: ``next_move`` is the move's new state if
        it keeps stepping, or None if it terminated (settled, intercepted, or
        dropped); ``event`` is the ArrivalEvent to emit, or None. Only terminal
        outcomes go through ``_settle`` - a plain per-cell commit reserves
        nothing.
        """
        current = move.current
        target = move.next_cell
        token = self._board.get(*target)
        empty = self._config.EMPTY_CELL

        # N empty: commit the step. If it was the final cell, settle there.
        if token == empty:
            self._board.relocate(current, target)
            if target == move.final:
                return None, self._settle(move, target, None)
            return self._advanced(move), None

        # N same colour: stop. Settle on the current cell iff we ever advanced;
        # a move blocked at its very first step leaves no trace at all.
        if token[0] == move.piece[0]:
            if move.advanced():
                return None, self._settle(move, current, None)
            return None, None

        # N enemy. Interception (destination-only) is tested BEFORE the capture
        # branch, because a jumper on the FINAL cell captures the mover instead
        # of being captured by it - the opposite outcome.
        if target == move.final:
            interceptor = self._jumper_on(target, move.piece)
            if interceptor is not None:
                # The mover is captured on its CURRENT cell (not its long-gone
                # source); the jumper stays put and is credited with the kill.
                self._board.set(*current, empty)
                return None, ArrivalEvent(
                    piece=interceptor.piece,
                    origin=interceptor.cell,
                    destination=interceptor.cell,
                    captured=move.piece,
                )
            if move.may_capture_final:
                self._board.relocate(current, target)
                return None, self._settle(move, target, token)

        # Mid-path enemy, or a final enemy this piece may not capture (e.g. a
        # pawn moving straight): stop short. Same settle-iff-advanced rule.
        if move.advanced():
            return None, self._settle(move, current, None)
        return None, None

    def _advanced(self, move):
        """The move's next state after committing one empty cell: index bumped,
        and the following step's arrival scheduled off THIS step's arrival (not
        the live clock) so a long slide accumulates no drift."""
        new_index = move.index + 1
        new_current = move.path[new_index - 1]
        next_cell = move.path[new_index]
        arrival = move.arrival + self._move_total(new_current, next_cell)
        return replace(move, index=new_index, arrival=arrival)

    def _settle(self, move, cell, captured):
        """Terminal landing on ``cell``: apply the injected promotion rule at
        the cell's row, begin the long_rest cooldown, and emit the ArrivalEvent.
        The piece is already physically on ``cell`` (a prior relocate put it
        there); this only rewrites the token if it promoted. ``origin`` is the
        move's original source; ``destination`` is where it actually stopped."""
        row, col = cell
        piece = self._promotion_rule.promote(move.piece, row, self._board.height)
        self._board.set(row, col, piece)
        self._begin_cooldown(cell, "long_rest", self._config.LONG_REST_DURATION)
        return ArrivalEvent(piece=piece, origin=move.source, destination=cell, captured=captured)

    def _jumper_on(self, cell, mover_piece):
        """An opposing jumping piece sitting on ``cell`` (the move's final cell),
        if any - it intercepts and captures the mover on arrival. Interception is
        destination-only: a jumper on an intermediate cell is just a blocker."""
        for jump in self._active_jumps:
            if jump.cell == cell and jump.piece[0] != mover_piece[0]:
                return jump
        return None

    def _resolve_jumps(self):
        airborne = []
        for jump in self._active_jumps:
            if self._clock < jump.end_time:
                airborne.append(jump)
            else:
                # A completed jump settles into a short rest on its cell.
                self._begin_cooldown(jump.cell, "short_rest", self._config.SHORT_REST_DURATION)
        self._active_jumps = airborne

    def _begin_cooldown(self, cell, rest_state, duration):
        self._cooldowns[cell] = (rest_state, self._clock, self._clock + duration)

    def _prune_cooldowns(self):
        self._cooldowns = {
            cell: entry
            for cell, entry in self._cooldowns.items()
            if self._clock < entry[2]  # entry[2] is the expiry clock
        }
