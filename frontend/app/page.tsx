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

function formatClock() {
  return new Date().toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
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
  if (message.role === "tool") {
    return (
      <div className="flex justify-center">
        <span className="rounded-full border border-amber-300/20 bg-amber-400/10 px-3 py-1 text-xs text-amber-100">
          Tool call: {message.text}
        </span>
      </div>
    );
  }

  const isAgent = message.role === "agent";

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

  const transcriptRef = useRef<HTMLDivElement>(null);
  const highlightTimerRef = useRef<number | null>(null);
  const voiceSocketRef = useRef<WebSocket | null>(null);
  const inputContextRef = useRef<AudioContext | null>(null);
  const outputContextRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const inputSourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const inputSinkRef = useRef<GainNode | null>(null);
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
    const channelData = decodePcmChunk(chunk);
    const audioBuffer = outputContext.createBuffer(
      1,
      channelData.length,
      OUTPUT_SAMPLE_RATE,
    );

    audioBuffer.getChannelData(0).set(channelData);

    const source = outputContext.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(outputContext.destination);

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
        setStatus(event.value);
        return;
      }

      if (event.type === "transcript") {
        startTransition(() => {
          setMessages((current) => [
            ...current,
            { role: event.role, text: event.text, time: formatClock() },
          ]);
        });
        return;
      }

      if (event.type === "tool_call") {
        startTransition(() => {
          setMessages((current) => [
            ...current,
            {
              role: "tool",
              text: `${event.name}(${JSON.stringify(event.args)})`,
              time: formatClock(),
            },
          ]);
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
      const mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const inputContext = new AudioContext({ sampleRate: INPUT_SAMPLE_RATE });
      const outputContext = new AudioContext();

      await inputContext.resume();
      await outputContext.resume();

      const inputSource = inputContext.createMediaStreamSource(mediaStream);
      const processor = inputContext.createScriptProcessor(2048, 1, 1);
      const sink = inputContext.createGain();
      sink.gain.value = 0;

      processor.onaudioprocess = (event) => {
        const socket = voiceSocketRef.current;
        if (!socket || socket.readyState !== WebSocket.OPEN) {
          return;
        }

        const channel = event.inputBuffer.getChannelData(0);
        socket.send(encodePcmChunk(channel, inputContext.sampleRate));
      };

      inputSource.connect(processor);
      processor.connect(sink);
      sink.connect(inputContext.destination);

      const voiceSocket = new WebSocket(wsUrl("/voice"));
      voiceSocket.binaryType = "arraybuffer";

      voiceSocket.onopen = () => {
        setCallState("live");
      };

      voiceSocket.onmessage = (event) => {
        if (typeof event.data === "string") {
          const payload = JSON.parse(event.data) as {
            type?: string;
            message?: string;
          };

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

      voiceSocket.onclose = () => {
        void cleanupCall({ closeSocket: false, nextState: "idle" });
      };

      mediaStreamRef.current = mediaStream;
      inputContextRef.current = inputContext;
      outputContextRef.current = outputContext;
      inputSourceRef.current = inputSource;
      processorRef.current = processor;
      inputSinkRef.current = sink;
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
            detail="Rows currently loaded from the shared CSV calendar."
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
                  key={`${message.time}-${index}`}
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
                Every booking change is read from the shared CSV backend.
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
