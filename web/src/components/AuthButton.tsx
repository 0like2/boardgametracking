"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { LogIn, LogOut } from "lucide-react";

import { browserSupabase } from "@/lib/supabase-browser";

type Viewer = { name: string; avatarUrl: string | null } | null;

/**
 * Reads its own session in the browser rather than taking it as a prop.
 *
 * Doing it server-side would mean calling cookies() in the root layout, which
 * opts every page — including the 109 statically generated game pages — into
 * dynamic rendering. The ranking page still checks the session on the server.
 */
export function AuthButton({ next = "/ranking" }: { next?: string }) {
  const router = useRouter();
  const [viewer, setViewer] = useState<Viewer>(null);
  const [ready, setReady] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let supabase;
    try {
      supabase = browserSupabase();
    } catch {
      setReady(true); // Supabase not configured — render nothing.
      return;
    }

    const read = async () => {
      const {
        data: { user },
      } = await supabase.auth.getUser();
      setViewer(
        user
          ? {
              name:
                user.user_metadata?.full_name ??
                user.user_metadata?.name ??
                user.email ??
                "",
              avatarUrl: user.user_metadata?.avatar_url ?? null,
            }
          : null,
      );
      setReady(true);
    };

    read();
    const { data: sub } = supabase.auth.onAuthStateChange(() => {
      read();
      router.refresh();
    });
    return () => sub.subscription.unsubscribe();
  }, [router]);

  async function signIn() {
    setBusy(true);
    try {
      const { error } = await browserSupabase().auth.signInWithOAuth({
        provider: "google",
        options: {
          redirectTo: `${window.location.origin}/auth/callback?next=${encodeURIComponent(next)}`,
        },
      });
      if (error) throw error;
      // The browser navigates to Google from here.
    } catch (err) {
      setBusy(false);
      alert(err instanceof Error ? err.message : "로그인에 실패했습니다.");
    }
  }

  async function signOut() {
    setBusy(true);
    await browserSupabase().auth.signOut();
    router.refresh();
    setBusy(false);
  }

  // Reserve the slot so the header does not jump once the session resolves.
  if (!ready) return <span className="w-16" aria-hidden />;

  if (viewer) {
    return (
      <div className="flex items-center gap-2">
        {viewer.avatarUrl && (
          // Google avatar hosts would need next/image remotePatterns; not worth it.
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={viewer.avatarUrl}
            alt=""
            className="size-7 rounded-full border border-line"
          />
        )}
        <span className="hidden max-w-28 truncate text-sm text-ink-dim sm:block">
          {viewer.name}
        </span>
        <button
          onClick={signOut}
          disabled={busy}
          aria-label="로그아웃"
          className="rounded-lg p-1.5 text-ink-faint transition-colors hover:bg-panel hover:text-ink disabled:opacity-50"
        >
          <LogOut size={16} />
        </button>
      </div>
    );
  }

  return (
    <button
      onClick={signIn}
      disabled={busy}
      className="inline-flex items-center gap-1.5 rounded-lg border border-line bg-panel px-3 py-1.5 text-sm text-ink-dim transition-colors hover:bg-panel-2 hover:text-ink disabled:opacity-50"
    >
      <LogIn size={15} />
      {busy ? "이동 중…" : "로그인"}
    </button>
  );
}
