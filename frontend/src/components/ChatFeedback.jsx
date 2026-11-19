export default function ChatFeedback({
  uploadError,
  streamError,
  uploading,
  isRecording,
  status,
  isWebSocketOpen = false,
}) {
  const errors = [...new Set([uploadError, streamError].filter(Boolean))];
  const statusText = uploading
    ? "Processing audio..."
    : isRecording
      ? "Microphone active"
      : status === "connecting"
        ? "Connecting..."
        : status === "processing"
          ? "Processing turn..."
          : isWebSocketOpen
            ? "Connected"
            : status === "disconnected" || status === "error"
              ? "Disconnected"
              : "Ready";

  return (
    <div className="chat-feedback">
      {errors.length > 0 && (
        <div className="chat-errors">
          {errors.map((error) => (
            <p className="chat-error" role="alert" key={error}>
              {error}
            </p>
          ))}
        </div>
      )}
      <p className="voice-status" role="status">{statusText}</p>
    </div>
  );
}
