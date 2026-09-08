// Run with Node 24: node --experimental-strip-types --test tests/azit-api.test.mjs
// Exercises the real route handlers with an in-process storage/auth stub, never a live database.
import assert from "node:assert/strict";
import { createRequire, registerHooks } from "node:module";
import test from "node:test";

const require = createRequire(import.meta.url);
const state = { database: null, user: null, authError: null, discordStatus: 200, messages: [] };
globalThis.__azitApiCheck = state;
process.env.NEXT_PUBLIC_COLLECTION = "";
process.env.DISCORD_WEBHOOK_URL = "https://discord.invalid/api/webhooks/test/token";
globalThis.fetch = async (url, options) => {
  assert.equal(new URL(url).hostname, "discord.invalid", "tests must never call a real service");
  state.messages.push(JSON.parse(options.body));
  return new Response("{}", { status: state.discordStatus });
};

registerHooks({
  resolve(specifier, context, next) {
    if (specifier === "@/lib/supabase" || specifier === "@/lib/supabase-server") {
      return { url: `azit-check:${specifier}`, shortCircuit: true };
    }
    if (specifier.startsWith("@/")) return next(new URL(`../src/${specifier.slice(2)}.ts`, import.meta.url).href, context);
    if (specifier === "next/server") return next(require.resolve(specifier), context);
    return next(specifier, context);
  },
  load(url, context, next) {
    if (url === "azit-check:@/lib/supabase") return { format: "module", source: "export function serverSupabase() { return globalThis.__azitApiCheck.database; }", shortCircuit: true };
    if (url === "azit-check:@/lib/supabase-server") return { format: "module", source: "export async function userSupabase() { return { auth: { getUser: async () => ({ data: { user: globalThis.__azitApiCheck.user }, error: globalThis.__azitApiCheck.authError }) } }; }", shortCircuit: true };
    return next(url, context);
  },
});

const api = await import("../src/app/api/azit/route.ts");
const admin = await import("../src/app/api/azit/admin/route.ts");
const requests = await import("../src/app/api/requests/route.ts");
const { isAzitAdmin } = await import("../src/lib/azit-admin.ts");
const { addDays, blockedIntervals, kstDate, toKstIso } = await import("../src/lib/azit.ts");
let date = addDays(kstDate(new Date()), 7);
while (blockedIntervals(date).length) date = addDays(date, 1);
const input = {
  startAt: toKstIso(date, "13:00"), endAt: toKstIso(date, "14:00"),
  name: "테스트 신청자", contact: "당근 test", partySize: 4, monthlyPassCount: 1,
  monthlyMemberName: "테스트 월회원", parking: 0, games: "", note: "비공개 메모",
  rulesAccepted: true, nightNoticeAccepted: false, hostPresenceRequested: false,
};
const row = {
  id: "10000000-0000-4000-8000-000000000001", start_at: input.startAt, end_at: input.endAt, status: "pending",
  name: input.name, contact: input.contact, note: input.note, parking: 0,
  monthly_member_name: input.monthlyMemberName, needs_host: false, member_verified: false,
};
let requestNumber = 0;
function post(body = input, overrides = {}) {
  return new Request("http://azit.test/api/azit", {
    method: "POST", headers: { "content-type": "application/json", "x-forwarded-for": `test-${++requestNumber}` },
    body: JSON.stringify(body), ...overrides,
  });
}
function database({ error = null, emptyUpdate = false } = {}) {
  const writes = [];
  const selects = [];
  return {
    writes, selects,
    from(table) {
      if (table === "space_admins") {
        let userId;
        return {
          select(columns) { assert.equal(columns, "user_id"); return this; },
          eq(column, value) { assert.equal(column, "user_id"); userId = value; return this; },
          maybeSingle: async () => ({ data: userId === "operator-uuid" ? { user_id: userId } : null, error: null }),
        };
      }
      assert.ok(["space_bookings", "requests"].includes(table));
      let columns = "";
      let operation = "read";
      let saved = { ...row };
      const project = () => Object.fromEntries(columns.split(",").map((key) => [key.trim(), saved[key.trim()]]));
      const query = {
        select(value) { columns = value; selects.push(value); return this; },
        insert(value) { operation = "insert"; writes.push(value); saved = { ...saved, ...value }; return this; },
        update(value) { operation = "update"; writes.push(value); saved = { ...saved, ...value }; return this; },
        lt() { return this; }, gt() { return this; }, eq() { return this; }, neq() { return this; },
        or() { return this; }, order() { return this; }, limit() { return this; }, range() { return this; },
        single: async () => ({ data: error ? null : project(), error }),
        maybeSingle: async () => ({ data: error || (operation === "update" && emptyUpdate) ? null : project(), error }),
        then(resolve) { return Promise.resolve({ data: error ? null : [project()], error }).then(resolve); },
      };
      return query;
    },
  };
}

