import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft, ArrowUpRight, Car, Clock3, Coffee, Dices, MapPin, ShieldCheck, Sparkles, Users } from "lucide-react";

import { AzitBooking } from "@/components/AzitBooking";
import { SOCIAL } from "@/lib/site";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "보드게임 아지트 · 공간 예약",
  description: "분당 보드게임 아지트. 이용 가능 시간표를 확인하고 월 이용권 보유자와 함께 공간을 예약하세요.",
};

const address = "경기도 성남시 분당구 돌마로 366번길 8 푸른마을상가 4-5동 1층 120호";

export default function AzitPage() {
  if (!SOCIAL) notFound();

  return (
    <div className="mx-auto max-w-6xl px-4 py-6 sm:py-8">
      <Link href="/" className="inline-flex items-center gap-1.5 text-sm text-ink-dim hover:text-ink">
        <ArrowLeft size={16} /> 보드게임 컬렉션
      </Link>

      <section className="relative mt-5 overflow-hidden rounded-3xl border border-line bg-panel p-6 sm:p-9">
        <Dices size={190} strokeWidth={0.8} className="pointer-events-none absolute -right-8 -bottom-8 -rotate-12 text-accent/10 sm:right-8" aria-hidden />
        <div className="relative max-w-2xl">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-accent/30 bg-accent/10 px-3 py-1 text-xs font-bold text-accent">
            <Sparkles size={13} /> 분당 수내 · 보드게임 아지트
          </span>
          <h1 className="mt-4 text-3xl leading-tight font-black tracking-tight sm:text-4xl">우리끼리, 한 판 더.</h1>
          <p className="mt-3 max-w-lg text-sm leading-7 text-ink-dim sm:text-base">
            좋아하는 게임과 함께 모일 공간이 생겼어요.<br />
            시간표를 확인하고, 월 이용권 보유자와 함께 놀러 오세요.
          </p>
          <div className="mt-6 flex flex-wrap gap-2">
            <a href="#reservation" className="inline-flex items-center gap-2 rounded-xl bg-accent px-5 py-3 text-sm font-bold text-bg hover:opacity-90">
              시간표 보고 예약하기 <ArrowUpRight size={16} />
            </a>
            <a href="#visit" className="rounded-xl border border-line bg-bg/50 px-5 py-3 text-sm font-medium hover:bg-panel-2">공간 이용 안내</a>
          </div>
        </div>
      </section>

      <div className="my-6 grid gap-3 sm:grid-cols-3">
        <div className="rounded-2xl border border-line bg-panel px-5 py-4">
          <p className="text-xs text-ink-dim">1인 이용권 안내</p>
          <p className="mt-2 font-bold">1일 <span className="tnum text-xl">5,000</span>원 <span className="mx-1 text-ink-dim">/</span> 월 <span className="tnum">15,000</span>원</p>
        </div>
        <div className="rounded-2xl border border-line bg-panel px-5 py-4">
          <p className="flex items-center gap-1.5 text-xs text-ink-dim"><Users size={14} /> 함께 이용하는 조건</p>
          <p className="mt-2 font-bold">월 이용권 보유자 1명 이상 동행</p>
        </div>
        <div className="rounded-2xl border border-line bg-panel px-5 py-4">
          <p className="flex items-center gap-1.5 text-xs text-ink-dim"><ShieldCheck size={14} /> 예약 안내</p>
          <p className="mt-2 font-bold">신청 접수 후 운영자가 확인해요</p>
        </div>
      </div>

      <section id="reservation" className="scroll-mt-32">
        <AzitBooking initialNow={new Date().toISOString()} />
      </section>

      <section id="visit" className="mt-12 scroll-mt-32 border-t border-line pt-8">
        <p className="text-xs font-bold tracking-wider text-accent">방문 전에 확인해 주세요</p>
        <h2 className="mt-2 text-2xl font-black">아지트 이용 안내</h2>
        <div className="mt-5 grid gap-4 md:grid-cols-2">
          <article className="rounded-2xl border border-line bg-panel p-5 sm:p-6">
            <h3 className="flex items-center gap-2 font-bold"><MapPin size={18} className="text-accent" /> 찾아오시는 길</h3>
            <p className="mt-3 text-sm leading-7">{address}</p>
            <p className="mt-2 text-xs leading-6 text-ink-dim">다른 주소 표기: 경기도 성남시 분당구 수내로 192번길 25 쌍용B상가 120호</p>
            <a href={`https://map.naver.com/p/search/${encodeURIComponent("성남시 분당구 수내로192번길 25")}`} target="_blank" rel="noreferrer" className="mt-4 inline-flex items-center gap-1 text-sm font-bold text-accent hover:underline">네이버 지도에서 보기 <ArrowUpRight size={15} /></a>
          </article>
          <article className="rounded-2xl border border-line bg-panel p-5 sm:p-6">
            <h3 className="flex items-center gap-2 font-bold"><Clock3 size={18} className="text-accent" /> 이용 시간 · 심야 이용</h3>
            <p className="mt-3 text-sm leading-7 text-ink-dim">월·화 18:00–22:00, 토 09:00–19:00, 일 09:00–12:00를 제외한 시간에 예약을 신청할 수 있어요.</p>
            <p className="mt-2 text-sm leading-7">자정을 넘기는 이용은 별도 안내가 필요해요. <strong className="text-weight">00:10–09:00에는 운영자가 함께 있어야 해요.</strong> 상가 문 관리가 필요해 신청 후 동행 가능 여부를 확인합니다.</p>
          </article>
          <article className="rounded-2xl border border-line bg-panel p-5 sm:p-6">
            <h3 className="flex items-center gap-2 font-bold"><Coffee size={18} className="text-accent" /> 음식 · 음료 · 보드게임</h3>
            <p className="mt-3 text-sm leading-7 text-ink-dim">외부 음식은 반입할 수 있어요. 식사 후 뒷정리와 분리수거를 부탁드립니다. 냉장고에 물이 있고, 커피 등은 주변에서 사 오시는 걸 권해요.</p>
            <p className="mt-2 text-sm leading-7 text-ink-dim">주변에 컴포즈·공차, 2층에 Various Bean이 있어요. Various Bean은 19시 전에 이용해 주세요.</p>
            <Link href="/" className="mt-4 inline-flex items-center gap-1 text-sm font-bold text-accent hover:underline">소장 보드게임 보기 · 게임 대여 신청 <ArrowUpRight size={15} /></Link>
          </article>
          <article className="rounded-2xl border border-line bg-panel p-5 sm:p-6">
            <h3 className="flex items-center gap-2 font-bold"><Car size={18} className="text-accent" /> 주차 · 마무리</h3>
            <p className="mt-3 text-sm leading-7 text-ink-dim">주차장은 이용 가능하지만 공간이 넉넉하지 않아요. 모임당 1–2대 기준으로 조율하고 있으니 미리 연락해 주세요. 신청서에 남긴 주차 요청도 운영자 확인 후 안내합니다.</p>
            <p className="mt-2 text-sm leading-7 text-ink-dim">이용 후에는 쓰레기를 분리수거하고 자리를 정리해 주세요. 보드게임 구성품도 빠짐없이 확인해 제자리에 넣어 주세요.</p>
          </article>
        </div>
        <div className="mt-6 flex flex-wrap justify-between gap-3 text-xs text-ink-dim">
          <p>예약 변경·취소는 운영자에게 연락해 주세요. 연락처와 메모는 운영자만 확인할 수 있어요.</p>
          <Link href="/azit/admin" className="hover:text-ink hover:underline">운영자 예약 관리 →</Link>
        </div>
      </section>
    </div>
  );
}
