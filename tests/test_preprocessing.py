from ai.speech.preprocessing.audio_processor import AudioProcessor


input_audio = "tests/audio/recording.m4a"
output_audio = "tests/audio/processed.wav"

processor = AudioProcessor()

result = processor.convert_to_wav(
    input_audio,
    output_audio
)

print("Processed audio:")
print(result)