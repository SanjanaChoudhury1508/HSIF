from ai.speech.speech_service import SpeechService
from ai.human_state.human_state_engine import HumanStateEngine
from ai.dialogue.dialogue_service import DialogueService
from backend.app.services.llm.llm_service import LLMService
from backend.app.services.llm.gemini_provider import GeminiProvider
class PipelineService:
    def __init__(self):
        self.speech_service = SpeechService()
        self.human_state_engine = HumanStateEngine()
        self.dialogue_service = DialogueService()
        self.llm_service = LLMService(
            provider=GeminiProvider()
        )
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
        return {
            "speech": speech_result,
            "human_state": human_state,
            "dialogue": dialogue_result,
            "response": llm_response,
        }