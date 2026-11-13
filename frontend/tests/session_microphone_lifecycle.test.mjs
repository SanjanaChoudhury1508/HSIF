import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { test } from "node:test";

import {
  ACTIVE_SESSION_STORAGE_KEY,
  USER_STORAGE_KEY,
  clearLocalUserSession,
  getRestorableSessionId,
} from "../src/services/localSession.js";
import {
  runMicrophoneStartOnce,
  startMicrophoneStreaming,
} from "../src/services/audioCapture.js";

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");

function makeStorage(initial = {}) {
  const values = new Map(Object.entries(initial));
  return {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, String(value)),
    removeItem: (key) => values.delete(key),
  };
}

async function readSource(path) {
  return readFile(resolve(frontendRoot, path), "utf8");
}

test("logout clears the active session and a later login cannot restore it", async () => {
  const storage = makeStorage({
    [USER_STORAGE_KEY]: JSON.stringify({ email: "first@example.test" }),
    [ACTIVE_SESSION_STORAGE_KEY]: "previous-session",
  });

  assert.equal(getRestorableSessionId(storage), "previous-session");
  clearLocalUserSession(storage);
  storage.setItem(USER_STORAGE_KEY, JSON.stringify({ email: "next@example.test" }));

  assert.equal(storage.getItem(ACTIVE_SESSION_STORAGE_KEY), null);
  assert.equal(getRestorableSessionId(storage), null);

  storage.setItem(ACTIVE_SESSION_STORAGE_KEY, "current-session");
  assert.equal(getRestorableSessionId(storage), "current-session");
});

test("all logout paths clear both keys and chat logout uses hook cleanup", async () => {
  const [shell, account, chat, hook] = await Promise.all([
    readSource("src/components/AppShell.jsx"),
    readSource("src/pages/AccountPage.jsx"),
    readSource("src/ChatPage.jsx"),
    readSource("src/hooks/useStreamingSession.js"),
  ]);

  assert.match(shell, /function handleLogout\(\)\s*\{\s*clearLocalUserSession\(\)/s);
  assert.match(account, /clearLocalUserSession\(\)/);
  assert.match(chat, /async function handleLogout\(\)\s*\{[^}]*await logout\(\)/s);
  assert.match(chat, /className="logout"[^>]*onClick=\{handleLogout\}/);
  assert.match(hook, /const logout = useCallback\(async \(\) => \{[\s\S]*?clearLocalUserSession\(\)[\s\S]*?await cleanupMic\(\)[\s\S]*?socket\.close\(\)/);
});

test("refresh restores a saved session only while logged in", async () => {
  const storage = makeStorage({
    [USER_STORAGE_KEY]: JSON.stringify({ email: "still-logged-in@example.test" }),
    [ACTIVE_SESSION_STORAGE_KEY]: "saved-session",
  });
  assert.equal(getRestorableSessionId(storage), "saved-session");

  const hook = await readSource("src/hooks/useStreamingSession.js");
  assert.match(hook, /const savedId = getRestorableSessionId\(\)/);
  assert.doesNotMatch(hook, /fetch\(`\$\{API_BASE_URL\}\/sessions`\)/);
  assert.match(hook, /restoreGeneration !== restoreGenerationRef\.current/);
});

test("microphone start guard allows one pending capture and resets after failure", async () => {
  const guard = { current: false };
  let startCount = 0;
  let finishFirst;
  const first = runMicrophoneStartOnce(guard, () => {
    startCount += 1;
    return new Promise((resolve) => { finishFirst = resolve; });
  });

  assert.equal(guard.current, true);
  assert.equal(runMicrophoneStartOnce(guard, async () => { startCount += 1; }), null);
  await Promise.resolve();
  assert.equal(startCount, 1);
  finishFirst();
  await first;
  assert.equal(guard.current, false);

  await assert.rejects(
    runMicrophoneStartOnce(guard, async () => { throw new Error("startup failed"); }),
    /startup failed/
  );
  assert.equal(guard.current, false);

  const retry = runMicrophoneStartOnce(guard, async () => "started");
  assert.equal(await retry, "started");
  assert.equal(guard.current, false);
});

test("microphone startup failure releases acquired tracks", async () => {
  const previousNavigator = Object.getOwnPropertyDescriptor(globalThis, "navigator");
  const previousAudioContext = Object.getOwnPropertyDescriptor(globalThis, "AudioContext");
  let stoppedTracks = 0;

  Object.defineProperty(globalThis, "navigator", {
    configurable: true,
    value: {
      mediaDevices: {
        getUserMedia: async () => ({
          getTracks: () => [{ stop: () => { stoppedTracks += 1; } }],
        }),
      },
    },
  });
  globalThis.AudioContext = class {
    constructor() { throw new Error("audio context unavailable"); }
  };

  try {
    await assert.rejects(
      startMicrophoneStreaming({ readyState: 1 }),
      /audio context unavailable/
    );
    assert.equal(stoppedTracks, 1);
  } finally {
    if (previousNavigator) {
      Object.defineProperty(globalThis, "navigator", previousNavigator);
    } else {
      delete globalThis.navigator;
    }
    if (previousAudioContext) {
      Object.defineProperty(globalThis, "AudioContext", previousAudioContext);
    } else {
      delete globalThis.AudioContext;
    }
  }
});

test("active microphone stop releases tracks and closes its context once", async () => {
  const previousNavigator = Object.getOwnPropertyDescriptor(globalThis, "navigator");
  const previousAudioContext = Object.getOwnPropertyDescriptor(globalThis, "AudioContext");
  let stoppedTracks = 0;
  let closedContexts = 0;
  const node = () => ({ connect() {}, disconnect() {} });

  Object.defineProperty(globalThis, "navigator", {
    configurable: true,
    value: {
      mediaDevices: {
        getUserMedia: async () => ({
          getTracks: () => [{ stop: () => { stoppedTracks += 1; } }],
        }),
      },
    },
  });
  globalThis.AudioContext = class {
    state = "running";
    sampleRate = 48000;
    destination = {};
    createMediaStreamSource() { return node(); }
    createScriptProcessor() { return node(); }
    createGain() { return { ...node(), gain: { value: 1 } }; }
    async close() { this.state = "closed"; closedContexts += 1; }
  };

  try {
    const stop = await startMicrophoneStreaming({ readyState: 1 });
    await stop();
    await stop();
    assert.equal(stoppedTracks, 1);
    assert.equal(closedContexts, 1);
  } finally {
    if (previousNavigator) {
      Object.defineProperty(globalThis, "navigator", previousNavigator);
    } else {
      delete globalThis.navigator;
    }
    if (previousAudioContext) {
      Object.defineProperty(globalThis, "AudioContext", previousAudioContext);
    } else {
      delete globalThis.AudioContext;
    }
  }
});

test("hook invalidates pending microphone startup on stop, socket close, and unmount", async () => {
  const hook = await readSource("src/hooks/useStreamingSession.js");

  assert.match(hook, /microphoneStartingRef\.current\) return/);
  assert.match(hook, /runMicrophoneStartOnce\(\s*microphoneStartingRef/);
  assert.match(hook, /startupId !== microphoneStartupIdRef\.current[\s\S]*?await stop\(\)/);
  assert.match(hook, /const endSession = useCallback\(async \(\) => \{\s*closingRef\.current = true;\s*microphoneStartupIdRef\.current \+= 1/s);
  assert.match(hook, /return \(\) => \{\s*closingRef\.current = true;\s*microphoneStartupIdRef\.current \+= 1/s);
});
