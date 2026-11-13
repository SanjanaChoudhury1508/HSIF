
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import AppShell from "../components/AppShell";
import {
  fetchSessionDetail,
  fetchSessionSummaries,
} from "../services/sessionData";

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1"
).replace(/\/$/, "");

function formatDate(value) {
  if (!value) return "Date unavailable";

  return new Date(value).toLocaleString([], {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function formatLabel(value) {
  if (typeof value !== "string" || !value.trim()) return "Not available";

  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function Score({ label, value }) {
  const valid = isValidScore(value);
  const score = valid ? value : null;

  return (
    <div className="history-score">
      <div className="history-score-heading">
        <span>{label}</span>
        <strong>{valid ? `${Math.round(score * 100)}%` : "—"}</strong>
      </div>
      <div className="history-score-track">
        <span
          style={{
            width: `${valid ? Math.max(0, Math.min(100, score * 100)) : 0}%`,
          }}
        />
      </div>
    </div>
  );
}

function isValidScore(value) {
  return typeof value === "number" && Number.isFinite(value) && value >= 0 && value <= 1;
}

export default function HistoryPage() {
  const [sessions, setSessions] = useState([]);
  const [selectedSession, setSelectedSession] = useState(null);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState("");
  const [detailError, setDetailError] = useState("");
  const [detailErrorSessionId, setDetailErrorSessionId] = useState(null);
  const listRequestRef = useRef(null);
  const detailRequestRef = useRef(null);

  const loadSessions = useCallback(async () => {
    if (listRequestRef.current) return;

    const controller = new AbortController();
    listRequestRef.current = controller;
    setLoading(true);
    setError("");
    setSessions([]);
    setSelectedSession(null);
    setDetailError("");
    setDetailErrorSessionId(null);

    const detailRequest = detailRequestRef.current;
    detailRequestRef.current = null;
    detailRequest?.controller.abort();
    setDetailLoading(false);

    try {
      const sessions = await fetchSessionSummaries(
        API_BASE_URL,
        fetch,
        controller.signal,
      );
      if (controller.signal.aborted) return;
      setSessions(
        sessions
          .filter((session) => session.turn_count > 0)
          .sort((a, b) => Date.parse(b.updated_at) - Date.parse(a.updated_at))
      );
    } catch (err) {
      if (!controller.signal.aborted) {
        setSessions([]);
        setError(err.message || "Could not connect to the server.");
      }
    } finally {
      if (listRequestRef.current === controller) {
        listRequestRef.current = null;
        if (!controller.signal.aborted) setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadSessions();
    return () => {
      const listRequest = listRequestRef.current;
      listRequestRef.current = null;
      listRequest?.abort();

      const detailRequest = detailRequestRef.current;
      detailRequestRef.current = null;
      detailRequest?.controller.abort();
    };
  }, [loadSessions]);

  const openSession = useCallback(async (sessionId) => {
    if (detailRequestRef.current?.sessionId === sessionId) return;
    detailRequestRef.current?.controller.abort();

    const controller = new AbortController();
    detailRequestRef.current = { sessionId, controller };
    setDetailLoading(true);
    setSelectedSession(null);
    setDetailError("");
    setDetailErrorSessionId(null);

    try {
      const data = await fetchSessionDetail(
        API_BASE_URL,
        sessionId,
        fetch,
        controller.signal,
      );
      if (controller.signal.aborted) return;
      setSelectedSession(data);
    } catch (err) {
      if (!controller.signal.aborted) {
        setDetailError(err.message || "Could not load this conversation.");
        setDetailErrorSessionId(sessionId);
      }
    } finally {
      if (detailRequestRef.current?.controller === controller) {
        detailRequestRef.current = null;
        if (!controller.signal.aborted) setDetailLoading(false);
      }
    }
  }, []);

  const filteredSessions = useMemo(() => {
    const query = search.trim().toLowerCase();

    if (!query) return sessions;

    return sessions.filter((session) =>
      (session.preview || "").toLowerCase().includes(query) ||
      session.session_id.toLowerCase().includes(query)
    );
  }, [sessions, search]);

  return (
    <AppShell
      title="History"
      subtitle="Every saved conversation, newest first"
      action={
        <Link className="btn btn-primary btn-sm" to="/chat">
          New chat
        </Link>
      }
    >
      <div className="page-tools">
        <div className="search-box">
          <label className="sr-only" htmlFor="h-search">
            Search sessions
          </label>
          <input
            id="h-search"
            type="text"
            placeholder="Search conversations"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>
      </div>

      {error && (
        <div className="history-error" role="alert">
          {error}
          <button type="button" onClick={loadSessions} disabled={loading}>
            Retry
          </button>
        </div>
      )}

      {loading ? (
        <section className="panel">
          <div className="empty">Loading saved conversations...</div>
        </section>
      ) : error ? (
        <section className="panel">
          <div className="empty">Sessions are unavailable. Retry to load the current list.</div>
        </section>
      ) : sessions.length === 0 ? (
        <section className="panel">
          <div className="empty">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <circle cx="12" cy="12" r="9" />
              <path d="M12 7v5l3 2" />
            </svg>

            <strong>No saved conversations yet</strong>
            Completed conversations will appear here.
            <br />
            <Link className="btn btn-primary btn-sm" to="/chat">
              Start a chat
            </Link>
          </div>
        </section>
      ) : (
        <div className="history-layout">
          <section className="panel history-list-panel">
            <div className="history-list-heading">
              <strong>Saved conversations</strong>
              <span>{filteredSessions.length} sessions</span>
            </div>

            {filteredSessions.length === 0 ? (
              <div className="empty">
                No conversations match your search.
              </div>
            ) : (
              <div className="history-list">
                {filteredSessions.map((session) => (
                  <button
                    type="button"
                    key={session.session_id}
                    className={`hist-item ${
                      selectedSession?.session_id === session.session_id
                        ? "selected"
                        : ""
                    }`}
                    onClick={() => openSession(session.session_id)}
                  >
                    <div className="history-item-top">
                      <strong>
                        {session.preview || "Conversation"}
                      </strong>
                      <span>{session.turn_count} turns</span>
                    </div>

                    <div className="history-item-bottom">
                      <span>{formatDate(session.updated_at)}</span>
                      <span>
                        {session.session_id.slice(0, 8)}...
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </section>

          <section className="panel history-detail-panel">
            {detailLoading ? (
              <div className="empty">Loading conversation...</div>
            ) : detailError ? (
              <div className="history-error" role="alert">
                {detailError}
                <button
                  type="button"
                  onClick={() => openSession(detailErrorSessionId)}
                  disabled={detailLoading}
                >
                  Retry
                </button>
              </div>
            ) : selectedSession ? (
              <>
                <div className="history-detail-header">
                  <div>
                    <strong>Conversation details</strong>
                    <p>{formatDate(selectedSession.created_at)}</p>
                  </div>

                  <button
                    type="button"
                    className="history-close"
                    onClick={() => setSelectedSession(null)}
                    aria-label="Close conversation details"
                  >
                    ×
                  </button>
                </div>

                <div className="history-messages">
                  {selectedSession.turns.map((turn) => (
                    <article className="history-turn" key={turn.id}>
                      <div className="history-message user">
                        <span className="history-message-label">
                          You
                        </span>
                        <p>{turn.user_message}</p>
                      </div>

                      <div className="history-message assistant">
                        <span className="history-message-label">
                          HSIF Assistant
                        </span>
                        <p>{turn.assistant_message}</p>
                      </div>

                      <div className="history-turn-meta">
                        <span>
                          Strategy: {formatLabel(turn.dialogue_strategy)}
                        </span>
                        <span>{formatDate(turn.created_at)}</span>
                      </div>

                      {turn.human_state && (
                        <div className="history-state">
                          <strong>Human state analysis</strong>

                          <div className="history-score-grid">
                            <Score
                              label="Confidence"
                              value={turn.human_state.confidence?.score}
                            />
                            <Score
                              label="Engagement"
                              value={turn.human_state.engagement?.score}
                            />
                            <Score
                              label="Hesitation"
                              value={turn.human_state.hesitation?.score}
                            />
                            <Score
                              label="Cognitive load"
                              value={turn.human_state.cognitive_load?.score}
                            />
                          </div>

                          {turn.human_state.emotion &&
                            typeof turn.human_state.emotion === "object" &&
                            !Array.isArray(turn.human_state.emotion) && (
                            <p className="history-emotion">
                              Emotion:{" "}
                              <strong>
                                {formatLabel(
                                  turn.human_state.emotion.label
                                )}
                              </strong>
                              {" · "}
                              {isValidScore(turn.human_state.emotion.score)
                                ? `${Math.round(turn.human_state.emotion.score * 100)}% score`
                                : "Score unavailable"}
                            </p>
                          )}
                        </div>
                      )}
                    </article>
                  ))}
                </div>
              </>
            ) : (
              <div className="empty">
                <strong>Select a conversation</strong>
                Choose a saved session to view its messages and analysis.
              </div>
            )}
          </section>
        </div>
      )}
    </AppShell>
  );
}
