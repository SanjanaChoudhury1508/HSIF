from ai.speech.preprocessing.audio_processor import AudioProcessor
from ai.speech.whisper.transcriber import SpeechTranscriber


input_audio = "tests/audio/recording.m4a"
processed_audio = "tests/audio/processed.wav"


processor = AudioProcessor()

processor.convert_to_wav(
    input_audio,
    processed_audio
)

transcriber = SpeechTranscriber()

result = transcriber.transcribe(processed_audio)

print("\nTranscript:")
print(result["text"])

print("\nLanguage:")
print(result["language"])

print("\nLanguage Probability:")
print(result["language_probability"])