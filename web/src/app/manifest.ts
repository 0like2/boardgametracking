import type { MetadataRoute } from "next";

import { SITE_TITLE, SOCIAL } from "@/lib/site";

/** Replaces the static manifest so the two deployments install under their
 *  own names on the home screen. */
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: SITE_TITLE,
    short_name: "보드게임",
    description: SOCIAL
      ? "소장 보드게임 목록 · 자료실 · 대여 및 모임 신청"
      : "소장 보드게임 목록 · 자료실",
    start_url: "/",
    display: "standalone",
    background_color: "#0e0f11",
    theme_color: "#0e0f11",
    orientation: "portrait",
    lang: "ko",
    icons: [{"src": "/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"}, {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"}, {"src": "/icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"}],
  };
}
