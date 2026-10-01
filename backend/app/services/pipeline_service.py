from ai.speech.speech_service import SpeechService
from ai.human_state.human_state_engine import HumanStateEngine
from ai.human_state.hsr import build_human_state
from ai.dialogue.dialogue_service import DialogueService
from backend.app.services.llm.llm_service import LLMService
from backend.app.services.llm.provider import LLMProvider
from database.repository import SessionRepository

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
        self.human_state_engine = HumanStateEngine()
        self.dialogue_service = DialogueService()
        self.llm_service = LLMService(provider=llm_provider)

        if self.session_id and self.repository:
            self._restore_history()

    def process_audio(self, audio_path):
        speech_result = self.speech_service.process(audio_path)

        human_state = self.human_state_engine.process_to_dict(
            speech_result
        )

        dialogue_result = self.dialogue_service.process(
            speech_result["transcript"],
            human_state
        )

        llm_response = self.llm_service.generate(
            dialogue_result["prompt"]
        )

        # Store the completed user-assistant interaction
        # after the LLM has generated its response.
        self.dialogue_service.add_response(
            user_message=speech_result["transcript"],
            assistant_message=llm_response,
            human_state=human_state,
            dialogue_strategy=dialogue_result["policy"]["strategy"],
        )
        if self.session_id and self.repository:
            self.repository.add_turn(
                session_id=self.session_id,
                user_message=speech_result["transcript"],
                assistant_message=llm_response,
                human_state=human_state,
                dialogue_strategy=dialogue_result["policy"]["strategy"],
            )

        return {
            "speech": speech_result,
            "human_state": human_state,
            "dialogue": dialogue_result,
            "response": llm_response,
        }


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

            restored_state = build_human_state(
                emotion_label=persisted_state["emotion"]["label"],
                emotion_score=persisted_state["emotion"]["score"],
                hesitation_score=persisted_state["hesitation"]["score"],
                confidence_score=persisted_state["confidence"]["score"],
                engagement_score=persisted_state["engagement"]["score"],
                cognitive_load_score=persisted_state["cognitive_load"]["score"],
            )

            self.human_state_engine.state_tracker.add_state(
                restored_state
            )