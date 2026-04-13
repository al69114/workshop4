"use client";

import { startTransition, useCallback, useEffect, useState } from "react";
import {
  type Appointment,
  appointmentStatusClasses,
  fetchAppointments,
  wsUrl,
} from "@/lib/backend";

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const TECHNICIANS = ["Carlos", "Maria", "Jake", "Sophie"];

function parseAppointmentDate(value: string) {
  return new Date(`${value}T12:00:00`);
}

function monthStart(date: Date) {
  return new Date(date.getFullYear(), date.getMonth(), 1);
}

function monthEnd(date: Date) {
  return new Date(date.getFullYear(), date.getMonth() + 1, 0);
}

function addDays(date: Date, days: number) {
  const next = new Date(date);
  next.setDate(next.getDate() + days);
  return next;
}

function toIsoDate(date: Date) {
  return [
    date.getFullYear(),
    `${date.getMonth() + 1}`.padStart(2, "0"),
    `${date.getDate()}`.padStart(2, "0"),
  ].join("-");
}

function toMonthLabel(date: Date) {
  return date.toLocaleDateString([], {
    month: "long",
    year: "numeric",
  });
}

function buildCalendarDays(date: Date) {
  const start = monthStart(date);
  const firstVisible = addDays(start, -start.getDay());
  return Array.from({ length: 42 }, (_, index) => addDays(firstVisible, index));
}

function statusCount(appointments: Appointment[], status: string) {
  return appointments.filter((appointment) => appointment.Status === status).length;
}

