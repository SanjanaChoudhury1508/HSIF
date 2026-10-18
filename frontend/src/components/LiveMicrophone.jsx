
import { useStreamingSession } from "../hooks/useStreamingSession";

export default function LiveMicrophone() {
  const {
    sessionId,
    status,
    transcript,
    humanState,
    strategy,
    assistantResponse,
    error,
    startSession,
    startRecording,
    endTurn,
    endSession,
  } = useStreamingSession();

  const isRecording = status === "recording";
  const isProcessing = status === "processing";

  return (
    <section style={{ maxWidth: 760, margin: "30px auto", padding: 24 }}>
      <h2>HSIF Live Session</h2>

      <p>
        Status: <strong>{status}</strong>
      </p>

      {sessionId && (
        <p>
          Session ID: <code>{sessionId}</code>
        </p>
      )}

      <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
        <button
          onClick={startSession}
          disabled={["connecting", "ready", "recording", "processing"].includes(status)}
        >
          Connect
        </button>

        <button
          onClick={startRecording}
          disabled={status !== "ready"}
        >
          Start microphone
        </button>

        <button
          onClick={endTurn}
          disabled={!isRecording}
        >
          Stop and process turn
        </button>

        <button
          onClick={endSession}
          disabled={["idle", "ended", "disconnected"].includes(status)}
        >
          End session
        </button>
      </div>

      {isRecording && (
        <p role="status">Microphone is active. Speak now.</p>
      )}

      {isProcessing && (
        <p role="status">Processing your turn…</p>
      )}

      {error && (
        <p role="alert" style={{ color: "crimson" }}>
          {error}
        </p>
      )}

      <hr />

      <h3>Transcript</h3>
      <p>{transcript || "Your finalized transcript will appear here."}</p>

      <h3>Human State</h3>
      {humanState ? (
        <pre>{JSON.stringify(humanState, null, 2)}</pre>
      ) : (
        <p>No state received yet.</p>
      )}

      <h3>Dialogue Strategy</h3>
      {strategy ? (
        <pre>{JSON.stringify(strategy, null, 2)}</pre>
      ) : (
        <p>No strategy received yet.</p>
      )}

      <h3>Assistant Response</h3>
      <p>{assistantResponse || "No response yet."}</p>
    </section>
  );
}
