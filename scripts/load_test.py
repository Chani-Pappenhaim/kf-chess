"""A real-infrastructure load test: many concurrent players against a running
server (`python -m server`), not a mock. Run separately from pytest, since it
opens real sockets and measures wall-clock time rather than asserting
behaviour - a load test answers "how does this perform," not "is this correct."

Usage:
    python -m server                              # in one terminal
    python scripts/load_test.py --players 200      # in another

Each simulated player: logs in over HTTP, opens a websocket, SeekGame()s into
a match, plays a few moves once seated, and the script reports how long the
whole fleet took to connect, get matched, and round-trip a move.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import secrets
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from websockets.asyncio.client import connect

from client.login import http_login
from config import settings
from protocol.messages import Connect, MoveRequest, RoomEntered, SeekGame, StateUpdate, decode, encode


async def _play_one(config, index, connect_times, match_times, move_round_trips):
    username = f"loadtest-{secrets.token_hex(4)}-{index}"
    # http_login is a blocking call (urllib); off the event loop so N logins
    # actually run concurrently instead of queuing behind one another.
    result = await asyncio.to_thread(http_login, config, username, "pw")
    if result is None:
        return
    token, _new_account = result

    start = time.perf_counter()
    async with connect(config.SERVER_URL) as ws:
        await ws.send(encode(Connect(token)))
        await ws.recv()  # Welcome
        connect_times.append(time.perf_counter() - start)

        await ws.send(encode(SeekGame()))
        seek_start = time.perf_counter()
        color = None
        async for line in ws:
            message = decode(line)
            if isinstance(message, RoomEntered):
                color = message.color
                match_times.append(time.perf_counter() - seek_start)
                break
        if color is None:
            return  # no opponent within the timeout

        # A move only a mover would send; a viewer or the wrong colour is
        # simply ignored server-side, so sending unconditionally is safe here.
        move_start = time.perf_counter()
        await ws.send(encode(MoveRequest(f"{color.upper()}Pe2e4" if color == "w" else f"{color.upper()}Pe7e5")))
        async for line in ws:
            if isinstance(decode(line), StateUpdate):
                move_round_trips.append(time.perf_counter() - move_start)
                break


async def _play_one_bounded(config, index, connect_times, match_times, move_round_trips, timeout):
    try:
        await asyncio.wait_for(
            _play_one(config, index, connect_times, match_times, move_round_trips), timeout
        )
    except asyncio.TimeoutError:
        print(f"player {index}: timed out after {timeout}s")
    except Exception as error:  # noqa: BLE001 - a load test reports every failure, not just some
        print(f"player {index}: {type(error).__name__}: {error}")


async def run(config, players, timeout):
    connect_times, match_times, move_round_trips = [], [], []
    start = time.perf_counter()
    await asyncio.gather(*(
        _play_one_bounded(config, i, connect_times, match_times, move_round_trips, timeout)
        for i in range(players)
    ))
    total = time.perf_counter() - start

    def summarize(label, values):
        if not values:
            print(f"{label}: no samples")
            return
        values = sorted(values)
        p50 = values[len(values) // 2]
        p95 = values[int(len(values) * 0.95)]
        print(f"{label}: n={len(values)} avg={sum(values)/len(values)*1000:.0f}ms "
              f"p50={p50*1000:.0f}ms p95={p95*1000:.0f}ms")

    print(f"\n{players} simulated players against {config.SERVER_URL}")
    print(f"total wall time: {total:.2f}s ({players/total:.1f} players/s)")
    summarize("connect+login", connect_times)
    summarize("time to matched", match_times)
    summarize("move round-trip", move_round_trips)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--players", type=int, default=50)
    parser.add_argument("--timeout", type=float, default=15.0, help="seconds before one simulated player gives up")
    args = parser.parse_args()
    asyncio.run(run(settings, args.players, args.timeout))
