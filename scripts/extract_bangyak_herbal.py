"""
방약합편 하권 본초(약재) 추출
Pages 70~444 of 방약합편 하.pdf
"""
import json
import re
from pathlib import Path
import fitz

PDF_PATH = Path.home() / "Desktop" / "방약합편 하.pdf"
OUTPUT_PATH = Path(__file__).parent.parent / "data" / "bangyak_herbal.json"

START_PAGE = 69  # 0-indexed (page 70)
END_PAGE = 444


def has_cjk(s):
    return any(0x4E00 <= ord(c) <= 0x9FFF or 0x3400 <= ord(c) <= 0x4DBF for c in s)


def has_korean(s):
    return any(0xAC00 <= ord(c) <= 0xD7A3 for c in s)


def is_page_footer(line):
    stripped = line.strip()
    if stripped.isdigit():
        return True
    if "種" in stripped and ("산" in stripped or "山" in stripped):
        return True
    return False


def parse_hanja_name(line):
    """한자 약재명 파싱 (별칭 분리)"""
    line = line.strip()
    # 공백으로 한자들을 분리
    parts = [p.strip() for p in line.split() if p.strip() and has_cjk(p)]
    return " ".join(parts) if parts else line


def parse_korean_name(line):
    """한글 약재명 파싱 (별칭 분리)"""
    line = line.strip()
    # 마침표 제거
    line = line.rstrip('.')
    return line


def is_herbal_hanja_name(line):
    """약재 한자명인지 판별"""
    line = line.strip()
    if not line or len(line) > 20:
        return False
    if "○" in line or is_page_footer(line):
        return False

    # "種" 포함: 카테고리이지 약재명 아님
    if "種" in line:
        return False

    # 구두점이 있으면 안 됨 (설명일 가능성)
    if any(c in line for c in ['，', '。', ',', '.', ':', '：', '；', '!', '！']):
        return False

    # 한자만으로 구성되고 공백 포함 가능
    parts = [p for p in line.split() if p]
    if not parts:
        return False

    # 모든 부분이 한자여야 함
    if not all(has_cjk(p) for p in parts):
        return False

    # 길이: 모든 부분을 합쳤을 때 2-15글자
    total_length = sum(len(p) for p in parts)
    if total_length < 2 or total_length > 15:
        return False

    return True


def is_herbal_korean_name(line):
    """약재 한글명인지 판별"""
    line = line.strip()
    if not line or len(line) > 30:
        return False
    if "○" in line or "種" in line or is_page_footer(line):
        return False
    # 한글을 포함해야 함
    return has_korean(line)


def extract_entries(pdf):
    entries = []
    current_category = ""

    for page_idx in range(START_PAGE, END_PAGE):
        text = pdf[page_idx].get_text()
        if not text:
            continue

        lines = text.strip().split('\n')

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            if not line or is_page_footer(line):
                i += 1
                continue

            # 카테고리 감지
            if ("種" in line or "종" in line) and len(line) < 30 and has_cjk(line):
                match = re.search(r'([一-龥]{2,})', line)
                if match:
                    current_category = match.group(1)
                i += 1
                continue

            # 약재명 감지: 현재 줄이 한자명, 다음 줄이 한글명
            if is_herbal_hanja_name(line) and i + 1 < len(lines):
                next_line = lines[i + 1].strip()

                if is_herbal_korean_name(next_line):
                    herbal_hanja = parse_hanja_name(line)
                    herbal_korean = parse_korean_name(next_line)
                    i += 2

                    # 한문 설명 수집
                    description_hanja = []
                    while i < len(lines):
                        curr = lines[i].strip()
                        if not curr or is_page_footer(curr):
                            i += 1
                            break

                        if has_cjk(curr) and not curr.startswith('○') and "種" not in curr and len(curr) < 200:
                            if is_herbal_hanja_name(curr):
                                break
                            description_hanja.append(curr)
                            i += 1
                        else:
                            break

                    # 한글 설명 수집
                    description_korean = []
                    while i < len(lines):
                        curr = lines[i].strip()
                        if not curr or is_page_footer(curr):
                            i += 1
                            break

                        if has_korean(curr) and not curr.startswith('○') and len(curr) < 200:
                            if is_herbal_hanja_name(curr):
                                break
                            description_korean.append(curr)
                            i += 1
                        else:
                            break

                    # 짧은 용어
                    term = ""
                    if i < len(lines):
                        curr = lines[i].strip()
                        if not curr.startswith('○') and not is_page_footer(curr) and len(curr) <= 15:
                            if not is_herbal_hanja_name(curr) and not is_herbal_korean_name(curr):
                                term = curr.rstrip('.')
                                i += 1

                    # ○로 시작하는 상세 정보
                    details = []
                    while i < len(lines):
                        curr = lines[i].strip()
                        if not curr or is_page_footer(curr):
                            i += 1
                            break
                        if curr.startswith('○'):
                            details.append(curr)
                            i += 1
                        elif is_herbal_hanja_name(curr):
                            break
                        else:
                            i += 1

                    entries.append({
                        "category": current_category,
                        "name_hanja": herbal_hanja,
                        "name_korean": herbal_korean,
                        "description_hanja": " ".join(description_hanja),
                        "description_korean": " ".join(description_korean),
                        "term": term,
                        "details": details,
                        "page": page_idx + 1,
                    })
                    continue

            i += 1

    return entries


def main():
    pdf = fitz.open(str(PDF_PATH))
    print(f"PDF loaded: {pdf.page_count} pages")

    entries = extract_entries(pdf)
    print(f"Extracted entries: {len(entries)}")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)

    print(f"Saved to: {OUTPUT_PATH}")

    # 샘플 출력
    print("\n=== 샘플 (처음 15개) ===")
    for i, entry in enumerate(entries[:15]):
        print(f"\n[{i+1}] [{entry['category']}] {entry['name_hanja']} / {entry['name_korean']}")
        if entry['description_hanja']:
            desc = entry['description_hanja'][:50].replace('\n', ' ')
            print(f"  한문: {desc}...")
        if entry['description_korean']:
            desc = entry['description_korean'][:50].replace('\n', ' ')
            print(f"  한글: {desc}...")
        if entry['term']:
            print(f"  용어: {entry['term']}")
        if entry['details']:
            print(f"  상세: {len(entry['details'])}개")


if __name__ == "__main__":
    main()
