import subprocess
from pathlib import Path


class AudioProcessor:

    def convert_to_wav(self, input_path, output_path):
        input_path = Path(input_path)
        output_path = Path(output_path)
        if not input_path.exists():
            raise FileNotFoundError(
                f"Audio file not found: {input_path}"
            )
            
        output_path.parent.mkdir(parents=True, exist_ok=True)

        command = [
            "ffmpeg",
            "-y",
            "-i",
            str(input_path),
            "-ar",
            "16000",
            "-ac",
            "1",
            "-sample_fmt",
            "s16",
            str(output_path)
        ]
        try:
            subprocess.run(command, check=True,
                    capture_output=True,
                    text=True)
        except subprocess.CalledProcessError as error:
            raise RuntimeError(
                f"Audio conversion failed: {error.stderr}"
            ) from error

        return str(output_path)