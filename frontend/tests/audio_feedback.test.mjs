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
let AssistantMessage;
let HumanStatePanel;

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
  ({ default: AssistantMessage } = await vite.ssrLoadModule(
    "/src/components/AssistantMessage.jsx"
  ));
  ({ default: HumanStatePanel } = await vite.ssrLoadModule(
    "/src/components/HumanStatePanel.jsx"
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

test("chat visibly renders the safe LLM quota detail from the message API", async () => {
  const quotaMessage = "The AI request quota or rate limit has been reached. Please try again later.";
  const html = renderToStaticMarkup(React.createElement(ChatFeedback, {
    uploadError: "Upload failed clearly.",
    streamError: quotaMessage,
    uploading: false,
    isRecording: false,
    status: "ready",
    isWebSocketOpen: false,
  }));
  const hook = await readFile(
    resolve(frontendRoot, "src/hooks/useStreamingSession.js"),
    "utf8",
  );

  assert.match(html, /class="chat-errors"/);
  assert.match(html, /role="alert"[^>]*>Upload failed clearly\./);
  assert.ok(html.includes(`role="alert">${quotaMessage}</p>`));
  assert.match(html, /role="status"[^>]*>Ready/);
  assert.match(
    hook,
    /if \(!response\.ok\)\s*\{\s*throw new Error\(\s*data\.detail \|\| "Message processing failed\."\s*\);/s,
  );
  assert.match(hook, /setError\(err\.message \|\| "Could not send message\."\)/);
});

test("assistant messages render Markdown safely with formatting and line breaks", async () => {
  const markdown = [
    "# Heading",
    "",
    "**Bold** and *italic* text.",
    "",
    "First line",
    "Second line<br>Third line.",
    "",
    "- unordered one",
    "- unordered two",
    "",
    "1. ordered one",
    "2. ordered two",
    "",
    "Inline `code`.",
    "",
    "```js",
    "const answer = 42;",
    "```",
    "",
    "[A safe link](https://example.com)",
    "",
    "<script>alert('unsafe')</script>",
  ].join("\n");
  const html = renderToStaticMarkup(
    React.createElement(AssistantMessage, { content: markdown }),
  );

  assert.match(html, /<h1>Heading<\/h1>/);
  assert.match(html, /<strong>Bold<\/strong>/);
  assert.match(html, /<em>italic<\/em>/);
  assert.match(html, /<ul>[\s\S]*<li>unordered one<\/li>[\s\S]*<\/ul>/);
  assert.match(html, /<ol>[\s\S]*<li>ordered one<\/li>[\s\S]*<\/ol>/);
  assert.match(html, /First line<br\/>\s*Second line<br\/>\s*Third line\./);
  assert.match(html, /<code>code<\/code>/);
  assert.match(html, /<pre><code class="language-js">const answer = 42;/);
  assert.match(html, /<a href="https:\/\/example\.com">A safe link<\/a>/);
  assert.doesNotMatch(html, /<script\b/i);
  assert.match(html, /&lt;script&gt;alert/);

  const chatPage = await readFile(resolve(frontendRoot, "src/ChatPage.jsx"), "utf8");
  assert.match(chatPage, /<p>\{turn\.user_message\}<\/p>/);
  assert.match(chatPage, /<AssistantMessage content=\{turn\.assistant_message\} \/>/);
});

test("assistant renderer preserves the end of a long Markdown response", () => {
  const finalSentence = "**The complete answer ends here.**";
  const markdown = [
    "# Detailed answer",
    ...Array.from({ length: 120 }, (_, index) => `${index + 1}. A full explanation paragraph with useful detail.`),
    finalSentence,
  ].join("\n\n");
  const html = renderToStaticMarkup(
    React.createElement(AssistantMessage, { content: markdown }),
  );

  assert.ok(html.length > 5000);
  assert.ok(html.includes("<strong>The complete answer ends here.</strong>"));
});

test("chat marks text-only measurements as not measured and suppresses meters", async () => {
  const textTurn = {
    emotion: { label: "unknown", score: 0 },
    confidence: { score: 0 },
    hesitation: { score: 0 },
    engagement: { score: 0 },
    cognitive_load: { score: 0 },
    _temporal: { observation_valid: false, source: "text_only" },
  };
  const html = renderToStaticMarkup(
    React.createElement(HumanStatePanel, { state: textTurn }),
  );

  assert.match(html, /Emotion: Not measured/);
  assert.match(html, /measurements are unavailable/i);
  assert.doesNotMatch(html, /class="meter"/);
  assert.doesNotMatch(html, />0\.00</);

  // The current turn replaces a prior audio observation after text input.
  const turns = [
    { _temporal: { observation_valid: true, source: "audio" }, emotion: { label: "neutral" } },
    textTurn,
  ];
  const currentTurnHtml = renderToStaticMarkup(
    React.createElement(HumanStatePanel, { state: turns.at(-1) }),
  );
  assert.match(currentTurnHtml, /Emotion: Not measured/);
  assert.doesNotMatch(currentTurnHtml, /Emotion: neutral/);

  const chatPage = await readFile(resolve(frontendRoot, "src/ChatPage.jsx"), "utf8");
  const streamingHook = await readFile(
    resolve(frontendRoot, "src/hooks/useStreamingSession.js"),
    "utf8",
  );
  assert.match(chatPage, /<HumanStatePanel state=\{state\} \/>/);
  assert.match(streamingHook, /setHumanState\(newTurn\.human_state\)/g);
  assert.equal((streamingHook.match(/setHumanState\(newTurn\.human_state\)/g) || []).length, 2);
});

test("audio with invalid features is unmeasured, while valid neutral audio remains neutral", () => {
  const invalidAudioHtml = renderToStaticMarkup(
    React.createElement(HumanStatePanel, {
      state: {
        emotion: { label: "unknown", score: 0 },
        confidence: { score: 0 },
        _temporal: { observation_valid: false, source: "audio" },
      },
    }),
  );
  assert.match(invalidAudioHtml, /Emotion: Not measured/);
  assert.doesNotMatch(invalidAudioHtml, /class="meter"/);

  const neutralAudioHtml = renderToStaticMarkup(
    React.createElement(HumanStatePanel, {
      state: {
        emotion: { label: "neutral", score: 0.7 },
        confidence: { score: 0.6 },
        hesitation: { score: 0.1 },
        engagement: { score: 0.5 },
        cognitive_load: { score: 0.2 },
        _temporal: { observation_valid: true, source: "audio" },
      },
    }),
  );
  assert.match(neutralAudioHtml, /Emotion: neutral/);
  assert.match(neutralAudioHtml, /class="meter"/);
  assert.doesNotMatch(neutralAudioHtml, /Not measured/);
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
