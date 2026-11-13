import time
import math
from ai.speech.speech_service import SpeechService
from ai.human_state.human_state_engine import HumanStateEngine
from ai.human_state.hsr import build_human_state
from ai.dialogue.dialogue_service import DialogueService
from backend.app.services.llm.llm_service import LLMService

from database.repository import SessionRepository


class NoSpeechDetectedError(ValueError):
    """Raised when audio processing produces no usable transcript."""


class PipelineService:
    def __init__(
        self,
        llm_provider=None,
        session_id: str | None = None,
        repository: SessionRepository | None = None,
    ):
        self.session_id = session_id
        self.repository = repository

        self.speech_service = SpeechService()
        self.human_state_engine = HumanStateEngine(
            enable_temporal_smoothing=True,
        )
        self.dialogue_service = DialogueService()
        self.llm_service = LLMService(provider=llm_provider)

        if self.session_id and self.repository:
            self._restore_history()

    def process_audio(self, audio_path):
        speech_result = self.speech_service.process(audio_path)
        transcript = (
            speech_result.get("transcript")
            if isinstance(speech_result, dict)
            else None
        )
        if not isinstance(transcript, str) or not transcript.strip():
            raise NoSpeechDetectedError(
                "No speech could be transcribed from this audio. "
                "Try a recording with clear, audible speech."
            )
        transcript = transcript.strip()
        speech_result = {**speech_result, "transcript": transcript}

        observation_timestamp=time.time()
        observation_valid=self._is_valid_observation(speech_result)
        human_state = self.human_state_engine.process_to_dict(
            speech_result,
            timestamp=observation_timestamp,
            observation_valid=observation_valid,
        )
        current_state = self.human_state_engine.get_current_state()
        persisted_human_state = self._build_persisted_human_state(
            human_state,
            current_state,
        )

        dialogue_result = self.dialogue_service.process(
            transcript,
            human_state
        )

        llm_response = self.llm_service.generate(
            dialogue_result["prompt"]
        )

        # Persist first so failed writes do not leave dialogue memory
        # containing a turn that was not saved.
        if self.session_id and self.repository:
            self.repository.add_turn(
                session_id=self.session_id,
                user_message=transcript,
                assistant_message=llm_response,
                human_state=persisted_human_state,
                dialogue_strategy=dialogue_result["policy"]["strategy"],
            )

        # Update in-memory conversation history only after persistence succeeds.
        self.dialogue_service.add_response(
            user_message=transcript,
            assistant_message=llm_response,
            human_state=human_state,
            dialogue_strategy=dialogue_result["policy"]["strategy"],
        )

        return {
            "speech": speech_result,
            "human_state": persisted_human_state,
            "dialogue": dialogue_result,
            "response": llm_response,
        }


    def process_text(self, user_message: str):
        """Process a typed message through the existing dialogue pipeline."""

        if not isinstance(user_message, str) or not user_message.strip():
            raise ValueError("Message cannot be empty.")

        user_message = user_message.strip()

        # Reuse the latest observed human state when available.
        current_state = self.human_state_engine.get_current_state()

        if current_state is not None:
            human_state = current_state.to_dict()
            persisted_human_state = self._build_persisted_human_state(
                human_state,
                current_state,
            )
        else:
            # No audio observation exists yet.
            # These are neutral fallback values, NOT measured human-state scores.
            human_state = {
                "emotion": {"label": "unknown", "score": 0.0},
                "hesitation": {"score": 0.0},
                "confidence": {"score": 0.0},
                "engagement": {"score": 0.0},
                "cognitive_load": {"score": 0.0},
            }

            persisted_human_state = {
                **human_state,
                "_temporal": {
                    "observation_valid": False,
                    "source": "text_only",
                },
            }

        dialogue_result = self.dialogue_service.process(
            user_message,
            human_state,
        )

        llm_response = self.llm_service.generate(
            dialogue_result["prompt"]
        )

        # Persist before updating in-memory conversation history.
        if self.session_id and self.repository:
            self.repository.add_turn(
                session_id=self.session_id,
                user_message=user_message,
                assistant_message=llm_response,
                human_state=persisted_human_state,
                dialogue_strategy=dialogue_result["policy"]["strategy"],
            )

        self.dialogue_service.add_response(
            user_message=user_message,
            assistant_message=llm_response,
            human_state=human_state,
            dialogue_strategy=dialogue_result["policy"]["strategy"],
        )

        return {
            "user_message": user_message,
            "human_state": persisted_human_state,
            "dialogue": dialogue_result,
            "response": llm_response,
        }


    @staticmethod
    def _build_persisted_human_state(
        human_state: dict,
        state=None,
    ) -> dict:
        """Preserve the public HSR fields and temporal metadata for storage."""
        snapshot = dict(human_state)

        if state is not None:
            snapshot["_temporal"] = {
                "timestamp": state.timestamp,
                "observation_valid": state.observation_valid,
            }

        return snapshot

    def _restore_history(self):
        """Restore persisted conversation history and human-state trajectory."""

        self.repository.get_or_create_session(self.session_id)

        turns = self.repository.get_turns(
            self.session_id,
            limit=self.dialogue_service.memory.max_turns,
        )

        for turn in turns:
            # Restore conversation memory.
            self.dialogue_service.add_response(
                user_message=turn.user_message,
                assistant_message=turn.assistant_message,
                human_state=turn.human_state,
                dialogue_strategy=turn.dialogue_strategy,
            )

            # Restore Human State trajectory.
            persisted_state = turn.human_state
            temporal=persisted_state.get("_temporal",{})

            restored_state = build_human_state(
                emotion_label=persisted_state["emotion"]["label"],
                emotion_score=persisted_state["emotion"]["score"],
                hesitation_score=persisted_state["hesitation"]["score"],
                confidence_score=persisted_state["confidence"]["score"],
                engagement_score=persisted_state["engagement"]["score"],
                cognitive_load_score=persisted_state["cognitive_load"]["score"],
                timestamp=temporal.get("timestamp"),
                observation_valid=temporal.get("observation_valid", True),
            )

            self.human_state_engine.state_tracker.add_state(
                restored_state
            )


    @staticmethod
    def _is_valid_observation(speech_result: dict) -> bool:
        """Return whether audio contains usable detected speech."""
        if not isinstance(speech_result, dict):
            return False

        audio = speech_result.get("audio")
        vad = speech_result.get("vad")

        if not isinstance(audio, dict) or not isinstance(vad, dict):
            return False

        try:
            duration = float(audio.get("duration", 0.0))
            speech_duration = float(audio.get("speech_duration", 0.0))
        except (TypeError, ValueError, OverflowError):
            return False

        if not math.isfinite(duration) or not math.isfinite(speech_duration):
            return False

        segments = vad.get("speech_segments")

        return (
            duration > 0.0
            and speech_duration > 0.0
            and isinstance(segments, (list, tuple))
            and bool(segments)
        )
