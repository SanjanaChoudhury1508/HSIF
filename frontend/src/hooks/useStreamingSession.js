import { useCallback, useEffect, useRef, useState } from "react";
import {
  runMicrophoneStartOnce,
  startMicrophoneStreaming,
} from "../services/audioCapture";
import { uploadAudio } from "../services/audioUpload";
import { getWebSocketErrorTransition } from "../services/streamingErrors";
import {
  ACTIVE_SESSION_STORAGE_KEY,
  clearLocalUserSession,
  getRestorableSessionId,
} from "../services/localSession";
import {
  buildSessionWebSocketUrl,
  DEFAULT_API_BASE_URL,
} from "../services/websocketUrl";

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ||
  DEFAULT_API_BASE_URL
).replace(/\/$/, "");

export function useStreamingSession() {
  const [sessionId, setSessionId] = useState(null);
  const [status, setStatus] = useState("idle");
  const [isWebSocketOpen, setIsWebSocketOpen] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [humanState, setHumanState] = useState(null);
  const [strategy, setStrategy] = useState(null);
  const [assistantResponse, setAssistantResponse] = useState("");
  const [turns, setTurns] = useState([]);
  const [restoreLoading, setRestoreLoading] = useState(true);
  const [error, setError] = useState("");

  const socketRef = useRef(null);
  const stopMicRef = useRef(null);
  const microphoneStartingRef = useRef(false);
  const microphoneStartupIdRef = useRef(0);
  const restoreGenerationRef = useRef(0);
  const readyRef = useRef(false);
  const closingRef = useRef(false);
  const textSendingRef = useRef(false);

  const currentTurnRef = useRef({
    transcript: "",
    humanState: null,
    strategy: null,
  });

  const cleanupMic = useCallback(async () => {
    const stop = stopMicRef.current;
    stopMicRef.current = null;

    if (stop) await stop();
  }, []);

  // Restore the last active conversation.
  useEffect(() => {
    let cancelled = false;
    const restoreGeneration = restoreGenerationRef.current;

    async function restoreSession() {
      try {
        const savedId = getRestorableSessionId();

        if (!savedId) return;

        const response = await fetch(
          `${API_BASE_URL}/sessions/${encodeURIComponent(savedId)}`
        );

        if (!response.ok) {
          if (response.status === 404) {
            localStorage.removeItem(ACTIVE_SESSION_STORAGE_KEY);
            return;
          }

          throw new Error("Could not restore the saved conversation.");
        }

        const data = await response.json();

        if (
          cancelled ||
          restoreGeneration !== restoreGenerationRef.current
        ) return;

        const restoredTurns = data.turns || [];

        setSessionId(data.session_id);
        localStorage.setItem(ACTIVE_SESSION_STORAGE_KEY, data.session_id);
        setTurns(restoredTurns);

        const latestTurn = restoredTurns[restoredTurns.length - 1];

        if (latestTurn) {
          setHumanState(latestTurn.human_state || null);

          setStrategy(
            latestTurn.dialogue_strategy
              ? { strategy: latestTurn.dialogue_strategy }
              : null
          );
        }
      } catch (err) {
        if (
          !cancelled &&
          restoreGeneration === restoreGenerationRef.current
        ) {
          setError(err.message || "Session restoration failed.");
        }
      } finally {
        if (
          !cancelled &&
          restoreGeneration === restoreGenerationRef.current
        ) {
          setRestoreLoading(false);
        }
      }
    }

    restoreSession();

    return () => {
      cancelled = true;
    };
  }, []);

  const startNewSession = useCallback(async () => {
    closingRef.current = true;
    readyRef.current = false;
    restoreGenerationRef.current += 1;
    microphoneStartupIdRef.current += 1;

    await cleanupMic();

    const socket = socketRef.current;
    socketRef.current = null;
    setIsWebSocketOpen(false);

    if (socket) socket.close();

    localStorage.removeItem(ACTIVE_SESSION_STORAGE_KEY);

    setSessionId(null);
    setTurns([]);
    setTranscript("");
    setHumanState(null);
    setStrategy(null);
    setAssistantResponse("");
    setError("");
    setStatus("idle");

    currentTurnRef.current = {
      transcript: "",
      humanState: null,
      strategy: null,
    };

    closingRef.current = false;
  }, [cleanupMic]);

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
    setAssistantResponse("");
    setIsWebSocketOpen(false);
    setStatus("connecting");

    readyRef.current = false;
    closingRef.current = false;

    currentTurnRef.current = {
      transcript: "",
      humanState: null,
      strategy: null,
    };

    const id = sessionId || crypto.randomUUID();

    setSessionId(id);
    localStorage.setItem(ACTIVE_SESSION_STORAGE_KEY, id);

    const socket = new WebSocket(buildSessionWebSocketUrl(
      id,
      API_BASE_URL,
      import.meta.env.VITE_WS_BASE_URL || "",
    ));

    socketRef.current = socket;

    socket.onopen = () => {
      if (socketRef.current === socket) {
        setIsWebSocketOpen(socket.readyState === WebSocket.OPEN);
      }
      socket.send(
        JSON.stringify({
          type: "start_session",
          protocol_version: 1,
          audio: {
            encoding: "pcm_s16le",
            sample_rate: 16000,
            channels: 1,
          },
        })
      );
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
        case "transcript_final":
          currentTurnRef.current.transcript = message.text || "";
          setTranscript(message.text || "");
          break;

        case "human_state_update":
          currentTurnRef.current.humanState = message.state;
          setHumanState(message.state);
          break;

        case "dialogue_strategy":
          currentTurnRef.current.strategy = message;
          setStrategy(message);
          break;

        case "assistant_response": {
          const responseText = message.text || "";

          const turn = {
            user_message: currentTurnRef.current.transcript,
            assistant_message: responseText,
            human_state: currentTurnRef.current.humanState,
            dialogue_strategy:
              currentTurnRef.current.strategy?.strategy ||
              currentTurnRef.current.strategy?.name ||
              "normal_response",
            created_at: new Date().toISOString(),
          };

          setTurns((previous) => [...previous, turn]);

          setTranscript("");
          setAssistantResponse("");

          currentTurnRef.current = {
            transcript: "",
            humanState: null,
            strategy: null,
          };

          setStatus("ready");
          break;
        }

        case "session_ended":
          setStatus("ended");
          break;

        case "error":
          setError(message.message || "Streaming error.");

          if (!message.recoverable) {
            await cleanupMic();
          }

          setStatus((current) =>
            getWebSocketErrorTransition(
              current,
              Boolean(message.recoverable)
            ).status
          );
          break;

        default:
          break;
      }
    };

    socket.onerror = (event) => {
      console.error("[HSIF WebSocket] Connection error:",event);
      setError("WebSocket connection failed. Check backend logs.");
      if (socketRef.current === socket) setIsWebSocketOpen(false);
    };

    socket.onclose = async (event) => {
      console.error("[HSIF WebSocket] Closed:", {
        code: event.code,
        reason: event.reason,
        wasClean: event.wasClean,
      });
      readyRef.current = false;
      microphoneStartupIdRef.current += 1;
      if (socketRef.current === socket) setIsWebSocketOpen(false);
      await cleanupMic();

      if (!closingRef.current) {
        setStatus((current) =>
          current === "error" ? "error" : "disconnected"
        );
      }
    };
  }, [cleanupMic, sessionId]);

  const processAudioUpload = useCallback(
    async (audioFile) => {
      if (!audioFile) return;

      if (["recording", "connecting", "processing", "starting"].includes(status)) {
        throw new Error("Finish the current operation before uploading audio.");
      }

      setError("");
      setStatus("processing");

      // Reuse the existing conversation ID.
      try {
        const id = sessionId || crypto.randomUUID();

        if (!sessionId) {
          setSessionId(id);
        }

        localStorage.setItem(ACTIVE_SESSION_STORAGE_KEY, id);

        const formData = new FormData();
        formData.append("audio", audioFile);

        const data = await uploadAudio(
          `${API_BASE_URL}/process?session_id=${encodeURIComponent(id)}`,
          formData
        );

        const newTurn = {
          user_message: data.speech?.transcript || "[Audio transcription unavailable]",
          assistant_message: data.response || "",
          human_state: data.human_state || null,
          dialogue_strategy:
            data.dialogue?.policy?.strategy || "normal_response",
          created_at: new Date().toISOString(),
        };

        // Audio and text now enter the same chronological conversation.
        setTurns((previous) => [...previous, newTurn]);

        setHumanState(newTurn.human_state);
        setStrategy({
          strategy: newTurn.dialogue_strategy,
          reason: data.dialogue?.policy?.reason || "",
        });

        setTranscript("");
        setAssistantResponse("");
        setStatus("ready");

        return data;
      } catch (err) {
        setError(err.message || "Audio processing failed.");
        setStatus("ready");
        throw err;
      }
    },
    [sessionId, status]
  );


  // Process a typed message through FastAPI.
  const sendTextMessage = useCallback(
    async (message) => {
      const text = message.trim();

      if (!text || textSendingRef.current) return;

      if (["recording", "processing", "starting"].includes(status)) {
        setError("Finish the current audio turn before sending a message.");
        return;
      }

      textSendingRef.current = true;
      setError("");
      setStatus("processing");

      // Reuse the existing conversation ID or create one.
      const id = sessionId || crypto.randomUUID();

      if (!sessionId) {
        setSessionId(id);
        localStorage.setItem(ACTIVE_SESSION_STORAGE_KEY, id);
      }

      try {
        const response = await fetch(
          `${API_BASE_URL}/message?session_id=${encodeURIComponent(id)}`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              message: text,
            }),
          }
        );

        const data = await response.json();

        if (!response.ok) {
          throw new Error(
            data.detail || "Message processing failed."
          );
        }

        const newTurn = {
          user_message: data.user_message || text,
          assistant_message: data.response || "",
          human_state: data.human_state || null,
          dialogue_strategy:
            data.dialogue?.policy?.strategy || "normal_response",
          created_at: new Date().toISOString(),
        };

        setTurns((previous) => [...previous, newTurn]);
        setHumanState(newTurn.human_state);
        setStrategy({
          strategy: newTurn.dialogue_strategy,
        });

        setTranscript("");
        setAssistantResponse("");
        setStatus("ready");

        return data;
      } catch (err) {
        setError(err.message || "Could not send message.");
        setStatus("ready");
        throw err;
      } finally {
        textSendingRef.current = false;
      }
    },
    [sessionId, status]
  );

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

    if (microphoneStartingRef.current) return;

    const startupId = ++microphoneStartupIdRef.current;
    const startup = runMicrophoneStartOnce(
      microphoneStartingRef,
      async () => {
        setStatus("starting");
        setError("");
        setTranscript("");
        setAssistantResponse("");

        currentTurnRef.current = {
          transcript: "",
          humanState: null,
          strategy: null,
        };

        const stop = await startMicrophoneStreaming(socket);

        if (
          startupId !== microphoneStartupIdRef.current ||
          socketRef.current !== socket ||
          socket.readyState !== WebSocket.OPEN
        ) {
          await stop();
          return;
        }

        stopMicRef.current = stop;
        setStatus("recording");
      }
    );

    if (!startup) return;

    try {
      await startup;
    } catch (err) {
      if (startupId === microphoneStartupIdRef.current) {
        setError(err.message || "Could not access the microphone.");
        setStatus("ready");
      }
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
    await cleanupMic();

    socket.send(
      JSON.stringify({
        type: "end_turn",
        turn_id: crypto.randomUUID(),
      })
    );
  }, [cleanupMic]);

  const endSession = useCallback(async () => {
    closingRef.current = true;
    microphoneStartupIdRef.current += 1;
    await cleanupMic();

    const socket = socketRef.current;

    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: "end_session" }));
    } else {
      setStatus("ended");
    }
  }, [cleanupMic]);

  const logout = useCallback(async () => {
    closingRef.current = true;
    readyRef.current = false;
    restoreGenerationRef.current += 1;
    microphoneStartupIdRef.current += 1;
    clearLocalUserSession();

    await cleanupMic();

    const socket = socketRef.current;
    socketRef.current = null;
    setIsWebSocketOpen(false);

    if (socket && socket.readyState !== WebSocket.CLOSED) {
      socket.close();
    }

    setSessionId(null);
    setStatus("idle");
  }, [cleanupMic]);

  useEffect(() => {
    return () => {
      closingRef.current = true;
      microphoneStartupIdRef.current += 1;

      const stop = stopMicRef.current;
      stopMicRef.current = null;

      if (stop) void stop();

      const socket = socketRef.current;

      if (socket) socket.close();
    };
  }, []);

  return {
    sessionId,
    status,
    isWebSocketOpen,
    transcript,
    humanState,
    strategy,
    assistantResponse,
    turns,
    restoreLoading,
    error,
    startSession,
    startRecording,
    endTurn,
    endSession,
    logout,
    startNewSession,
    sendTextMessage,
    processAudioUpload,
  };
}
