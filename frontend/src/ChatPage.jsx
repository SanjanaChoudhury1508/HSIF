import { useEffect, useRef, useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { useStreamingSession } from "./hooks/useStreamingSession";
import { withLoadingState } from "./services/audioUpload";
import ChatFeedback from "./components/ChatFeedback";
import "../ui-preview/styles.css";
import "./App.css";

function Icon({ children }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {children}
    </svg>
  );
}

function Metric({ label, value, color }) {
  const raw = typeof value === "object" && value !== null
    ? value.score
    : value;

  const number = raw == null ? null : Number(raw);
  const percentage =
    number == null ? 0 : Math.max(0, Math.min(100, number * 100));

  
  return (
    <div className="meter">
      <span className="name">{label}</span>
      <span className="track">
        <span
          className={`fill ${color}`}
          style={{ width: `${percentage}%` }}
        />
      </span>
      <span className="val">
        {number == null ? "–" : number.toFixed(2)}
      </span>
    </div>
  );
}

export default function App() {
  const navigate = useNavigate();
  const {
    sessionId,
    status,
    isWebSocketOpen,
    turns,
    restoreLoading,
    startNewSession,
    transcript,
    humanState,
    strategy,
    sendTextMessage,
    processAudioUpload,
    assistantResponse,
    error: streamError,
    startSession,
    startRecording,
    endTurn,
    endSession,
    logout,
  } = useStreamingSession();

  const [audioFile, setAudioFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [search, setSearch] = useState("");
  const [inputMode, setInputMode] = useState("–");
  const [textMessage, setTextMessage] = useState("");
  const [settings, setSettings] = useState(() => {
    try {
      return {
        showHumanState: true,
        showStrategy: true,
        ...JSON.parse(localStorage.getItem("hsif-settings") || "{}"),
      };
    } catch {
      return {
        showHumanState: true,
        showStrategy: true,
      };
    }
  });
  const pendingConnection = useRef(false);
  const state = humanState;
  const currentStrategy = strategy;
  const currentTranscript = transcript;
  const currentResponse = assistantResponse;

  const emotion =
    state?.emotion?.label || state?.emotion || "–";

  const strategyName =
    currentStrategy?.strategy ||
    currentStrategy?.name ||
    "None yet";

  useEffect(() => {
    if (pendingConnection.current && status === "ready") {
      pendingConnection.current=false;
      startRecording();
    }
  }, [status, startRecording]);

  useEffect(() => {
    function syncSettings() {
      try {
        const saved = JSON.parse(
          localStorage.getItem("hsif-settings") || "{}"
        );
  
        setSettings({
          showHumanState: true,
          showStrategy: true,
          ...saved,
        });
      } catch {
        // Retain current settings if stored data is invalid.
      }
    }
  
    window.addEventListener("storage", syncSettings);
    window.addEventListener("hsif-settings-updated", syncSettings);
  
    return () => {
      window.removeEventListener("storage", syncSettings);
      window.removeEventListener("hsif-settings-updated", syncSettings);
    };
  }, []);

  async function handleUpload() {
    if (!audioFile || uploading) return;

    setUploadError("");

    try {
      await withLoadingState(setUploading, async () => {
        await processAudioUpload(audioFile);
        setInputMode("Audio upload");
        setAudioFile(null);
      });

    } catch (error) {
      setUploadError(error.message || "Audio processing failed.");
    } finally {
      setUploading(false);
    }
  }

  function handleLive() {
    if (status === "ready") {
      startRecording();
      setInputMode("Live microphone");
      return;
    }

    if (["idle", "ended", "disconnected", "error"].includes(status)) {
      pendingConnection.current=true;
      startSession();
    }
  }

  function handleRecord() {
    if (status === "ready") {
      startRecording();
      setInputMode("Microphone recording");
    } else if (["idle", "ended", "disconnected", "error"].includes(status)) {
      pendingConnection.current=false;
      startSession();
    }
  }

  function handleEnd() {
    if (status === "recording") {
      endTurn();
    } else if (!["idle", "ended", "disconnected"].includes(status)) {
      endSession();
    }
  }

  async function handleLogout() {
    pendingConnection.current = false;
    await logout();
    navigate("/login", { replace: true });
  }

  async function handleTextSubmit(event) {
    event.preventDefault();
    const message=textMessage.trim();
    if(!message) return;
    try{
      setTextMessage("");
      setUploadError("");

      await sendTextMessage(message);
      setInputMode("Text message");
    } catch{
      setTextMessage(message);
    }
    
  }

  const filteredHistory = turns
    .map((turn, index) => ({ ...turn, turnIndex: index }))
    .filter((turn) =>
      (turn.user_message || "")
        .toLowerCase()
        .includes(search.toLowerCase())
    )
    .reverse();

  const isRecording = status === "recording";
  const isBusy = ["connecting", "processing", "starting"].includes(status);

  return (
    <div className="shell light">
      <aside className="sidebar">
        <Link className="logo" to="/">
          <svg viewBox="0 0 32 32" aria-hidden="true">
            <rect width="32" height="32" rx="9" fill="#3fd6c2" />
            <g fill="#101b2e">
              <rect x="6" y="13" width="3" height="6" rx="1.5" />
              <rect x="11" y="9" width="3" height="14" rx="1.5" />
              <rect x="16" y="6" width="3" height="20" rx="1.5" />
              <rect x="21" y="10" width="3" height="12" rx="1.5" />
            </g>
          </svg>
          HSIF
        </Link>

        <nav className="side-nav" aria-label="App">
          <NavLink to="/dashboard">
            <Icon>
              <rect x="3" y="3" width="7" height="9" rx="1.5" />
              <rect x="14" y="3" width="7" height="5" rx="1.5" />
              <rect x="14" y="12" width="7" height="9" rx="1.5" />
              <rect x="3" y="16" width="7" height="5" rx="1.5" />
            </Icon>
            <span>Dashboard</span>
          </NavLink>

          <NavLink to="/chat">
            <Icon>
              <path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z" />
            </Icon>
            <span>Chat</span>
          </NavLink>

          <NavLink to="/history">
            <Icon>
              <circle cx="12" cy="12" r="9" />
              <path d="M12 7v5l3 2" />
            </Icon>
            <span>History</span>
          </NavLink>

          <NavLink to="/account">
            <Icon>
              <circle cx="12" cy="8" r="4" />
              <path d="M4 21a8 8 0 0 1 16 0" />
            </Icon>
            <span>Account</span>
          </NavLink>

          <NavLink to="/settings">
            <Icon>
              <circle cx="12" cy="12" r="3" />
              <path d="M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M19 5l-2 2M7 17l-2 2" />
            </Icon>
            <span>Settings</span>
          </NavLink>
        </nav>

        <button className="logout" type="button" onClick={handleLogout}>
          <Icon>
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9" />
          </Icon>
          <span>Log out</span>
        </button>
      </aside>

      <div className="main flush">
        <div className="workspace" data-chat>
          <aside className="hist-col" aria-label="History">
            <div className="col-head">
              <h2>In this chat</h2>
              <button
                className="btn btn-primary btn-sm"
                type="button"
                onClick={async () => {
                  pendingConnection.current=false;
                  await startNewSession();

                  setAudioFile(null);
                  setUploadError("");
                  setInputMode("-");
                  setTextMessage("");
                }}
              >
                New chat
              </button>
            </div>

            <div className="search-box">
              <label className="sr-only" htmlFor="hist-search">
                Search history
              </label>
              <input
                id="hist-search"
                type="text"
                placeholder="Search messages"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />
            </div>

            {filteredHistory.length === 0 ? (
              <div className="empty small">
                <Icon>
                  <circle cx="12" cy="12" r="9" />
                  <path d="M12 7v5l3 2" />
                </Icon>
                <strong>
                  {search ? "No matching messages":"No messages yet"}
                </strong>
                {search
                ? "Try another search term."
                : "Your conversation will appear here."}
              </div>
            ) : (
              <div className="hist-list">
                {filteredHistory.map((item) => (
                  <button
                    className="hist-item"
                    key={item.id || item.turnIndex}
                    type="button"
                    onClick={() => {
                      document
                       .getElementById(`turn-${item.turnIndex}`)
                       ?.scrollIntoView({
                          behavior: "smooth",
                          block: "center",
                      });
                    }}
                  >
                    <span className="t">{item.user_message}</span>
                    <span className="m">
                      <span className="badge">
                        {item.dialogue_strategy || "-"}
                      </span>
                    </span>
                  </button>
                ))}
              </div>
            )}
          </aside>

          <section className="chat-col" aria-label="Chat">
            <header className="chat-head">
              <div>
                <h1>Chat</h1>
                <p className="session">
                  {sessionId
                    ? `Session ${sessionId.slice(0, 8)}`
                    : "New session"}
                </p>
              </div>

              <button
                className="btn btn-ghost btn-sm"
                type="button"
                onClick={handleEnd}
                disabled={["idle", "ended", "disconnected"].includes(status)}
              >
                End session
              </button>
            </header>

            <div className="messages" role="log" aria-live="polite">
              {restoreLoading ? (
                <div className="empty">
                  <strong>Restoring conversation...</strong>
                </div>
              ) : turns.length === 0 && !currentTranscript && !currentResponse ? (
                <div className="empty">
                  <Icon>
                    <path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z" />
                  </Icon>
                  <strong>No messages yet</strong>
                  Start live streaming, record, or upload an audio file.
                  You can also type a message below.
                </div>
              ) : (
                <>
                  {turns.map((turn, index) => (
                    <div
                      className="conversation-turn"
                      id={`turn-${index}`}
                      key={turn.id || `${turn.created_at}-${index}`}
                    >
                      {turn.user_message && (
                        <div className="msg me">
                          <div className="bubble">
                            <p>{turn.user_message}</p>
                            <small>You</small>
                          </div>
                        </div>
                      )}
            
                      {turn.assistant_message && (
                        <div className="msg">
                          <div className="bubble">
                            <p>{turn.assistant_message}</p>
                            <small>HSIF Assistant</small>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
            
                  {currentTranscript && (
                    <div className="msg me">
                      <div className="bubble">
                        <p>{currentTranscript}</p>
                        <small>You</small>
                      </div>
                    </div>
                  )}
            
                  {currentResponse && (
                    <div className="msg">
                      <div className="bubble">
                        <p>{currentResponse}</p>
                        <small>HSIF Assistant</small>
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
            

            <div className="composer">
              {audioFile && (
                <div className="file-card">
                  <span className="fname">{audioFile.name}</span>
                  <span>{(audioFile.size / 1024 / 1024).toFixed(2)} MB</span>
                  <button
                    className="btn btn-ghost btn-sm"
                    type="button"
                    onClick={() => setAudioFile(null)}
                  >
                    Remove
                  </button>
                </div>
              )}

              <div className="controls">
                <button
                  className={`btn btn-ghost btn-sm ${isRecording ? "on" : ""}`}
                  type="button"
                  onClick={handleLive}
                  disabled={isBusy}
                  aria-pressed={isRecording}
                >
                  <Icon>
                    <rect x="9" y="3" width="6" height="11" rx="3" />
                    <path d="M5 11a7 7 0 0 0 14 0M12 18v3" />
                  </Icon>
                  <span>
                    {isRecording
                      ? "Live streaming"
                      : status === "ready"
                        ? "Start microphone"
                        : "Start live streaming"}
                  </span>
                </button>

                <button
                  className={`btn btn-ghost btn-sm btn-rec ${isRecording ? "on" : ""}`}
                  type="button"
                  onClick={handleRecord}
                  disabled={isBusy || isRecording}
                >
                  <i className="rec-dot" aria-hidden="true" />
                  <span>Record</span>
                </button>

                {isRecording && (
                  <button
                    className="btn btn-ghost btn-sm"
                    type="button"
                    onClick={endTurn}
                  >
                    Stop and process
                  </button>
                )}

                <label className="btn btn-ghost btn-sm" htmlFor="audio-file">
                  <Icon>
                    <path d="M12 16V4M7 9l5-5 5 5M4 20h16" />
                  </Icon>
                  Upload audio file
                </label>

                <input
                  id="audio-file"
                  className="sr-only"
                  type="file"
                  accept="audio/*"
                  onChange={(event) =>
                    setAudioFile(event.target.files?.[0] || null)
                  }
                />

                <ChatFeedback
                  uploadError={uploadError}
                  streamError={streamError}
                  uploading={uploading}
                  isRecording={isRecording}
                  status={status}
                  isWebSocketOpen={isWebSocketOpen}
                />
                
                {audioFile && (
                  <button
                    className="btn btn-primary btn-sm"
                    type="button"
                    onClick={handleUpload}
                    disabled={uploading || isBusy || isRecording}
                  >
                    {uploading ? "Processing..." : "Process audio"}
                  </button>
                )}
              </div>

              <form className="composer-row" onSubmit={handleTextSubmit}>
                <label className="sr-only" htmlFor="msg">
                  Message
                </label>
                <input
                  id="msg"
                  className="text-input"
                  type="text"
                  placeholder="Type your message..."
                  value={textMessage}
                  onChange={(event) => setTextMessage(event.target.value)}
                  disabled={status==="processing" || status==="recording"}
                />
                <button className="btn btn-primary" type="submit" disabled={!textMessage.trim() || status==="processing" || status==="recording"}>
                  {status==="processing" ? "Sending...":"Send"}
                </button>
              </form>
            </div>
          </section>

          {(settings.showHumanState || settings.showStrategy) && (
            <aside className="state-col" aria-label="Human state">
          
              {settings.showHumanState && (
                <>
                  <h2>Human state</h2>
          
                  <p className="desc">
                    Scores appear here once the assistant has analysed a message.
                  </p>
          
                  <div className="chips">
                    <span
                      className="chip"
                      style={{ background: "#eceffa", color: "var(--ink)" }}
                    >
                      Emotion: {emotion}
                    </span>
                  </div>
          
                  <div className="meters">
                    <Metric label="Confidence" value={state?.confidence} color="teal" />
                    <Metric label="Hesitation" value={state?.hesitation} color="amber" />
                    <Metric label="Engagement" value={state?.engagement} color="violet" />
                    <Metric label="Cognitive load" value={state?.cognitive_load} color="coral" />
                  </div>
          
                  <h3>Session details</h3>
          
                  <dl className="kv">
                    <dt>Messages</dt>
                    <dd>{turns.length}</dd>
                    <dt>Last input</dt>
                    <dd>{inputMode}</dd>
                  </dl>
                </>
              )}
          
              {settings.showStrategy && (
                <div className="strategy-box">
                  <small>Recommended strategy</small>
                  {strategyName}
          
                  {currentStrategy?.reason && (
                    <p>{currentStrategy.reason}</p>
                  )}
                </div>
              )}
          
            </aside>
          )}
        </div>
      </div>
    </div>
  );
}
