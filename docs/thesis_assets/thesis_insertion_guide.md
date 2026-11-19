# Thesis insertion guide

Chapter and subsection references below are recommendations only. The thesis source and existing figure numbering/placeholders were unavailable, so verify numbering and replace/retain decisions against the original before insertion.

## Figure 2.1: Overall HSIF system architecture

- **Chapter / subsection:** Chapter 2 — system design and methodology; place in the subsection covering overall hsif system architecture.
- **Suggested location:** After the paragraph that first explains this implementation/evaluation topic.
- **Figure title and caption:** Figure 2.1. Implemented HSIF components and external LLM services.
- **Explanation:** The React/Vite client communicates with FastAPI through audio/text REST endpoints and a live-audio WebSocket. Backend orchestration connects speech processing, heuristic state estimation, dialogue policy, LLM provider selection, and PostgreSQL persistence. Groq is the source-code default and Gemini is selectable; the diagram does not imply provider fallback.
- **Placement status:** Proposed new figure. Whether it replaces an existing placeholder is unknown until the thesis is supplied.
- **Caveat:** See `missing_evidence.md`; specifically, the diagram represents source implementation, not unverified live deployment behavior.

## Figure 2.2: Frontend–backend architecture

- **Chapter / subsection:** Chapter 2 — system design and methodology; place in the subsection covering frontend–backend architecture.
- **Suggested location:** After the paragraph that first explains this implementation/evaluation topic.
- **Figure title and caption:** Figure 2.2. Frontend inputs, API communication, and returned interaction data.
- **Explanation:** The client offers text chat, audio upload, live microphone interaction, dashboard, and history views. REST handles text, uploads, and retrieval; WebSocket carries live audio and event messages. Responses include transcript, HSR metadata, dialogue strategy, and assistant text where applicable.
- **Placement status:** Proposed new figure. Whether it replaces an existing placeholder is unknown until the thesis is supplied.
- **Caveat:** See `missing_evidence.md`; specifically, the diagram represents source implementation, not unverified live deployment behavior.

## Figure 2.3: Backend component architecture

- **Chapter / subsection:** Chapter 2 — system design and methodology; place in the subsection covering backend component architecture.
- **Suggested location:** After the paragraph that first explains this implementation/evaluation topic.
- **Figure title and caption:** Figure 2.3. Backend modules involved in processing and persistence.
- **Explanation:** FastAPI route handlers dispatch work to PipelineService. Audio turns pass through SpeechService; valid observations reach HumanStateEngine and temporal tracking. DialogueService fuses state, selects policy, constructs context, and calls LLMService. Successful turns are stored through SessionRepository.
- **Placement status:** Proposed new figure. Whether it replaces an existing placeholder is unknown until the thesis is supplied.
- **Caveat:** See `missing_evidence.md`; specifically, the diagram represents source implementation, not unverified live deployment behavior.

## Figure 2.4: Audio upload processing workflow

- **Chapter / subsection:** Chapter 2 — system design and methodology; place in the subsection covering audio upload processing workflow.
- **Suggested location:** After the paragraph that first explains this implementation/evaluation topic.
- **Figure title and caption:** Figure 2.4. REST audio-upload path from validation through successful turn persistence.
- **Explanation:** The upload route accepts supported extensions up to 25 MiB, creates a temporary file, and runs synchronous processing in a thread pool. The speech service converts to 16 kHz mono PCM, detects speech, transcribes, and extracts VAD-aligned features. Blank transcripts stop before dialogue generation. Successful LLM results are persisted; temporary files are cleaned up.
- **Placement status:** Proposed new figure. Whether it replaces an existing placeholder is unknown until the thesis is supplied.
- **Caveat:** See `missing_evidence.md`; specifically, the diagram represents source implementation, not unverified live deployment behavior.

## Figure 2.5: Text-only processing workflow

- **Chapter / subsection:** Chapter 2 — system design and methodology; place in the subsection covering text-only processing workflow.
- **Suggested location:** After the paragraph that first explains this implementation/evaluation topic.
- **Figure title and caption:** Figure 2.5. Text turns bypass acoustic inference and are marked as unmeasured.
- **Explanation:** A validated text request creates a state record with observation_valid=false and source=text_only. It does not call the acoustic feature extractor or HumanStateEngine inference. StateFusion receives the unmeasured marker; dialogue policy and prompt construction still run. Only successful generated turns are persisted.
- **Placement status:** Proposed new figure. Whether it replaces an existing placeholder is unknown until the thesis is supplied.
- **Caveat:** See `missing_evidence.md`; specifically, the diagram represents source implementation, not unverified live deployment behavior.

