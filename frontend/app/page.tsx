"use client";

import {
  startTransition,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import {
  type AgentStatus,
  type Appointment,
  type DashboardEvent,
  type Message,
  appointmentStatusClasses,
  fetchAppointments,
  wsUrl,
} from "@/lib/backend";

type CallState = "idle" | "connecting" | "live";

const INPUT_SAMPLE_RATE = 16_000;
const OUTPUT_SAMPLE_RATE = 24_000;
const OUTPUT_GAIN = 0.72;
const VOICE_OPTIONS = [
  { value: "1", label: "Aoede", detail: "Warm, conversational" },
  { value: "2", label: "Puck", detail: "Upbeat, energetic" },
  { value: "3", label: "Charon", detail: "Deep, authoritative" },
  { value: "4", label: "Kore", detail: "Clear, neutral" },
  { value: "5", label: "Fenrir", detail: "Expressive" },
  { value: "6", label: "Leda", detail: "Friendly" },
  { value: "7", label: "Orus", detail: "Confident" },
  { value: "8", label: "Zephyr", detail: "Calm" },
] as const;
const LANGUAGE_OPTIONS = [
  { value: "en", label: "English" },
  { value: "es", label: "Spanish" },
  { value: "fr", label: "French" },
  { value: "de", label: "German" },
  { value: "it", label: "Italian" },
  { value: "pt", label: "Portuguese" },
] as const;
const MICROPHONE_CONSTRAINTS: MediaTrackConstraints = {
  channelCount: 1,
  echoCancellation: true,
  noiseSuppression: true,
  autoGainControl: true,
};

function formatClock() {
  return new Date().toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function normalizeTranscriptText(text: string) {
  return text.replace(/\s+/g, " ").trim();
}

function compactTranscriptText(text: string) {
  return normalizeTranscriptText(text).replace(/\s+/g, "");
}

function mergeTranscriptUpdate(currentText: string, nextText: string) {
  const normalizedCurrent = normalizeTranscriptText(currentText);
  const normalizedNext = normalizeTranscriptText(nextText);

  if (!normalizedCurrent) {
    return normalizedNext;
  }
  if (!normalizedNext) {
    return normalizedCurrent;
  }

  const currentCompact = compactTranscriptText(normalizedCurrent);
  const nextCompact = compactTranscriptText(normalizedNext);

  if (currentCompact === nextCompact) {
    return normalizedNext.length >= normalizedCurrent.length
      ? normalizedNext
      : normalizedCurrent;
  }
  if (nextCompact.startsWith(currentCompact)) {
    return normalizedNext;
  }
  if (currentCompact.startsWith(nextCompact)) {
    return normalizedCurrent;
  }

  return nextCompact.length > currentCompact.length
    ? normalizedNext
    : normalizedCurrent;
}

function shouldRenderTranscript(text: string, finished: boolean) {
  if (!text) {
    return false;
  }
  if (finished) {
    return true;
  }
  return /[A-Za-z0-9]/.test(text);
}

function encodePcmChunk(
  input: Float32Array,
  sourceSampleRate: number,
): ArrayBuffer {
  const sampleRateRatio = sourceSampleRate / INPUT_SAMPLE_RATE;
  const outputLength = Math.max(1, Math.round(input.length / sampleRateRatio));
  const buffer = new ArrayBuffer(outputLength * 2);
  const view = new DataView(buffer);

  let inputOffset = 0;
  for (let index = 0; index < outputLength; index += 1) {
    const nextOffset = Math.min(
      input.length,
      Math.round((index + 1) * sampleRateRatio),
    );
    let total = 0;
    let count = 0;

    for (let cursor = inputOffset; cursor < nextOffset; cursor += 1) {
      total += input[cursor] ?? 0;
      count += 1;
    }

    const sample = count > 0 ? total / count : 0;
    const clamped = Math.max(-1, Math.min(1, sample));
    view.setInt16(
      index * 2,
      clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff,
      true,
    );
    inputOffset = nextOffset;
  }

  return buffer;
}

function decodePcmChunk(chunk: ArrayBuffer): Float32Array {
  const pcm = new Int16Array(chunk);
  const result = new Float32Array(pcm.length);
  for (let index = 0; index < pcm.length; index += 1) {
    result[index] = pcm[index] / 0x8000;
  }
  return result;
}

function StatusBadge({ status }: { status: AgentStatus }) {
  const styles: Record<AgentStatus, { label: string; tone: string; dot: string }> =
    {
      idle: {
        label: "Idle",
        tone: "bg-white/5 text-slate-300 ring-1 ring-white/10",
        dot: "bg-slate-500",
      },
      listening: {
        label: "Listening",
        tone: "bg-emerald-500/15 text-emerald-100 ring-1 ring-emerald-400/25",
        dot: "bg-emerald-300 animate-pulse",
      },
      speaking: {
        label: "Speaking",
        tone: "bg-sky-500/15 text-sky-100 ring-1 ring-sky-400/25",
        dot: "bg-sky-300 animate-pulse",
      },
    };

  const style = styles[status];

  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-sm font-medium ${style.tone}`}
    >
      <span className={`h-2.5 w-2.5 rounded-full ${style.dot}`} />
      {style.label}
    </span>
  );
}

function CallBadge({ state }: { state: CallState }) {
  const styles: Record<CallState, { label: string; tone: string }> = {
    idle: {
      label: "Browser call idle",
      tone: "bg-white/5 text-slate-300 ring-1 ring-white/10",
    },
    connecting: {
      label: "Connecting call",
      tone: "bg-amber-500/15 text-amber-100 ring-1 ring-amber-300/25",
    },
    live: {
      label: "Browser mic live",
      tone: "bg-emerald-500/15 text-emerald-100 ring-1 ring-emerald-400/25",
    },
  };

  const style = styles[state];
  return (
    <span className={`inline-flex rounded-full px-3 py-1.5 text-sm font-medium ${style.tone}`}>
      {style.label}
    </span>
  );
}

function MetricCard({
  eyebrow,
  value,
  detail,
}: {
  eyebrow: string;
  value: string;
  detail: string;
}) {
  return (
    <article className="panel rounded-[24px] p-4">
      <p className="text-[0.72rem] uppercase tracking-[0.24em] text-slate-400">
        {eyebrow}
      </p>
      <p className="mt-3 text-3xl font-semibold tracking-tight text-stone-50">
        {value}
      </p>
      <p className="mt-1 text-sm text-slate-400">{detail}</p>
    </article>
  );
}

function MessageBubble({ message }: { message: Message }) {
  const isTool = message.role === "tool";
  const isAgent = message.role === "agent";

  if (isTool) {
    return (
      <div className="flex justify-center">
        <span className="rounded-full border border-amber-300/20 bg-amber-400/10 px-3 py-1 text-xs text-amber-100">
          Tool call: {message.text}
        </span>
      </div>
    );
  }

  return (
    <div className={`flex flex-col gap-1 ${isAgent ? "items-end" : "items-start"}`}>
      <span className="px-1 text-[0.72rem] uppercase tracking-[0.18em] text-slate-500">
        {isAgent ? "Agent" : "Customer"} · {message.time}
      </span>
      <div
        className={`max-w-[88%] rounded-[22px] px-4 py-3 text-sm leading-relaxed shadow-[0_12px_30px_rgba(2,6,23,0.22)] ${
          isAgent
            ? "rounded-tr-sm bg-[linear-gradient(135deg,rgba(245,158,11,0.95),rgba(249,115,22,0.95))] text-slate-950"
            : "rounded-tl-sm border border-white/10 bg-slate-900/90 text-slate-100"
        }`}
      >
        {message.text}
      </div>
    </div>
  );
}

function AppointmentRow({
  appointment,
  highlight,
}: {
  appointment: Appointment;
  highlight: boolean;
}) {
  const statusClass =
    appointmentStatusClasses[appointment.Status] ??
    "bg-white/5 text-slate-200 ring-1 ring-white/10";

  return (
    <tr
      className={`border-b border-white/6 transition-colors ${
        highlight ? "bg-amber-300/8" : "hover:bg-white/5"
      }`}
    >
      <td className="px-3 py-3 text-xs font-medium uppercase tracking-[0.16em] text-slate-400">
        {appointment["Appointment ID"]}
      </td>
      <td className="px-3 py-3 text-sm text-stone-100">{appointment.Customer}</td>
      <td className="px-3 py-3 text-sm text-slate-300">{appointment.Service}</td>
      <td className="px-3 py-3 text-sm text-slate-300">{appointment.Date}</td>
      <td className="px-3 py-3 text-sm text-slate-300">{appointment.Time}</td>
      <td className="px-3 py-3 text-sm text-slate-400">{appointment.Technician}</td>
      <td className="px-3 py-3">
        <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${statusClass}`}>
          {appointment.Status}
        </span>
      </td>
    </tr>
  );
}

