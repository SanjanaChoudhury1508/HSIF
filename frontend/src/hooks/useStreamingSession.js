
import { useCallback, useEffect, useRef, useState } from "react";
import { startMicrophoneStreaming } from "../services/audioCapture";

const WS_BASE_URL = "ws://localhost:8000";

export function useStreamingSession() {
  const [sessionId, setSessionId] = useState(null);
  const [status, setStatus] = useState("idle");
  const [transcript, setTranscript] = useState("");
  const [humanState, setHumanState] = useState(null);
  const [strategy, setStrategy] = useState(null);
  const [assistantResponse, setAssistantResponse] = useState("");
  const [error, setError] = useState("");

  const socketRef = useRef(null);
  const stopMicRef = useRef(null);
  const readyRef = useRef(false);
  const closingRef = useRef(false);

  const cleanupMic = useCallback(async () => {
    const stop = stopMicRef.current;
    stopMicRef.current = null;

    if (stop) {
      await stop();
    }
  }, []);

  const startSession = useCallback(async () => {
    if (
      socketRef.current &&
      socketRef.current.readyState !== WebSocket.CLOSED
    ) {
      setError("A session is already active.");
      return;
    }

    setError("");
    setTranscript("");
    setHumanState(null);
    setStrategy(null);
    setAssistantResponse("");
    setStatus("connecting");
    readyRef.current = false;
    closingRef.current = false;

    const id = crypto.randomUUID();
    setSessionId(id);

    const socket = new WebSocket(
      `${WS_BASE_URL}/ws/session/${encodeURIComponent(id)}`
    );

    socketRef.current = socket;

    socket.onopen = () => {
      socket.send(JSON.stringify({
        type: "start_session",
        protocol_version: 1,
        audio: {
          encoding: "pcm_s16le",
          sample_rate: 16000,
          channels: 1,
        },
      }));
    };

    socket.onmessage = async (event) => {
      let message;

      try {
        message = JSON.parse(event.data);
      } catch {
        setError("The server returned an invalid event.");
        return;
      }

      switch (message.type) {
        case "session_ready":
          readyRef.current = true;
          setStatus("ready");
          break;

        case "transcript_partial":
          setTranscript(message.text || "");
          break;

        case "transcript_final":
          setTranscript(message.text || "");
          break;

        case "human_state_update":
          setHumanState(message.state);
          break;

        case "dialogue_strategy":
          setStrategy(message);
          break;

        case "assistant_response":
          setAssistantResponse(message.text || "");
          setStatus("ready");
          break;

        case "session_ended":
          setStatus("ended");
          break;

        case "error":
          setError(message.message || "Streaming error.");
          if (!message.recoverable) {
            await cleanupMic();
            setStatus("error");
          }
          break;

        default:
          // Ignore events this frontend version does not use.
          break;
      }
    };

    socket.onerror = () => {
      setError("WebSocket connection failed.");
    };

    socket.onclose = async () => {
      readyRef.current = false;
      await cleanupMic();

      if (!closingRef.current) {
        setStatus((current) =>
          current === "error" ? "error" : "disconnected"
        );
      }
    };
  }, [cleanupMic]);

  const startRecording = useCallback(async () => {
    const socket = socketRef.current;

    if (
      !readyRef.current ||
      !socket ||
      socket.readyState !== WebSocket.OPEN
    ) {
      setError("Connect and wait for session_ready first.");
      return;
    }

    if (stopMicRef.current) {
      setError("Recording is already active.");
      return;
    }

    try {
      setError("");
      setTranscript("");
      setAssistantResponse("");

      const stop = await startMicrophoneStreaming(socket);
      stopMicRef.current = stop;

      setStatus("recording");
    } catch (err) {
      setError(err.message || "Could not access the microphone.");
      setStatus("ready");
    }
  }, []);

  const endTurn = useCallback(async () => {
    const socket = socketRef.current;

    if (!socket || socket.readyState !== WebSocket.OPEN) {
      setError("The WebSocket is not connected.");
      return;
    }

    if (!stopMicRef.current) {
      setError("Start recording before ending a turn.");
      return;
    }

    setStatus("processing");

    // Stop capture before sending the end-turn message.
    await cleanupMic();

    socket.send(JSON.stringify({
      type: "end_turn",
      turn_id: crypto.randomUUID(),
    }));
  }, [cleanupMic]);

  const endSession = useCallback(async () => {
    closingRef.current = true;
    await cleanupMic();

    const socket = socketRef.current;

    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: "end_session" }));
    } else {
      setStatus("ended");
    }
  }, [cleanupMic]);

  useEffect(() => {
    return () => {
      closingRef.current = true;

      const stop = stopMicRef.current;
      stopMicRef.current = null;

      if (stop) {
        void stop();
      }

      const socket = socketRef.current;
      if (socket) {
        socket.close();
      }
    };
  }, []);

  return {
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
  };
}
