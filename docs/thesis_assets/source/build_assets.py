"""Build HSIF thesis figures from the source-verified specifications below.

Run from the repository root with Python. SVG, Mermaid source, and a JSON
render specification are written beneath docs/thesis_assets. PNG rendering is
performed by render_png.ps1 using Windows System.Drawing.
"""
from __future__ import annotations

import json
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "docs" / "thesis_assets"

# id, figure number, category, title, caption, explanation, nodes, edges, refs
FLOW_DATA = [
    ("fig_2_1_overall_system_architecture", "2.1", "architecture", "Overall HSIF system architecture",
     "Figure 2.1. Implemented HSIF components and external LLM services.",
     "The React/Vite client communicates with FastAPI through audio/text REST endpoints and a live-audio WebSocket. Backend orchestration connects speech processing, heuristic state estimation, dialogue policy, LLM provider selection, and PostgreSQL persistence. Groq is the source-code default and Gemini is selectable; the diagram does not imply provider fallback.",
     [("frontend", "React / Vite frontend"), ("rest", "REST: audio upload and text"), ("ws", "WebSocket: live microphone"), ("api", "FastAPI routes"), ("pipe", "PipelineService orchestration"), ("speech", "SpeechService: conversion, VAD, Whisper"), ("hsr", "HumanStateEngine: five heuristic dimensions"), ("state", "Validity, smoothing, StateTracker"), ("dialogue", "StateFusion and DialoguePolicy"), ("prompt", "ConversationMemory and PromptBuilder"), ("llm", "LLMService provider adapter"), ("groq", "External Groq API (default)"), ("gemini", "External Gemini API (optional)"), ("db", "PostgreSQL: sessions, conversation_turns")],
     [("frontend","rest","request"),("frontend","ws","audio chunks"),("rest","api","HTTP"),("ws","api","events"),("api","pipe","dispatch"),("pipe","speech","audio only"),("speech","hsr","transcript and features"),("hsr","state","observation"),("state","dialogue","current valid state"),("dialogue","prompt","strategy and context"),("prompt","llm","prompt"),("llm","groq","selected provider"),("llm","gemini","selected provider"),("pipe","db","successful turn"),("api","frontend","response/events")],
     ["frontend/src/App.jsx", "frontend/src/ChatPage.jsx", "backend/app/main.py", "backend/app/api/process.py", "backend/app/api/streaming.py", "backend/app/services/pipeline_service.py", "ai/speech/speech_service.py", "ai/human_state/human_state_engine.py", "ai/dialogue/dialogue_service.py", "backend/app/services/llm/llm_service.py", "database/models.py"]),
    ("fig_2_2_frontend_backend_architecture", "2.2", "architecture", "Frontend–backend architecture",
     "Figure 2.2. Frontend inputs, API communication, and returned interaction data.",
     "The client offers text chat, audio upload, live microphone interaction, dashboard, and history views. REST handles text, uploads, and retrieval; WebSocket carries live audio and event messages. Responses include transcript, HSR metadata, dialogue strategy, and assistant text where applicable.",
     [("ui","Chat, Dashboard, History UI"),("text","Text input"),("upload","Audio file input"),("mic","Microphone capture"),("rest","REST API"),("ws","WebSocket session"),("backend","FastAPI + PipelineService"),("out","Transcript, state, strategy, response"),("history","Session history from API")],
     [("ui","text","submit"),("ui","upload","select file"),("ui","mic","start/capture"),("text","rest","POST /message"),("upload","rest","POST /process"),("mic","ws","PCM chunks/end_turn"),("rest","backend","request"),("ws","backend","session events"),("backend","out","processed turn"),("out","ui","render"),("rest","history","GET list/detail"),("history","ui","history view")],
     ["frontend/src/App.jsx", "frontend/src/ChatPage.jsx", "frontend/src/hooks/useStreamingSession.js", "frontend/src/pages/DashboardPage.jsx", "frontend/src/pages/HistoryPage.jsx", "backend/app/api/process.py", "backend/app/api/streaming.py", "backend/app/schemas/process.py"]),
    ("fig_2_3_backend_component_architecture", "2.3", "architecture", "Backend component architecture",
     "Figure 2.3. Backend modules involved in processing and persistence.",
     "FastAPI route handlers dispatch work to PipelineService. Audio turns pass through SpeechService; valid observations reach HumanStateEngine and temporal tracking. DialogueService fuses state, selects policy, constructs context, and calls LLMService. Successful turns are stored through SessionRepository.",
     [("routes","process.py / streaming.py routes"),("pipeline","PipelineService"),("speech","SpeechService / preprocessing / VAD / Whisper"),("features","AcousticFeatureExtractor"),("engine","HumanStateEngine"),("tracker","TemporalSmoother / StateTracker"),("dialogue","DialogueService / StateFusion"),("policy","DialoguePolicy"),("llm","LLMService / GroqProvider / GeminiProvider"),("repo","SessionRepository"),("db","SQLAlchemy models / PostgreSQL")],
     [("routes","pipeline","dispatch"),("pipeline","speech","audio path"),("speech","features","VAD segments"),("features","engine","features and timing"),("engine","tracker","state"),("tracker","dialogue","state + validity"),("dialogue","policy","fused state"),("policy","llm","prompt context"),("pipeline","repo","successful turn"),("repo","db","ORM operations")],
     ["backend/app/api/process.py", "backend/app/api/streaming.py", "backend/app/services/pipeline_service.py", "ai/speech/speech_service.py", "ai/speech/feature_extraction/acoustic_features.py", "ai/human_state/human_state_engine.py", "ai/human_state/temporal_smoother.py", "ai/human_state/state_tracker.py", "ai/dialogue/dialogue_service.py", "ai/dialogue/policy/dialogue_policy.py", "database/repository.py"]),
    ("fig_2_4_audio_upload_workflow", "2.4", "workflows", "Audio upload processing workflow",
     "Figure 2.4. REST audio-upload path from validation through successful turn persistence.",
     "The upload route accepts supported extensions up to 25 MiB, creates a temporary file, and runs synchronous processing in a thread pool. The speech service converts to 16 kHz mono PCM, detects speech, transcribes, and extracts VAD-aligned features. Blank transcripts stop before dialogue generation. Successful LLM results are persisted; temporary files are cleaned up.",
     [("upload","Multipart audio upload"),("validate","Extension + 25 MiB validation"),("temp","Temporary file"),("convert","ffmpeg: 16 kHz mono s16 PCM"),("vad","VAD: 30 ms frames, RMS .01"),("whisper","Faster-Whisper base, CPU/int8"),("features","Features from VAD speech segments"),("check","Transcript and observation validity"),("hsr","HumanStateEngine + temporal state"),("policy","State fusion + dialogue policy"),("llm","Configured LLM provider"),("persist","Persist successful turn"),("response","ProcessResponse to frontend"),("cleanup","Remove temporary files"),("failure","No-speech or provider failure: no successful turn")],
     [("upload","validate","multipart"),("validate","temp","valid file"),("temp","convert","process in thread pool"),("convert","vad","converted audio"),("vad","whisper","audio + speech intervals"),("whisper","features","transcript"),("features","check","features/timing"),("check","hsr","nonempty transcript"),("check","failure","empty transcript"),("hsr","policy","state + validity"),("policy","llm","prompt"),("llm","persist","generation succeeds"),("llm","failure","generation fails"),("persist","cleanup","finally cleanup"),("failure","cleanup","finally cleanup"),("cleanup","response","response after cleanup")],
     ["backend/app/api/process.py:process_audio", "backend/app/services/pipeline_service.py:process_audio", "ai/speech/speech_service.py:process", "ai/speech/preprocessing/audio_processor.py:convert_to_wav", "ai/speech/vad/detector.py", "ai/speech/whisper/transcriber.py", "ai/speech/feature_extraction/acoustic_features.py", "database/repository.py:add_turn"]),
    ("fig_2_5_text_processing_workflow", "2.5", "workflows", "Text-only processing workflow",
     "Figure 2.5. Text turns bypass acoustic inference and are marked as unmeasured.",
     "A validated text request creates a state record with observation_valid=false and source=text_only. It does not call the acoustic feature extractor or HumanStateEngine inference. StateFusion receives the unmeasured marker; dialogue policy and prompt construction still run. Only successful generated turns are persisted.",
     [("input","Text message"),("validate","Pydantic request validation"),("state","HSR metadata: invalid / text_only"),("bypass","No audio features or HSE inference"),("fusion","StateFusion handles unmeasured input"),("policy","Rule-based dialogue policy"),("memory","Conversation memory + prompt"),("llm","Configured LLM provider"),("persist","Persist successful conversation turn"),("out","JSON response to client")],
     [("input","validate","POST /api/v1/message"),("validate","state","valid message"),("state","bypass","observation_valid=false"),("bypass","fusion","text and conversation context"),("fusion","policy","neutral internal defaults"),("policy","memory","selected strategy"),("memory","llm","prompt"),("llm","persist","success only"),("persist","out","response")],
     ["backend/app/api/process.py:process_text_message", "backend/app/services/pipeline_service.py:process_text", "ai/dialogue/fusion/state_fusion.py", "ai/dialogue/dialogue_service.py", "ai/dialogue/policy/dialogue_policy.py", "database/repository.py:add_turn"]),
    ("fig_2_6_websocket_workflow", "2.6", "workflows", "Live microphone WebSocket workflow",
     "Figure 2.6. Implemented buffered live-audio protocol; final turn processing remains full-recording.",
     "The client opens a session, sends PCM chunks, and signals end_turn. The server emits chunk metadata and may transcribe the accumulated interim buffer after a one-second minimum and three-second interval. At end_turn it processes the complete turn and emits transcript, state, strategy, and response events. The diagram does not imply incremental HSR or continuous partial generation.",
     [("connect","Connect /ws/session/{session_id}"),("start","start_session → session_ready"),("chunks","Binary 16 kHz mono PCM chunks"),("chunk_event","speech_chunk: chunk timing/activity metadata"),("buffer","Turn buffer (10 MiB limit)"),("interim","transcript_partial: periodic transcript"),("end","end_turn"),("final","Full-recording pipeline in thread pool"),("events","transcript_final, human_state_update, dialogue_strategy, assistant_response"),("error","error event: recoverable flag / code / message"),("close","end_session or disconnect")],
     [("connect","start","UUID accepted"),("start","chunks","session active"),("chunks","chunk_event","each valid PCM chunk"),("chunk_event","buffer","append audio"),("buffer","interim","periodic when threshold met"),("buffer","end","client ends turn"),("end","final","full buffer"),("final","events","success"),("final","error","processing failure"),("events","chunks","next turn possible"),("error","chunks","if recoverable")],
     ["frontend/src/hooks/useStreamingSession.js", "frontend/src/components/LiveMicrophone.jsx", "backend/app/api/streaming.py:stream_session", "ai/speech/streaming/chunk_processor.py", "backend/app/services/pipeline_service.py:process_audio"]),
    ("fig_2_7_speech_preprocessing_workflow", "2.7", "workflows", "Audio preprocessing and speech recognition",
     "Figure 2.7. Supported upload validation, conversion, segmentation, transcription, and no-speech handling.",
     "Uploads are limited by extension and file size before temporary storage. ffmpeg produces 16 kHz mono signed 16-bit PCM. Librosa-based VAD uses 30 ms frames and RMS threshold .01. Faster-Whisper transcribes the audio; acoustic pitch is extracted per speech segment where the segment is usable. Empty transcript raises a no-speech processing error.",
     [("formats","WAV / MP3 / M4A / OGG / FLAC / AAC"),("limits","25 MiB upload maximum"),("convert","16 kHz mono signed 16-bit PCM"),("vad","30 ms frames; RMS threshold .01"),("segments","Speech intervals and pauses"),("transcribe","Faster-Whisper base, CPU/int8"),("features","Per-segment pitch + timing/energy"),("empty","Blank transcript → no-speech error"),("clean","Temporary audio cleanup")],
     [("formats","limits","validate extension"),("limits","convert","accepted file"),("convert","vad","WAV"),("vad","segments","speech intervals"),("segments","transcribe","audio transcript"),("segments","features","selected intervals"),("transcribe","empty","transcript validation"),("features","clean","derived file cleanup"),("empty","clean","finally")],
     ["backend/app/api/process.py:ALLOWED_AUDIO_EXTENSIONS", "backend/app/api/process.py:process_audio", "ai/speech/preprocessing/audio_processor.py", "ai/speech/vad/detector.py", "ai/speech/whisper/transcriber.py", "ai/speech/feature_extraction/acoustic_features.py", "backend/app/services/pipeline_service.py:_is_valid_observation"]),
    ("fig_2_8_hsr_architecture", "2.8", "human_state", "Human State Recognition architecture",
     "Figure 2.8. Heuristic feature-to-state pipeline; outputs are estimates, not validated psychological measures.",
     "For audio turns, speech timing, VAD intervals, and acoustic features feed five separate heuristic dimensions. HumanStateEngine packages the outputs and validity metadata; smoothing/tracking operate on valid observations. Text-only turns do not enter this audio inference chain.",
     [("audio","Audio and VAD timing"),("features","Pitch, energy, pauses, speech duration"),("emotion","Emotion heuristic"),("hesitation","Hesitation heuristic"),("confidence","Confidence heuristic"),("engagement","Engagement heuristic"),("load","Cognitive-load heuristic"),("engine","HumanStateEngine / HSR"),("temporal","Validity, smoothing, tracking"),("consumer","Dialogue and UI"),("note","Heuristic proxies; accuracy not established")],
     [("audio","features","VAD speech segments"),("features","emotion","acoustic values"),("features","hesitation","pause timing"),("features","confidence","pitch, energy, pauses"),("features","engagement","activity, pitch, energy"),("features","load","activity, pause, pitch, energy"),("emotion","engine","label + score"),("hesitation","engine","score"),("confidence","engine","score"),("engagement","engine","score"),("load","engine","score"),("engine","temporal","validity-aware state"),("temporal","consumer","current observation")],
     ["ai/speech/feature_extraction/acoustic_features.py", "ai/human_state/emotion/detector.py", "ai/human_state/hesitation/detector.py", "ai/human_state/confidence/estimator.py", "ai/human_state/engagement/estimator.py", "ai/human_state/cognitive_load/estimator.py", "ai/human_state/human_state_engine.py", "ai/human_state/temporal_smoother.py"]),
    ("fig_2_9_five_hsr_dimensions", "2.9", "human_state", "Five human-state dimensions and input features",
     "Figure 2.9. Implemented feature families used by the five HSR estimators.",
     "The five values are derived from overlapping speech timing and acoustic features. Emotion uses pitch and energy heuristics; the remaining dimensions combine pause statistics, speech activity/duration, pitch range, and energy. They should be reported as heuristic proxies, not calibrated scores.",
     [("pitch","Pitch: mean, min, max, range"),("energy","Mean RMS energy"),("pauses","Pause count, mean/max duration, silence"),("activity","Speech and silence duration"),("emotion","Emotion: pitch + energy"),("hes","Hesitation: pause metrics"),("conf","Confidence: pauses + duration + pitch + energy"),("eng","Engagement: activity + energy + pauses + pitch"),("load","Cognitive load: pauses + activity + pitch ratio + energy"),("range","Each score is bounded; heuristics, not calibrated probabilities")],
     [("pitch","emotion","input"),("energy","emotion","input"),("pauses","hes","input"),("pauses","conf","input"),("activity","conf","duration"),("pitch","conf","input"),("energy","conf","input"),("activity","eng","input"),("energy","eng","input"),("pauses","eng","input"),("pitch","eng","input"),("pauses","load","input"),("activity","load","input"),("pitch","load","ratio"),("energy","load","input"),("emotion","range","estimate"),("hes","range","estimate"),("conf","range","estimate"),("eng","range","estimate"),("load","range","estimate")],
     ["ai/speech/feature_extraction/acoustic_features.py", "ai/human_state/emotion/detector.py", "ai/human_state/hesitation/detector.py", "ai/human_state/confidence/estimator.py", "ai/human_state/engagement/estimator.py", "ai/human_state/cognitive_load/estimator.py"]),
    ("fig_2_10_state_fusion_temporal_smoothing", "2.10", "human_state", "State fusion and temporal smoothing",
     "Figure 2.10. Validity-aware temporal state handling and dialogue fusion.",
     "Valid HSR observations pass through numeric smoothing (alpha .4 by default) and state tracking (change threshold .1). Emotion confirmation count defaults to 1, so labels can change immediately. Invalid observations do not replace the valid smoothing baseline and are not counted as fresh state changes. StateFusion derives interaction conditions for dialogue policy.",
     [("obs","Current HSR observation"),("valid","Validity check"),("invalid","Invalid: preserve previous smoother baseline; no fresh change"),("smooth","Numeric smoothing, alpha = 0.4"),("label","Emotion confirmation count = 1 by default"),("tracker","StateTracker, threshold = 0.1"),("history","State history / changes"),("fusion","StateFusion interaction flags"),("policy","DialoguePolicy input")],
     [("obs","valid","check metadata"),("valid","invalid","false"),("valid","smooth","true"),("smooth","label","smoothed scores"),("label","tracker","current label"),("tracker","history","thresholded changes"),("history","fusion","state/context"),("fusion","policy","fused state")],
     ["ai/human_state/temporal_smoother.py", "ai/human_state/state_tracker.py", "ai/human_state/human_state_engine.py", "ai/dialogue/fusion/state_fusion.py"]),
    ("fig_2_11_observation_validity", "2.11", "human_state", "Human-state observation validity",
     "Figure 2.11. Valid audio, unusable audio, and text-only turns remain distinct.",
     "Valid audio may yield a measured neutral emotion. Invalid audio features and text-only input are unmeasured and use unknown/invalid metadata rather than a neutral measurement. Text-only turns carry source=text_only and do not reuse a previous audio-derived value as the current observation.",
     [("audio_valid","Valid audio features"),("audio_invalid","Audio present; required features unusable"),("text","Text-only request"),("measured","Observation valid; emotion may be Neutral"),("unmeasured","Not measured / unknown; observation_valid=false"),("source","Text source=text_only; invalid audio remains audio-sourced"),("fusion","Do not fuse unmeasured values as fresh observations"),("ui","UI says Not measured; hides emotion meters")],
     [("audio_valid","measured","valid features"),("audio_invalid","unmeasured","invalid features"),("text","unmeasured","no audio observation"),("measured","fusion","measured state"),("unmeasured","source","retain source metadata"),("source","fusion","validity-aware handling"),("fusion","ui","display state")],
     ["backend/app/services/pipeline_service.py", "ai/human_state/hsr.py", "ai/dialogue/fusion/state_fusion.py", "frontend/src/components/HumanStatePanel.jsx", "frontend/src/pages/HistoryPage.jsx"]),
    ("fig_2_12_adaptive_dialogue_workflow", "2.12", "dialogue", "Adaptive dialogue policy workflow",
     "Figure 2.12. HSR/context to strategy and generated response.",
     "DialogueService combines the current interaction with conversation memory, fuses valid state or handles unmeasured input, applies ordered policy rules, and constructs a prompt. LLMService dispatches to the configured provider. The API returns the strategy and generated text; successful turns are persisted.",
     [("turn","Audio-derived or text turn"),("state","StateFusion + current validity"),("memory","ConversationMemory retrieval"),("policy","DialoguePolicy rules"),("strategy","Selected strategy"),("prompt","PromptBuilder"),("provider","LLMService provider"),("response","Generated assistant response"),("persist","Successful turn persistence"),("client","REST result / WebSocket events")],
     [("turn","state","text or measured state"),("state","policy","fused flags"),("memory","prompt","relevant/recent context"),("policy","strategy","ordered conditions"),("strategy","prompt","instructions"),("prompt","provider","prompt"),("provider","response","generated text"),("response","persist","on success"),("persist","client","response")],
     ["ai/dialogue/dialogue_service.py", "ai/dialogue/fusion/state_fusion.py", "ai/dialogue/policy/dialogue_policy.py", "ai/dialogue/memory/conversation_memory.py", "ai/dialogue/prompt_builder.py", "backend/app/services/llm/llm_service.py", "backend/app/services/pipeline_service.py"]),
    ("fig_2_13_dialogue_strategy_decision", "2.13", "dialogue", "Dialogue strategy decision flow",
     "Figure 2.13. Condensed policy precedence; synthetic cases do not establish audio-triggered coverage.",
     "The policy evaluates conditions in precedence order: frustration acknowledgment, reassurance, overload-related simplification or reduction, slow-down, clarification/re-engagement/continuation, follow-up or encouragement, then normal response. Several branches depend on labels not emitted by the current acoustic emotion detector; those branches are implemented but not demonstrated end-to-end by the audio classifier.",
     [("start","Fused state"),("r1","1. emotion frustrated? → acknowledge_frustration"),("r2","2. hesitation ≥ .7 AND confidence ≤ .45? → reassure"),("r3","3. overloaded_uncertain AND confidence ≤ .35? → simplify"),("r4","4. interaction overloaded/overloaded_uncertain AND load ≥ .9? → reduce_information"),("r5","5. hesitation ≥ .7? → slow_down"),("r6","6. interaction overloaded? → simplify"),("r7","7. interaction struggling? → clarify"),("r8","8. interaction disengaged? → re_engage"),("r9","9. confident_engaged? → continue"),("r10","10. needs_clarification? uncertain → ask_follow_up; else clarify"),("r11","11. needs_encouragement? → encourage"),("r12","12. otherwise → normal_response"),("caveat","Precedence ordered; frustrated/uncertain labels are not emitted by current audio emotion detector")],
     [("start","r1","evaluate"),("r1","r2","if no"),("r2","r3","if no"),("r3","r4","if no"),("r4","r5","if no"),("r5","r6","if no"),("r6","r7","if no"),("r7","r8","if no"),("r8","r9","if no"),("r9","r10","if no"),("r10","r11","if no"),("r11","r12","if no"),("r12","caveat","scope")],
     ["ai/dialogue/policy/dialogue_policy.py", "ai/dialogue/fusion/state_fusion.py", "ai/human_state/emotion/detector.py", "evaluation/benchmark_dialogue.py"]),
    ("fig_2_14_llm_provider_integration", "2.14", "dialogue", "LLM provider integration",
     "Figure 2.14. Configuration selects one provider; no automatic fallback is implemented.",
     "LLMService validates LLM_PROVIDER and constructs either GroqProvider or GeminiProvider. Groq is the source default. Each adapter sends a prompt to its external service and returns text or a typed safe error. The application does not automatically switch providers after a failure.",
     [("config","LLM_PROVIDER configuration"),("service","LLMService"),("groq","GroqProvider (default)"),("gemini","GeminiProvider (supported)"),("external_g","External Groq API"),("external_m","External Gemini API"),("success","Non-empty generated response"),("errors","Typed timeout / auth / rate / incomplete / unavailable errors"),("api","Safe API/WebSocket response")],
     [("config","service","validate provider"),("service","groq","if groq"),("service","gemini","if gemini"),("groq","external_g","request"),("gemini","external_m","request"),("external_g","success","response"),("external_m","success","response"),("external_g","errors","provider error"),("external_m","errors","provider error"),("errors","api","mapped error; no fallback")],
     ["backend/app/services/llm/llm_service.py", "backend/app/services/llm/groq_provider.py", "backend/app/services/llm/gemini_provider.py", "backend/app/services/llm/errors.py", "backend/app/api/process.py", "backend/app/api/streaming.py"]),
    ("fig_2_15_database_erd", "2.15", "database_api", "PostgreSQL entity–relationship model",
     "Figure 2.15. SQLAlchemy session and conversation-turn tables; schema shown from model declarations.",
     "A session has a string primary key and timestamps. ConversationTurn uses an integer primary key, a non-null foreign key to sessions.id with cascade deletion, message text, JSONB human state, strategy text, and creation time. The relationship is one session to many turns. This diagram reflects ORM declarations; live database schema was not inspected.",
     [("session","sessions\nPK id VARCHAR(100)\ncreated_at TIMESTAMP NOT NULL\nupdated_at TIMESTAMP NOT NULL"),("turn","conversation_turns\nPK id INTEGER\nsession_id VARCHAR(100) FK NOT NULL\nuser_message TEXT NOT NULL\nassistant_message TEXT NOT NULL\nhuman_state JSONB NOT NULL\ndialogue_strategy VARCHAR(100) NOT NULL\ncreated_at TIMESTAMP NOT NULL")],
     [("session","turn","1 to many; FK ON DELETE CASCADE")],
     ["database/models.py:Session", "database/models.py:ConversationTurn", "database/repository.py"]),
    ("fig_2_16_api_interaction", "2.16", "database_api", "API interaction overview",
     "Figure 2.16. Implemented REST and WebSocket entry points and their response forms.",
     "Audio uses multipart REST and returns ProcessResponse. Text uses JSON REST and returns processed turn data. Live audio uses a WebSocket session with binary PCM and JSON events. Session list/detail and state trajectory are separate REST reads. The health endpoint is static and does not assert database readiness.",
     [("client","React client"),("audio","POST /api/v1/process\nmultipart audio + session_id"),("text","POST /api/v1/message\nJSON message + session_id"),("ws","/ws/session/{session_id}\nbinary PCM + control messages"),("history","GET /api/v1/sessions\nGET /api/v1/sessions/{id}"),("state","GET /api/v1/session/{id}/state"),("health","GET /health\nstatic status"),("pipeline","PipelineService"),("response","ProcessResponse / errors / WS events")],
     [("client","audio","upload"),("client","text","message"),("client","ws","live audio"),("client","history","list/detail"),("client","state","trajectory"),("client","health","health check"),("audio","pipeline","process"),("text","pipeline","process"),("ws","pipeline","end_turn"),("pipeline","response","JSON or events")],
     ["backend/app/api/process.py", "backend/app/api/streaming.py", "backend/app/schemas/process.py", "backend/app/main.py:health", "frontend/src/services/"] ),
    ("fig_2_17_persistence_workflow", "2.17", "database_api", "Conversation persistence and retrieval",
     "Figure 2.17. Successful turn persistence and session/history retrieval.",
     "A session ID identifies a session; the repository can create or retrieve the session before turn processing. A conversation turn is added only after successful generation. History endpoints read summaries/details from PostgreSQL, and the state endpoint returns trajectory data reconstructed by the pipeline service. Frontend account/session prototype data in localStorage is separate from conversation persistence.",
     [("id","Session ID"),("session","SessionRepository get/create"),("process","Process turn: speech/text, HSR, dialogue, LLM"),("ok","Generation succeeds"),("turn","Insert conversation_turn"),("fail","Failure: no successful turn insert"),("history","List/detail history API"),("trajectory","State trajectory API"),("local","Browser localStorage prototype (separate)")],
     [("id","session","session lookup"),("session","process","turn request"),("process","ok","provider returns text"),("ok","turn","persist"),("process","fail","processing/provider error"),("turn","history","retrieve turns"),("session","history","list sessions"),("turn","trajectory","stored HSR history"),("local","history","not source of DB history")],
     ["backend/app/services/pipeline_service.py", "database/repository.py", "database/models.py", "backend/app/api/process.py", "frontend/src/services/localSession.js"]),
    ("fig_2_18_deployment_architecture", "2.18", "deployment_security", "Local development deployment architecture",
     "Figure 2.18. Verified local development components; not a production cloud deployment.",
     "The repository configures a Vite frontend, local FastAPI backend, PostgreSQL 18 Compose service on host port 5434, and external LLM APIs selected through environment configuration. The Vite development port defaults to 5173 but may vary. The actual running container, server versions, credentials, and readiness were not verified.",
     [("browser","Browser / React client"),("vite","Vite dev server (default 5173)"),("fastapi","FastAPI / Uvicorn (configured 127.0.0.1:8000)"),("pg","Docker Compose PostgreSQL 18\nhost 5434 → container 5432"),("env","Private environment configuration\n(names documented; values not shown)"),("llm","External Groq or Gemini API\nselected provider only"),("volume","Named PostgreSQL volume\nhsif_postgres_data")],
     [("browser","vite","HTTP"),("vite","fastapi","REST / WS"),("fastapi","pg","SQLAlchemy"),("env","fastapi","settings/credentials"),("fastapi","llm","provider API request"),("pg","volume","persistent volume")],
     ["frontend/vite.config.js", "backend/app/main.py", "docker-compose.yml", "database/database.py", "backend/app/services/llm/llm_service.py", ".env.example (variable names only)"]),
    ("fig_2_19_security_data_flow", "2.19", "deployment_security", "Security and data-handling flow",
     "Figure 2.19. Current handling controls and verified security limitations.",
     "Audio requests receive extension/size validation and temporary files are removed after processing; audio is not stored in conversation tables. Successful message/state/strategy data are persisted in PostgreSQL. Provider credentials are configured through environment variables. Browser-local authentication is only a prototype, and API/WS ownership checks and rate limiting are absent; this is not production-secure authentication.",
     [("upload","Audio upload: extension + size checks"),("temp","Temporary audio file"),("process","Process and clean up"),("db","PostgreSQL: text, HSR JSON, strategy"),("secret","Provider credentials from environment"),("browser","Browser-local prototype login"),("api","REST / WebSocket session ID"),("limitation","No server auth/ownership enforcement or rate limit"),("raw","Raw audio not stored in turn tables")],
     [("upload","temp","accepted file"),("temp","process","temporary processing"),("process","db","successful turn only"),("process","raw","temporary cleanup"),("secret","process","provider configuration"),("browser","api","session ID supplied by client"),("api","limitation","no ownership check")],
     ["backend/app/api/process.py", "backend/app/api/streaming.py", "frontend/src/services/localSession.js", "database/models.py", ".gitignore", "docker-compose.yml"]),
    ("fig_4_1_evaluation_methodology", "4.1", "evaluation", "Evaluation methodology and evidence tracks",
     "Figure 4.1. Separate software, dataset, synthetic, and exploratory evaluation tracks.",
     "The repository contains five distinct evaluation tracks with different evidence strength: CREMA-D labeled audio evaluation; a one-fixture speech benchmark; synthetic HSR behavior checks; synthetic dialogue-policy checks; and a small historical Gemini response comparison. Their results should not be combined as a single accuracy or human-study claim.",
     [("crema","CREMA-D emotion\n7,442 recordings\nEvaluation, not training"),("speech","Speech benchmark\n1 audio/reference fixture"),("hsr","HSR benchmark\n4 synthetic profiles × 5"),("dialogue","Dialogue policy\n5 scenarios × 30 per mode"),("gemini","Gemini response comparison\n5 scenarios, 10 historical calls"),("scope","Different evidence types; no single aggregate score")],
     [("crema","scope","labeled dataset metrics"),("speech","scope","one-fixture WER/CER/latency"),("hsr","scope","directionality/bounds/determinism"),("dialogue","scope","policy behavior only"),("gemini","scope","exploratory paired ratings")],
     ["evaluation/benchmark_cremad_emotion.py", "evaluation/benchmark_speech.py", "evaluation/benchmark_human_state.py", "evaluation/benchmark_dialogue.py", "evaluation/benchmark_gemini_responses.py", "evaluation/results/"]),
    ("fig_4_2_cremad_evaluation", "4.2", "evaluation", "CREMA-D emotion evaluation results",
     "Figure 4.2. CREMA-D evaluation metrics; data were evaluated, not used for training.",
     "The stored result covers 7,442 recordings. The six-reference-class accuracy is 21.61%; six-class macro-F1 recomputed from stored per-class values is approximately .156. On the happy/neutral/sad subset, accuracy is approximately .443 and macro-F1 approximately .439. Detector outputs are narrower than the six reference classes, so these numbers should not be generalized as overall emotion-recognition accuracy.",
     [], [], ["evaluation/benchmark_cremad_emotion.py", "evaluation/results/cremad"]),
    ("fig_4_3_speech_benchmark", "4.3", "evaluation", "Speech benchmark: one-fixture results",
     "Figure 4.3. Faster-Whisper measurements for one audio/reference fixture only.",
     "Five warm runs on a single fixture produced mean latency 1.839 seconds, median 1.841 seconds, and P95 2.209 seconds. WER was .125 and CER .0392 for that fixture. The sample is too small to support a general transcription-quality or performance claim.",
     [], [], ["evaluation/benchmark_speech.py", "evaluation/results/speech_20261030T052436Z_3e8ed483.json"]),
    ("fig_4_4_hsr_benchmark", "4.4", "evaluation", "Synthetic human-state behavior checks",
     "Figure 4.4. Twenty synthetic HSR benchmark runs across four constructed profiles.",
     "The benchmark repeats four synthetic profiles five times each. It checks expected heuristic directionality, bounded output, and determinism. It does not compare predictions against labeled human observations and therefore is not an emotion or HSR accuracy evaluation.",
     [], [], ["evaluation/benchmark_human_state.py", "evaluation/results/human_state_20261030T162245Z_2e5fd208.json"]),
    ("fig_4_5_dialogue_benchmark", "4.5", "evaluation", "Synthetic dialogue-policy behavior checks",
     "Figure 4.5. Three hundred local policy attempts over five synthetic scenarios.",
     "Five synthetic cases were repeated 30 times for baseline and adaptive modes, totaling 300 local attempts. The experiment checks policy/strategy behavior, not external LLM response quality, user outcomes, or conversational effectiveness.",
     [], [], ["evaluation/benchmark_dialogue.py", "evaluation/results/dialogue_20261030T163347Z_ba01ff17.json"]),
    ("fig_4_6_gemini_response_comparison", "4.6", "evaluation", "Exploratory Gemini response comparison",
     "Figure 4.6. Historical response ratings: exploratory results; reviewer provenance was not recorded.",
     "Across five scenarios, the historical artifact records ten direct Gemini calls. The adaptive condition has mean rating 4.24/5 versus 3.96/5 baseline, and was preferred in four of five pairs. Reviewer identity and provenance are absent and the sample is small; this is exploratory evidence, not a controlled human study. The evaluation README contains conflicting summary values.",
     [], [], ["evaluation/benchmark_gemini_responses.py", "evaluation/results/gemini_response_20261105T180011Z_5ec43391.json", "evaluation/README.md"]),
]

