export type AgentStatus = "idle" | "listening" | "speaking";

export type Message = {
  role: "agent" | "customer" | "tool";
  text: string;
  time: string;
};

export type Appointment = {
  "Appointment ID": string;
  Account: string;
  Customer: string;
  Service: string;
  Date: string;
  Time: string;
  Technician: string;
  Status: string;
};

export type DashboardEvent =
  | { type: "status"; value: AgentStatus }
  | { type: "transcript"; role: "agent" | "customer"; text: string }
  | { type: "tool_call"; name: string; args: Record<string, unknown> }
  | { type: "appointments_updated" };

const DEFAULT_API_BASE = "http://localhost:8000";

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? DEFAULT_API_BASE;
export const WS_BASE = API_BASE.replace(/^http/, "ws");

export const appointmentStatusClasses: Record<string, string> = {
  Scheduled: "bg-sky-500/15 text-sky-200 ring-1 ring-sky-400/20",
  Cancelled: "bg-rose-500/15 text-rose-200 ring-1 ring-rose-400/20",
  Rescheduled: "bg-amber-500/15 text-amber-100 ring-1 ring-amber-300/25",
};

export function apiUrl(path: string): string {
  return `${API_BASE}${path}`;
}

export function wsUrl(path: string): string {
  return `${WS_BASE}${path}`;
}

export async function fetchAppointments(): Promise<Appointment[]> {
  const response = await fetch(apiUrl("/appointments"), { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Failed to load appointments: ${response.status}`);
  }
  return (await response.json()) as Appointment[];
}
