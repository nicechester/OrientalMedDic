"""
방약합편 증상-처방 매핑 추출
Pages 39~156 (index 38~155) of 방약합편 상.pdf
"""
import json
import re
from pathlib import Path
import fitz

PDF_PATH = Path.home() / "Desktop" / "방약합편 상.pdf"
OUTPUT_PATH = Path(__file__).parent.parent / "data" / "bangyak_symptom_formula.json"

# 색인 페이지 범위
START_PAGE = 38  # 0-indexed
END_PAGE = 156


def has_cjk(s):
    return any(0x4E00 <= ord(c) <= 0x9FFF or 0x3400 <= ord(c) <= 0x4DBF for c in s)


def is_page_footer(line):
    """페이지 하단 번호/제목 라인"""
    stripped = line.strip()
    if stripped.isdigit():
        return True
    # "풍 風", "대변 大便" 같은 페이지 하단 제목 (한글+한자 조합)
    if len(stripped) < 10 and ' ' in stripped and has_cjk(stripped):
        return True
    return False


def extract_entries(pdf):
    entries = []
    current_category = ""

    for page_idx in range(START_PAGE, END_PAGE):
        text = pdf[page_idx].get_text()
        if not text:
            continue

        lines = text.strip().split('\n')

        # 줄바꿈으로 끊긴 것 합치기
        merged = []
        for line in lines:
            if is_page_footer(line):
                continue
            # 이전 줄이 ：를 포함하고 현재 줄이 ：를 미포함이면 이어붙이기
            if merged and '：' not in line and not line.startswith('○'):
                # 번호 패턴 (上001, 中002, 下003, 상001, 중002, 하003)
                if re.match(r'^[上中下상중하]\d{3}', line.strip()):
                    merged[-1] += line
                    continue
                # 이전 줄이 쉼표로 끝나거나, 현재 줄이 쉼표로 시작
                if merged[-1].rstrip().endswith(',') or line.strip().startswith(','):
                    merged[-1] += line
                    continue
            merged.append(line)

        for line in merged:
            line = line.strip()
            if not line or is_page_footer(line):
                continue

            # 카테고리 (한자만 있는 짧은 줄: 風, 寒, 暑 등)
            if len(line) <= 4 and has_cjk(line) and '：' not in line:
                current_category = line
                continue
            # 한글만 카테고리 (풍, 한, 서 등)
            if len(line) <= 4 and not has_cjk(line) and '：' not in line:
                continue

            # 증상 ： 처방 패턴
            if '：' not in line:
                continue

            parts = line.split('：', 1)
            if len(parts) != 2:
                continue

            symptom = parts[0].strip()
            formulas_str = parts[1].strip()

            # 처방 파싱: "처방명 위치, 처방명 위치, ..."
            formula_list = []
            # 한자 줄인지 한글 줄인지 판별
            is_hanja_line = has_cjk(symptom)

            for item in re.split(r',\s*', formulas_str):
                item = item.strip()
                if not item:
                    continue
                # 위치 번호 추출: "中001" 또는 "中" (숫자 없음)
                loc_match = re.search(r'[上中下상중하]\d*', item)
                loc = loc_match.group() if loc_match else ""
                name = re.sub(r'\s*[上中下상중하]\d*.*', '', item).strip()
                # 《》출전 제거
                name = re.sub(r'[《》\[\]].*', '', name).strip()
                if name:
                    formula_list.append({"name": name, "location": loc})

            if formula_list:
                entries.append({
                    "category": current_category,
                    "symptom": symptom,
                    "formulas": formula_list,
                    "is_hanja": is_hanja_line,
                    "page": page_idx + 1,
                })

    return entries


def pair_entries(entries):
    """한자 줄과 한글 줄을 짝지어 통합"""
    paired = []
    i = 0
    while i < len(entries):
        entry = entries[i]
        if entry["is_hanja"] and i + 1 < len(entries) and not entries[i + 1]["is_hanja"]:
            # 한자+한글 쌍
            korean = entries[i + 1]
            paired.append({
                "category": entry["category"],
                "symptom_hanja": entry["symptom"],
                "symptom_korean": korean["symptom"],
                "formulas_hanja": entry["formulas"],
                "formulas_korean": korean["formulas"],
                "page": entry["page"],
            })
            i += 2
        else:
            # 짝이 안 맞는 경우
            if entry["is_hanja"]:
                paired.append({
                    "category": entry["category"],
                    "symptom_hanja": entry["symptom"],
                    "symptom_korean": "",
                    "formulas_hanja": entry["formulas"],
                    "formulas_korean": [],
                    "page": entry["page"],
                })
            else:
                paired.append({
                    "category": entry["category"],
                    "symptom_hanja": "",
                    "symptom_korean": entry["symptom"],
                    "formulas_hanja": [],
                    "formulas_korean": entry["formulas"],
                    "page": entry["page"],
                })
            i += 1

    return paired


def main():
    pdf = fitz.open(str(PDF_PATH))
    print(f"PDF loaded: {pdf.page_count} pages")

    entries = extract_entries(pdf)
    print(f"Raw entries: {len(entries)}")

    paired = pair_entries(entries)
    print(f"Paired entries: {len(paired)}")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(paired, f, ensure_ascii=False, indent=2)

    print(f"Saved to: {OUTPUT_PATH}")

    # 샘플 출력
    for entry in paired[:5]:
        print(f"\n[{entry['category']}] {entry['symptom_hanja']}")
        print(f"  → {entry['symptom_korean']}")
        for f in entry['formulas_hanja'][:3]:
            print(f"    - {f['name']} ({f['location']})")


if __name__ == "__main__":
    main()