## Figure 2.6: Live microphone WebSocket workflow

- **Chapter / subsection:** Chapter 2 — system design and methodology; place in the subsection covering live microphone websocket workflow.
- **Suggested location:** After the paragraph that first explains this implementation/evaluation topic.
- **Figure title and caption:** Figure 2.6. Implemented buffered live-audio protocol; final turn processing remains full-recording.
- **Explanation:** The client opens a session, sends PCM chunks, and signals end_turn. The server emits chunk metadata and may transcribe the accumulated interim buffer after a one-second minimum and three-second interval. At end_turn it processes the complete turn and emits transcript, state, strategy, and response events. The diagram does not imply incremental HSR or continuous partial generation.
- **Placement status:** Proposed new figure. Whether it replaces an existing placeholder is unknown until the thesis is supplied.
- **Caveat:** See `missing_evidence.md`; specifically, the diagram represents source implementation, not unverified live deployment behavior.

## Figure 2.7: Audio preprocessing and speech recognition

- **Chapter / subsection:** Chapter 2 — system design and methodology; place in the subsection covering audio preprocessing and speech recognition.
- **Suggested location:** After the paragraph that first explains this implementation/evaluation topic.
- **Figure title and caption:** Figure 2.7. Supported upload validation, conversion, segmentation, transcription, and no-speech handling.
- **Explanation:** Uploads are limited by extension and file size before temporary storage. ffmpeg produces 16 kHz mono signed 16-bit PCM. Librosa-based VAD uses 30 ms frames and RMS threshold .01. Faster-Whisper transcribes the audio; acoustic pitch is extracted per speech segment where the segment is usable. Empty transcript raises a no-speech processing error.
- **Placement status:** Proposed new figure. Whether it replaces an existing placeholder is unknown until the thesis is supplied.
- **Caveat:** See `missing_evidence.md`; specifically, the diagram represents source implementation, not unverified live deployment behavior.

## Figure 2.8: Human State Recognition architecture

- **Chapter / subsection:** Chapter 2 — system design and methodology; place in the subsection covering human state recognition architecture.
- **Suggested location:** After the paragraph that first explains this implementation/evaluation topic.
- **Figure title and caption:** Figure 2.8. Heuristic feature-to-state pipeline; outputs are estimates, not validated psychological measures.
- **Explanation:** For audio turns, speech timing, VAD intervals, and acoustic features feed five separate heuristic dimensions. HumanStateEngine packages the outputs and validity metadata; smoothing/tracking operate on valid observations. Text-only turns do not enter this audio inference chain.
- **Placement status:** Proposed new figure. Whether it replaces an existing placeholder is unknown until the thesis is supplied.
- **Caveat:** See `missing_evidence.md`; specifically, the diagram represents source implementation, not unverified live deployment behavior.

## Figure 2.9: Five human-state dimensions and input features

- **Chapter / subsection:** Chapter 2 — system design and methodology; place in the subsection covering five human-state dimensions and input features.
- **Suggested location:** After the paragraph that first explains this implementation/evaluation topic.
- **Figure title and caption:** Figure 2.9. Implemented feature families used by the five HSR estimators.
- **Explanation:** The five values are derived from overlapping speech timing and acoustic features. Emotion uses pitch and energy heuristics; the remaining dimensions combine pause statistics, speech activity/duration, pitch range, and energy. They should be reported as heuristic proxies, not calibrated scores.
- **Placement status:** Proposed new figure. Whether it replaces an existing placeholder is unknown until the thesis is supplied.
- **Caveat:** See `missing_evidence.md`; specifically, the diagram represents source implementation, not unverified live deployment behavior.

## Figure 2.10: State fusion and temporal smoothing

- **Chapter / subsection:** Chapter 2 — system design and methodology; place in the subsection covering state fusion and temporal smoothing.
- **Suggested location:** After the paragraph that first explains this implementation/evaluation topic.
- **Figure title and caption:** Figure 2.10. Validity-aware temporal state handling and dialogue fusion.
- **Explanation:** Valid HSR observations pass through numeric smoothing (alpha .4 by default) and state tracking (change threshold .1). Emotion confirmation count defaults to 1, so labels can change immediately. Invalid observations do not replace the valid smoothing baseline and are not counted as fresh state changes. StateFusion derives interaction conditions for dialogue policy.
- **Placement status:** Proposed new figure. Whether it replaces an existing placeholder is unknown until the thesis is supplied.
- **Caveat:** See `missing_evidence.md`; specifically, the diagram represents source implementation, not unverified live deployment behavior.