CHART_DATA = {
    "fig_4_2_cremad_evaluation": [
        ("Six-class accuracy", 21.61, "%"), ("Six-class macro-F1", 15.6, "%"),
        ("Happy/neutral/sad accuracy", 44.3, "%"), ("Happy/neutral/sad macro-F1", 43.9, "%")],
    "fig_4_3_speech_benchmark": [
        ("Mean latency", 1.839, "s"), ("Median latency", 1.841, "s"), ("P95 latency", 2.209, "s"),
        ("WER", 0.125, "ratio"), ("CER", 0.0392, "ratio")],
    "fig_4_4_hsr_benchmark": [
        ("Synthetic profiles", 4, "profiles"), ("Repeats per profile", 5, "runs"), ("Total cases", 20, "runs")],
    "fig_4_5_dialogue_benchmark": [
        ("Synthetic scenarios", 5, "scenarios"), ("Repeats per mode", 30, "attempts"), ("Modes", 2, "modes"), ("Total attempts", 300, "attempts")],
    "fig_4_6_gemini_response_comparison": [
        ("Baseline mean rating", 3.96, "/5"), ("Adaptive mean rating", 4.24, "/5"), ("Adaptive pair preferences", 4, "of 5")],
}

def category_for(fig_id: str) -> str:
    for item in FLOW_DATA:
        if item[0] == fig_id:
            return item[2]
    return "evaluation"

