import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { test } from "node:test";

import {
  fetchDashboardData,
  validateSessionDetail,
  validateSessionList,
} from "../src/services/sessionData.js";

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const session = {
  session_id: "session-1",
  created_at: "2026-10-01T10:00:00Z",
  updated_at: "2026-10-01T10:01:00Z",
  turn_count: 1,
  preview: "Hello",
};
const turn = {
  id: 1,
  user_message: "Hello",
  assistant_message: "Hi",
  human_state: null,
  dialogue_strategy: "normal_response",
  created_at: "2026-10-01T10:00:30Z",
};
const detail = { ...session, turns: [turn] };

test("session fetch can be retried after a failed request", async () => {
  let listAttempts = 0;
  const fetchImpl = async (url) => {
    if (url.endsWith("/sessions")) {
      listAttempts += 1;
      if (listAttempts === 1) {
        return { ok: false, status: 503 };
      }
      return { ok: true, json: async () => ({ sessions: [session] }) };
    }
    return { ok: true, json: async () => detail };
  };

  await assert.rejects(
    fetchDashboardData("http://api.test/api/v1", fetchImpl),
    /Could not load sessions \(503\)/,
  );
  const result = await fetchDashboardData("http://api.test/api/v1", fetchImpl);

  assert.equal(listAttempts, 2);
  assert.deepEqual(result.sessions, [session]);
  assert.deepEqual(result.turns, [turn]);
});

test("malformed detail responses prevent partial dashboard metrics", async () => {
  const secondSession = { ...session, session_id: "session-2" };
  const fetchImpl = async (url) => {
    if (url.endsWith("/sessions")) {
      return {
        ok: true,
        json: async () => ({ sessions: [session, secondSession] }),
      };
    }
    if (url.endsWith("/session-1")) {
      return { ok: true, json: async () => detail };
    }
    return { ok: true, json: async () => ({ ...detail, session_id: "wrong-session" }) };
  };

  await assert.rejects(
    fetchDashboardData("http://api.test/api/v1", fetchImpl),
    /Dashboard metrics may be incomplete/,
  );
});

test("Dashboard detail fanout is capped at four and returns all 22 details", async () => {
  const sessions = Array.from({ length: 22 }, (_, index) => ({
    ...session,
    session_id: `session-${index + 1}`,
  }));
  let activeRequests = 0;
  let maximumActiveRequests = 0;
  const fetchImpl = async (url) => {
    if (url.endsWith("/sessions")) {
      return { ok: true, json: async () => ({ sessions }) };
    }

    activeRequests += 1;
    maximumActiveRequests = Math.max(maximumActiveRequests, activeRequests);
    await new Promise((resolve) => setTimeout(resolve, 5));
    const sessionId = decodeURIComponent(url.split("/").at(-1));
    const index = Number(sessionId.slice("session-".length)) - 1;
    activeRequests -= 1;
    return {
      ok: true,
      json: async () => ({
        ...sessions[index],
        turns: [{ ...turn, id: index + 1 }],
      }),
    };
  };

  const result = await fetchDashboardData("http://api.test/api/v1", fetchImpl);

  assert.equal(maximumActiveRequests, 4);
  assert.equal(result.sessions.length, 22);
  assert.equal(result.turns.length, 22);
});

test("failed details preserve successful dashboard results and still reject", async () => {
  const sessions = Array.from({ length: 4 }, (_, index) => ({
    ...session,
    session_id: `session-${index + 1}`,
  }));
  const fetchImpl = async (url) => {
    if (url.endsWith("/sessions")) {
      return { ok: true, json: async () => ({ sessions }) };
    }
    if (url.endsWith("/session-2")) {
      return { ok: false, status: 503 };
    }

    const sessionId = decodeURIComponent(url.split("/").at(-1));
    const index = Number(sessionId.slice("session-".length)) - 1;
    return {
      ok: true,
      json: async () => ({
        ...sessions[index],
        turns: [{ ...turn, id: index + 1 }],
      }),
    };
  };

  await assert.rejects(
    fetchDashboardData("http://api.test/api/v1", fetchImpl),
    (error) => {
      assert.match(error.message, /1 session\(s\).*metrics may be incomplete/);
      assert.equal(error.partialData.sessions.length, 4);
      assert.equal(error.partialData.turns.length, 3);
      assert.deepEqual(
        error.partialData.turns.map((item) => item.id),
        [1, 3, 4],
      );
      return true;
    },
  );
});

