export function getWebSocketErrorTransition(currentStatus, recoverable) {
  return {
    status: recoverable
      ? currentStatus === "processing"
        ? "ready"
        : currentStatus
      : "error",
    cleanupMicrophone: !recoverable,
    closeSocket: false,
  };
}
