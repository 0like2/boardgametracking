"use client";

import { useState } from "react";
import { Check, Loader2 } from "lucide-react";

export type Field = {
  name: string;
  label: string;
  type?: "text" | "date" | "time" | "number" | "textarea" | "days";
  placeholder?: string;
  required?: boolean;
  /** Half-width on desktop so date/time sit side by side. */
  half?: boolean;
};

const DAYS = ["월", "화", "수", "목", "금", "토", "일"] as const;

type Props = {
  type: "rental" | "meetup";
  /** Extra values merged into the payload (e.g. the game being borrowed). */
  hidden?: Record<string, string>;
  fields: Field[];
  submitLabel: string;
  successText: string;
};

export function RequestForm({ type, hidden, fields, submitLabel, successText }: Props) {
  const [values, setValues] = useState<Record<string, string>>({});
  const [state, setState] = useState<"idle" | "sending" | "done">("idle");
  const [error, setError] = useState<string | null>(null);

  const [channel, setChannel] = useState<Channel>("당근");

  const allFields: Field[] = [
    { name: "name", label: "이름", required: true, placeholder: "홍길동", half: true },
    ...fields,
  ];

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setState("sending");
    setError(null);

    try {
      const res = await fetch("/api/requests", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          type,
          ...hidden,
          ...values,
          // "당근 @gildong" reads clearly in the Discord embed and the email.
          contact: `${channel} ${values.contactValue ?? ""}`.trim(),
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error ?? "전송에 실패했습니다.");
      setState("done");
    } catch (err) {
      setState("idle");
      setError(err instanceof Error ? err.message : "전송에 실패했습니다.");
    }
  }

  if (state === "done") {
    return (
      <div className="flex flex-col items-center gap-3 rounded-2xl border border-line bg-panel p-8 text-center">
        <span className="flex size-12 items-center justify-center rounded-full bg-accent/15 text-accent">
          <Check size={26} />
        </span>
        <p className="font-bold">신청이 전달됐습니다</p>
        <p className="text-sm text-ink-dim">{successText}</p>
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-4">
      {/* --- contact: channel picker + handle --- */}
      <div className="flex flex-col gap-1.5">
        <span className="text-xs text-ink-dim">
          연락 방법<span className="ml-1 text-weight">*</span>
        </span>
        <div className="flex gap-1.5">
          {CHANNELS.map((c) => (
            <button
              key={c}
              type="button"
              onClick={() => setChannel(c)}
              className={`rounded-full px-3.5 py-1.5 text-sm transition-colors ${
                channel === c
                  ? "bg-ink font-medium text-bg"
                  : "bg-panel text-ink-dim hover:bg-panel-2"
              }`}
            >
              {c}
            </button>
          ))}
        </div>
        <input
          required
          placeholder={CHANNEL_PLACEHOLDER[channel]}
          value={values.contactValue ?? ""}
          onChange={(e) => setValues({ ...values, contactValue: e.target.value })}
          className={inputClass}
        />
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {allFields.map((f) =>
          f.type === "days" ? (
            <DayPicker
              key={f.name}
              label={f.label}
              value={values[f.name] ?? ""}
              onChange={(v) => setValues({ ...values, [f.name]: v })}
            />
          ) : (
          <label
            key={f.name}
            className={`flex flex-col gap-1.5 ${f.half ? "" : "sm:col-span-2"}`}
          >
            <span className="text-xs text-ink-dim">
              {f.label}
              {f.required && <span className="ml-1 text-weight">*</span>}
            </span>

            {f.type === "textarea" ? (
              <textarea
                rows={3}
                required={f.required}
                placeholder={f.placeholder}
                value={values[f.name] ?? ""}
                onChange={(e) => setValues({ ...values, [f.name]: e.target.value })}
                className={inputClass}
              />
            ) : (
              <input
                type={f.type ?? "text"}
                required={f.required}
                placeholder={f.placeholder}
                value={values[f.name] ?? ""}
                onChange={(e) => setValues({ ...values, [f.name]: e.target.value })}
                className={inputClass}
              />
            )}
          </label>
          ),
        )}
      </div>

      {/* Honeypot — hidden from people, tempting to bots. */}
      <input
        type="text"
        name="website"
        tabIndex={-1}
        autoComplete="off"
        aria-hidden="true"
        value={values.website ?? ""}
        onChange={(e) => setValues({ ...values, website: e.target.value })}
        className="absolute left-[-9999px] size-0"
      />

      {error && (
        <p className="rounded-lg bg-weight/10 px-3 py-2 text-sm text-weight">{error}</p>
      )}

      <button
        type="submit"
        disabled={state === "sending"}
        className="inline-flex items-center justify-center gap-2 rounded-xl bg-accent px-5 py-3 font-bold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
      >
        {state === "sending" && <Loader2 size={16} className="animate-spin" />}
        {state === "sending" ? "전송 중…" : submitLabel}
      </button>
    </form>
  );
}

/** Weekday multi-select. Stored as a comma-joined string, e.g. "토,일". */
function DayPicker({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  const picked = value ? value.split(",") : [];

  function toggleDay(day: string) {
    const next = picked.includes(day)
      ? picked.filter((d) => d !== day)
      : [...picked, day];
    // Keep 월→일 order regardless of click order.
    onChange(DAYS.filter((d) => next.includes(d)).join(","));
  }

  return (
    <div className="flex flex-col gap-1.5 sm:col-span-2">
      <span className="text-xs text-ink-dim">{label}</span>
      <div className="flex gap-1.5">
        {DAYS.map((d) => (
          <button
            key={d}
            type="button"
            onClick={() => toggleDay(d)}
            aria-pressed={picked.includes(d)}
            className={`size-10 shrink-0 rounded-full text-sm transition-colors ${
              picked.includes(d)
                ? "bg-ink font-bold text-bg"
                : "bg-panel text-ink-dim hover:bg-panel-2"
            }`}
          >
            {d}
          </button>
        ))}
      </div>
      <p className="text-xs text-ink-faint">
        {picked.length === 0 ? "선택하지 않으면 아무 요일이나 괜찮다는 뜻입니다." : `${picked.join("·")}요일 가능`}
      </p>
    </div>
  );
}

const CHANNELS = ["당근", "카카오톡", "전화"] as const;
type Channel = (typeof CHANNELS)[number];

const CHANNEL_PLACEHOLDER: Record<Channel, string> = {
  당근: "당근 닉네임 또는 프로필 링크",
  카카오톡: "카톡 ID",
  전화: "010-0000-0000",
};

const inputClass =
  "rounded-xl border border-line bg-panel px-3.5 py-2.5 text-ink placeholder:text-ink-faint focus:border-accent focus:outline-none";
