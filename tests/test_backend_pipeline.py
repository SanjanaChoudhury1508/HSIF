from pathlib import Path

from backend.app.services.pipeline_service import PipelineService


def main():
    audio_path = Path("tests/audio/recording.m4a")

    pipeline = PipelineService()
    result = pipeline.process_audio(audio_path)

    print("\n" + "=" * 60)
    print("SPEECH PROCESSING")
    print("=" * 60)

    print("\nTranscript:")
    print(result["speech"]["transcript"])

    print("\nLanguage:")
    print(result["speech"]["language"])

    print("\nAudio:")
    print(result["speech"]["audio"])

    print("\nFeatures:")
    print(result["speech"]["features"])

    print("\n" + "=" * 60)
    print("HUMAN STATE")
    print("=" * 60)

    print(result["human_state"])

    print("\n" + "=" * 60)
    print("DIALOGUE POLICY")
    print("=" * 60)

    print("Strategy:")
    print(result["dialogue"]["policy"]["strategy"])

    print("\nReason:")
    print(result["dialogue"]["policy"]["reason"])

    print("\nPriority:")
    print(result["dialogue"]["policy"]["priority"])

    print("\n" + "=" * 60)
    print("GENERATED PROMPT")
    print("=" * 60)

    print(result["dialogue"]["prompt"])


if __name__ == "__main__":
    main()