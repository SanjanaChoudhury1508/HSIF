import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { test } from "node:test";

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");

test("History details mark invalid human-state observations as not measured", async () => {
  const historyPage = await readFile(
    resolve(frontendRoot, "src/pages/HistoryPage.jsx"),
    "utf8",
  );

  assert.match(
    historyPage,
    /turn\.human_state\?\._temporal\?\.observation_valid !== false/,
  );
  assert.match(historyPage, /observationSource === "text_only"/);
  assert.match(historyPage, /this interaction used text input/);
  assert.match(historyPage, /observationSource === "audio"/);
  assert.match(historyPage, /usable audio features were unavailable/);
  assert.match(historyPage, /Emotion was not measured for this interaction/);
  assert.doesNotMatch(historyPage, /Not measured for this text-only interaction/);
  assert.match(historyPage, /function Score\(\{ label, value, observationValid = true \}\)/);
  assert.match(historyPage, /valid \? `\$\{Math\.round\(score \* 100\)\}%` : "N\/A"/);
  assert.match(historyPage, /observationValid\s*\? formatLabel\(turn\.human_state\.emotion\.label\)\s*:\s*"Not measured"/);
  assert.match(historyPage, /observationValid &&\s*isValidScore\(turn\.human_state\.emotion\.score\)/);
});
