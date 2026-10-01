import { useState } from "react";

const API_BASE_URL = "http://localhost:8000/api/v1";

function App() {
  const [audioFile, setAudioFile] = useState(null);
  const [sessionId] = useState("review2-demo");

  const [result, setResult] = useState(null);
  const [sessionState, setSessionState] = useState(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const processAudio = async () => {
    if (!audioFile) {
      setError("Please select an audio file.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const formData = new FormData();
      formData.append("audio", audioFile);

      const response = await fetch(
        `${API_BASE_URL}/process?session_id=${encodeURIComponent(sessionId)}`,
        {
          method: "POST",
          body: formData,
        }
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);

        throw new Error(
          errorData?.detail || `Backend returned ${response.status}`
        );
      }

      const data = await response.json();
      setResult(data);

      // Fetch session-level human state after processing.
      const stateResponse = await fetch(
        `${API_BASE_URL}/session/${encodeURIComponent(sessionId)}/state`
      );

      if (!stateResponse.ok) {
        throw new Error(
          `Failed to fetch session state (${stateResponse.status})`
        );
      }

      const stateData = await stateResponse.json();
      setSessionState(stateData);
    } catch (err) {
      setError(err.message || "Failed to connect to HSIF backend.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: "40px", fontFamily: "Arial, sans-serif" }}>
      <h1>HSIF</h1>

      <p>Human State Intelligence Framework</p>

      <hr />

      <h2>Process Audio</h2>

      <p>
        Session ID: <strong>{sessionId}</strong>
      </p>

      <input
        type="file"
        accept=".wav,.mp3,.m4a,.ogg,.flac,.aac"
        onChange={(event) => setAudioFile(event.target.files[0])}
      />

      <br />
      <br />

      <button onClick={processAudio} disabled={loading}>
        {loading ? "Processing..." : "Process Audio"}
      </button>

      {error && (
        <p style={{ color: "red" }}>
          Error: {error}
        </p>
      )}

      {result && (
        <div style={{ marginTop: "30px" }}>
          <hr />

          <h2>Transcript</h2>

          <p>{result.speech?.transcript}</p>

          <h2>Current Human State</h2>

          <ul>
            <li>
              Emotion: {result.human_state?.emotion?.label} (
              {result.human_state?.emotion?.score})
            </li>

            <li>
              Hesitation: {result.human_state?.hesitation?.score}
            </li>

            <li>
              Confidence: {result.human_state?.confidence?.score}
            </li>

            <li>
              Engagement: {result.human_state?.engagement?.score}
            </li>

            <li>
              Cognitive Load: {result.human_state?.cognitive_load?.score}
            </li>
          </ul>

          <h2>Dialogue Strategy</h2>

          <p>
            <strong>
              {result.dialogue?.policy?.strategy}
            </strong>
          </p>

          <p>{result.dialogue?.policy?.reason}</p>

          <h2>AI Response</h2>

          <p>{result.response}</p>

          <h2>Conversation History</h2>

          {result.dialogue?.history?.length > 0 ? (
            result.dialogue.history.map((turn, index) => (
              <div key={index}>
                <p>
                  <strong>User:</strong> {turn.user_message}
                </p>

                <p>
                  <strong>Assistant:</strong> {turn.assistant_message}
                </p>

                <hr />
              </div>
            ))
          ) : (
            <p>No previous conversation.</p>
          )}
        </div>
      )}

      {sessionState && (
        <div style={{ marginTop: "30px" }}>
          <hr />

          <h2>Human State Trajectory</h2>

          <p>
            Total recorded states:{" "}
            <strong>{sessionState.trajectory?.length || 0}</strong>
          </p>

          {sessionState.trajectory?.map((state) => (
            <div key={state.step} style={{ marginBottom: "20px" }}>
              <h3>Turn {state.step}</h3>

              <ul>
                <li>
                   Emotion: {state.emotion?.label} (
                   {state.emotion?.score})
                </li>

                <li>
                  Hesitation: {state.hesitation}
                </li>

                <li>
                  Confidence: {state.confidence}
                </li>

                <li>
                  Engagement: {state.engagement}
                </li>

                <li>
                  Cognitive Load: {state.cognitive_load}
                </li>
              </ul>
            </div>
          ))}

          <h2>State Changes</h2>

          {sessionState.changes?.length > 0 ? (
            sessionState.changes.map((change, index) => (
              <div key={index}>
                <p>
                  <strong>
                    Turn {change.from_step} → Turn {change.to_step}
                  </strong>
                </p>

                <pre>
                  {JSON.stringify(change.changes, null, 2)}
                </pre>
              </div>
            ))
          ) : (
            <p>No significant state changes detected.</p>
          )}
        </div>
      )}
    </div>
  );
}

export default App;