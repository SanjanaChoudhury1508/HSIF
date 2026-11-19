const TARGET_SAMPLE_RATE = 16000;

export function runMicrophoneStartOnce(startingRef, start) {
  if (startingRef.current) return null;

  startingRef.current = true;

  return Promise.resolve()
    .then(start)
    .finally(() => {
      startingRef.current = false;
    });
}

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

export async function startMicrophoneStreaming(websocket) {
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: {
      channelCount: 1,
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
    },
  });

  let audioContext;
  let source;
  let processor;
  let mute;
  let stopped = false;

  const stop = async () => {
    if (stopped) return;
    stopped = true;

    if (processor) processor.onaudioprocess = null;
    for (const node of [source, processor, mute]) {
      try {
        node?.disconnect();
      } catch {
        // Keep releasing resources even if one node cannot disconnect.
      }
    }

    stream.getTracks().forEach((track) => track.stop());

    if (audioContext && audioContext.state !== "closed") {
      try {
        await audioContext.close();
      } catch {
        // Tracks are stopped; do not hide the original startup error.
      }
    }
  };

  try {
    audioContext = new AudioContext();
    source = audioContext.createMediaStreamSource(stream);

    // ScriptProcessorNode is deprecated, but is a simple first
    // integration step. Replace with AudioWorklet for production.
    processor = audioContext.createScriptProcessor(4096, 1, 1);

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
    mute = audioContext.createGain();
    mute.gain.value = 0;

    processor.connect(mute);
    mute.connect(audioContext.destination);

    return stop;
  } catch (error) {
    await stop();
    throw error;
  }
}