## Figure 2.11: Human-state observation validity

- **Chapter / subsection:** Chapter 2 — system design and methodology; place in the subsection covering human-state observation validity.
- **Suggested location:** After the paragraph that first explains this implementation/evaluation topic.
- **Figure title and caption:** Figure 2.11. Valid audio, unusable audio, and text-only turns remain distinct.
- **Explanation:** Valid audio may yield a measured neutral emotion. Invalid audio features and text-only input are unmeasured and use unknown/invalid metadata rather than a neutral measurement. Text-only turns carry source=text_only and do not reuse a previous audio-derived value as the current observation.
- **Placement status:** Proposed new figure. Whether it replaces an existing placeholder is unknown until the thesis is supplied.
- **Caveat:** See `missing_evidence.md`; specifically, the diagram represents source implementation, not unverified live deployment behavior.

## Figure 2.12: Adaptive dialogue policy workflow

- **Chapter / subsection:** Chapter 2 — system design and methodology; place in the subsection covering adaptive dialogue policy workflow.
- **Suggested location:** After the paragraph that first explains this implementation/evaluation topic.
- **Figure title and caption:** Figure 2.12. HSR/context to strategy and generated response.
- **Explanation:** DialogueService combines the current interaction with conversation memory, fuses valid state or handles unmeasured input, applies ordered policy rules, and constructs a prompt. LLMService dispatches to the configured provider. The API returns the strategy and generated text; successful turns are persisted.
- **Placement status:** Proposed new figure. Whether it replaces an existing placeholder is unknown until the thesis is supplied.
- **Caveat:** See `missing_evidence.md`; specifically, the diagram represents source implementation, not unverified live deployment behavior.

## Figure 2.13: Dialogue strategy decision flow

- **Chapter / subsection:** Chapter 2 — system design and methodology; place in the subsection covering dialogue strategy decision flow.
- **Suggested location:** After the paragraph that first explains this implementation/evaluation topic.
- **Figure title and caption:** Figure 2.13. Condensed policy precedence; synthetic cases do not establish audio-triggered coverage.
- **Explanation:** The policy evaluates conditions in precedence order: frustration acknowledgment, reassurance, overload-related simplification or reduction, slow-down, clarification/re-engagement/continuation, follow-up or encouragement, then normal response. Several branches depend on labels not emitted by the current acoustic emotion detector; those branches are implemented but not demonstrated end-to-end by the audio classifier.
- **Placement status:** Proposed new figure. Whether it replaces an existing placeholder is unknown until the thesis is supplied.
- **Caveat:** See `missing_evidence.md`; specifically, the diagram represents source implementation, not unverified live deployment behavior.

## Figure 2.14: LLM provider integration

- **Chapter / subsection:** Chapter 2 — system design and methodology; place in the subsection covering llm provider integration.
- **Suggested location:** After the paragraph that first explains this implementation/evaluation topic.
- **Figure title and caption:** Figure 2.14. Configuration selects one provider; no automatic fallback is implemented.
- **Explanation:** LLMService validates LLM_PROVIDER and constructs either GroqProvider or GeminiProvider. Groq is the source default. Each adapter sends a prompt to its external service and returns text or a typed safe error. The application does not automatically switch providers after a failure.
- **Placement status:** Proposed new figure. Whether it replaces an existing placeholder is unknown until the thesis is supplied.
- **Caveat:** See `missing_evidence.md`; specifically, the diagram represents source implementation, not unverified live deployment behavior.

## Figure 2.15: PostgreSQL entity–relationship model

- **Chapter / subsection:** Chapter 2 — system design and methodology; place in the subsection covering postgresql entity–relationship model.
- **Suggested location:** After the paragraph that first explains this implementation/evaluation topic.
- **Figure title and caption:** Figure 2.15. SQLAlchemy session and conversation-turn tables; schema shown from model declarations.
- **Explanation:** A session has a string primary key and timestamps. ConversationTurn uses an integer primary key, a non-null foreign key to sessions.id with cascade deletion, message text, JSONB human state, strategy text, and creation time. The relationship is one session to many turns. This diagram reflects ORM declarations; live database schema was not inspected.
- **Placement status:** Proposed new figure. Whether it replaces an existing placeholder is unknown until the thesis is supplied.
- **Caveat:** See `missing_evidence.md`; specifically, the diagram represents source implementation, not unverified live deployment behavior.

