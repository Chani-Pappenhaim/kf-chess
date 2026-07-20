from __future__ import annotations

from dataclasses import dataclass, replace

from realtime.models import Move, Jump, MotionView


@dataclass(frozen=True)
class ArrivalEvent:
    """A move that has ended, by settling on a cell or by being captured."""

    piece: str            # the token as placed, already promoted if it promoted
    origin: tuple         # where the move began; the board has since cleared it
    destination: tuple    # where it actually stopped, which may be short of the target
    captured: str | None  # the token taken, if any
    at_ms: int = 0        # clock time it happened


class RealTimeArbiter:
    """Simulates the passage of time and resolves moves, jumps, and cooldowns."""

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

    def is_mover_on(self, cell):
        """Whether a piece in flight is currently sitting on ``cell``.

        Keyed off where the piece is now, not where it started, so a source it
        has already stepped off reads as free.
        """
        return any(move.current == cell for move in self._active_moves)

    def is_jumping_on(self, cell):
        return any(jump.cell == cell for jump in self._active_jumps)

    def jump_progress(self, cell):
        """How far a jumping piece is through its jump: 0.0 the instant it leaves the cell, 
        rising to 1.0 as it lands (None if no jump is in progress)."""
        total = self._config.JUMP_DURATION
        for jump in self._active_jumps:
            if jump.cell == cell:
                if total <= 0:
                    return 1.0
                elapsed = total - (jump.end_time - self._clock)
                return max(0.0, min(1.0, elapsed / total))
        return None

    def cooldown_of(self, cell):
        """The rest state of a piece on ``cell``, if it is currently resting (None if free to act)."""
        entry = self._cooldowns.get(cell)
        if entry is None:
            return None
        rest_state, _start, expiry = entry
        return None if self._clock >= expiry else rest_state

    def cooldown_progress(self, cell):
        """How far a resting piece is through its cooldown: 0.0 the instant it begins resting,
        rising to 1.0 as it becomes free to act (None if no cooldown is in progress"""
        entry = self._cooldowns.get(cell)
        if entry is None:
            return None
        _rest_state, start, expiry = entry
        return max(0.0, min(1.0, (self._clock - start) / (expiry - start)))

    def is_resting(self, cell):
        return self.cooldown_of(cell) is not None

    def active_motions(self):
        """ The current one-cell step of every piece in flight, for the view to interpolate.
        Motion is resolved per cell, so this describes the step in progress,
         not the whole move: the renderer slides the piece from `start` to `end` by `progress`."""
        return [self._motion_view(move) for move in self._active_moves]

    def _motion_view(self, move):
        step = self._move_total(move.current, move.next_cell)
        travelled = step - (move.arrival - self._clock)
        progress = 1.0 if step <= 0 else max(0.0, min(1.0, travelled / step))
        return MotionView(move.piece, move.current, move.next_cell, progress)

    def start_move(self, piece, source, path, may_capture_final):
        """Begin stepping ``piece`` from ``source`` along ``path``.

        Nothing moves yet: the piece stays on ``source`` until the first step
        falls due. ``may_capture_final`` false means it stops short of an enemy
        on the last cell instead of taking it.
        """
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

        Always takes the earliest due step next, tie-broken by who started
        first, rather than draining one move before the next. Two pieces racing
        for the same cell therefore resolve the same way every run.
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
        """Time to travel from `start` to `end`: MOVE_DURATION per square of
        Chebyshev distance. A one-cell step costs one; a leap costs its span, so
        leapers are timed right without being special-cased."""
        distance = max(abs(end[0] - start[0]), abs(end[1] - start[1]))
        return distance * self._config.MOVE_DURATION

    def _step_move(self, move):
        """Advance ``move`` by exactly one cell.

        Returns (next_move, event): next_move is None once the move has ended,
        event is the ArrivalEvent to report, or None.
        """
        current = move.current
        target = move.next_cell
        token = self._board.get(*target)
        empty = self._config.EMPTY_CELL

        # Empty: commit the step, and settle if that was the last cell.
        if token == empty:
            self._board.relocate(current, target)
            if target == move.final:
                return None, self._settle(move, target, None)
            return self._stepped(move), None

        # Own piece ahead: stop where we are. A move blocked before it ever
        # moved leaves no trace - no arrival, no cooldown.
        if token[0] == move.piece[0]:
            if move.advanced():
                return None, self._settle(move, current, None)
            return None, None

        # Enemy on the destination. Interception is checked first: an airborne
        # defender captures the mover rather than the other way round.
        if target == move.final:
            interceptor = self._jumper_on(target, move.piece)
            if interceptor is not None:
                # The mover dies where it stands; the jumper stays put.
                self._board.set(*current, empty)
                return None, ArrivalEvent(
                    piece=interceptor.piece,
                    origin=interceptor.cell,
                    destination=interceptor.cell,
                    captured=move.piece,
                    at_ms=self._clock,
                )
            if move.may_capture_final:
                self._board.relocate(current, target)
                return None, self._settle(move, target, token)

        # Enemy mid-path, or one on the destination this piece may not take:
        # stop short.
        if move.advanced():
            return None, self._settle(move, current, None)
        return None, None

    def _stepped(self, move):
        """The move's next state after committing one empty cell.

        The following step is scheduled off THIS step's arrival rather than the
        live clock, so a long slide accumulates no drift.
        """
        new_index = move.index + 1
        new_current = move.path[new_index - 1]
        next_cell = move.path[new_index]
        arrival = move.arrival + self._move_total(new_current, next_cell)
        return replace(move, index=new_index, arrival=arrival)

    def _settle(self, move, cell, captured):
        """End the move on ``cell``: apply promotion, start the long rest, and
        report the arrival. The piece is already there; this only rewrites the
        token if it promoted."""
        row, col = cell
        piece = self._promotion_rule.promote(move.piece, row, self._board.height)
        self._board.set(row, col, piece)
        self._begin_cooldown(cell, self._config.LONG_REST_STATE, self._config.LONG_REST_DURATION)
        return ArrivalEvent(
            piece=piece,
            origin=move.source,
            destination=cell,
            captured=captured,
            at_ms=self._clock,
        )

    def _jumper_on(self, cell, mover_piece):
        """An opposing airborne piece on ``cell``, which captures the mover on
        arrival. Only the destination counts; a jumper mid-path merely blocks."""
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
                self._begin_cooldown(jump.cell, self._config.SHORT_REST_STATE, self._config.SHORT_REST_DURATION)
        self._active_jumps = airborne

    def _begin_cooldown(self, cell, rest_state, duration):
        self._cooldowns[cell] = (rest_state, self._clock, self._clock + duration)

    def _prune_cooldowns(self):
        self._cooldowns = {
            cell: entry
            for cell, entry in self._cooldowns.items()
            if self._clock < entry[2]  # entry[2] is the expiry clock
        }
