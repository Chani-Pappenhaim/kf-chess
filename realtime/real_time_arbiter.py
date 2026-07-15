from __future__ import annotations

from dataclasses import dataclass

from realtime.models import Move, Jump, MotionView


@dataclass(frozen=True)
class ArrivalEvent:
    """What the arbiter reports back when a moving piece arrives.

    The arbiter mutates the board itself, but it does not decide the win
    condition - it only reports which token (if any) was captured, so the
    GameEngine can apply its injected WinCondition. `piece` is the token as
    placed at the destination (already promoted if a promotion applied).
    """

    piece: str
    destination: tuple
    captured: str | None


class RealTimeArbiter:
    """Owns all real-time motion: active Moves/Jumps, the simulated clock,
    arrival timing, and arrival/interception resolution.

    Kept separate from GameEngine so the real-time model can be tested in
    isolation, and so Board keeps representing only logical occupancy while
    in-flight motion state lives here. Time never advances from the wall
    clock: it only moves when `advance_time` is called with a delta.

    Promotion happens on arrival, so the promotion rule is injected here
    (into the layer that owns arrival), not into the engine.
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
        return any(move.start == cell for move in self._active_moves)

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
        Lets the view drain the rest veil from the top down as time elapses."""
        entry = self._cooldowns.get(cell)
        if entry is None:
            return None
        _rest_state, start, expiry = entry
        if self._clock >= expiry:
            return None
        total = expiry - start
        if total <= 0:
            return 1.0
        return max(0.0, min(1.0, (self._clock - start) / total))

    def is_resting(self, cell):
        return self.cooldown_of(cell) is not None

    def active_motions(self):
        """Read-only views of the in-flight moves, each with its progress (0..1)
        at the current clock - for the renderer to interpolate a sliding piece."""
        return [self._motion_view(move) for move in self._active_moves]

    def _motion_view(self, move):
        total = self._move_total(move.start, move.end)
        travelled = total - (move.arrival - self._clock)
        progress = 1.0 if total <= 0 else max(0.0, min(1.0, travelled / total))
        return MotionView(move.piece, move.start, move.end, progress)

    def start_move(self, piece, start, end):
        self._active_moves.append(Move(piece, start, end, self._arrival_clock(start, end)))

    def start_jump(self, piece, cell):
        self._active_jumps.append(Jump(piece, cell, self._clock + self._config.JUMP_DURATION))

    def advance_time(self, dt):
        """Advance simulated time and resolve whatever became due."""
        self._clock += dt
        return self.resolve()

    def resolve(self):
        """Settle any moves whose arrival time has been reached, without
        advancing the clock. Returns the arrival events produced."""
        remaining = []
        events = []
        for move in self._active_moves:
            if self._clock < move.arrival:
                remaining.append(move)
                continue
            event = self._settle_move(move)
            if event is not None:
                events.append(event)
        self._active_moves = remaining
        self._resolve_jumps()
        self._prune_cooldowns()
        return events

    # -- internal helpers -------------------------------------------------

    def _arrival_clock(self, start, end):
        return self._clock + self._move_total(start, end)

    def _move_total(self, start, end):
        """Total travel time of a move: MOVE_DURATION per square, where distance
        is the number of squares on a straight/diagonal path (Chebyshev metric)."""
        distance = max(abs(end[0] - start[0]), abs(end[1] - start[1]))
        return distance * self._config.MOVE_DURATION

    def _settle_move(self, move):
        if self._is_intercepted(move):
            # The moving piece is captured mid-flight by the jumping piece,
            # so it is removed from its source rather than surviving there.
            self._board.set(*move.start, self._config.EMPTY_CELL)
            return None

        r, c = move.end
        target = self._board.get(r, c)
        if target != self._config.EMPTY_CELL and target[0] == move.piece[0]:
            return None

        captured = None if target == self._config.EMPTY_CELL else target
        piece = self._promotion_rule.promote(move.piece, r, self._board.height)
        # The piece stays visible at its source while in flight; it leaves the
        # source only now, on arrival. (A same-color piece blocking the target
        # returns above, so the mover survives in place in that case.)
        self._board.set(*move.start, self._config.EMPTY_CELL)
        self._board.set(r, c, piece)
        # A completed move settles into a long rest before the piece can act
        # again (the state the move animation transitions into).
        self._begin_cooldown((r, c), "long_rest", self._config.LONG_REST_DURATION)
        return ArrivalEvent(piece=piece, destination=(r, c), captured=captured)

    def _is_intercepted(self, move):
        r, c = move.end
        return any(
            jump.cell == (r, c) and jump.piece[0] != move.piece[0]
            for jump in self._active_jumps
        )

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
