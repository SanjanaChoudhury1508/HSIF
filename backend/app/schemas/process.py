from pydantic import BaseModel


class AudioResponse(BaseModel):
    duration: float
    speech_duration: float
    silence_duration: float


class SpeechSegment(BaseModel):
    start: float
    end: float


class Pause(BaseModel):
    start: float
    end: float
    duration: float


class VADResponse(BaseModel):
    speech_segments: list[SpeechSegment]
    pauses: list[Pause]


class AudioFeaturesResponse(BaseModel):
    number_of_pauses: int
    average_pause_duration: float
    max_pause_duration: float
    mean_energy: float
    mean_pitch: float
    min_pitch: float
    max_pitch: float


class SpeechResponse(BaseModel):
    transcript: str
    language: str
    language_probability: float
    audio: AudioResponse
    vad: VADResponse
    features: AudioFeaturesResponse


class EmotionResponse(BaseModel):
    label: str
    score: float


class ScoreResponse(BaseModel):
    score: float


class HumanStateResponse(BaseModel):
    emotion: EmotionResponse
    hesitation: ScoreResponse
    confidence: ScoreResponse
    engagement: ScoreResponse
    cognitive_load: ScoreResponse


class DialogueStateResponse(BaseModel):
    emotion: str
    emotion_score: float
    hesitation: float
    confidence: float
    engagement: float
    cognitive_load: float
    interaction_state: str
    needs_clarification: bool
    needs_encouragement: bool


class DialoguePolicyResponse(BaseModel):
    strategy: str
    reason: str
    priority: str


class ConversationTurnResponse(BaseModel):
    user_message: str
    assistant_message: str


class DialogueResponse(BaseModel):
    dialogue_state: DialogueStateResponse
    policy: DialoguePolicyResponse
    history: list[ConversationTurnResponse]
    prompt: str


class ProcessResponse(BaseModel):
    speech: SpeechResponse
    human_state: HumanStateResponse
    dialogue: DialogueResponse