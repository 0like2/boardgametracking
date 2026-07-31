"use client";

import { useEffect } from "react";
import { ArrowLeft, X } from "lucide-react";

type Props = {
  title: string;
  children: React.ReactNode;
  onClose: () => void;
  /** Shows a back arrow instead of only the close button. */
  onBack?: () => void;
};

export function Sheet({ title, children, onClose, onBack }: Props) {
  // Escape to close, and stop the page behind from scrolling.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [onClose]);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={title}
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/70 backdrop-blur-sm sm:items-center sm:p-4"
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="card-in max-h-[92dvh] w-full max-w-lg overflow-y-auto rounded-t-3xl border border-line bg-bg sm:rounded-3xl"
      >
        <div className="sticky top-0 z-10 flex items-center gap-3 border-b border-line bg-bg/95 px-5 py-4 backdrop-blur">
          {onBack && (
            <button
              onClick={onBack}
              aria-label="뒤로"
              className="-ml-1 rounded-lg p-1 text-ink-faint transition-colors hover:bg-panel hover:text-ink"
            >
              <ArrowLeft size={20} />
            </button>
          )}
          <h2 className="min-w-0 flex-1 truncate text-base font-black">{title}</h2>
          <button
            onClick={onClose}
            aria-label="닫기"
            className="-mr-1 rounded-lg p-1 text-ink-faint transition-colors hover:bg-panel hover:text-ink"
          >
            <X size={20} />
          </button>
        </div>

        <div className="p-5">{children}</div>
      </div>
    </div>
  );
}
