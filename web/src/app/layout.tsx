import type { Metadata, Viewport } from "next";
import { Noto_Sans_KR } from "next/font/google";
import Link from "next/link";
import "./globals.css";

import { AuthButton } from "@/components/AuthButton";

const notoKr = Noto_Sans_KR({
  variable: "--font-noto-kr",
  subsets: ["latin"],
  weight: ["400", "500", "700", "900"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "보드게임 컬렉션",
  description: "소장 보드게임 목록 · 자료실 · 대여 및 모임 신청",
  manifest: "/manifest.webmanifest",
  appleWebApp: { capable: true, statusBarStyle: "black-translucent", title: "보드게임" },
};

export const viewport: Viewport = {
  themeColor: "#0e0f11",
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ko">
      <body className={`${notoKr.variable} antialiased min-h-dvh flex flex-col`}>
        <header className="sticky top-0 z-40 border-b border-line bg-bg/85 backdrop-blur-md">
          <div className="mx-auto flex h-14 max-w-6xl items-center gap-4 px-4">
            <Link href="/" className="flex items-center gap-2 font-black tracking-tight">
              <span className="text-xl">🎲</span>
              <span>보드게임 컬렉션</span>
            </Link>
            <nav className="ml-auto flex items-center gap-1 text-sm">
              <Link
                href="/collection"
                className="rounded-lg px-3 py-1.5 text-ink-dim transition-colors hover:bg-panel hover:text-ink"
              >
                내 카드
              </Link>
              <Link
                href="/ranking"
                className="rounded-lg px-3 py-1.5 text-ink-dim transition-colors hover:bg-panel hover:text-ink"
              >
                랭킹
              </Link>
              <Link
                href="/requests"
                className="rounded-lg px-3 py-1.5 text-ink-dim transition-colors hover:bg-panel hover:text-ink"
              >
                신청 현황
              </Link>
              <AuthButton />
            </nav>
          </div>
        </header>

        <main className="flex-1">{children}</main>

        <footer className="border-t border-line px-4 py-8 text-center text-xs text-ink-faint">
          데이터 출처 · 보드라이프 / BoardGameGeek
        </footer>
      </body>
    </html>
  );
}