## Figure 2.16: API interaction overview

- **Chapter / subsection:** Chapter 2 — system design and methodology; place in the subsection covering api interaction overview.
- **Suggested location:** After the paragraph that first explains this implementation/evaluation topic.
- **Figure title and caption:** Figure 2.16. Implemented REST and WebSocket entry points and their response forms.
- **Explanation:** Audio uses multipart REST and returns ProcessResponse. Text uses JSON REST and returns processed turn data. Live audio uses a WebSocket session with binary PCM and JSON events. Session list/detail and state trajectory are separate REST reads. The health endpoint is static and does not assert database readiness.
- **Placement status:** Proposed new figure. Whether it replaces an existing placeholder is unknown until the thesis is supplied.
- **Caveat:** See `missing_evidence.md`; specifically, the diagram represents source implementation, not unverified live deployment behavior.

## Figure 2.17: Conversation persistence and retrieval

- **Chapter / subsection:** Chapter 2 — system design and methodology; place in the subsection covering conversation persistence and retrieval.
- **Suggested location:** After the paragraph that first explains this implementation/evaluation topic.
- **Figure title and caption:** Figure 2.17. Successful turn persistence and session/history retrieval.
- **Explanation:** A session ID identifies a session; the repository can create or retrieve the session before turn processing. A conversation turn is added only after successful generation. History endpoints read summaries/details from PostgreSQL, and the state endpoint returns trajectory data reconstructed by the pipeline service. Frontend account/session prototype data in localStorage is separate from conversation persistence.
- **Placement status:** Proposed new figure. Whether it replaces an existing placeholder is unknown until the thesis is supplied.
- **Caveat:** See `missing_evidence.md`; specifically, the diagram represents source implementation, not unverified live deployment behavior.

## Figure 2.18: Local development deployment architecture

- **Chapter / subsection:** Chapter 2 — system design and methodology; place in the subsection covering local development deployment architecture.
- **Suggested location:** After the paragraph that first explains this implementation/evaluation topic.
- **Figure title and caption:** Figure 2.18. Verified local development components; not a production cloud deployment.
- **Explanation:** The repository configures a Vite frontend, local FastAPI backend, PostgreSQL 18 Compose service on host port 5434, and external LLM APIs selected through environment configuration. The Vite development port defaults to 5173 but may vary. The actual running container, server versions, credentials, and readiness were not verified.
- **Placement status:** Proposed new figure. Whether it replaces an existing placeholder is unknown until the thesis is supplied.
- **Caveat:** See `missing_evidence.md`; specifically, the diagram represents source implementation, not unverified live deployment behavior.

## Figure 2.19: Security and data-handling flow

- **Chapter / subsection:** Chapter 2 — system design and methodology; place in the subsection covering security and data-handling flow.
- **Suggested location:** After the paragraph that first explains this implementation/evaluation topic.
- **Figure title and caption:** Figure 2.19. Current handling controls and verified security limitations.
- **Explanation:** Audio requests receive extension/size validation and temporary files are removed after processing; audio is not stored in conversation tables. Successful message/state/strategy data are persisted in PostgreSQL. Provider credentials are configured through environment variables. Browser-local authentication is only a prototype, and API/WS ownership checks and rate limiting are absent; this is not production-secure authentication.
- **Placement status:** Proposed new figure. Whether it replaces an existing placeholder is unknown until the thesis is supplied.
- **Caveat:** See `missing_evidence.md`; specifically, the diagram represents source implementation, not unverified live deployment behavior.

## Figure 4.1: Evaluation methodology and evidence tracks

- **Chapter / subsection:** Chapter 4 — evaluation methodology/results; place in the subsection covering evaluation methodology and evidence tracks.
- **Suggested location:** After the paragraph that first explains this implementation/evaluation topic.
- **Figure title and caption:** Figure 4.1. Separate software, dataset, synthetic, and exploratory evaluation tracks.
- **Explanation:** The repository contains five distinct evaluation tracks with different evidence strength: CREMA-D labeled audio evaluation; a one-fixture speech benchmark; synthetic HSR behavior checks; synthetic dialogue-policy checks; and a small historical Gemini response comparison. Their results should not be combined as a single accuracy or human-study claim.
- **Placement status:** Proposed new figure. Whether it replaces an existing placeholder is unknown until the thesis is supplied.
- **Caveat:** See `missing_evidence.md`; specifically, historical evaluation scope/provenance applies.

