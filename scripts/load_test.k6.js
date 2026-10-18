// A k6 load test against a running server (`python -m server`) - the tool
// Server_Design.md names for proving scale, alongside scripts/load_test.py
// (which stays too: its per-phase p50/p95 breakdown is handy for local
// debugging in a way k6's own summary isn't). k6 adds ramping virtual users
// and pass/fail thresholds, so a run can fail a CI-style check on its own
// instead of only being read by a person.
//
// Usage:
//   python -m server                                     # in one terminal
//   k6 run scripts/load_test.k6.js --vus 50 --duration 30s
//
// Each virtual user: logs in over HTTP, opens a websocket, sends SeekGame(),
// plays a move once seated, and k6 reports connect/match/move-round-trip
// timings as its own metrics.
import http from "k6/http";
import ws from "k6/ws";
import { Trend } from "k6/metrics";
import { check } from "k6";

const API_URL = __ENV.KF_API_URL || "http://localhost:8766";
const WS_URL = __ENV.KF_SERVER_URL || "ws://localhost:8765";

const connectTime = new Trend("kf_connect_ms");
const matchTime = new Trend("kf_match_ms");
const moveRoundTripTime = new Trend("kf_move_round_trip_ms");

export const options = {
  thresholds: {
    // A run fails loudly if matching or a move round-trip gets slow, not
    // just when a request errors outright.
    kf_match_ms: ["p(95)<15000"],
    kf_move_round_trip_ms: ["p(95)<1000"],
  },
};

function envelope(name, fields) {
  return JSON.stringify({ name, fields });
}

export default function () {
  const username = `loadtest-${__VU}-${__ITER}-${Date.now()}`;
  const loginRes = http.post(
    `${API_URL}/login`,
    JSON.stringify({ username, password: "pw" }),
    { headers: { "Content-Type": "application/json" } },
  );
  if (!check(loginRes, { "login succeeded": (r) => r.status === 200 })) {
    return;
  }
  const token = loginRes.json("token");

  const start = Date.now();
  let matched = false;
  let moveSentAt = null;
  let color = null;

  const response = ws.connect(WS_URL, {}, function (socket) {
    socket.on("open", function () {
      socket.send(envelope("Connect", { token }));
    });

    socket.on("message", function (data) {
      const message = JSON.parse(data);

      if (message.name === "Welcome") {
        connectTime.add(Date.now() - start);
        socket.send(envelope("SeekGame", {}));
        return;
      }

      if (message.name === "RoomEntered" && !matched) {
        matched = true;
        matchTime.add(Date.now() - start);
        color = message.fields.color;
        const command = color === "w" ? "WPe2e4" : "BPe7e5";
        moveSentAt = Date.now();
        socket.send(envelope("MoveRequest", { command, msg_id: `${__VU}-${__ITER}` }));
        return;
      }

      if (message.name === "StateUpdate" && moveSentAt !== null) {
        moveRoundTripTime.add(Date.now() - moveSentAt);
        moveSentAt = null; // only the first round-trip after our move counts
        socket.close();
      }
    });

    socket.setTimeout(function () {
      socket.close();
    }, 15000);
  });

  check(response, { "websocket handshake succeeded": (r) => r && r.status === 101 });
}
