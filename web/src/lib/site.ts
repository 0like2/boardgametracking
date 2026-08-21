/**
 * Per-deployment settings. One codebase serves two collections; which one is
 * decided by env vars on the Vercel project, not by a code branch.
 *
 *   NEXT_PUBLIC_COLLECTION=b        -> the second owner's catalog
 *   NEXT_PUBLIC_SITE_TITLE=…        -> header and <title>
 */
export const COLLECTION = process.env.NEXT_PUBLIC_COLLECTION === "b" ? "b" : "main";

export const SITE_TITLE = process.env.NEXT_PUBLIC_SITE_TITLE ?? "보드게임 컬렉션";

/**
 * Whether this deployment has the social half — meetup requests, the ranking
 * board, play logging. The second site is catalog-only, and its Vercel project
 * has no Supabase or notification credentials at all.
 */
export const SOCIAL = COLLECTION === "main";