def main() -> None:
    source_dir = OUT / "diagram_sources"
    source_dir.mkdir(parents=True, exist_ok=True)
    positions = {
        "fig_2_1_overall_system_architecture": {"frontend": (0,0), "rest": (0,1), "ws": (1,1), "api": (0,2), "pipe": (1,2), "speech": (1,0), "hsr": (2,0), "state": (2,1), "dialogue": (3,0), "prompt": (3,1), "llm": (3,2), "groq": (4,0), "gemini": (4,1), "db": (4,2)},
        "fig_2_2_frontend_backend_architecture": {"ui": (0,0), "text": (1,0), "upload": (2,0), "mic": (3,0), "rest": (1,1), "ws": (2,1), "backend": (2,2), "out": (3,2), "history": (0,1)},
        "fig_2_3_backend_component_architecture": {"routes": (0,1), "pipeline": (1,1), "speech": (2,0), "features": (2,1), "engine": (2,2), "tracker": (3,0), "dialogue": (3,1), "policy": (3,2), "llm": (4,1), "repo": (4,2), "db": (5,2)},
        "fig_2_4_audio_upload_workflow": {"upload": (0,0), "validate": (0,1), "temp": (0,2), "convert": (1,2), "vad": (1,1), "whisper": (1,0), "features": (2,0), "check": (2,1), "hsr": (2,2), "policy": (3,2), "llm": (3,1), "failure": (3,0), "persist": (4,2), "cleanup": (4,1), "response": (4,0)},
        "fig_2_12_adaptive_dialogue_workflow": {"turn": (0,0), "state": (0,1), "memory": (0,2), "policy": (1,2), "strategy": (1,1), "prompt": (1,0), "provider": (2,0), "response": (2,1), "persist": (2,2), "client": (3,1)},
        "fig_2_14_llm_provider_integration": {"config": (0,1), "service": (1,1), "groq": (2,0), "gemini": (2,2), "external_g": (3,0), "external_m": (3,2), "success": (4,0), "errors": (4,2), "api": (5,1)},
        "fig_2_15_database_erd": {"session": (0,0), "turn": (0,1)},
        "fig_2_16_api_interaction": {"client": (0,1), "audio": (1,0), "text": (1,1), "ws": (1,2), "history": (2,0), "state": (2,1), "health": (2,2), "pipeline": (3,1), "response": (4,1)},
        "fig_2_17_persistence_workflow": {"id": (0,1), "session": (1,1), "process": (2,1), "ok": (3,0), "turn": (4,0), "fail": (3,2), "history": (5,0), "trajectory": (5,1), "local": (1,2)},
        "fig_2_19_security_data_flow": {"upload": (0,0), "temp": (1,0), "process": (2,0), "db": (3,0), "secret": (0,2), "browser": (1,2), "api": (2,2), "limitation": (3,2), "raw": (4,1)},
    }
    for fig_id, number, category, title, caption, explanation, nodes, edges, refs in FLOW_DATA:
        spec = {"id": fig_id, "number": number, "category": category, "title": title,
                "caption": caption, "explanation": explanation,
                "nodes": [{"id": n, "label": label, **({"row": positions[fig_id][n][0], "col": positions[fig_id][n][1]} if fig_id in positions and n in positions[fig_id] else {})} for n, label in nodes],
                "edges": [{"from": a, "to": b, "label": label} for a, b, label in edges],
                "references": refs}
        if fig_id in CHART_DATA:
            spec["kind"] = "chart"
            spec["metrics"] = [{"label": a, "value": b, "unit": c} for a, b, c in CHART_DATA[fig_id]]
        else:
            spec["kind"] = "flow"
        # Three-column grid used by both PNG and SVG renderers.
        cols = 3
        margin_x, margin_y, card_w, card_h, gap_x, gap_y = 60, 100, 360, 92, 42, 42
        if fig_id == "fig_2_15_database_erd":
            card_h = 270
        count = len(spec.get("nodes", [])) if spec["kind"] == "flow" else len(spec["metrics"])
        rows = max(1, (count + cols - 1) // cols)
        if fig_id in positions:
            rows = max(rows, max(r for r, _ in positions[fig_id].values()) + 1)
        width = margin_x * 2 + cols * card_w + (cols - 1) * gap_x
        if spec["kind"] == "chart":
            width = 1500
            if fig_id in {"fig_4_2_cremad_evaluation", "fig_4_6_gemini_response_comparison"}:
                height = 180 + len(spec["metrics"]) * 92
            else:
                height = 180 + ((len(spec["metrics"])+2)//3) * 175
        else:
            height = margin_y + rows * card_h + max(0, rows - 1) * gap_y + 70
        spec["canvas"] = {"width": width, "height": height, "columns": cols,
                          "margin_x": margin_x, "margin_y": margin_y,
                          "card_width": card_w, "card_height": card_h,
                          "gap_x": gap_x, "gap_y": gap_y}
        (source_dir / f"{fig_id}.json").write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
        (source_dir / f"{fig_id}.mmd").write_text(to_mermaid(spec), encoding="utf-8")
        export_dir = OUT / category
        export_dir.mkdir(parents=True, exist_ok=True)
        (export_dir / f"{fig_id}.svg").write_text(to_svg(spec), encoding="utf-8")
    write_supporting_docs()

def write_supporting_docs() -> None:
    catalog = ["# HSIF thesis diagram catalog", "", "Figures are grouped by suggested thesis chapter. Figure numbers are provisional because the thesis source was not available for checking existing numbering or placeholders. Each figure also has an exact-name JSON rendering specification at `diagram_sources/<figure-id>.json`.", "", "| Figure | Asset | Title | Caption | Suggested placement |", "|---:|---|---|---|---|"]
    explanations = ["# Thesis-ready figure explanations", ""]
    mapping = ["# Diagram-to-implementation mapping", "", "The figure specifications were checked against the listed source files. Runtime/deployment behavior not verifiable from source is called out in missing_evidence.md.", "", "| Figure | Diagram | Source files / symbols |", "|---:|---|---|"]
    insertion = ["# Thesis insertion guide", "", "Chapter and subsection references below are recommendations only. The thesis source and existing figure numbering/placeholders were unavailable, so verify numbering and replace/retain decisions against the original before insertion.", ""]
    for item in FLOW_DATA:
        fig_id, number, category, title, caption, explanation, _nodes, _edges, refs = item
        placement = "Chapter 4 — evaluation methodology/results" if number.startswith("4.") else "Chapter 2 — system design and methodology"
        catalog.append(f"| {number} | `{category}/{fig_id}.png` (PNG), `{category}/{fig_id}.svg` (SVG), `diagram_sources/{fig_id}.mmd` (editable) | {title} | {caption} | {placement} |")
        explanations.extend([f"## Figure {number}: {title}", "", caption, "", explanation, ""])
        mapping.append(f"| {number} | {title} | " + "; ".join(f"`{r}`" for r in refs) + " |")
        insertion.extend([f"## Figure {number}: {title}", "",
                          f"- **Chapter / subsection:** {placement}; place in the subsection covering {title.lower()}.",
                          f"- **Suggested location:** After the paragraph that first explains this implementation/evaluation topic.",
                          f"- **Figure title and caption:** {caption}",
                          f"- **Explanation:** {explanation}",
                          "- **Placement status:** Proposed new figure. Whether it replaces an existing placeholder is unknown until the thesis is supplied.",
                          f"- **Caveat:** See `missing_evidence.md`; specifically, {('historical evaluation scope/provenance applies' if number.startswith('4.') else 'the diagram represents source implementation, not unverified live deployment behavior')}.", ""])
    (OUT / "diagram_catalog.md").write_text("\n".join(catalog) + "\n", encoding="utf-8")
    (OUT / "figure_explanations.md").write_text("\n".join(explanations), encoding="utf-8")
    (OUT / "implementation_mapping.md").write_text("\n".join(mapping) + "\n", encoding="utf-8")
    (OUT / "thesis_insertion_guide.md").write_text("\n".join(insertion), encoding="utf-8")

def to_mermaid(spec: dict) -> str:
    lines = ["flowchart LR", f"  %% Figure {spec['number']}: {spec['title']}"]
    if spec["kind"] == "flow":
        for n in spec["nodes"]:
            lines.append(f"  {n['id']}[\"{n['label'].replace(chr(10), '<br/>')}\"]")
        for e in spec["edges"]:
            label = f"|{e['label']}|" if e["label"] else ""
            lines.append(f"  {e['from']} -->{label} {e['to']}")
    else:
        lines.append(f"  heading[\"{spec['title']}\"]")
        for i, m in enumerate(spec["metrics"]):
            lines.append(f"  m{i}[\"{m['label']}: {m['value']} {m['unit']}\"]")
        lines.append("  note[\"See caption for sample-size and interpretation limits\"]")
        if spec["metrics"]:
            lines.append("  heading --> m0")
        for i in range(len(spec["metrics"])):
            lines.append(f"  m{i} --> note")
    return "\n".join(lines) + "\n"

def wrap_lines(text: str, max_chars: int = 34) -> list[str]:
    result: list[str] = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        line = ""
        for word in words:
            if line and len(line) + len(word) + 1 > max_chars:
                result.append(line)
                line = word
            else:
                line = f"{line} {word}".strip()
        result.append(line)
    return result

def to_svg(spec: dict) -> str:
    c = spec["canvas"]
    w, h = c["width"], c["height"]
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
           f'<title>{escape(spec["title"])}</title>', f'<desc>{escape(spec["caption"])}</desc>',
           '<defs><marker id="arrow" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto"><path d="M0,0 L10,4 L0,8 Z" fill="#64748b"/></marker></defs>',
           '<rect width="100%" height="100%" fill="#ffffff"/>',
           f'<text x="{w/2}" y="48" text-anchor="middle" font-family="Arial,sans-serif" font-size="28" font-weight="700" fill="#18324b">{escape(spec["title"])}</text>']
    if spec["kind"] == "flow":
        positions = {}
        for i, node in enumerate(spec["nodes"]):
            col = node.get("col", i % c["columns"])
            row = node.get("row", i // c["columns"])
            x = c["margin_x"] + col * (c["card_width"] + c["gap_x"])
            y = c["margin_y"] + row * (c["card_height"] + c["gap_y"])
            positions[node["id"]] = (x, y)
        for edge in spec["edges"]:
            if edge["from"] not in positions or edge["to"] not in positions:
                continue
            x1, y1 = positions[edge["from"]]; x2, y2 = positions[edge["to"]]
            cx1, cy1 = x1 + c["card_width"]/2, y1 + c["card_height"]/2
            cx2, cy2 = x2 + c["card_width"]/2, y2 + c["card_height"]/2
            dx, dy = cx2-cx1, cy2-cy1
            norm = max((dx*dx + dy*dy) ** 0.5, 1)
            ux, uy = dx/norm, dy/norm
            d1 = min((c["card_width"]/2)/abs(ux) if ux else 1e9,
                     (c["card_height"]/2)/abs(uy) if uy else 1e9)
            d2 = min((c["card_width"]/2)/abs(ux) if ux else 1e9,
                     (c["card_height"]/2)/abs(uy) if uy else 1e9)
            sx, sy = cx1+ux*d1, cy1+uy*d1
            tx, ty = cx2-ux*d2, cy2-uy*d2
            out.append(f'<path d="M {sx} {sy} L {tx} {ty}" stroke="#64748b" stroke-width="2" fill="none" marker-end="url(#arrow)"/>')
        for i, node in enumerate(spec["nodes"]):
            x, y = positions[node["id"]]
            fill = "#eaf1f6" if i % 2 == 0 else "#f4f7f9"
            out.append(f'<rect x="{x}" y="{y}" width="{c["card_width"]}" height="{c["card_height"]}" rx="12" fill="{fill}" stroke="#8da2b5" stroke-width="1.5"/>')
            lines = wrap_lines(node["label"])
            start_y = y + c["card_height"]/2 - ((len(lines)-1)*11)
            for j, line in enumerate(lines):
                out.append(f'<text x="{x+c["card_width"]/2}" y="{start_y+j*23}" text-anchor="middle" font-family="Arial,sans-serif" font-size="16" fill="#20364b">{escape(line)}</text>')
    elif spec["id"] in {"fig_4_2_cremad_evaluation", "fig_4_6_gemini_response_comparison"}:
        metrics = spec["metrics"]
        max_value = 6 if spec["id"] == "fig_4_6_gemini_response_comparison" else 50
        left, top, row_h = 350, 130, 92
        axis_w = w - left - 160
        plotted = metrics if spec["id"] == "fig_4_2_cremad_evaluation" else metrics[:2]
        for i, m in enumerate(plotted):
            y = top + i * row_h
            width = axis_w * float(m["value"]) / max_value
            out.append(f'<text x="{left-20}" y="{y+30}" text-anchor="end" font-family="Arial,sans-serif" font-size="17" fill="#20364b">{escape(m["label"])}</text>')
            out.append(f'<rect x="{left}" y="{y}" width="{width}" height="40" rx="5" fill="#477a9e"/>')
            value = f"{m['value']} {m['unit']}"
            out.append(f'<text x="{left+width+10}" y="{y+27}" font-family="Arial,sans-serif" font-size="16" fill="#20364b">{escape(value)}</text>')
        if spec["id"] == "fig_4_2_cremad_evaluation":
            out.append(f'<text x="{left}" y="{top+4*row_h+20}" font-family="Arial,sans-serif" font-size="16" fill="#20364b">Evaluation only; reference classes exceed the detector output labels.</text>')
        else:
            out.append(f'<text x="{left}" y="{top+2*row_h+20}" font-family="Arial,sans-serif" font-size="16" fill="#20364b">Adaptive preference: 4 of 5 paired comparisons (separate count, not rating scale).</text>')
    else:
        metrics = spec["metrics"]
        card_w, card_h = 390, 105
        left, top, gx, gy = 60, 135, 42, 38
        for i, m in enumerate(metrics):
            col, row = i % 3, i // 3
            x, y = left+col*(card_w+gx), top+row*(card_h+gy)
            out.append(f'<rect x="{x}" y="{y}" width="{card_w}" height="{card_h}" rx="12" fill="#eaf1f6" stroke="#8da2b5"/>')
            out.append(f'<text x="{x+card_w/2}" y="{y+40}" text-anchor="middle" font-family="Arial,sans-serif" font-size="16" fill="#20364b">{escape(m["label"])}</text>')
            out.append(f'<text x="{x+card_w/2}" y="{y+76}" text-anchor="middle" font-family="Arial,sans-serif" font-size="23" font-weight="700" fill="#18324b">{escape(str(m["value"]) + " " + m["unit"])}</text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"

if __name__ == "__main__":
    main()
