"""One game, and everyone gathered around it.

A room is a single self-contained game - its own engine, its own player registry,
its own set of member sessions - so many rooms run side by side in one process
without ever touching each other. Events and state go only to this room's
members, never to every connected client, which is the whole of what "many
concurrent games" needs.

The first to join takes White, the second Black; anyone after that is a viewer,
who sees the game but holds no colour and so can move nothing. When a player
disconnects mid-game the room does not resign at once: it counts DISCONNECT_GRACE
down, in view of the remaining player, and only then concedes the game in the
leaver's name - long enough that a blink of a connection is not a lost game.

Time is handed in through tick(dt); the room counts the grace period from it, so
the server clock stays the only clock here too.
"""
from __future__ import annotations

from protocol.messages import RoomEntered, encode
from server.broadcast import broadcast_state


class Room:
    def __init__(self, room_id, engine, registry, board_height, config):
        self._id = room_id
        self._engine = engine
        self._registry = registry
        self._height = board_height
        self._config = config
        self._members = []          # ClientSessions in this room
        self._started = False       # whether both seats filled and the game began
        self._countdown = None      # ms left before a disconnected player resigns
        self._resigning = None      # the colour that left, awaiting auto-resign

    @property
    def id(self):
        return self._id

    @property
    def is_empty(self):
        """No one left in the room, so the lobby may forget it."""
        return not self._members

    def join(self, session):
        """Seat `session` (White, then Black, then viewer), tell it where it
        landed, and start the game once both seats are taken. A player
        reconnecting mid-disconnect-grace gets their own seat back, resigning
        countdown cancelled, instead of being turned into a viewer."""
        color = self._registry.seated_color(session.account.username)
        if color is not None:
            if self._resigning == color:
                self._cancel_countdown()
        else:
            color = self._registry.seat(session.account)  # None when the room is full
        session.enter_room(self, color, self._engine, self._height)
        self._members.append(session)
        session.send(encode(RoomEntered(color, self._id, color is None)))
        if color is not None and self._both_seats_filled() and not self._started:
            self._engine.start()
            self._started = True
        self._broadcast_state()

    def leave(self, session):
        """A member disconnected. A viewer just goes; a player mid-game starts
        the resign countdown, unless there is no game to lose."""
        self._members.remove(session)
        if session.color is None:
            self._broadcast_state()
            return
        if self._countdown is not None:
            # The other player already left - both are gone now, so no one wins.
            self._cancel_countdown()
        elif not self._engine.game_over and self._both_seats_filled():
            self._countdown = self._config.DISCONNECT_GRACE_MS
            self._resigning = session.color
        else:
            self._free_seat(session.color)
        self._broadcast_state()

    def broadcast(self, line):
        """Queue `line` for every current member, players and viewers alike."""
        for member in self._members:
            member.send(line)

    def tick(self, dt):
        """Advance this room's game, run any resign countdown, send the state."""
        self._engine.wait(dt)
        if self._countdown is not None:
            self._countdown -= dt
            if self._countdown <= 0:
                self._resign()
        self._broadcast_state()

    def _resign(self):
        """The grace ran out: the one who stayed wins, exactly as any game ends,
        and the empty seat is freed only now - the rating needs both names."""
        winner = self._other_color(self._resigning)
        self._engine.concede(winner, self._config.GAME_END_FORFEIT)
        self._free_seat(self._resigning)
        self._cancel_countdown()

    def _cancel_countdown(self):
        self._countdown = None
        self._resigning = None

    def _free_seat(self, color):
        self._registry.leave(color)

    def _both_seats_filled(self):
        return all(self._registry.name_of(color) is not None for color in self._config.COLORS)

    def _other_color(self, color):
        return next(other for other in self._config.COLORS if other != color)

    def _viewer_names(self):
        return tuple(m.account.username for m in self._members if m.color is None)

    def _countdown_seconds(self):
        # Whole seconds left, rounded up, so the last tick still reads "1"; None
        # when nothing is counting down.
        if self._countdown is None:
            return None
        return max(0, -(-self._countdown // 1000))

    def _broadcast_state(self):
        broadcast_state(
            self._engine, self._registry.names(), self._registry.ratings(),
            self._viewer_names(), self._countdown_seconds(), self.broadcast,
        )
