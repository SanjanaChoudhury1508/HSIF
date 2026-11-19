const configuredTimeout = Number(
  import.meta.env?.VITE_AUDIO_UPLOAD_TIMEOUT_MS
);

export const AUDIO_UPLOAD_TIMEOUT_MS =
  Number.isFinite(configuredTimeout) && configuredTimeout > 0
    ? configuredTimeout
    : 180_000;

export class AudioUploadTimeoutError extends Error {
  constructor(timeoutMs) {
    super(
      `Audio upload timed out after ${Math.ceil(timeoutMs / 1000)} seconds. Please try again.`
    );
    this.name = "AudioUploadTimeoutError";
  }
}

export async function uploadAudio(
  url,
  formData,
  timeoutMs = AUDIO_UPLOAD_TIMEOUT_MS,
  fetchImpl = globalThis.fetch
) {
  const controller = new AbortController();
  let timedOut = false;
  const timeoutId = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, timeoutMs);

  try {
    const response = await fetchImpl(url, {
      method: "POST",
      body: formData,
      signal: controller.signal,
    });
    const data = await response.json();

    if (timedOut) {
      throw new AudioUploadTimeoutError(timeoutMs);
    }

    if (!response.ok) {
      throw new Error(data.detail || "Audio processing failed.");
    }

    return data;
  } catch (error) {
    if (timedOut || (controller.signal.aborted && error.name === "AbortError")) {
      throw new AudioUploadTimeoutError(timeoutMs);
    }
    throw error;
  } finally {
    clearTimeout(timeoutId);
  }
}

export async function withLoadingState(setLoading, operation) {
  setLoading(true);
  try {
    return await operation();
  } finally {
    setLoading(false);
  }
}
