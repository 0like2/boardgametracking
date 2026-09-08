export { adminUpdateError } from "@/lib/azit";
export type { AdminBookingUpdate } from "@/lib/azit";
import { serverSupabase } from "@/lib/supabase";
import { userSupabase } from "@/lib/supabase-server";

export async function isAzitAdmin(): Promise<boolean> {
  try {
    const userClient = await userSupabase();
    if (!userClient) return false;
    const { data: auth, error: authError } = await userClient.auth.getUser();
    if (authError || !auth.user) return false;

    const adminClient = serverSupabase();
    if (!adminClient) return false;
    const { data, error } = await adminClient
      .from("space_admins")
      .select("user_id")
      .eq("user_id", auth.user.id)
      .maybeSingle();
    return !error && !!data;
  } catch {
    return false;
  }
}
