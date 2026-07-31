import { createClient, type SupabaseClient } from "@supabase/supabase-js";

/**
 * Server-side client using the service role key.
 *
 * Returns null when Supabase is not configured — requests still get delivered
 * over Discord/email, they just are not persisted.
 */
export function serverSupabase(): SupabaseClient | null {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) return null;
  return createClient(url, key, {
    auth: { persistSession: false, autoRefreshToken: false },
  });
}
