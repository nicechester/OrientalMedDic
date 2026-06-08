#!/usr/bin/env python3
"""
동의보감 JSONL에서 본초 정보 추출 (개선 버전)
"""

import json
import re
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path(__file__).parent.parent / "data"
DONGEUIBOGAM_FILE = DATA_DIR / "dongeuibogam_raw.jsonl"
OUTPUT_HERBAL = DATA_DIR / "herbal_dongeuibogam.json"

def extract_herb_info(entry: dict) -> dict:
    """항목에서 본초 정보 추출"""
    original = entry.get("original", "")
    korean = entry.get("korean", "")

    # 패턴 1: "卽~~~也" (예: "卽蜻蜓也" = 즉 잠자리이다)
    match = re.match(r"^卽([^也]+)也", original)
    if match:
        herb_name = match.group(1).strip()
        if is_valid_herb(herb_name):
            return {
                "name_hanja": herb_name,
                "name_korean": korean[:100],
                "efficacy": korean[100:300] if len(korean) > 100 else "",
            }

    # 패턴 2: 제목 형식 (예: "人參", "黃芪" - 1~4글자 한자만)
    match = re.match(r"^([一-鿿]{1,4})$", original.strip())
    if match:
        herb_name = match.group(1)
        if is_valid_herb(herb_name) and ("本草" in korean or "效" in korean or "主" in korean):
            return {
                "name_hanja": herb_name,
                "name_korean": korean[:100],
                "efficacy": korean[:300],
            }

    # 패턴 3: 첫 줄이 한자명으로 시작
    first_line = original.split('\n')[0].strip() if '\n' in original else original.strip()
    match = re.match(r"^([一-鿿]{1,4})\s", first_line)
    if match:
        herb_name = match.group(1)
        if is_valid_herb(herb_name):
            # 성질, 맛, 효능 등 추출
            efficacy_keywords = ["性", "味", "歸經", "效能", "主", "治", "補", "滋", "益"]
            if any(kw in original or kw in korean for kw in efficacy_keywords):
                return {
                    "name_hanja": herb_name,
                    "name_korean": korean[:100],
                    "efficacy": korean[:300],
                }

    return None


def is_valid_herb(name: str) -> bool:
    """유효한 본초명인지 확인"""
    # 1~4글자 한자이고, 특정 단어 제외
    if not (1 <= len(name) <= 4):
        return False

    # 모든 글자가 한자인지 확인
    for char in name:
        code = ord(char)
        is_hanja = (0x4E00 <= code <= 0x9FFF) or (0x3400 <= code <= 0x4DBF)
        if not is_hanja:
            return False

    # 제외 목록
    exclude = ["篇", "編", "序", "例", "部", "註", "曰", "云", "法", "式", "品", "卷", "章"]
    if name in exclude:
        return False

    return True


def deduplicate(herbs: list) -> list:
    """중복 제거"""
    seen = set()
    unique = []
    for herb in herbs:
        name = herb.get("name_hanja")
        if name not in seen:
            seen.add(name)
            unique.append(herb)
    return unique


def main():
    herbs = []

    print("동의보감에서 본초 정보 추출 중...")

    with open(DONGEUIBOGAM_FILE, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            if line_num % 2000 == 0:
                print(f"  {line_num}항목 처리... ({len(herbs)}종)", end="\r", flush=True)

            try:
                entry = json.loads(line)
                herb = extract_herb_info(entry)
                if herb:
                    herbs.append(herb)
            except:
                continue

    # 중복 제거
    herbs = deduplicate(herbs)

    print(f"\n총 {len(herbs)}종 추출 완료")

    # 기존 데이터와 병합
    existing = []
    if Path(OUTPUT_HERBAL).exists():
        with open(OUTPUT_HERBAL, "r", encoding="utf-8") as f:
            existing = json.load(f)

    existing_names = {h.get("name_hanja") for h in existing}
    merged = existing.copy()

    for herb in herbs:
        if herb.get("name_hanja") not in existing_names:
            merged.append(herb)

    # JSON 저장
    with open(OUTPUT_HERBAL, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    print(f"✓ {len(merged)}종 저장: {OUTPUT_HERBAL}")
    print()
    print("다음 단계:")
    print("  python3 scripts/load_herbal.py")


if __name__ == "__main__":
    main()
