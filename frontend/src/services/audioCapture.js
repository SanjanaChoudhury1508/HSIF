
const TARGET_SAMPLE_RATE = 16000;

function resampleAudio(input, sourceRate, targetRate) {
  if (sourceRate === targetRate) {
    return input;
  }

  const outputLength = Math.round(
    input.length * targetRate / sourceRate
  );

  const output = new Float32Array(outputLength);
  const ratio = sourceRate / targetRate;

  for (let i = 0; i < outputLength; i++) {
    const position = i * ratio;
    const left = Math.floor(position);
    const right = Math.min(left + 1, input.length - 1);
    const fraction = position - left;

    output[i] =
      input[left] * (1 - fraction) +
      input[right] * fraction;
  }

  return output;
}

function floatToPcm16(samples) {
  const pcm = new Int16Array(samples.length);

  for (let i = 0; i < samples.length; i++) {
    const sample = Math.max(-1, Math.min(1, samples[i]));

    pcm[i] = sample < 0
      ? sample * 32768
      : sample * 32767;
  }

  return pcm;
}

export async function startMicrophoneStreaming(
  websocket,
  onError = console.error
) {
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: {
      channelCount: 1,
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
    },
  });

  const audioContext = new AudioContext();
  const source = audioContext.createMediaStreamSource(stream);

  // ScriptProcessorNode is deprecated, but is a simple first
  // integration step. Replace it with AudioWorklet for production.
  const processor = audioContext.createScriptProcessor(
    4096,
    1,
    1
  );

  processor.onaudioprocess = (event) => {
    if (websocket.readyState !== WebSocket.OPEN) {
      return;
    }

    const input = event.inputBuffer.getChannelData(0);
    const resampled = resampleAudio(
      input,
      audioContext.sampleRate,
      TARGET_SAMPLE_RATE
    );

    const pcm = floatToPcm16(resampled);

    // Send raw PCM bytes, not JSON or Base64.
    websocket.send(pcm.buffer);
  };

  source.connect(processor);

  // A muted output avoids feeding microphone audio back to speakers.
  const mute = audioContext.createGain();
  mute.gain.value = 0;

  processor.connect(mute);
  mute.connect(audioContext.destination);

  let stopped = false;

  return async function stopMicrophoneStreaming() {
    if (stopped) return;
    stopped = true;

    processor.onaudioprocess = null;
    source.disconnect();
    processor.disconnect();
    mute.disconnect();

    stream.getTracks().forEach((track) => track.stop());

    await audioContext.close();
  };
}