export default function DashboardPage() {
  const [status, setStatus] = useState<AgentStatus>("idle");
  const [messages, setMessages] = useState<Message[]>([]);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [callState, setCallState] = useState<CallState>("idle");
  const [dashboardConnected, setDashboardConnected] = useState(false);
  const [callError, setCallError] = useState<string | null>(null);
  const [highlightAppointments, setHighlightAppointments] = useState(false);
  const [selectedVoice, setSelectedVoice] =
    useState<(typeof VOICE_OPTIONS)[number]["value"]>("1");
  const [selectedLanguage, setSelectedLanguage] =
    useState<(typeof LANGUAGE_OPTIONS)[number]["value"]>("en");

  const transcriptRef = useRef<HTMLDivElement>(null);
  const highlightTimerRef = useRef<number | null>(null);
  const voiceSocketRef = useRef<WebSocket | null>(null);
  const inputContextRef = useRef<AudioContext | null>(null);
  const outputContextRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const inputSourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const inputSinkRef = useRef<GainNode | null>(null);
  const outputGainRef = useRef<GainNode | null>(null);
  const voiceReadyRef = useRef(false);
  const agentSpeakingRef = useRef(false);
  const playbackCursorRef = useRef(0);

  const loadAppointments = useCallback(async () => {
    try {
      const nextAppointments = await fetchAppointments();
      startTransition(() => setAppointments(nextAppointments));
    } catch {
      // Backend can legitimately be offline while the frontend is open.
    }
  }, []);

  const flashAppointments = useCallback(() => {
    if (highlightTimerRef.current) {
      window.clearTimeout(highlightTimerRef.current);
    }
    setHighlightAppointments(true);
    highlightTimerRef.current = window.setTimeout(() => {
      setHighlightAppointments(false);
    }, 1600);
  }, []);

  const playAgentAudio = useCallback(async (payload: ArrayBuffer | Blob) => {
    const outputContext = outputContextRef.current;
    if (!outputContext) {
      return;
    }

    if (outputContext.state === "suspended") {
      await outputContext.resume();
    }

    const chunk = payload instanceof Blob ? await payload.arrayBuffer() : payload;
    if (chunk.byteLength < 2) {
      return;
    }

    const channelData = decodePcmChunk(chunk);
    if (channelData.length === 0) {
      return;
    }

    const audioBuffer = outputContext.createBuffer(
      1,
      channelData.length,
      OUTPUT_SAMPLE_RATE,
    );

    audioBuffer.getChannelData(0).set(channelData);

    const source = outputContext.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(outputGainRef.current ?? outputContext.destination);

    const startAt = Math.max(outputContext.currentTime, playbackCursorRef.current);
    source.start(startAt);
    playbackCursorRef.current = startAt + audioBuffer.duration;
  }, []);

  const cleanupCall = useCallback(
    async ({
      closeSocket,
      nextState,
    }: {
      closeSocket: boolean;
      nextState: CallState;
    }) => {
      const socket = voiceSocketRef.current;
      voiceSocketRef.current = null;
      voiceReadyRef.current = false;
      agentSpeakingRef.current = false;

      if (socket) {
        socket.onopen = null;
        socket.onmessage = null;
        socket.onerror = null;
        socket.onclose = null;

        if (closeSocket && socket.readyState < WebSocket.CLOSING) {
          try {
            socket.send(JSON.stringify({ type: "audio_stream_end" }));
          } catch {
            // Socket is already on its way down.
          }
          socket.close();
        }
      }

      processorRef.current?.disconnect();
      processorRef.current = null;

      inputSourceRef.current?.disconnect();
      inputSourceRef.current = null;

      inputSinkRef.current?.disconnect();
      inputSinkRef.current = null;

      outputGainRef.current?.disconnect();
      outputGainRef.current = null;

      mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;

      if (inputContextRef.current && inputContextRef.current.state !== "closed") {
        await inputContextRef.current.close();
      }
      inputContextRef.current = null;

      if (outputContextRef.current && outputContextRef.current.state !== "closed") {
        await outputContextRef.current.close();
      }
      outputContextRef.current = null;

      playbackCursorRef.current = 0;
      setCallState(nextState);
    },
    [],
  );

  const handleDashboardEvent = useCallback(
    (event: DashboardEvent) => {
      if (event.type === "status") {
        agentSpeakingRef.current = event.value === "speaking";
        setStatus(event.value);
        return;
      }

      if (event.type === "transcript") {
        startTransition(() => {
          setMessages((current) => {
            const nextText = normalizeTranscriptText(event.text);
            const isFinal = Boolean(event.finished);
            if (!shouldRenderTranscript(nextText, isFinal)) {
              return current;
            }

            if (event.turn_id) {
              const existingIndex = current.findIndex(
                (message) =>
                  message.role === event.role &&
                  message.role !== "tool" &&
                  message.turnId === event.turn_id,
              );

              if (existingIndex >= 0) {
                const existing = current[existingIndex];
                const updated = {
                  ...existing,
                  text: mergeTranscriptUpdate(existing.text, nextText),
                  final: Boolean(existing.final) || isFinal,
                };
                return [
                  ...current.slice(0, existingIndex),
                  updated,
                  ...current.slice(existingIndex + 1),
                ];
              }
            }

            const last = current.at(-1);
            if (
              last &&
              last.role === event.role &&
              last.text === nextText &&
              Boolean(last.final) === isFinal &&
              last.turnId === event.turn_id
            ) {
              return current;
            }

            return [
              ...current,
              {
                role: event.role,
                text: nextText,
                time: formatClock(),
                final: isFinal,
                turnId: event.turn_id,
              },
            ];
          });
        });
        return;
      }

      if (event.type === "tool_call") {
        startTransition(() => {
          setMessages((current) => {
            const text = `${event.name}(${JSON.stringify(event.args)})`;
            const last = current.at(-1);
            if (last?.role === "tool" && last.text === text) {
              return current;
            }
            return [
              ...current,
              {
                role: "tool",
                text,
                time: formatClock(),
              },
            ];
          });
        });
        return;
      }

      void loadAppointments();
      flashAppointments();
    },
    [flashAppointments, loadAppointments],
  );

  useEffect(() => {
    void loadAppointments();

    const dashboardSocket = new WebSocket(wsUrl("/ws"));
    dashboardSocket.onopen = () => setDashboardConnected(true);
    dashboardSocket.onclose = () => {
      setDashboardConnected(false);
      setStatus("idle");
    };
    dashboardSocket.onmessage = (event) => {
      try {
        handleDashboardEvent(JSON.parse(event.data as string) as DashboardEvent);
      } catch {
        // Ignore malformed events so the console stays live.
      }
    };

    return () => {
      dashboardSocket.close();
    };
  }, [flashAppointments, handleDashboardEvent, loadAppointments]);

  useEffect(() => {
    if (transcriptRef.current) {
      transcriptRef.current.scrollTop = transcriptRef.current.scrollHeight;
    }
  }, [messages]);

  useEffect(() => {
    return () => {
      if (highlightTimerRef.current) {
        window.clearTimeout(highlightTimerRef.current);
      }
      void cleanupCall({ closeSocket: true, nextState: "idle" });
    };
  }, [cleanupCall]);

  async function startCall() {
    if (callState !== "idle") {
      return;
    }

    if (
      typeof navigator === "undefined" ||
      !navigator.mediaDevices ||
      !window.AudioContext
    ) {
      setCallError("This browser does not support live microphone audio.");
      return;
    }

    setCallError(null);
    setCallState("connecting");
    startTransition(() => setMessages([]));

    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: MICROPHONE_CONSTRAINTS,
      });
      const inputContext = new AudioContext({ sampleRate: INPUT_SAMPLE_RATE });
      const outputContext = new AudioContext({ sampleRate: OUTPUT_SAMPLE_RATE });

      await inputContext.resume();
      await outputContext.resume();

      const inputSource = inputContext.createMediaStreamSource(mediaStream);
      const processor = inputContext.createScriptProcessor(2048, 1, 1);
      const sink = inputContext.createGain();
      const outputGain = outputContext.createGain();
      sink.gain.value = 0;
      outputGain.gain.value = OUTPUT_GAIN;
      outputGain.connect(outputContext.destination);

      processor.onaudioprocess = (event) => {
        const socket = voiceSocketRef.current;
        if (
          !socket ||
          socket.readyState !== WebSocket.OPEN ||
          !voiceReadyRef.current ||
          agentSpeakingRef.current
        ) {
          return;
        }

        const channel = event.inputBuffer.getChannelData(0);
        socket.send(encodePcmChunk(channel, inputContext.sampleRate));
      };

      inputSource.connect(processor);
      processor.connect(sink);
      sink.connect(inputContext.destination);

      const voiceSocket = new WebSocket(
        `${wsUrl("/voice")}?voice=${encodeURIComponent(selectedVoice)}&language=${encodeURIComponent(selectedLanguage)}`,
      );
      voiceSocket.binaryType = "arraybuffer";

      voiceSocket.onopen = () => {
        setCallState("connecting");
      };

      voiceSocket.onmessage = (event) => {
        if (typeof event.data === "string") {
          const payload = JSON.parse(event.data) as {
            type?: string;
            message?: string;
            value?: AgentStatus;
          };

          if (payload.type === "session_ready") {
            voiceReadyRef.current = true;
            agentSpeakingRef.current = true;
            setCallState("live");
            return;
          }

          if (payload.type === "agent_state" && payload.value) {
            agentSpeakingRef.current = payload.value === "speaking";
            setStatus(payload.value);
            return;
          }

          if (payload.type === "transcript" || payload.type === "tool_call") {
            handleDashboardEvent(payload as DashboardEvent);
            return;
          }

          if (payload.type === "error") {
            setCallError(payload.message ?? "The voice session ended unexpectedly.");
            void cleanupCall({ closeSocket: false, nextState: "idle" });
          }
          return;
        }

        void playAgentAudio(event.data);
      };

      voiceSocket.onerror = () => {
        setCallError("The browser could not reach the backend voice socket.");
      };

      voiceSocket.onclose = (event) => {
        if (event.code !== 1000 && event.code !== 1005) {
          const reason = event.reason
            ? `${event.code}: ${event.reason}`
            : `Voice socket closed (${event.code}).`;
          setCallError(reason);
        }
        void cleanupCall({ closeSocket: false, nextState: "idle" });
      };

      mediaStreamRef.current = mediaStream;
      inputContextRef.current = inputContext;
      outputContextRef.current = outputContext;
      inputSourceRef.current = inputSource;
      processorRef.current = processor;
      inputSinkRef.current = sink;
      outputGainRef.current = outputGain;
      voiceSocketRef.current = voiceSocket;
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Microphone access failed.";
      setCallError(message);
      await cleanupCall({ closeSocket: true, nextState: "idle" });
    }
  }

  async function stopCall() {
    await cleanupCall({ closeSocket: true, nextState: "idle" });
  }

  return (
    <div className="space-y-6">
      <section className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
        <article className="panel rounded-[32px] p-6 sm:p-8">
          <p className="text-[0.72rem] font-semibold uppercase tracking-[0.28em] text-amber-300/80">
            Live Operations Console
          </p>
          <div className="mt-5 flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-2xl space-y-3">
              <h2 className="text-4xl font-semibold tracking-tight text-stone-50 sm:text-5xl">
                Interact with the agent directly from the browser.
              </h2>
              <p className="max-w-xl text-base leading-7 text-slate-300">
                Start a live call, speak into the browser microphone, and watch
                the transcript and appointment table update in real time.
              </p>
            </div>

            <div className="flex flex-col items-start gap-3">
              <label className="flex w-full min-w-[260px] flex-col gap-2">
                <span className="text-[0.72rem] font-semibold uppercase tracking-[0.22em] text-slate-400">
                  Agent Voice
                </span>
                <select
                  value={selectedVoice}
                  onChange={(event) =>
                    setSelectedVoice(
                      event.target.value as (typeof VOICE_OPTIONS)[number]["value"],
                    )
                  }
                  disabled={callState !== "idle"}
                  className="w-full rounded-2xl border border-white/10 bg-slate-950/80 px-4 py-3 text-sm text-stone-100 outline-none transition focus:border-amber-300/40 focus:bg-slate-950 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {VOICE_OPTIONS.map((voice) => (
                    <option key={voice.value} value={voice.value}>
                      {voice.label} — {voice.detail}
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex w-full min-w-[260px] flex-col gap-2">
                <span className="text-[0.72rem] font-semibold uppercase tracking-[0.22em] text-slate-400">
                  Agent Language
                </span>
                <select
                  value={selectedLanguage}
                  onChange={(event) =>
                    setSelectedLanguage(
                      event.target.value as (typeof LANGUAGE_OPTIONS)[number]["value"],
                    )
                  }
                  disabled={callState !== "idle"}
                  className="w-full rounded-2xl border border-white/10 bg-slate-950/80 px-4 py-3 text-sm text-stone-100 outline-none transition focus:border-amber-300/40 focus:bg-slate-950 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {LANGUAGE_OPTIONS.map((language) => (
                    <option key={language.value} value={language.value}>
                      {language.label}
                    </option>
                  ))}
                </select>
              </label>
              <button
                type="button"
                onClick={callState === "live" ? () => void stopCall() : () => void startCall()}
                disabled={callState === "connecting"}
                className={`inline-flex min-w-[220px] items-center justify-center rounded-full px-6 py-3.5 text-sm font-semibold shadow-[0_16px_40px_rgba(2,6,23,0.28)] ${
                  callState === "live"
                    ? "bg-rose-500 text-white hover:bg-rose-400"
                    : "bg-amber-300 text-slate-950 hover:-translate-y-0.5 hover:bg-amber-200 disabled:translate-y-0 disabled:bg-amber-200/70"
                }`}
              >
                {callState === "idle" && "Interact With Agent"}
                {callState === "connecting" && "Connecting..."}
                {callState === "live" && "End Live Call"}
              </button>
              <p className="text-sm text-slate-400">
                Allow microphone access when the browser prompts you.
              </p>
              <p className="max-w-[260px] text-xs leading-5 text-slate-500">
                If you are using Mac speakers, use headphones or lower speaker
                volume to avoid feedback squeal during live calls.
              </p>
            </div>
          </div>
        </article>

        <div className="grid gap-4 sm:grid-cols-3 lg:grid-cols-1">
          <MetricCard
            eyebrow="Backend Link"
            value={dashboardConnected ? "Online" : "Offline"}
            detail={
              dashboardConnected
                ? "Realtime dashboard events are flowing."
                : "The UI is waiting for the FastAPI server."
            }
          />
          <MetricCard
            eyebrow="Conversation"
            value={`${messages.length}`}
            detail="Transcript events collected in this browser session."
          />
          <MetricCard
            eyebrow="Appointments"
            value={`${appointments.length}`}
            detail="Appointments currently loaded in the dashboard."
          />
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
        <article className="panel flex min-h-[620px] flex-col rounded-[32px] overflow-hidden">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/8 px-5 py-4">
            <div>
              <p className="text-sm font-semibold text-stone-50">Live Conversation</p>
              <p className="mt-1 text-sm text-slate-400">
                Voice activity, transcripts, and tool calls stream here.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <span
                className={`rounded-full px-3 py-1.5 text-sm font-medium ${
                  dashboardConnected
                    ? "bg-emerald-500/15 text-emerald-100 ring-1 ring-emerald-400/25"
                    : "bg-white/5 text-slate-300 ring-1 ring-white/10"
                }`}
              >
                {dashboardConnected ? "Dashboard connected" : "Waiting for backend"}
              </span>
              <StatusBadge status={status} />
              <CallBadge state={callState} />
            </div>
          </div>

          <div ref={transcriptRef} className="flex-1 space-y-4 overflow-y-auto p-5">
            {messages.length === 0 ? (
              <div className="flex h-full items-center justify-center rounded-[28px] border border-dashed border-white/10 bg-black/10 px-6 text-center text-sm text-slate-500">
                The transcript will populate after the call starts or when the
                backend agent begins speaking.
              </div>
            ) : (
              messages.map((message, index) => (
                <MessageBubble
                  key={`${message.turnId ?? message.time}-${index}`}
                  message={message}
                />
              ))
            )}
          </div>

          {callError ? (
            <div className="border-t border-rose-400/20 bg-rose-500/10 px-5 py-3 text-sm text-rose-100">
              {callError}
            </div>
          ) : null}
        </article>

        <article className="panel flex min-h-[620px] flex-col rounded-[32px] overflow-hidden">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/8 px-5 py-4">
            <div>
              <p className="text-sm font-semibold text-stone-50">Appointment Ledger</p>
              <p className="mt-1 text-sm text-slate-400">
                Every booking change updates this appointment list.
              </p>
            </div>
            <button
              type="button"
              onClick={() => void loadAppointments()}
              className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-slate-200 hover:border-amber-300/30 hover:bg-white/10"
            >
              Refresh appointments
            </button>
          </div>

          <div className="flex-1 overflow-auto">
            {appointments.length === 0 ? (
              <div className="flex h-full items-center justify-center px-6 text-center text-sm text-slate-500">
                No appointments are loaded yet. Start a booking flow or refresh
                once the backend is online.
              </div>
            ) : (
              <table className="w-full min-w-[760px] text-left">
                <thead className="sticky top-0 bg-slate-950/95 backdrop-blur">
                  <tr className="border-b border-white/8">
                    {[
                      "ID",
                      "Customer",
                      "Service",
                      "Date",
                      "Time",
                      "Technician",
                      "Status",
                    ].map((heading) => (
                      <th
                        key={heading}
                        className="px-3 py-3 text-[0.72rem] font-semibold uppercase tracking-[0.22em] text-slate-400"
                      >
                        {heading}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {appointments.map((appointment) => (
                    <AppointmentRow
                      key={appointment["Appointment ID"]}
                      appointment={appointment}
                      highlight={highlightAppointments}
                    />
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </article>
      </section>
    </div>
  );
}
