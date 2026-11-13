import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { after, before, test } from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import reactPlugin from "@vitejs/plugin-react";
import { createServer } from "vite";

import {
  AudioUploadTimeoutError,
  uploadAudio,
  withLoadingState,
} from "../src/services/audioUpload.js";
import { getWebSocketErrorTransition } from "../src/services/streamingErrors.js";

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
let vite;
let ChatFeedback;

before(async () => {
  vite = await createServer({
    configFile: false,
    root: frontendRoot,
    plugins: [reactPlugin()],
    server: { middlewareMode: true },
    appType: "custom",
    logLevel: "silent",
  });
  ({ default: ChatFeedback } = await vite.ssrLoadModule(
    "/src/components/ChatFeedback.jsx"
  ));
});

after(async () => {
  await vite?.close();
});

test("recoverable WebSocket failures reset processing without cleanup", () => {
  const quotaEvent = {
    code: "LLM_QUOTA_EXHAUSTED",
    recoverable: true,
  };
  const quota = getWebSocketErrorTransition(
    "processing",
    quotaEvent.recoverable
  );
  assert.deepEqual(quota, {
    status: "ready",
    cleanupMicrophone: false,
    closeSocket: false,
  });

  const generic = getWebSocketErrorTransition("processing", true);
  assert.equal(generic.status, "ready");
  assert.equal(generic.closeSocket, false);

  const whileRecording = getWebSocketErrorTransition("recording", true);
  assert.equal(whileRecording.status, "recording");
});

test("non-recoverable WebSocket failures preserve cleanup behavior", () => {
  const transition = getWebSocketErrorTransition("processing", false);
  assert.equal(transition.status, "error");
  assert.equal(transition.cleanupMicrophone, true);
  assert.equal(transition.closeSocket, false);
});

test("audio upload timeout rejects instead of returning late success", async () => {
  const lateResponse = async () => ({
    ok: true,
    json: () => new Promise((resolveJson) => setTimeout(
      () => resolveJson({ response: "late" }),
      25
    )),
  });

  await assert.rejects(
    uploadAudio("/api/v1/process", new FormData(), 5, lateResponse),
    AudioUploadTimeoutError
  );
});

test("timed-out fetch is aborted and reported as a timeout", async () => {
  const abortableFetch = (_url, { signal }) => new Promise((_, reject) => {
    signal.addEventListener("abort", () => {
      const error = new Error("aborted");
      error.name = "AbortError";
      reject(error);
    }, { once: true });
  });

  await assert.rejects(
    uploadAudio("/api/v1/process", new FormData(), 5, abortableFetch),
    /timed out after 1 seconds/
  );
});

test("upload loading state resets after API errors and timeouts", async () => {
  let loading = false;
  const setLoading = (value) => { loading = value; };
  const operations = [
    () => uploadAudio("/api/v1/process", new FormData(), 100, async () => ({
      ok: false,
      json: async () => ({ detail: "Gemini quota exhausted." }),
    })),
    () => uploadAudio("/api/v1/process", new FormData(), 5, async () => ({
      ok: true,
      json: () => new Promise((resolveJson) => setTimeout(
        () => resolveJson({ response: "late" }),
        25
      )),
    })),
  ];

  for (const operation of operations) {
    await assert.rejects(withLoadingState(setLoading, async () => {
      assert.equal(loading, true);
      return operation();
    }));
    assert.equal(loading, false);
  }
});

test("HTTP upload errors are rendered and return the UI to ready status", async () => {
  let loading = false;
  let uploadError = "";

  try {
    await withLoadingState((value) => { loading = value; }, async () => {
      await uploadAudio(
        "/api/v1/process",
        new FormData(),
        100,
        async () => ({
          ok: false,
          json: async () => ({ detail: "Gemini quota is exhausted." }),
        }),
      );
    });
  } catch (error) {
    uploadError = error.message;
  }

  const html = renderToStaticMarkup(React.createElement(ChatFeedback, {
    uploadError,
    streamError: "",
    uploading: loading,
    isRecording: false,
    status: "ready",
    isWebSocketOpen: false,
  }));

  assert.equal(loading, false);
  assert.match(html, /role="alert"[^>]*>Gemini quota is exhausted\./);
  assert.match(html, /role="status"[^>]*>Ready/);
  assert.doesNotMatch(html, />Connected</);
});

