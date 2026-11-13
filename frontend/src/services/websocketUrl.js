export const DEFAULT_API_BASE_URL = "http://localhost:8000/api/v1";

function withoutTrailingSlashes(value) {
  return value.replace(/\/+$/, "");
}

export function resolveWebSocketBaseUrl(
  apiBaseUrl = DEFAULT_API_BASE_URL,
  explicitWebSocketBaseUrl = "",
) {
  const explicit = explicitWebSocketBaseUrl.trim();
  if (explicit) {
    const explicitUrl = new URL(explicit);
    if (explicitUrl.protocol !== "ws:" && explicitUrl.protocol !== "wss:") {
      throw new Error("VITE_WS_BASE_URL must use ws or wss.");
    }
    explicitUrl.pathname = withoutTrailingSlashes(explicitUrl.pathname);
    explicitUrl.search = "";
    explicitUrl.hash = "";
    return `${explicitUrl.origin}${explicitUrl.pathname}`;
  }

  const apiUrl = new URL(apiBaseUrl);
  if (apiUrl.protocol === "http:") {
    apiUrl.protocol = "ws:";
  } else if (apiUrl.protocol === "https:") {
    apiUrl.protocol = "wss:";
  } else {
    throw new Error("VITE_API_BASE_URL must use http or https.");
  }

  const apiPath = withoutTrailingSlashes(apiUrl.pathname)
    .replace(/\/api\/v1$/i, "");
  apiUrl.search = "";
  apiUrl.hash = "";

  return `${apiUrl.origin}${apiPath}`;
}

export function buildSessionWebSocketUrl(
  sessionId,
  apiBaseUrl = DEFAULT_API_BASE_URL,
  explicitWebSocketBaseUrl = "",
) {
  const baseUrl = resolveWebSocketBaseUrl(
    apiBaseUrl,
    explicitWebSocketBaseUrl,
  );
  const normalizedBaseUrl = `${withoutTrailingSlashes(baseUrl)}/`;
  const basePath = withoutTrailingSlashes(
    new URL(normalizedBaseUrl).pathname
  );
  const route = /\/ws$/i.test(basePath)
    ? `session/${encodeURIComponent(sessionId)}`
    : `ws/session/${encodeURIComponent(sessionId)}`;
  return new URL(
    route,
    normalizedBaseUrl,
  ).toString();
}
