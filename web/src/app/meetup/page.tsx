import { notFound } from "next/navigation";

import { SOCIAL } from "@/lib/site";
import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { RequestForm } from "@/components/RequestForm";

export const metadata: Metadata = {
  title: "모임 열어주세요 · 보드게임 컬렉션",
  description: "하고 싶은 게임을 남기면 당근모임으로 열어드립니다.",
};

export default function MeetupPage() {
  if (!SOCIAL) notFound();

  return (
    <div className="mx-auto max-w-lg px-4 py-6">
      <Link
        href="/requests"
        className="mb-5 inline-flex items-center gap-1.5 text-sm text-ink-dim transition-colors hover:text-ink"
      >
        <ArrowLeft size={16} /> 신청 현황
      </Link>

      <h1 className="text-2xl font-black">모임 열어주세요</h1>
      <p className="mt-1.5 mb-6 text-sm text-ink-dim">
        하고 싶은 게임과 가능한 요일만 남겨주세요. 인원이 모이면 당근모임에 올리고
        연락드릴게요. 특정 게임은 목록에서 카드를 눌러 신청하는 게 더 빠릅니다.
      </p>

      <RequestForm
        type="meetup"
        submitLabel="모임 열어달라고 요청하기"
        successText="인원이 모이면 당근모임에 올리고 연락드릴게요."
        fields={[
          {
            name: "games",
            label: "하고 싶은 게임",
            placeholder: "예) 브라스 버밍엄, 아크 노바 / 가벼운 거 아무거나",
          },
          { name: "days", label: "가능한 요일", type: "days" },
        ]}
      />
    </div>
  );
}
