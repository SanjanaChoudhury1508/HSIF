import assert from "node:assert/strict";
import { test } from "node:test";

import {
  DEFAULT_API_BASE_URL,
  buildSessionWebSocketUrl,
  resolveWebSocketBaseUrl,
} from "../src/services/websocketUrl.js";

const sessionId = "session-123";

test("HTTP API base derives a ws URL and removes the API path", () => {
  const resolved = buildSessionWebSocketUrl(
    sessionId,
    "http://api.example.test/api/v1/",
  );

  assert.equal(resolved, "ws://api.example.test/ws/session/session-123");
});

test("HTTPS API base derives a secure WebSocket URL", () => {
  const resolved = buildSessionWebSocketUrl(
    sessionId,
    "https://api.example.test/api/v1",
  );

  assert.equal(resolved, "wss://api.example.test/ws/session/session-123");
});

test("explicit WebSocket base overrides the API-derived URL", () => {
  const resolved = buildSessionWebSocketUrl(
    sessionId,
    "https://api.example.test/api/v1",
    "wss://socket.example.test/",
  );

  assert.equal(resolved, "wss://socket.example.test/ws/session/session-123");
});

test("default local configuration keeps the local WebSocket URL", () => {
  assert.equal(
    buildSessionWebSocketUrl(sessionId),
    "ws://localhost:8000/ws/session/session-123",
  );
  assert.equal(
    resolveWebSocketBaseUrl(DEFAULT_API_BASE_URL),
    "ws://localhost:8000",
  );
});

test("API prefixes and explicit /ws bases do not duplicate route segments", () => {
  assert.equal(
    buildSessionWebSocketUrl(
      sessionId,
      "https://example.test/hsif/api/v1///",
    ),
    "wss://example.test/hsif/ws/session/session-123",
  );
  assert.equal(
    buildSessionWebSocketUrl(
      sessionId,
      DEFAULT_API_BASE_URL,
      "ws://localhost:9000/ws/",
    ),
    "ws://localhost:9000/ws/session/session-123",
  );
});