## Figure 4.2: CREMA-D emotion evaluation results

- **Chapter / subsection:** Chapter 4 — evaluation methodology/results; place in the subsection covering crema-d emotion evaluation results.
- **Suggested location:** After the paragraph that first explains this implementation/evaluation topic.
- **Figure title and caption:** Figure 4.2. CREMA-D evaluation metrics; data were evaluated, not used for training.
- **Explanation:** The stored result covers 7,442 recordings. The six-reference-class accuracy is 21.61%; six-class macro-F1 recomputed from stored per-class values is approximately .156. On the happy/neutral/sad subset, accuracy is approximately .443 and macro-F1 approximately .439. Detector outputs are narrower than the six reference classes, so these numbers should not be generalized as overall emotion-recognition accuracy.
- **Placement status:** Proposed new figure. Whether it replaces an existing placeholder is unknown until the thesis is supplied.
- **Caveat:** See `missing_evidence.md`; specifically, historical evaluation scope/provenance applies.

## Figure 4.3: Speech benchmark: one-fixture results

- **Chapter / subsection:** Chapter 4 — evaluation methodology/results; place in the subsection covering speech benchmark: one-fixture results.
- **Suggested location:** After the paragraph that first explains this implementation/evaluation topic.
- **Figure title and caption:** Figure 4.3. Faster-Whisper measurements for one audio/reference fixture only.
- **Explanation:** Five warm runs on a single fixture produced mean latency 1.839 seconds, median 1.841 seconds, and P95 2.209 seconds. WER was .125 and CER .0392 for that fixture. The sample is too small to support a general transcription-quality or performance claim.
- **Placement status:** Proposed new figure. Whether it replaces an existing placeholder is unknown until the thesis is supplied.
- **Caveat:** See `missing_evidence.md`; specifically, historical evaluation scope/provenance applies.

## Figure 4.4: Synthetic human-state behavior checks

- **Chapter / subsection:** Chapter 4 — evaluation methodology/results; place in the subsection covering synthetic human-state behavior checks.
- **Suggested location:** After the paragraph that first explains this implementation/evaluation topic.
- **Figure title and caption:** Figure 4.4. Twenty synthetic HSR benchmark runs across four constructed profiles.
- **Explanation:** The benchmark repeats four synthetic profiles five times each. It checks expected heuristic directionality, bounded output, and determinism. It does not compare predictions against labeled human observations and therefore is not an emotion or HSR accuracy evaluation.
- **Placement status:** Proposed new figure. Whether it replaces an existing placeholder is unknown until the thesis is supplied.
- **Caveat:** See `missing_evidence.md`; specifically, historical evaluation scope/provenance applies.

## Figure 4.5: Synthetic dialogue-policy behavior checks

- **Chapter / subsection:** Chapter 4 — evaluation methodology/results; place in the subsection covering synthetic dialogue-policy behavior checks.
- **Suggested location:** After the paragraph that first explains this implementation/evaluation topic.
- **Figure title and caption:** Figure 4.5. Three hundred local policy attempts over five synthetic scenarios.
- **Explanation:** Five synthetic cases were repeated 30 times for baseline and adaptive modes, totaling 300 local attempts. The experiment checks policy/strategy behavior, not external LLM response quality, user outcomes, or conversational effectiveness.
- **Placement status:** Proposed new figure. Whether it replaces an existing placeholder is unknown until the thesis is supplied.
- **Caveat:** See `missing_evidence.md`; specifically, historical evaluation scope/provenance applies.

## Figure 4.6: Exploratory Gemini response comparison

- **Chapter / subsection:** Chapter 4 — evaluation methodology/results; place in the subsection covering exploratory gemini response comparison.
- **Suggested location:** After the paragraph that first explains this implementation/evaluation topic.
- **Figure title and caption:** Figure 4.6. Historical response ratings: exploratory results; reviewer provenance was not recorded.
- **Explanation:** Across five scenarios, the historical artifact records ten direct Gemini calls. The adaptive condition has mean rating 4.24/5 versus 3.96/5 baseline, and was preferred in four of five pairs. Reviewer identity and provenance are absent and the sample is small; this is exploratory evidence, not a controlled human study. The evaluation README contains conflicting summary values.
- **Placement status:** Proposed new figure. Whether it replaces an existing placeholder is unknown until the thesis is supplied.
- **Caveat:** See `missing_evidence.md`; specifically, historical evaluation scope/provenance applies.
