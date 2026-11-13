function isRecord(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function isValidDate(value) {
  return typeof value === "string" && Number.isFinite(Date.parse(value));
}

function validateSessionSummary(session, index) {
  if (!isRecord(session)) {
    throw new Error(`Session ${index + 1} has an invalid format.`);
  }
  if (typeof session.session_id !== "string" || !session.session_id.trim()) {
    throw new Error(`Session ${index + 1} is missing its session ID.`);
  }
  if (!Number.isInteger(session.turn_count) || session.turn_count < 0) {
    throw new Error(`Session ${session.session_id} has an invalid turn count.`);
  }
  if (!isValidDate(session.updated_at)) {
    throw new Error(`Session ${session.session_id} has an invalid update date.`);
  }
  if (
    session.preview !== undefined &&
    session.preview !== null &&
    typeof session.preview !== "string"
  ) {
    throw new Error(`Session ${session.session_id} has an invalid preview.`);
  }
  return session;
}

function validateTurn(turn, index, sessionId) {
  const label = `Turn ${index + 1} in session ${sessionId}`;
  if (!isRecord(turn)) throw new Error(`${label} has an invalid format.`);
  if (
    !(typeof turn.id === "string" && turn.id.trim()) &&
    !(typeof turn.id === "number" && Number.isFinite(turn.id))
  ) {
    throw new Error(`${label} is missing its ID.`);
  }
  if (typeof turn.user_message !== "string" || typeof turn.assistant_message !== "string") {
    throw new Error(`${label} has invalid message text.`);
  }
  if (!isValidDate(turn.created_at)) {
    throw new Error(`${label} has an invalid creation date.`);
  }
  if (turn.human_state !== null && turn.human_state !== undefined && !isRecord(turn.human_state)) {
    throw new Error(`${label} has invalid human-state data.`);
  }
  if (
    turn.dialogue_strategy !== null &&
    turn.dialogue_strategy !== undefined &&
    typeof turn.dialogue_strategy !== "string"
  ) {
    throw new Error(`${label} has an invalid dialogue strategy.`);
  }
  return turn;
}

export function validateSessionList(payload) {
  if (!isRecord(payload) || !Array.isArray(payload.sessions)) {
    throw new Error("The server returned an invalid session list.");
  }
  return payload.sessions.map(validateSessionSummary);
}

export function validateSessionDetail(payload, expectedSessionId) {
  if (!isRecord(payload)) {
    throw new Error("The server returned invalid conversation details.");
  }
  if (
    typeof payload.session_id !== "string" ||
    !payload.session_id.trim() ||
    (expectedSessionId && payload.session_id !== expectedSessionId)
  ) {
    throw new Error("The server returned conversation details for an unexpected session.");
  }
  if (!isValidDate(payload.created_at) || !isValidDate(payload.updated_at)) {
    throw new Error(`Session ${payload.session_id} has invalid dates.`);
  }
  if (!Array.isArray(payload.turns)) {
    throw new Error(`Session ${payload.session_id} has an invalid turns list.`);
  }
  payload.turns.forEach((turn, index) => validateTurn(turn, index, payload.session_id));
  return payload;
}

async function readJsonResponse(url, errorLabel, fetchImpl, signal) {
  const response = await fetchImpl(url, { signal });
  if (!response.ok) {
    throw new Error(`${errorLabel} (${response.status}).`);
  }
  try {
    return await response.json();
  } catch {
    throw new Error("The server returned an invalid JSON response.");
  }
}

export async function fetchSessionSummaries(apiBaseUrl, fetchImpl = fetch, signal) {
  const payload = await readJsonResponse(
    `${apiBaseUrl}/sessions`,
    "Could not load sessions",
    fetchImpl,
    signal,
  );
  return validateSessionList(payload);
}

export async function fetchSessionDetail(
  apiBaseUrl,
  sessionId,
  fetchImpl = fetch,
  signal,
) {
  const payload = await readJsonResponse(
    `${apiBaseUrl}/sessions/${encodeURIComponent(sessionId)}`,
    "Could not load conversation",
    fetchImpl,
    signal,
  );
  return validateSessionDetail(payload, sessionId);
}

export async function fetchDashboardData(apiBaseUrl, fetchImpl = fetch, signal) {
  const sessions = (await fetchSessionSummaries(apiBaseUrl, fetchImpl, signal))
    .filter((session) => session.turn_count > 0)
    .sort((a, b) => Date.parse(b.updated_at) - Date.parse(a.updated_at));

  const maxConcurrentDetails = 4;
  const results = new Array(sessions.length);
  let nextSessionIndex = 0;

  async function fetchDetailsWorker() {
    while (nextSessionIndex < sessions.length) {
      const index = nextSessionIndex;
      nextSessionIndex += 1;

      try {
        results[index] = {
          status: "fulfilled",
          value: await fetchSessionDetail(
            apiBaseUrl,
            sessions[index].session_id,
            fetchImpl,
            signal,
          ),
        };
      } catch (reason) {
        results[index] = { status: "rejected", reason };
      }
    }
  }

  const workerCount = Math.min(maxConcurrentDetails, sessions.length);
  await Promise.all(
    Array.from({ length: workerCount }, () => fetchDetailsWorker())
  );

  if (signal?.aborted) {
    throw new DOMException("Dashboard request was cancelled.", "AbortError");
  }

  const successfulDetails = results
    .filter((result) => result.status === "fulfilled")
    .map((result) => result.value);
  const failedDetails = results.length - successfulDetails.length;
  const turns = successfulDetails
    .flatMap((detail) => detail.turns)
    .sort((a, b) => Date.parse(a.created_at) - Date.parse(b.created_at));

  if (failedDetails > 0) {
    const error = new Error(
      `Could not load details for ${failedDetails} session(s). Dashboard metrics may be incomplete; please retry.`
    );
    error.partialData = { sessions, turns };
    throw error;
  }

  return { sessions, turns };
}
