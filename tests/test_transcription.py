from ai.speech.whisper.transcriber import SpeechTranscriber


audio_path = "tests/audio/sample.wav"

transcriber = SpeechTranscriber()

result = transcriber.transcribe(audio_path)

print("Transcript:")
print(result["text"])

print("\nLanguage:")
print(result["language"])

print("\nLanguage Probability:")
print(result["language_probability"])