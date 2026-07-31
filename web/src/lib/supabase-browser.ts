"use client";

import { createBrowserClient } from "@supabase/ssr";

/**
 * Browser client, used only for the sign-in/sign-out handshake.
 *
 * Reads and writes go through Server Components with the request-scoped
 * client, so the anon key here never touches privileged data.
 */
export function browserSupabase() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !key) {
    throw new Error("Supabase 로그인 설정이 없습니다 (.env.local 확인)");
  }
  return createBrowserClient(url, key);
}