export default function CalendarPage() {
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [visibleMonth, setVisibleMonth] = useState(() => monthStart(new Date()));
  const [selectedDate, setSelectedDate] = useState(() => toIsoDate(new Date()));
  const [connected, setConnected] = useState(false);
  const [highlightRefresh, setHighlightRefresh] = useState(false);

  const loadAppointments = useCallback(async () => {
    try {
      const nextAppointments = await fetchAppointments();
      startTransition(() => setAppointments(nextAppointments));
    } catch {
      // Leave stale data in place if the backend drops temporarily.
    }
  }, []);

  useEffect(() => {
    void loadAppointments();

    const socket = new WebSocket(wsUrl("/ws"));
    socket.onopen = () => setConnected(true);
    socket.onclose = () => setConnected(false);
    socket.onmessage = (event) => {
      const payload = JSON.parse(event.data as string) as {
        type?: string;
        action?: string;
        appointment?: {
          appointment_id?: string;
          date?: string;
        };
      };
      if (payload.type === "appointments_updated") {
        void loadAppointments();
        if (payload.action === "book_appointment" && payload.appointment?.date) {
          const bookedDate = parseAppointmentDate(payload.appointment.date);
          setSelectedDate(payload.appointment.date);
          setVisibleMonth(monthStart(bookedDate));
        }
        setHighlightRefresh(true);
        window.setTimeout(() => setHighlightRefresh(false), 1500);
      }
    };

    return () => socket.close();
  }, [loadAppointments]);

  const currentMonthStart = monthStart(visibleMonth);
  const currentMonthEnd = monthEnd(visibleMonth);
  const visibleAppointments = appointments.filter((appointment) => {
    const date = parseAppointmentDate(appointment.Date);
    return date >= currentMonthStart && date <= currentMonthEnd;
  });
  const calendarDays = buildCalendarDays(visibleMonth);
  const selectedDayAppointments = appointments
    .filter((appointment) => appointment.Date === selectedDate)
    .sort((left, right) => left.Time.localeCompare(right.Time));
  const occupiedTechnicians = Array.from(
    new Set(
      selectedDayAppointments
        .filter((appointment) => appointment.Status !== "Cancelled")
        .map((appointment) => appointment.Technician),
    ),
  );
  const knownTechnicians = Array.from(
    new Set([
      ...TECHNICIANS,
      ...appointments.map((appointment) => appointment.Technician),
    ]),
  );
  const availableTechnicians = knownTechnicians.filter(
    (technician) => !occupiedTechnicians.includes(technician),
  );

  return (
    <div className="space-y-6">
      <section className="panel rounded-[32px] p-6 sm:p-8">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-3">
            <p className="text-[0.72rem] font-semibold uppercase tracking-[0.28em] text-amber-300/80">
              Service Calendar
            </p>
            <h2 className="text-4xl font-semibold tracking-tight text-stone-50 sm:text-5xl">
              Watch the schedule update by day.
            </h2>
            <p className="max-w-2xl text-base leading-7 text-slate-300">
              This view reads the same appointment CSV as the dashboard table.
              When the agent books, cancels, or reschedules work, the calendar
              refreshes automatically.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <span
              className={`rounded-full px-3 py-1.5 text-sm font-medium ${
                connected
                  ? "bg-emerald-500/15 text-emerald-100 ring-1 ring-emerald-400/25"
                  : "bg-white/5 text-slate-300 ring-1 ring-white/10"
              }`}
            >
              {connected ? "Live updates connected" : "Waiting for backend"}
            </span>
            <button
              type="button"
              onClick={() =>
                setVisibleMonth(
                  new Date(visibleMonth.getFullYear(), visibleMonth.getMonth() - 1, 1),
                )
              }
              className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-slate-200 hover:border-amber-300/30 hover:bg-white/10"
            >
              Previous month
            </button>
            <button
              type="button"
              onClick={() =>
                setVisibleMonth(
                  new Date(visibleMonth.getFullYear(), visibleMonth.getMonth() + 1, 1),
                )
              }
              className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-slate-200 hover:border-amber-300/30 hover:bg-white/10"
            >
              Next month
            </button>
          </div>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-4">
        <article className="panel rounded-[24px] p-4">
          <p className="text-[0.72rem] uppercase tracking-[0.22em] text-slate-400">
            Visible Month
          </p>
          <p className="mt-3 text-2xl font-semibold text-stone-50">
            {toMonthLabel(visibleMonth)}
          </p>
        </article>
        <article className="panel rounded-[24px] p-4">
          <p className="text-[0.72rem] uppercase tracking-[0.22em] text-slate-400">
            Scheduled
          </p>
          <p className="mt-3 text-2xl font-semibold text-stone-50">
            {statusCount(visibleAppointments, "Scheduled")}
          </p>
        </article>
        <article className="panel rounded-[24px] p-4">
          <p className="text-[0.72rem] uppercase tracking-[0.22em] text-slate-400">
            Rescheduled
          </p>
          <p className="mt-3 text-2xl font-semibold text-stone-50">
            {statusCount(visibleAppointments, "Rescheduled")}
          </p>
        </article>
        <article className="panel rounded-[24px] p-4">
          <p className="text-[0.72rem] uppercase tracking-[0.22em] text-slate-400">
            Cancelled
          </p>
          <p className="mt-3 text-2xl font-semibold text-stone-50">
            {statusCount(visibleAppointments, "Cancelled")}
          </p>
        </article>
      </section>

      <section className="grid gap-4 xl:grid-cols-[0.72fr_1.28fr]">
        <article className="panel rounded-[32px] p-5 sm:p-6">
          <p className="text-[0.72rem] font-semibold uppercase tracking-[0.22em] text-amber-300/80">
            Technician Coverage
          </p>
          <h3 className="mt-3 text-2xl font-semibold tracking-tight text-stone-50">
            {new Date(`${selectedDate}T12:00:00`).toLocaleDateString([], {
              weekday: "long",
              month: "long",
              day: "numeric",
            })}
          </h3>
          <p className="mt-2 text-sm leading-6 text-slate-400">
            Occupied technicians have at least one non-cancelled visit on the
            selected day. Available technicians are open for new work.
          </p>

          <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-1">
            <div className="rounded-[24px] border border-rose-300/15 bg-rose-500/8 p-4">
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-semibold text-rose-100">Occupied</p>
                <span className="rounded-full bg-rose-400/15 px-2.5 py-1 text-xs text-rose-100">
                  {occupiedTechnicians.length}
                </span>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                {occupiedTechnicians.length === 0 ? (
                  <span className="text-sm text-slate-400">No technicians booked.</span>
                ) : (
                  occupiedTechnicians.map((technician) => (
                    <span
                      key={technician}
                      className="rounded-full border border-rose-300/20 bg-rose-400/10 px-3 py-1.5 text-sm text-rose-50"
                    >
                      {technician}
                    </span>
                  ))
                )}
              </div>
            </div>

            <div className="rounded-[24px] border border-emerald-300/15 bg-emerald-500/8 p-4">
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-semibold text-emerald-100">Available</p>
                <span className="rounded-full bg-emerald-400/15 px-2.5 py-1 text-xs text-emerald-100">
                  {availableTechnicians.length}
                </span>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                {availableTechnicians.length === 0 ? (
                  <span className="text-sm text-slate-400">Every technician is booked.</span>
                ) : (
                  availableTechnicians.map((technician) => (
                    <span
                      key={technician}
                      className="rounded-full border border-emerald-300/20 bg-emerald-400/10 px-3 py-1.5 text-sm text-emerald-50"
                    >
                      {technician}
                    </span>
                  ))
                )}
              </div>
            </div>
          </div>

          <div className="mt-5 rounded-[24px] border border-white/8 bg-black/10 p-4">
            <div className="flex items-center justify-between gap-3">
              <p className="text-sm font-semibold text-stone-50">Selected day appointments</p>
              <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-xs text-slate-300">
                {selectedDayAppointments.length}
              </span>
            </div>

            <div className="mt-4 space-y-3">
              {selectedDayAppointments.length === 0 ? (
                <p className="text-sm text-slate-500">
                  No appointments are seeded for this day yet.
                </p>
              ) : (
                selectedDayAppointments.map((appointment) => {
                  const statusClass =
                    appointmentStatusClasses[appointment.Status] ??
                    "bg-white/5 text-slate-200 ring-1 ring-white/10";

                  return (
                    <div
                      key={appointment["Appointment ID"]}
                      className="rounded-[18px] border border-white/8 bg-white/5 p-3"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-sm font-medium text-stone-100">
                            {appointment.Time} · {appointment.Customer}
                          </p>
                          <p className="mt-1 text-sm text-slate-400">
                            {appointment.Service}
                          </p>
                        </div>
                        <span
                          className={`rounded-full px-2 py-1 text-[0.68rem] font-medium ${statusClass}`}
                        >
                          {appointment.Status}
                        </span>
                      </div>
                      <p className="mt-2 text-xs uppercase tracking-[0.16em] text-slate-500">
                        {appointment.Technician} · {appointment["Appointment ID"]}
                      </p>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </article>

      </section>

      <section className="panel rounded-[32px] p-4 sm:p-5">
        <div className="grid grid-cols-7 gap-2 pb-3">
          {WEEKDAYS.map((weekday) => (
            <div
              key={weekday}
              className="px-2 py-2 text-center text-[0.72rem] font-semibold uppercase tracking-[0.22em] text-slate-400"
            >
              {weekday}
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-7">
          {calendarDays.map((day) => {
            const inMonth = day.getMonth() === visibleMonth.getMonth();
            const isoDate = toIsoDate(day);
            const dayAppointments = appointments.filter(
              (appointment) => appointment.Date === isoDate,
            );

            return (
              <article
                key={isoDate}
                onClick={() => setSelectedDate(isoDate)}
                className={`min-h-[180px] rounded-[24px] border p-3 transition ${
                  inMonth
                    ? "border-white/10 bg-slate-950/55"
                    : "border-white/6 bg-black/10 text-slate-500"
                } ${highlightRefresh ? "ring-1 ring-amber-300/20" : ""} ${
                  selectedDate === isoDate
                    ? "ring-2 ring-amber-300/60"
                    : "hover:border-amber-300/30"
                } cursor-pointer`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-[0.7rem] uppercase tracking-[0.18em] text-slate-500">
                      {day.toLocaleDateString([], { weekday: "short" })}
                    </p>
                    <p className="mt-1 text-2xl font-semibold text-stone-50">
                      {day.getDate()}
                    </p>
                  </div>
                  <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-xs text-slate-300">
                    {dayAppointments.length}
                  </span>
                </div>

                <div className="mt-4 space-y-2">
                  {dayAppointments.length === 0 ? (
                    <p className="text-sm text-slate-500">No service visits</p>
                  ) : (
                    dayAppointments.map((appointment) => {
                      const statusClass =
                        appointmentStatusClasses[appointment.Status] ??
                        "bg-white/5 text-slate-200 ring-1 ring-white/10";

                      return (
                        <div
                          key={appointment["Appointment ID"]}
                          className="rounded-[18px] border border-white/8 bg-white/5 p-3"
                        >
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <p className="text-sm font-medium text-stone-100">
                                {appointment.Time}
                              </p>
                              <p className="mt-1 text-sm text-slate-300">
                                {appointment.Customer}
                              </p>
                            </div>
                            <span
                              className={`rounded-full px-2 py-1 text-[0.68rem] font-medium ${statusClass}`}
                            >
                              {appointment.Status}
                            </span>
                          </div>
                          <p className="mt-2 text-sm text-slate-400">
                            {appointment.Service}
                          </p>
                          <p className="mt-1 text-xs uppercase tracking-[0.16em] text-slate-500">
                            {appointment.Technician} · {appointment["Appointment ID"]}
                          </p>
                        </div>
                      );
                    })
                  )}
                </div>
              </article>
            );
          })}
        </div>
      </section>
    </div>
  );
}
