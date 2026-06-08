#!/usr/bin/env python3
"""
동의보감에서 경혈(침구)과 병명(질병) 정보 추출
"""

import json
import re
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path(__file__).parent.parent / "data"
DONGEUIBOGAM_FILE = DATA_DIR / "dongeuibogam_raw.jsonl"
OUTPUT_ACUPOINTS = DATA_DIR / "acupoints_dongeuibogam.json"
OUTPUT_DISEASES = DATA_DIR / "diseases_dongeuibogam.json"


def extract_acupoint_info(entry: dict) -> dict:
    """경혈 정보 추출"""
    original = entry.get("original", "")
    korean = entry.get("korean", "")

    # 패턴 1: "~~~穴" (예: "足三里穴")
    match = re.match(r"^([一-鿿]{2,6})穴", original.strip())
    if match:
        acupoint_name = match.group(1)
        # 경락명 추출 (예: "足")
        meridian = acupoint_name[0] if acupoint_name else ""

        return {
            "name_hanja": acupoint_name + "穴",
            "name_korean": korean[:100],
            "meridian": meridian,
            "code": "",
            "indication": korean[:300],
        }

    # 패턴 2: 경락명 + 경혈명 (예: "手陽明 大腸經 商陽")
    if "穴" in original or "혈" in korean:
        # 제목 형식 확인
        first_line = original.split("\n")[0].strip()
        match = re.match(r"^([一-鿿]{2,6})", first_line)
        if match:
            potential_name = match.group(1)
            if is_likely_acupoint(potential_name, original, korean):
                return {
                    "name_hanja": potential_name,
                    "name_korean": korean[:100],
                    "meridian": potential_name[0] if potential_name else "",
                    "code": "",
                    "indication": korean[:300],
                }

    return None


def extract_disease_info(entry: dict) -> dict:
    """병명(질병) 정보 추출"""
    original = entry.get("original", "")
    korean = entry.get("korean", "")

    # 패턴 1: "~~~病", "~~~症", "~~~疾"
    patterns = [
        r"^([一-鿿]{2,6})病",
        r"^([一-鿿]{2,6})症",
        r"^([一-鿿]{2,6})疾",
    ]

    for pattern in patterns:
        match = re.match(pattern, original.strip())
        if match:
            disease_name = match.group(1)
            suffix = original.strip()[len(disease_name)]
            return {
                "name_hanja": disease_name + suffix,
                "name_korean": korean[:100],
                "category": suffix,  # 病/症/疾
                "symptoms": korean[:300],
                "treatment": "",
            }

    # 패턴 2: 치료 대상으로 나타나는 병명
    # "治~~~" 또는 "主~~~" 패턴
    treatment_patterns = [
        (r"治([一-鿿]{2,5})", "治"),
        (r"主([一-鿿]{2,5})", "主"),
    ]

    for pattern, prefix in treatment_patterns:
        match = re.search(pattern, original)
        if match:
            disease_name = match.group(1)
            if is_likely_disease(disease_name, original, korean):
                return {
                    "name_hanja": disease_name,
                    "name_korean": korean[:100],
                    "category": "病",
                    "symptoms": korean[:300],
                    "treatment": original[:200],
                }

    return None


def is_likely_acupoint(name: str, original: str, korean: str) -> bool:
    """경혈인지 판단"""
    acupoint_keywords = [
        "穴",
        "혈",
        "경맥",
        "경락",
        "주치",
        "位置",
        "針法",
    ]

    for keyword in acupoint_keywords:
        if keyword in original or keyword in korean:
            return True

    return False


def is_likely_disease(name: str, original: str, korean: str) -> bool:
    """질병인지 판단"""
    disease_keywords = [
        "病",
        "症",
        "疾",
        "증상",
        "질병",
        "병",
        "치료",
        "치료법",
        "주치",
    ]

    for keyword in disease_keywords:
        if keyword in original or keyword in korean:
            return True

    return False


def deduplicate(items: list, key: str = "name_hanja") -> list:
    """중복 제거"""
    seen = set()
    unique = []
    for item in items:
        name = item.get(key)
        if name not in seen:
            seen.add(name)
            unique.append(item)
    return unique


def main():
    acupoints = []
    diseases = []

    print("동의보감에서 경혈과 병명 정보 추출 중...")

    with open(DONGEUIBOGAM_FILE, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            if line_num % 2000 == 0:
                print(
                    f"  {line_num}항목 처리... (경혈: {len(acupoints)}, 병명: {len(diseases)})",
                    end="\r",
                    flush=True,
                )

            try:
                entry = json.loads(line)

                # 경혈 추출
                acupoint = extract_acupoint_info(entry)
                if acupoint:
                    acupoints.append(acupoint)

                # 병명 추출
                disease = extract_disease_info(entry)
                if disease:
                    diseases.append(disease)

            except:
                continue

    # 중복 제거
    acupoints = deduplicate(acupoints)
    diseases = deduplicate(diseases)

    print(f"\n경혈: {len(acupoints)}개 추출 완료")
    print(f"병명: {len(diseases)}개 추출 완료")

    # JSON 저장
    with open(OUTPUT_ACUPOINTS, "w", encoding="utf-8") as f:
        json.dump(acupoints, f, ensure_ascii=False, indent=2)

    with open(OUTPUT_DISEASES, "w", encoding="utf-8") as f:
        json.dump(diseases, f, ensure_ascii=False, indent=2)

    print()
    print(f"✓ 경혈 {len(acupoints)}개 저장: {OUTPUT_ACUPOINTS}")
    print(f"✓ 병명 {len(diseases)}개 저장: {OUTPUT_DISEASES}")


if __name__ == "__main__":
    main()
