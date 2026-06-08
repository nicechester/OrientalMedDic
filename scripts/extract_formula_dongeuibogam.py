#!/usr/bin/env python3
"""
동의보감 JSONL에서 처방(방제) 정보 추출
"""

import json
import re
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path(__file__).parent.parent / "data"
DONGEUIBOGAM_FILE = DATA_DIR / "dongeuibogam_raw.jsonl"
OUTPUT_FORMULA = DATA_DIR / "formula_dongeuibogam.json"


def extract_formula_info(entry: dict) -> dict:
    """항목에서 처방 정보 추출"""
    original = entry.get("original", "")
    korean = entry.get("korean", "")

    # 패턴 1: "~~~湯", "~~~散", "~~~丸", "~~~膏" (제목)
    match = re.match(r"^([一-鿿]{2,6})(湯|散|丸|膏|酒)$", original.strip())
    if match:
        formula_name = match.group(1) + match.group(2)
        return {
            "name_hanja": formula_name,
            "name_korean": korean[:100],
            "source_text": "",
            "composition": "",
            "indication": korean[:300],
        }

    # 패턴 2: 첫 줄이 처방명으로 시작
    first_line = original.split("\n")[0].strip() if "\n" in original else original.strip()
    match = re.match(r"^([一-鿿]{2,6})(湯|散|丸|膏|酒)", first_line)
    if match:
        formula_name = match.group(1) + match.group(2)

        # 구성 정보 추출
        composition = extract_composition(original)

        # 주치/효능 추출
        indication = extract_indication(original, korean)

        if is_valid_formula(formula_name):
            return {
                "name_hanja": formula_name,
                "name_korean": korean[:100],
                "source_text": extract_source(original),
                "composition": composition,
                "indication": indication,
            }

    return None


def extract_composition(text: str) -> str:
    """구성 정보 추출"""
    # "組成:", "構成:", "方組:", "藥物:" 등의 패턴 찾기
    patterns = [
        r"[組構]成[：:]\s*([^\n]+)",
        r"方[組成][：:]\s*([^\n]+)",
        r"藥物[：:]\s*([^\n]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()[:200]

    # 약물명 패턴 추출 (숫자 + 글자 조합)
    medicines = re.findall(r"[一-鿿]{1,3}\s+\d+[克錢兩匙]", text)
    if medicines:
        return ", ".join(medicines[:5])

    return ""


def extract_indication(original: str, korean: str) -> str:
    """주치/효능 추출"""
    # "主治:", "效能:", "治:" 등의 패턴
    patterns = [
        r"主治[：:]\s*([^\n]+)",
        r"效能[：:]\s*([^\n]+)",
        r"治[：:]\s*([^\n]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, original)
        if match:
            return match.group(1).strip()[:300]

    # 한국어에서 추출
    return korean[:300]


def extract_source(text: str) -> str:
    """출처 정보 추출"""
    # "《~~~》", "《~~~篇》" 패턴
    match = re.search(r"《([^》]+)》", text)
    if match:
        return match.group(1).strip()

    return ""


def is_valid_formula(name: str) -> bool:
    """유효한 처방명인지 확인"""
    # 2~7글자이고, 끝이 湯/散/丸/膏/酒 등이어야 함
    if not (2 <= len(name) <= 7):
        return False

    valid_endings = ["湯", "散", "丸", "膏", "酒", "露", "汁", "水", "油"]
    if name[-1] not in valid_endings:
        return False

    # 모든 글자가 한자인지 확인
    for char in name:
        code = ord(char)
        is_hanja = (0x4E00 <= code <= 0x9FFF) or (0x3400 <= code <= 0x4DBF)
        if not is_hanja:
            return False

    return True


def deduplicate(formulas: list) -> list:
    """중복 제거"""
    seen = set()
    unique = []
    for formula in formulas:
        name = formula.get("name_hanja")
        if name not in seen:
            seen.add(name)
            unique.append(formula)
    return unique


def main():
    formulas = []

    print("동의보감에서 처방(방제) 정보 추출 중...")

    with open(DONGEUIBOGAM_FILE, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            if line_num % 2000 == 0:
                print(f"  {line_num}항목 처리... ({len(formulas)}수)", end="\r", flush=True)

            try:
                entry = json.loads(line)
                formula = extract_formula_info(entry)
                if formula:
                    formulas.append(formula)
            except:
                continue

    # 중복 제거
    formulas = deduplicate(formulas)

    print(f"\n총 {len(formulas)}수 추출 완료")

    # 기존 데이터와 병합
    existing = []
    if Path(OUTPUT_FORMULA).exists():
        with open(OUTPUT_FORMULA, "r", encoding="utf-8") as f:
            existing = json.load(f)

    existing_names = {f.get("name_hanja") for f in existing}
    merged = existing.copy()

    for formula in formulas:
        if formula.get("name_hanja") not in existing_names:
            merged.append(formula)

    # JSON 저장
    with open(OUTPUT_FORMULA, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    print(f"✓ {len(merged)}수 저장: {OUTPUT_FORMULA}")
    print()
    print("다음 단계:")
    print("  python3 scripts/load_formula.py")


if __name__ == "__main__":
    main()
