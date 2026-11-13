
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import AppShell from "../components/AppShell";
import { fetchDashboardData } from "../services/sessionData";

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
  if (!value) return "Not available";

  return String(value)
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function getScore(state, key) {
  if (!state || state._temporal?.observation_valid === false) {
    return null;
  }

  const rawValue = state[key]?.score;

  if (
    typeof rawValue !== "number" ||
    !Number.isFinite(rawValue) ||
    rawValue < 0 ||
    rawValue > 1
  ) {
    return null;
  }
  return rawValue;
}

function SummaryTile({ label, value, note }) {
  return (
    <div className="tile">
      <p className="label">{label}</p>
      <p className="value">{value}</p>
      <p className="note">{note}</p>
    </div>
  );
}

function EmptyState({ children, small = false }) {
  return (
    <div className={`empty${small ? " small" : ""}`}>
      <strong>{children}</strong>
    </div>
  );
}

export default function DashboardPage() {
  const [sessions, setSessions] = useState([]);
  const [turns, setTurns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const requestRef = useRef(null);

  const loadDashboard = useCallback(async () => {
    if (requestRef.current) return;

    const controller = new AbortController();
    requestRef.current = controller;
    setLoading(true);
    setError("");
    setSessions([]);
    setTurns([]);

    try {
      const data = await fetchDashboardData(
        API_BASE_URL,
        fetch,
        controller.signal,
      );
      if (controller.signal.aborted) return;
      setSessions(data.sessions);
      setTurns(data.turns);
    } catch (err) {
      if (!controller.signal.aborted) {
        setSessions(err.partialData?.sessions || []);
        setTurns(err.partialData?.turns || []);
        setError(err.message || "Could not connect to the server.");
      }
    } finally {
      if (requestRef.current === controller) {
        requestRef.current = null;
        if (!controller.signal.aborted) setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadDashboard();
    return () => {
      const controller = requestRef.current;
      requestRef.current = null;
      controller?.abort();
    };
  }, [loadDashboard]);

  const metrics = useMemo(() => {
    const validTurns = turns.filter(
      (turn) =>
        turn.human_state &&
        turn.human_state._temporal?.observation_valid !== false
    );

    const average = (key) => {
      const values = validTurns
        .map((turn) => getScore(turn.human_state, key))
        .filter((value) => value !== null);

      if (!values.length) return "—";

      return `${Math.round(
        (values.reduce((sum, value) => sum + value, 0) /
          values.length) *
          100
      )}%`;
    };

    const strategyCounts = {};

    turns.forEach((turn) => {
      const strategy = turn.dialogue_strategy;

      if (strategy) {
        strategyCounts[strategy] =
          (strategyCounts[strategy] || 0) + 1;
      }
    });

    const mostUsedStrategy = Object.entries(strategyCounts).sort(
      (a, b) => b[1] - a[1]
    )[0];

    return {
      totalTurns: turns.length,
      confidence: average("confidence"),
      hesitation: average("hesitation"),
      mostUsedStrategy: mostUsedStrategy
        ? formatLabel(mostUsedStrategy[0])
        : "—",
    };
  }, [turns]);

  const strategyDistribution = useMemo(() => {
    const counts = {};

    turns.forEach((turn) => {
      if (turn.dialogue_strategy) {
        counts[turn.dialogue_strategy] =
          (counts[turn.dialogue_strategy] || 0) + 1;
      }
    });

    return Object.entries(counts).sort(
      (a, b) => b[1] - a[1]
    );
  }, [turns]);

  const chartTurns = useMemo(() => {
    return turns
      .filter(
        (turn) =>
          turn.human_state &&
          turn.human_state._temporal?.observation_valid !== false
      )
      .slice(-8);
  }, [turns]);

  return (
    <AppShell
      title="Dashboard"
      subtitle="Your sessions at a glance"
      action={
        <Link className="btn btn-primary btn-sm" to="/chat">
          Start a chat
        </Link>
      }
    >
      {error && (
        <div className="history-error" role="alert">
          {error}
          <button type="button" onClick={loadDashboard} disabled={loading}>
            Retry
          </button>
        </div>
      )}

      {loading ? (
        <section className="panel">
          <div className="empty">Loading dashboard...</div>
        </section>
      ) : error && turns.length === 0 ? (
        <section className="panel">
          <div className="empty">
            Dashboard data is unavailable. Retry to load current metrics.
          </div>
        </section>
      ) : (
        <>
          <section className="tiles" aria-label="Summary">
            <SummaryTile
              label="Sessions"
              value={sessions.length}
              note="Saved conversations"
            />
            <SummaryTile
              label="Total conversations"
              value={metrics.totalTurns}
              note="Completed exchanges"
            />
            <SummaryTile
              label="Average confidence"
              value={metrics.confidence}
              note="Across valid observations"
            />
            <SummaryTile
              label="Average hesitation"
              value={metrics.hesitation}
              note="Across valid observations"
            />
          </section>

          <div className="dash-grid">
            <section className="panel" aria-labelledby="trend-title">
              <h2 id="trend-title">
                How speakers sound over time
              </h2>

              {chartTurns.length === 0 ? (
                <EmptyState>
                  No human-state observations available yet.
                </EmptyState>
              ) : (
                <div className="dashboard-trend">
                  <div className="dashboard-legend">
                    <span>Confidence</span>
                    <span>Engagement</span>
                    <span>Hesitation</span>
                  </div>

                  {chartTurns.map((turn, index) => (
                    <div className="dashboard-chart-row" key={turn.id}>
                      <span className="dashboard-chart-label">
                        {index + 1}
                      </span>

                      <div className="dashboard-chart-bars">
                        {["confidence", "engagement", "hesitation"].map(
                          (key) => {
                            const score = getScore(
                              turn.human_state,
                              key
                            );

                            return (
                              <div
                                className="dashboard-bar-track"
                                key={key}
                                title={`${formatLabel(key)}: ${
                                  score === null
                                    ? "Unavailable"
                                    : `${Math.round(score * 100)}%`
                                }`}
                              >
                                <span
                                  className={`dashboard-bar ${key}`}
                                  style={{
                                    width: `${
                                      score === null
                                        ? 0
                                        : Math.max(
                                            0,
                                            Math.min(100, score * 100)
                                          )
                                    }%`,
                                  }}
                                />
                              </div>
                            );
                          }
                        )}
                      </div>

                      <span className="dashboard-chart-date">
                        {formatDate(turn.created_at)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </section>

            <section className="panel" aria-labelledby="strat-title">
              <h2 id="strat-title">Strategies chosen</h2>

              {strategyDistribution.length === 0 ? (
                <EmptyState>
                  No dialogue strategies recorded yet.
                </EmptyState>
              ) : (
                <div className="dashboard-strategies">
                  <p className="dashboard-most-used">
                    Most used: <strong>{metrics.mostUsedStrategy}</strong>
                  </p>

                  {strategyDistribution.map(([strategy, count]) => {
                    const percentage = Math.round(
                      (count / metrics.totalTurns) * 100
                    );

                    return (
                      <div
                        className="dashboard-strategy"
                        key={strategy}
                      >
                        <div className="dashboard-strategy-heading">
                          <span>{formatLabel(strategy)}</span>
                          <strong>{count}</strong>
                        </div>

                        <div className="dashboard-bar-track">
                          <span
                            className="dashboard-bar strategy"
                            style={{ width: `${percentage}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </section>
          </div>

          <section className="panel" aria-labelledby="recent-title">
            <div className="dashboard-section-heading">
              <h2 id="recent-title">Recent sessions</h2>
              <Link to="/history">View all</Link>
            </div>

            {sessions.length === 0 ? (
              <EmptyState>
                No saved conversations yet. Start a chat to see activity here.
              </EmptyState>
            ) : (
              <div className="dashboard-recent">
                {sessions.slice(0, 5).map((session) => (
                  <Link
                    className="dashboard-recent-item"
                    to="/history"
                    key={session.session_id}
                  >
                    <div>
                      <strong>
                        {session.preview || "Conversation"}
                      </strong>
                      <span>{formatDate(session.updated_at)}</span>
                    </div>

                    <span className="dashboard-turn-count">
                      {session.turn_count} turns
                    </span>
                  </Link>
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </AppShell>
  );
}
