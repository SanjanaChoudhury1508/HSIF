import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { test } from "node:test";

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");

test("Chat sidebar routes use React Router links", async () => {
  const source = await readFile(
    resolve(frontendRoot, "src/ChatPage.jsx"),
    "utf8",
  );

  assert.match(source, /import\s*\{[^}]*\bLink\b[^}]*\bNavLink\b[^}]*\}\s*from\s*["']react-router-dom["']/);
  assert.match(source, /<Link\b[^>]*className="logo"[^>]*to="\/"/);

  for (const route of ["dashboard", "chat", "history", "account", "settings"]) {
    assert.match(
      source,
      new RegExp(`<NavLink\\s+to="/${route}"`),
      `Expected ${route} sidebar navigation to use NavLink`,
    );
    assert.doesNotMatch(
      source,
      new RegExp(`<a\\b[^>]*href="/${route}"`),
      `Found a document navigation anchor for ${route}`,
    );
  }
});
