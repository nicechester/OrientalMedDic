#!/usr/bin/env python3
"""
KIOM OASIS PDF 파일을 JSON으로 변환
본초(herbal) 및 처방(formula) 정보 추출
"""

import json
import sys
from pathlib import Path
from typing import List, Dict

try:
    import pdfplumber
except ImportError:
    print("ERROR: pdfplumber 설치 필요")
    print("설치: pip3 install pdfplumber")
    sys.exit(1)

DATA_DIR = Path(__file__).parent.parent / "data"


def parse_herbal_pdf(pdf_path: str) -> List[Dict]:
    """본초 PDF 파싱"""
    herbs = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            print(f"본초 PDF 파싱: {pdf_path}")
            print(f"총 {len(pdf.pages)}쪽")

            for page_num, page in enumerate(pdf.pages, 1):
                print(f"  페이지 {page_num}...", end="", flush=True)

                # 테이블 추출
                tables = page.extract_tables()
                if not tables:
                    text = page.extract_text()
                    print(f" (텍스트 {len(text)} chars)")
                    continue

                for table in tables:
                    for row in table:
                        if not row or all(not cell for cell in row):
                            continue

                        # 테이블 구조에 따라 파싱
                        # 일반적으로: 한문명 | 한글명 | 성질 | 맛 | 귀경 | 효능 등
                        herb = parse_herb_row(row)
                        if herb and herb.get("name_hanja"):
                            herbs.append(herb)

                print(f" OK ({len(herbs)} 종)")

    except Exception as e:
        print(f"ERROR: {e}")
        return []

    return herbs


def parse_formula_pdf(pdf_path: str) -> List[Dict]:
    """처방 PDF 파싱"""
    formulas = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            print(f"처방 PDF 파싱: {pdf_path}")
            print(f"총 {len(pdf.pages)}쪽")

            for page_num, page in enumerate(pdf.pages, 1):
                print(f"  페이지 {page_num}...", end="", flush=True)

                # 테이블 추출
                tables = page.extract_tables()
                if not tables:
                    text = page.extract_text()
                    print(f" (텍스트 {len(text)} chars)")
                    continue

                for table in tables:
                    for row in table:
                        if not row or all(not cell for cell in row):
                            continue

                        # 테이블 구조에 따라 파싱
                        # 일반적으로: 방명 | 한글명 | 출처 | 주요성분 | 주치 등
                        formula = parse_formula_row(row)
                        if formula and formula.get("name_hanja"):
                            formulas.append(formula)

                print(f" OK ({len(formulas)} 수)")

    except Exception as e:
        print(f"ERROR: {e}")
        return []

    return formulas


def parse_herb_row(row: List) -> Dict:
    """본초 행 파싱 (테이블 구조에 맞게 수정 필요)"""
    if len(row) < 2:
        return {}

    # 기본 구조: [한문명, 한글명, 성질, 맛, 귀경, 효능, ...]
    herb = {
        "name_hanja": (row[0] or "").strip(),
        "name_korean": (row[1] or "").strip(),
        "name_pinyin": "",
        "nature": (row[2] or "").strip() if len(row) > 2 else "",
        "flavor": (row[3] or "").strip() if len(row) > 3 else "",
        "meridian_tropism": (row[4] or "").strip() if len(row) > 4 else "",
        "efficacy": (row[5] or "").strip() if len(row) > 5 else "",
    }

    return herb


def parse_formula_row(row: List) -> Dict:
    """처방 행 파싱 (테이블 구조에 맞게 수정 필요)"""
    if len(row) < 2:
        return {}

    # 기본 구조: [방명, 한글명, 출처, 구성, 주치, ...]
    formula = {
        "name_hanja": (row[0] or "").strip(),
        "name_korean": (row[1] or "").strip(),
        "source_text": (row[2] or "").strip() if len(row) > 2 else "",
        "composition": (row[3] or "").strip() if len(row) > 3 else "",
        "indication": (row[4] or "").strip() if len(row) > 4 else "",
    }

    return formula


def deduplicate_and_merge(new_data: List[Dict], existing_file: Path) -> List[Dict]:
    """기존 데이터와 중복 제거 후 병합"""
    existing = []
    if existing_file.exists():
        with open(existing_file, "r", encoding="utf-8") as f:
            existing = json.load(f)

    # 기존 데이터의 name_hanja 수집
    existing_names = {item.get("name_hanja") for item in existing}

    # 새 데이터 중 기존에 없는 것만 추가
    merged = existing.copy()
    for item in new_data:
        if item.get("name_hanja") not in existing_names:
            merged.append(item)
            existing_names.add(item.get("name_hanja"))

    return merged


def main():
    if len(sys.argv) < 2:
        print("사용법:")
        print("  python3 parse_pdf_to_json.py <pdf_파일> [herbal|formula]")
        print()
        print("예시:")
        print("  python3 parse_pdf_to_json.py herbal.pdf herbal")
        print("  python3 parse_pdf_to_json.py formula.pdf formula")
        return

    pdf_path = sys.argv[1]
    pdf_type = sys.argv[2].lower() if len(sys.argv) > 2 else "herbal"

    if not Path(pdf_path).exists():
        print(f"ERROR: 파일 없음 - {pdf_path}")
        return

    if pdf_type == "herbal":
        data = parse_herbal_pdf(pdf_path)
        output_file = DATA_DIR / "herbal_kiom.json"
    elif pdf_type == "formula":
        data = parse_formula_pdf(pdf_path)
        output_file = DATA_DIR / "formula_kiom.json"
    else:
        print(f"ERROR: 유효하지 않은 타입 - {pdf_type}")
        return

    if not data:
        print(f"ERROR: 데이터 추출 실패")
        return

    # 기존 데이터와 병합
    merged = deduplicate_and_merge(data, output_file)

    # JSON 저장
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    print()
    print(f"✓ {pdf_type.upper()} 데이터 {len(merged)}개 저장")
    print(f"  파일: {output_file}")
    print()
    print("다음 단계:")
    if pdf_type == "herbal":
        print("  python3 scripts/load_herbal.py")
    else:
        print("  python3 scripts/load_formula.py")


if __name__ == "__main__":
    main()