test("an open WebSocket is the only condition that shows Connected", async () => {
  const disconnectedHtml = renderToStaticMarkup(React.createElement(ChatFeedback, {
    uploadError: "Upload failed.",
    streamError: "",
    uploading: false,
    isRecording: false,
    status: "ready",
    isWebSocketOpen: false,
  }));
  const connectedHtml = renderToStaticMarkup(React.createElement(ChatFeedback, {
    uploadError: "",
    streamError: "",
    uploading: false,
    isRecording: false,
    status: "ready",
    isWebSocketOpen: true,
  }));
  const hook = await readFile(
    resolve(frontendRoot, "src/hooks/useStreamingSession.js"),
    "utf8",
  );
  const chat = await readFile(resolve(frontendRoot, "src/ChatPage.jsx"), "utf8");

  assert.match(disconnectedHtml, /role="status"[^>]*>Ready/);
  assert.doesNotMatch(disconnectedHtml, />Connected</);
  assert.match(disconnectedHtml, /role="alert"[^>]*>Upload failed\./);
  assert.match(connectedHtml, /role="status"[^>]*>Connected/);
  assert.match(hook, /socket\.onopen = \(\) => \{\s*if \(socketRef\.current === socket\) \{\s*setIsWebSocketOpen\(socket\.readyState === WebSocket\.OPEN\)/s);
  assert.match(hook, /socket\.onclose = async \(event\) => \{[\s\S]*?setIsWebSocketOpen\(false\)/);
  assert.match(chat, /isWebSocketOpen=\{isWebSocketOpen\}/);
});

test("upload can be retried after failure without leaving loading active", async () => {
  let loading = false;
  let attempts = 0;
  let uploadError = "";
  const formData = new FormData();
  const fetchImpl = async () => {
    attempts += 1;
    if (attempts === 1) {
      return {
        ok: false,
        json: async () => ({ detail: "Audio processing failed." }),
      };
    }
    return { ok: true, json: async () => ({ response: "Processed" }) };
  };

  try {
    await withLoadingState(
      (value) => { loading = value; },
      () => uploadAudio("/api/v1/process", formData, 100, fetchImpl),
    );
  } catch (error) {
    uploadError = error.message;
  }

  assert.equal(loading, false);
  assert.equal(uploadError, "Audio processing failed.");

  const retried = await withLoadingState(
    (value) => { loading = value; },
    () => uploadAudio("/api/v1/process", formData, 100, fetchImpl),
  );

  assert.equal(retried.response, "Processed");
  assert.equal(attempts, 2);
  assert.equal(loading, false);
});

test("non-recoverable WebSocket errors invoke microphone cleanup", async () => {
  const source = await readFile(
    resolve(frontendRoot, "src/hooks/useStreamingSession.js"),
    "utf8",
  );

  assert.match(
    source,
    /case "error":\s*setError\(message\.message \|\| "Streaming error\."\);\s*if \(!message\.recoverable\) \{\s*await cleanupMic\(\);/s,
  );
});

test("chat renders upload and stream errors visibly apart from status", () => {
  const html = renderToStaticMarkup(React.createElement(ChatFeedback, {
    uploadError: "Upload failed clearly.",
    streamError: "Gemini quota is exhausted.",
    uploading: false,
    isRecording: false,
    status: "ready",
    isWebSocketOpen: false,
  }));

  assert.match(html, /class="chat-errors"/);
  assert.match(html, /role="alert"[^>]*>Upload failed clearly\./);
  assert.match(html, /role="alert"[^>]*>Gemini quota is exhausted\./);
  assert.match(html, /role="status"[^>]*>Ready/);
});

test("chat feedback CSS is visible and spans the controls on narrow layouts", async () => {
  const css = await readFile(resolve(frontendRoot, "src/App.css"), "utf8");
  assert.match(
    css,
    /\.composer \.controls > \.chat-feedback\s*\{[^}]*grid-column:\s*1\s*\/\s*-1/s
  );
  assert.match(css, /\.chat-error\s*\{[^}]*background:[^}]*color:/s);
  assert.doesNotMatch(css, /\.voice-status\s*\{[^}]*clip:\s*rect/s);
  assert.match(css, /@media \(max-width: 760px\)/);
});
