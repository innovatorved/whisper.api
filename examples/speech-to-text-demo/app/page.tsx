"use client";

import { DeepgramClient } from "@deepgram/sdk";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

const DEEPGRAM_API_KEY = "a078f4b3560745a7a52b8335cad94c25bYNNABFswluovMP94prkwrW2ji6hQ3eo";
const DEEPGRAM_BASE_URL = "https://innovatorved-whisper-api.hf.space";

type LiveResultMessage = {
  type: "Results";
  is_final?: boolean;
  channel?: {
    alternatives?: Array<{
      transcript?: string;
    }>;
  };
};

type DeepgramLiveSocket = {
  readyState: number;
  on: (event: "open" | "message" | "close" | "error", callback: (...args: unknown[]) => void) => void;
  connect: () => DeepgramLiveSocket;
  waitForOpen: () => Promise<unknown>;
  close: () => void;
  sendMedia: (message: ArrayBufferLike | Blob | ArrayBufferView) => void;
  sendCloseStream: (message: { type: "CloseStream" }) => void;
};

const TARGET_SAMPLE_RATE = 16_000;
const BLANK_AUDIO_REGEX = /\[\s*BLANK_AUDIO\s*\]/gi;

function isLiveResultMessage(payload: unknown): payload is LiveResultMessage {
  if (!payload || typeof payload !== "object") {
    return false;
  }
  return (payload as { type?: string }).type === "Results";
}

function downsampleBuffer(input: Float32Array, inputSampleRate: number, outputSampleRate: number) {
  if (inputSampleRate === outputSampleRate) {
    return input;
  }

  const sampleRateRatio = inputSampleRate / outputSampleRate;
  const newLength = Math.round(input.length / sampleRateRatio);
  const result = new Float32Array(newLength);

  let offsetResult = 0;
  let offsetBuffer = 0;

  while (offsetResult < result.length) {
    const nextOffsetBuffer = Math.round((offsetResult + 1) * sampleRateRatio);
    let accumulator = 0;
    let count = 0;

    for (let i = offsetBuffer; i < nextOffsetBuffer && i < input.length; i += 1) {
      accumulator += input[i];
      count += 1;
    }

    result[offsetResult] = count > 0 ? accumulator / count : 0;
    offsetResult += 1;
    offsetBuffer = nextOffsetBuffer;
  }

  return result;
}

function float32ToInt16Buffer(input: Float32Array) {
  const output = new Int16Array(input.length);
  for (let i = 0; i < input.length; i += 1) {
    const value = Math.max(-1, Math.min(1, input[i]));
    output[i] = value < 0 ? value * 0x8000 : value * 0x7fff;
  }
  return output;
}

function normalizeTranscriptSegment(text: string) {
  return text
    .replace(BLANK_AUDIO_REGEX, " ")
    .replace(/\s+/g, " ")
    .trim();
}

