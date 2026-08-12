from ai.speech.vad.detector import VoiceActivityDetector


audio_path = "tests/audio/processed.wav"

vad = VoiceActivityDetector()

result = vad.detect(audio_path)

print("Total duration:", result["duration"])

print("Speech duration:", result["speech_duration"])

print("Silence duration:", result["silence_duration"])

print("\nSpeech segments:")

for segment in result["speech_segments"]:
    print(
        f"{segment['start']:.2f}s - "
        f"{segment['end']:.2f}s"
    )