test("public schedule projects only time/status, and failures never become empty availability", async () => {
  state.database = database();
  const request = new Request(`http://azit.test/api/azit?from=${date}&to=${addDays(date, 1)}`);
  const response = await api.GET(request);
  assert.equal(response.status, 200);
  assert.equal(response.headers.get("cache-control"), "no-store");
  const { bookings } = await response.json();
  assert.deepEqual(Object.keys(bookings[0]).sort(), ["end_at", "id", "start_at", "status"]);
  assert.equal(state.database.selects[0], "id, start_at, end_at, status");
  state.database = null;
  assert.equal((await api.GET(request)).status, 503);
  assert.equal((await api.GET(new Request("http://azit.test/api/azit?from=2026-02-30&to=2026-03-05"))).status, 400);
});

test("submission validates before writing, persists pending, and maps storage conflict/failure", async () => {
  state.messages.length = 0;
  state.database = database();
  assert.equal((await api.POST(post({ ...input, monthlyPassCount: 0 }))).status, 400);
  assert.equal(state.database.writes.length, 0);
  const response = await api.POST(post());
  assert.equal(response.status, 201);
  const { booking, notified } = await response.json();
  assert.equal(notified, true);
  assert.equal(booking.status, "pending");
  assert.equal(booking.contact, undefined);
  assert.equal(state.database.writes[0].monthly_member_name, input.monthlyMemberName);
  assert.equal(state.messages.length, 1);
  const message = JSON.stringify(state.messages[0]);
  assert.ok(message.includes("예약 접수중"));
  assert.ok(message.includes("/azit/admin"));
  for (const secret of [input.name, input.contact, input.note, input.monthlyMemberName]) assert.ok(!message.includes(secret));
  state.database = database({ error: { code: "23P01" } });
  assert.equal((await api.POST(post())).status, 409);
  state.database = database({ error: { code: "test_db_failure" } });
  assert.equal((await api.POST(post())).status, 503);
  state.database = null;
  assert.equal((await api.POST(post())).status, 503);
  assert.equal(state.messages.length, 1, "never notify an unsaved or conflicting request");
});

test("Discord failure leaves a successful booking saved and reports the notification gap", async () => {
  state.database = database();
  state.discordStatus = 500;
  const response = await api.POST(post());
  assert.equal(response.status, 201);
  assert.equal((await response.json()).notified, false);
  assert.equal(state.database.writes.length, 1);
  state.discordStatus = 200;
});

test("invalid JSON/types and oversized requests are rejected without storage access", async () => {
  assert.equal((await api.POST(post(null))).status, 400);
  assert.equal((await api.POST(post([], { body: "{" }))).status, 400);
  assert.equal((await api.POST(post(input, { headers: { "content-type": "text/plain" } }))).status, 415);
  assert.equal((await api.POST(post({ ...input, note: "x".repeat(9000) }))).status, 413);
});

test("admin requires authenticated DB membership, rejects forged origins, and enforces approval", async () => {
  state.database = database();
  state.user = { id: "guest-uuid", email: "operator@example.test", user_metadata: { is_admin: true } };
  assert.equal(await isAzitAdmin(), false);
  assert.equal((await admin.GET()).status, 403);
  state.user = { id: "operator-uuid" };
  state.authError = new Error("invalid session");
  assert.equal(await isAzitAdmin(), false);
  state.authError = null;
  assert.equal(await isAzitAdmin(), true);
  const privateResponse = await admin.GET();
  assert.equal(privateResponse.status, 200);
  assert.equal((await privateResponse.json()).bookings[0].contact, input.contact);
  const patch = (memberVerified, origin = "http://azit.test") => new Request("http://azit.test/api/azit/admin", {
    method: "PATCH", headers: { "content-type": "application/json", origin },
    body: JSON.stringify({ id: row.id, status: "approved", memberVerified, hostConfirmed: false, parkingConfirmed: false }),
  });
  assert.equal((await admin.PATCH(patch(true, "http://untrusted.test"))).status, 403);
  assert.equal((await admin.PATCH(patch(false))).status, 409);
  assert.equal(state.database.writes.length, 0);
  const response = await admin.PATCH(patch(true));
  assert.equal(response.status, 200);
  assert.equal((await response.json()).booking.status, "approved");
  state.database = database({ emptyUpdate: true });
  assert.equal((await admin.PATCH(patch(true))).status, 409);
  state.database = null;
  assert.equal(await isAzitAdmin(), false);
});

test("game and meetup requests also require DB persistence and survive a Discord outage", async () => {
  const request = { type: "meetup", name: "test", contact: "당근 test", games: "테스트 게임" };
  state.messages.length = 0;
  state.database = null;
  assert.equal((await requests.POST(post(request))).status, 503);
  state.database = database({ error: { code: "test_db_failure" } });
  assert.equal((await requests.POST(post(request))).status, 503);
  assert.equal(state.messages.length, 0);
  state.database = database();
  state.discordStatus = 500;
  const response = await requests.POST(post(request));
  assert.equal(response.status, 200);
  const data = await response.json();
  assert.equal(data.saved, true);
  assert.deepEqual(data.failed, ["discord"]);
  state.discordStatus = 200;
  assert.equal((await requests.POST(post(null))).status, 400);
});
