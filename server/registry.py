"""Who is playing which colour, and how they are rated right now.

The server's alone: the game itself is turnless and colour-blind, so player
identity lives out here, beside the connections, and never reaches the engine.

The first to join takes the first colour, the second the next, and a third is
turned away - two players, as the slide asks. Spectators come later, and will be
those this refuses a colour rather than the connection.

A seated player's rating is held here in memory - read once from the store at
login, updated once when a game ends - so the state can be sent every frame
without touching the database.
"""
from __future__ import annotations


class PlayerRegistry:
    def __init__(self, colors):
        self._colors = tuple(colors)
        self._by_color = {}  # colour -> Account

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
        return any(account.username == username for account in self._by_color.values())

    def leave(self, color):
        """Free a colour when its player disconnects, so the seat can be retaken."""
        self._by_color.pop(color, None)

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
