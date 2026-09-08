import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft, Lock } from "lucide-react";

import { AzitAdmin } from "@/components/AzitAdmin";
import { AuthButton } from "@/components/AuthButton";
import { isAzitAdmin } from "@/lib/azit-admin";
import { SOCIAL } from "@/lib/site";

export const metadata: Metadata = {
  title: "아지트 예약 관리 · 보드게임 컬렉션",
  description: "보드게임 아지트 예약을 확인하고 관리합니다.",
};

export const dynamic = "force-dynamic";

export default async function AzitAdminPage() {
  if (!SOCIAL) notFound();

  const allowed = await isAzitAdmin();

  return (
    <div className="mx-auto max-w-5xl px-4 py-6">
      <Link
        href="/azit"
        className="mb-5 inline-flex items-center gap-1.5 rounded-lg py-1 text-sm text-ink-dim transition-colors hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
      >
        <ArrowLeft size={16} /> 아지트 안내
      </Link>

      {!allowed ? (
        <section className="mx-auto flex max-w-md flex-col items-center gap-4 rounded-2xl border border-line bg-panel px-6 py-12 text-center">
          <span className="flex size-14 items-center justify-center rounded-full bg-panel-2 text-ink-faint">
            <Lock size={26} />
          </span>
          <div>
            <h1 className="text-xl font-black">예약 관리 전용 화면입니다</h1>
            <p className="mt-2 text-sm leading-relaxed text-ink-dim">
              운영 계정으로 로그인하면 예약 신청을 확인할 수 있습니다.
            </p>
          </div>
          <AuthButton next="/azit/admin" />
        </section>
      ) : (
        <AzitAdmin />
      )}
    </div>
  );
}
