"""Copy the 보드라이프 자료 files into the web app, compressing oversized PDFs.

Emits web/data/materials.json:  { "<boardlife game id>": [Material, ...] }

Re-runnable: files already present with the right size are skipped.
"""

from __future__ import annotations

import json
import shutil
import sys
import zipfile
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image

ROOT = Path(__file__).parent
SRC = Path("/Users/iyeonglag/Desktop/보드게임 자료")
DEST = ROOT / "web/public/materials"
OUT = ROOT / "web/data/materials.json"
GAMES = ROOT / "web/data/games.json"

# Anything above this gets re-rendered at RASTER_DPI.
MAX_BYTES = 2_500_000
RASTER_DPI = 130
JPEG_QUALITY = 72

# (game name_kr, kind, label, source filename)
MAP: list[tuple[str, str, str, str]] = [
    ("버건디의 성", "참조표", "참조표 (긴쪽 양면)", "[버건디의 성] 참조표(긴쪽 양면 ver).pdf"),
    ("버건디의 성", "참조표", "참조표 (접는 버전)", "[버건디의 성] 참조표(접는 ver).pdf"),
    ("버건디의 성", "참조표", "방패 확장 참조표", "[버건디의 성] 방패 확장 참조표.pdf"),

    ("루트", "요약표", "룰 요약", "루트 룰 요약.pdf"),
    ("루트", "요약표", "규칙 ONE SHEET (xlsx)", "루트 규칙 ONE SHEET 요약.xlsx"),

    ("메이지 나이트: 얼티밋 에디션", "요약표", "하는 법", "메이지 나이트 하는 법 1025 23시.pdf"),
    ("메이지 나이트: 얼티밋 에디션", "룰북", "정식 규칙 (나머지)", "정식 규칙 나머지 1007 11시.pdf"),

    ("브라스: 버밍엄", "요약표", "룰 요약", "브라스 버밍엄 룰 요약.pdf"),
    ("브라스: 버밍엄", "참조표", "참조표", "브라스 버밍험 참조표 수정.pdf"),
    ("브라스: 버밍엄", "점수판", "점수표", "점수표_브라스버밍엄.pdf"),
    ("브라스: 버밍엄", "룰북", "한글 룰북", "브라스-버밍엄(K).pdf"),

    ("셀레스티아", "참조표", "카드 참조표", "셀레스티아 카드 참조표_벽공.jpg"),
    ("셀레스티아", "참조표", "캐릭터 참조표", "셀레스티아 캐릭터 참조표_벽공.jpg"),

    ("엘드리치 호러", "참조표", "참조표 한글화", "엘드리치 호러 참조표 한글화.pdf"),

    ("테라포밍 마스", "참조표", "리마인더", "테포마 리마인더.pdf"),

    ("좀비사이드: 흑사병", "기타", "Massive Darkness 크로스오버",
     "Zombicide Black Plague - Massive Darkness Crossover Set.pdf"),
]

# Zip archives whose members each become one material.
ZIP_MAP: list[tuple[str, str, str, str]] = [
    ("클랭크!: 카타콤", "개인판", "개인매트", "클랭크 개인매트.zip"),
]


def compress_pdf(src: Path, dest: Path) -> None:
    """Rasterise each page at RASTER_DPI into a fresh, much smaller PDF."""
    doc = fitz.open(src)
    out = fitz.open()
    for page in doc:
        pix = page.get_pixmap(dpi=RASTER_DPI)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        buf = dest.parent / f".{dest.stem}_tmp.jpg"
        img.save(buf, "JPEG", quality=JPEG_QUALITY, optimize=True)
        rect = fitz.Rect(0, 0, page.rect.width, page.rect.height)
        new_page = out.new_page(width=rect.width, height=rect.height)
        new_page.insert_image(rect, filename=str(buf))
        buf.unlink()
    out.save(dest, deflate=True, garbage=4)
    out.close()
    doc.close()


def compress_image(src: Path, dest: Path) -> None:
    img = Image.open(src).convert("RGB")
    img.thumbnail((2200, 2200), Image.LANCZOS)
    img.save(dest, "JPEG", quality=80, optimize=True)


def place(src: Path, dest: Path) -> int:
    """Copy src -> dest, compressing if it is over budget. Returns final size."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    size = src.stat().st_size
    suffix = src.suffix.lower()

    if size <= MAX_BYTES:
        shutil.copy2(src, dest)
    elif suffix == ".pdf":
        compress_pdf(src, dest)
    elif suffix in {".jpg", ".jpeg", ".png"}:
        compress_image(src, dest)
    else:
        shutil.copy2(src, dest)

    final = dest.stat().st_size
    note = "" if final == size else f"  ({size / 1e6:.1f}MB -> {final / 1e6:.1f}MB)"
    print(f"  {dest.name}{note}")
    return final


def main() -> int:
    games = json.loads(GAMES.read_text(encoding="utf-8"))
    id_by_name = {g["nameKr"]: g["id"] for g in games}

    if DEST.exists():
        shutil.rmtree(DEST)

    manifest: dict[str, list[dict]] = {}
    unmatched: list[str] = []

    for name_kr, kind, label, filename in MAP:
        gid = id_by_name.get(name_kr)
        if gid is None:
            unmatched.append(f"{name_kr} (게임 목록에 없음)")
            continue
        src = SRC / filename
        if not src.exists():
            unmatched.append(f"{filename} (파일 없음)")
            continue

        print(f"{name_kr} · {label}")
        ext = src.suffix.lower()
        safe = f"{kind}_{label}".replace(" ", "_").replace("/", "-")
        dest = DEST / gid / f"{safe}{ext}"
        size = place(src, dest)

        manifest.setdefault(gid, []).append(
            {"kind": kind, "label": label, "file": f"/materials/{gid}/{dest.name}", "size": size}
        )

    for name_kr, kind, label, filename in ZIP_MAP:
        gid = id_by_name.get(name_kr)
        src = SRC / filename
        if gid is None or not src.exists():
            unmatched.append(f"{filename} ({name_kr})")
            continue
        print(f"{name_kr} · {label} (zip)")
        with zipfile.ZipFile(src) as zf:
            members = [m for m in zf.namelist() if not m.endswith("/")]
            for i, member in enumerate(sorted(members), 1):
                ext = Path(member).suffix.lower()
                dest = DEST / gid / f"{kind}_{label}_{i}{ext}"
                dest.parent.mkdir(parents=True, exist_ok=True)
                tmp = dest.parent / f".raw{ext}"
                tmp.write_bytes(zf.read(member))
                size = place(tmp, dest)
                tmp.unlink(missing_ok=True)
                manifest.setdefault(gid, []).append(
                    {
                        "kind": kind,
                        "label": f"{label} {i}",
                        "file": f"/materials/{gid}/{dest.name}",
                        "size": size,
                    }
                )

    OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    total = sum(m["size"] for ms in manifest.values() for m in ms)
    count = sum(len(ms) for ms in manifest.values())
    print(f"\n{count} materials for {len(manifest)} games, {total / 1e6:.1f}MB total")
    print(f"-> {OUT}")
    if unmatched:
        print(f"skipped ({len(unmatched)}): {unmatched}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
