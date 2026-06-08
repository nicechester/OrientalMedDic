#!/usr/bin/env python3
"""
동의보감 JSONL에서 본초와 처방 정보 추출
"""

import json
import re
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path(__file__).parent.parent / "data"
DONGEUIBOGAM_FILE = DATA_DIR / "dongeuibogam_raw.jsonl"
OUTPUT_HERBAL = DATA_DIR / "herbal_dongeuibogam.json"
OUTPUT_FORMULA = DATA_DIR / "formula_dongeuibogam.json"


def extract_herbs_and_formulas():
    """동의보감에서 본초와 처방 추출"""

    herbs = defaultdict(dict)  # name_hanja -> details
    formulas = defaultdict(dict)  # name_hanja -> details

    print("동의보감에서 데이터 추출 중...")

    with open(DONGEUIBOGAM_FILE, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            if line_num % 1000 == 0:
                print(f"  {line_num}항목 처리...", end="\r", flush=True)

            try:
                entry = json.loads(line)
            except:
                continue

            original = entry.get("original", "")
            korean = entry.get("korean", "")

            # 본초명 패턴 (예: "人參" "當歸" 등)
            # 보통 제목이나 처음에 나타남
            herb_match = re.search(r"^([一-鿿]{1,4})(?:\s|$|：|:)", original)
            if herb_match:
                herb_name = herb_match.group(1)
                if is_likely_herb(herb_name, original, korean):
                    if herb_name not in herbs:
                        herbs[herb_name] = {
                            "name_hanja": herb_name,
                            "name_korean": "",
                            "efficacy": korean[:200],  # 처음 200자를 효능으로
                            "full_text": original,
                        }

            # 처방명 패턴
            # 보통 처방은 더 긴 한자명을 가짐
            formula_match = re.search(
                r"^([一-鿿]{2,6})湯|^([一-鿿]{2,6})散|^([一-鿿]{2,6})丸",
                original,
            )
            if formula_match:
                formula_name = formula_match.group(1) or formula_match.group(2)
                if is_likely_formula(formula_name, original, korean):
                    if formula_name not in formulas:
                        # 구성 추출
                        composition = extract_composition(original)
                        formulas[formula_name] = {
                            "name_hanja": formula_name,
                            "name_korean": "",
                            "composition": composition,
                            "indication": korean[:200],
                            "full_text": original,
                        }

    print(f"\n본초 {len(herbs)}종 추출")
    print(f"처방 {len(formulas)}수 추출")

    return list(herbs.values()), list(formulas.values())


def is_likely_herb(name: str, original: str, korean: str) -> bool:
    """본초인지 판단"""
    # 한 글자 또는 두 글자 한자이고,
    # 성질, 맛, 귀경, 효능 등의 단어가 포함되어 있으면 본초로 판단

    herb_keywords = ["性", "味", "歸經", "效能", "功效", "主治", "溫", "寒", "熱", "涼", "甘", "苦", "酸", "鹹"]

    for keyword in herb_keywords:
        if keyword in original or keyword in korean:
            return True

    return False


def is_likely_formula(name: str, original: str, korean: str) -> bool:
    """처방인지 판단"""
    # 방명이 "湯", "散", "丸" 등으로 끝나고,
    # 구성, 주치 등의 단어가 포함되어 있으면 처방으로 판단

    formula_keywords = [
        "組成",
        "主治",
        "藥物",
        "材料",
        "製法",
        "用法",
        "方劑",
        "治療",
        "療效",
    ]

    for keyword in formula_keywords:
        if keyword in original or keyword in korean:
            return True

    return False


def extract_composition(text: str) -> str:
    """처방 구성 추출"""
    # "組成" 이후의 텍스트에서 약물 목록 추출
    composition_match = re.search(r"組成[：:]\s*([^\n]+)", text)
    if composition_match:
        return composition_match.group(1).strip()

    # 약물명 패턴 추출 (숫자 + 글자 + 제목)
    medicines = re.findall(r"[一-鿿]{1,3}\s+\d+[克錢兩]", text)
    if medicines:
        return ", ".join(medicines)

    return ""


def merge_with_existing(new_data: list, existing_file: Path) -> list:
    """기존 데이터와 병합"""
    existing = []
    if existing_file.exists():
        with open(existing_file, "r", encoding="utf-8") as f:
            existing = json.load(f)

    # name_hanja로 중복 제거
    existing_names = {item.get("name_hanja") for item in existing}
    merged = existing.copy()

    for item in new_data:
        if item.get("name_hanja") not in existing_names:
            merged.append(item)
            existing_names.add(item.get("name_hanja"))

    return merged


def save_json(data: list, output_file: Path):
    """JSON 저장 (정제)"""
    # 불필요한 필드 제거
    cleaned = []
    for item in data:
        cleaned.append(
            {
                "name_hanja": item.get("name_hanja", ""),
                "name_korean": item.get("name_korean", ""),
                "name_pinyin": item.get("name_pinyin", ""),
                **(
                    {
                        "nature": item.get("nature", ""),
                        "flavor": item.get("flavor", ""),
                        "meridian_tropism": item.get("meridian_tropism", ""),
                        "efficacy": item.get("efficacy", ""),
                    }
                    if "efficacy" in item
                    else {
                        "source_text": item.get("source_text", ""),
                        "composition": item.get("composition", ""),
                        "indication": item.get("indication", ""),
                    }
                ),
            }
        )

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)


def main():
    herbs, formulas = extract_herbs_and_formulas()

    # 기존 데이터와 병합
    herbs = merge_with_existing(herbs, OUTPUT_HERBAL)
    formulas = merge_with_existing(formulas, OUTPUT_FORMULA)

    # 저장
    save_json(herbs, OUTPUT_HERBAL)
    save_json(formulas, OUTPUT_FORMULA)

    print()
    print(f"✓ 본초 {len(herbs)}종 저장: {OUTPUT_HERBAL}")
    print(f"✓ 처방 {len(formulas)}수 저장: {OUTPUT_FORMULA}")
    print()
    print("다음 단계:")
    print("  python3 scripts/load_herbal.py")
    print("  python3 scripts/load_formula.py")


if __name__ == "__main__":
    main()
