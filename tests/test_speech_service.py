from pprint import pprint

from ai.speech.speech_service import SpeechService


audio_path = "tests/audio/recording.m4a"

speech_service = SpeechService()

result = speech_service.process(audio_path)

pprint(result)