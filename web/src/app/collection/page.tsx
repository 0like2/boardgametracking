import type { Metadata } from "next";

import { CollectionView } from "@/components/CollectionView";
import { games } from "@/lib/games";

export const metadata: Metadata = {
  title: "내 카드 · 보드게임 컬렉션",
  description: "플레이한 게임의 카드를 모아보세요.",
};

export default function CollectionPage() {
  return <CollectionView games={games} />;
}