export default function Home() {
  const [isListening, setIsListening] = useState(false);
  const [status, setStatus] = useState("Idle");
  const [error, setError] = useState<string | null>(null);
  const [interimTranscript, setInterimTranscript] = useState("");
  const [finalTranscripts, setFinalTranscripts] = useState<string[]>([]);

  const connectionRef = useRef<DeepgramLiveSocket | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const transcriptBodyRef = useRef<HTMLDivElement | null>(null);

  const transcript = useMemo(
    () =>
      [...finalTranscripts, interimTranscript]
        .map(normalizeTranscriptSegment)
        .filter(Boolean)
        .join(" "),
    [finalTranscripts, interimTranscript],
  );

  useEffect(() => {
    const transcriptBody = transcriptBodyRef.current;
    if (!transcriptBody) {
      return;
    }

    transcriptBody.scrollTop = transcriptBody.scrollHeight;
  }, [transcript]);

  const cleanupMediaCapture = useCallback(() => {
    processorRef.current?.disconnect();
    processorRef.current = null;

    sourceRef.current?.disconnect();
    sourceRef.current = null;

    audioContextRef.current?.close().catch(() => undefined);
    audioContextRef.current = null;

    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  }, []);

  const stopListening = useCallback(() => {
    setIsListening(false);
    setStatus("Stopping...");

    cleanupMediaCapture();

    if (connectionRef.current?.readyState === 1) {
      connectionRef.current.sendCloseStream({ type: "CloseStream" });
    }
    connectionRef.current?.close();
    connectionRef.current = null;

    setStatus("Idle");
  }, [cleanupMediaCapture]);

  const startListening = useCallback(async () => {
    setError(null);

    if (!DEEPGRAM_API_KEY) {
      setError("Add your Deepgram API key in app/page.tsx before starting.");
      return;
    }

    try {
      setStatus("Requesting mic access...");

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const client = new DeepgramClient({
        apiKey: DEEPGRAM_API_KEY,
        baseUrl: DEEPGRAM_BASE_URL,
      });

      const connection = await client.listen.v1.connect({
        model: "tiny.en",
        language: "en",
        smart_format: "true",
        interim_results: "true",
        endpointing: "300",
        punctuate: "true",
        Authorization: `Token ${DEEPGRAM_API_KEY}`,
      });
      connectionRef.current = connection;

      connection.on("open", () => {
        setStatus("Listening live...");
        setIsListening(true);

        const audioContext = new AudioContext();
        audioContextRef.current = audioContext;

        const source = audioContext.createMediaStreamSource(stream);
        sourceRef.current = source;

        const processor = audioContext.createScriptProcessor(4096, 1, 1);
        processorRef.current = processor;

        processor.onaudioprocess = (event) => {
          if (connectionRef.current?.readyState !== 1) {
            return;
          }

          const channelData = event.inputBuffer.getChannelData(0);
          const downsampled = downsampleBuffer(channelData, audioContext.sampleRate, TARGET_SAMPLE_RATE);
          const pcm16 = float32ToInt16Buffer(downsampled);

          connectionRef.current.sendMedia(pcm16);
        };

        source.connect(processor);
        processor.connect(audioContext.destination);
      });

      connection.on("message", (payload) => {
        if (!isLiveResultMessage(payload)) {
          return;
        }

        const rawText = payload.channel?.alternatives?.[0]?.transcript;
        const text = rawText ? normalizeTranscriptSegment(rawText) : "";
        if (!text) {
          return;
        }

        if (payload.is_final) {
          setFinalTranscripts((prev) => [...prev, text]);
          setInterimTranscript("");
          return;
        }

        setInterimTranscript(text);
      });

      connection.on("error", () => {
        cleanupMediaCapture();
        connectionRef.current?.close();
        connectionRef.current = null;
        setIsListening(false);
        setError("Deepgram connection failed. Check key and base URL.");
        setStatus("Connection error");
      });

      connection.on("close", () => {
        cleanupMediaCapture();
        connectionRef.current = null;
        setIsListening(false);
        setStatus("Idle");
      });

      connection.connect();
      await connection.waitForOpen();

    } catch (caughtError) {
      cleanupMediaCapture();
      connectionRef.current?.close();
      connectionRef.current = null;
      if (caughtError instanceof Error && caughtError.message) {
        setError(`Unable to start live transcription: ${caughtError.message}`);
      } else {
        setError("Microphone permission denied or unavailable.");
      }
      setStatus("Idle");
      setIsListening(false);
    }
  }, [cleanupMediaCapture]);

  useEffect(() => stopListening, [stopListening]);

  return (
    <main className="relative min-h-screen overflow-hidden bg-[linear-gradient(130deg,#fff7e6_0%,#fff1d5_52%,#ffe6d5_100%)] px-4 pb-8 pt-6 text-[#130f29] md:px-7 md:pt-10">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -left-12 -top-20 h-60 w-60 rounded-full bg-[#ffe4bf] blur-2xl"
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -bottom-24 -right-16 h-72 w-72 rounded-full bg-[#cfe2ff] blur-2xl"
      />

      <div className="relative z-10 mx-auto flex min-h-[calc(100vh-3rem)] w-full max-w-5xl flex-col gap-4">
        <section className="rounded-3xl px-2 py-2">
          <div className="flex flex-col gap-5 md:flex-row md:items-start md:justify-between md:gap-8">
            <div className="max-w-3xl">
              <p className="m-0 text-[11px] uppercase tracking-[0.15em] text-[#7b6858]">Speech to text • live</p>
              <h1 className="mt-2 font-display text-[clamp(2.2rem,4.2vw,3.4rem)] leading-[0.95] text-balance">
                Talk. Watch It Type.
              </h1>
              <p className="mt-2 text-[#5f4e43]">Clean real-time transcript, no blank markers.</p>
              {error ? <p className="mt-3 text-sm text-[#a83323]">{error}</p> : null}
            </div>

            <div className="flex shrink-0 flex-col items-start gap-3 md:items-end">
              <button
                type="button"
                className={`inline-flex items-center gap-3 rounded-full bg-gradient-to-br from-[#ff5a1f] to-[#ff2f84] px-6 py-4 text-[15px] font-semibold text-[#fff9f5] shadow-[0_10px_18px_rgba(164,55,27,0.28)] transition hover:-translate-y-0.5 hover:scale-[1.015] ${isListening ? "animate-pulse" : ""}`}
                onClick={isListening ? stopListening : startListening}
              >
                <span
                  aria-hidden="true"
                  className={`h-4 w-4 rounded-full bg-[#ffe6d8] ${isListening ? "animate-ping" : ""}`}
                />
                {isListening ? "Stop Mic" : "Start Mic"}
              </button>

              <div className="flex flex-wrap items-center gap-3 md:justify-end">
                <button
                  type="button"
                  className="rounded-full border border-[#ffd7ba] bg-[#fff7ec] px-4 py-3 text-sm font-semibold text-[#6f4a36] transition hover:-translate-y-0.5 hover:border-[#ffc59a]"
                  onClick={() => {
                    setFinalTranscripts([]);
                    setInterimTranscript("");
                  }}
                >
                  Clear
                </button>
                <span className="text-sm text-[#6f5848]">{status}</span>
                {isListening ? (
                  <span className="animate-pulse rounded-full border border-[#bce8d7] bg-[#ecfbf4] px-2.5 py-1 text-[11px] font-semibold text-[#0f7b56]">
                    LIVE
                  </span>
                ) : null}
              </div>
            </div>
          </div>
        </section>

        <section
          aria-live="polite"
          className="mt-[clamp(2rem,8vh,7rem)] flex min-h-[clamp(440px,58vh,700px)] min-w-0 flex-col rounded-3xl border border-[#ffe8cd] bg-[#fffbf2]/90 p-4 shadow-[0_10px_24px_rgba(101,53,20,0.1)] md:p-5"
        >
          <div className="flex items-center justify-between gap-3">
            <h2 className="m-0 text-sm uppercase tracking-wide text-[#6e594a]">Transcription</h2>
          </div>

          <div
            ref={transcriptBodyRef}
            className="mt-4 min-h-0 flex-1 overflow-y-auto overscroll-contain pr-1"
          >
            {transcript ? (
              <p className="m-0 text-[clamp(1.04rem,2.25vw,1.27rem)] leading-[1.75] text-[#2a2132]">
                {transcript}
              </p>
            ) : (
              <p className="m-0 text-[clamp(1.04rem,2.25vw,1.27rem)] leading-[1.75] text-[#7d6767]">
                Your transcription appears here once you start speaking.
              </p>
            )}
          </div>
        </section>
      </div>
    </main>
  );
}