test("Dashboard request failures settle loading and retain returned details", async () => {
  const dashboard = await readFile(
    resolve(frontendRoot, "src/pages/DashboardPage.jsx"),
    "utf8",
  );
  const sessions = [session, { ...session, session_id: "session-2" }];
  const fetchImpl = async (url) => {
    if (url.endsWith("/sessions")) {
      return { ok: true, json: async () => ({ sessions }) };
    }
    if (url.endsWith("/session-2")) {
      return { ok: false, status: 503 };
    }
    return { ok: true, json: async () => detail };
  };

  let loading = true;
  let partialData;
  try {
    await fetchDashboardData("http://api.test/api/v1", fetchImpl);
  } catch (error) {
    partialData = error.partialData;
  } finally {
    loading = false;
  }

  assert.equal(loading, false);
  assert.equal(partialData.turns.length, 1);
  assert.match(dashboard, /setSessions\(err\.partialData\?\.sessions \|\| \[\]\)/);
  assert.match(dashboard, /setTurns\(err\.partialData\?\.turns \|\| \[\]\)/);
  assert.match(dashboard, /finally\s*\{[\s\S]*?setLoading\(false\)/);
});

test("session-list responses reject missing, null, or wrongly shaped sessions", () => {
  for (const payload of [null, {}, { sessions: null }, { sessions: {} }]) {
    assert.throws(() => validateSessionList(payload), /invalid session list/);
  }
  assert.throws(
    () => validateSessionList({ sessions: [null] }),
    /Session 1 has an invalid format/,
  );
  assert.throws(
    () => validateSessionList({ sessions: [{ ...session, turn_count: "1" }] }),
    /invalid turn count/,
  );
  assert.deepEqual(validateSessionList({ sessions: [] }), []);
});

test("invalid JSON returns a readable API response error", async () => {
  const fetchImpl = async () => ({
    ok: true,
    json: async () => { throw new SyntaxError("bad json"); },
  });

  await assert.rejects(
    fetchDashboardData("http://api.test/api/v1", fetchImpl),
    /server returned an invalid JSON response/,
  );
});

test("session-detail responses reject malformed turns and session fields", () => {
  assert.throws(
    () => validateSessionDetail({ ...detail, turns: null }, session.session_id),
    /invalid turns list/,
  );
  assert.throws(
    () => validateSessionDetail({ ...detail, session_id: "other" }, session.session_id),
    /unexpected session/,
  );
  assert.throws(
    () => validateSessionDetail({ ...detail, turns: [null] }, session.session_id),
    /Turn 1.*invalid format/,
  );
  assert.throws(
    () => validateSessionDetail({ ...detail, turns: [{ ...turn, human_state: [] }] }, session.session_id),
    /invalid human-state data/,
  );
  assert.deepEqual(validateSessionDetail(detail, session.session_id), detail);
});

test("Dashboard and History set loading on retry, suppress duplicates, and abort on unmount", async () => {
  const dashboard = await readFile(resolve(frontendRoot, "src/pages/DashboardPage.jsx"), "utf8");
  const history = await readFile(resolve(frontendRoot, "src/pages/HistoryPage.jsx"), "utf8");

  assert.match(dashboard, /if \(requestRef\.current\) return;[\s\S]*?setLoading\(true\);[\s\S]*?setSessions\(\[\]\);[\s\S]*?setTurns\(\[\]\)/);
  assert.match(dashboard, /requestRef\.current = null;\s*controller\?\.abort\(\)/);
  assert.match(history, /if \(listRequestRef\.current\) return;[\s\S]*?setLoading\(true\);[\s\S]*?setSessions\(\[\]\)/);
  assert.match(history, /listRequestRef\.current = null;\s*listRequest\?\.abort\(\)/);
  assert.match(history, /if \(detailRequestRef\.current\?\.sessionId === sessionId\) return/);
});
