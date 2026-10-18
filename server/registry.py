"""Who is playing which colour, and how they are rated right now.

The server's alone: the game itself is turnless and colour-blind, so player
identity lives out here, beside the connections, and never reaches the engine.

The first to join takes the first colour, the second the next, and a third is
turned away - two players, as the slide asks. Spectators come later, and will be
those this refuses a colour rather than the connection.

A seat may instead be held by the server's computer player (bot/). It is seated
on purpose, onto the colour the human did not ask for, rather than arriving in
turn; and it is never mistaken for a reconnecting human, even one who happens to
share its display name.

A seated player's rating is held here in memory - read once from the store at
login, updated once when a game ends - so the state can be sent every frame
without touching the database.
"""
from __future__ import annotations

from accounts.store import Account


class PlayerRegistry:
    def __init__(self, colors):
        self._colors = tuple(colors)
        self._by_color = {}  # colour -> Account
        self._computers = set()  # colours held by the computer player

    def restore(self, players):
        """Seat every colour in `players` ({colour: {"username", "rating",
        "computer"}}) directly, bypassing the one-at-a-time queue `seat()`
        enforces - used only to rehydrate a room from a saved snapshot, where
        both seats are already decided and there is no "who arrived first" to
        preserve. "computer" may be missing, from a snapshot saved before
        computer seats existed, and then means a human seat."""
        for color, player in players.items():
            self._by_color[color] = Account(player["username"], player["rating"])
            if player.get("computer", False):
                self._computers.add(color)

    def seat_computer(self, color, account):
        """Give `color` to the computer player, shown as `account`. False when
        the colour is unknown or already taken, so a computer never displaces
        anyone."""
        if color not in self._colors or color in self._by_color:
            return False
        self._by_color[color] = account
        self._computers.add(color)
        return True

    def is_computer(self, color):
        """Whether the computer player holds `color`."""
        return color in self._computers

    def computer_colors(self):
        """The colours the computer player holds, in seating order."""
        return tuple(color for color in self._colors if color in self._computers)

    def seat(self, account):
        """Give `account` the next free colour, or None when both are taken or
        this player is already seated - so one person cannot hold both colours
        and play against themselves."""
        if self._already_seated(account.username):
            return None
        for color in self._colors:
            if color not in self._by_color:
                self._by_color[color] = account
                return color
        return None

    def _already_seated(self, username):
        return self.seated_color(username) is not None

    def seated_color(self, username):
        """The colour `username` already holds, or None - lets a reconnecting
        player be recognised instead of turned into a fresh seat/viewer. The
        computer's seat never counts, so no human can take it over by name."""
        for color, account in self._by_color.items():
            if account.username == username and color not in self._computers:
                return color
        return None

    def leave(self, color):
        """Free a colour when its player disconnects, so the seat can be retaken."""
        self._by_color.pop(color, None)
        self._computers.discard(color)

    def name_of(self, color):
        """The username seated on `color`, or None if the seat is empty."""
        account = self._by_color.get(color)
        return account.username if account is not None else None

    def set_rating(self, color, rating):
        """Update the cached rating of whoever holds `color`, after a game moves
        it. A no-op if the seat is empty."""
        from dataclasses import replace

        account = self._by_color.get(color)
        if account is not None:
            self._by_color[color] = replace(account, rating=rating)

    def names(self):
        """A plain {colour: username} for the state the view draws."""
        return {color: account.username for color, account in self._by_color.items()}

    def ratings(self):
        """A plain {colour: rating} for the state the view draws."""
        return {color: account.rating for color, account in self._by_color.items()}
