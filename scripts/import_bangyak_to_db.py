"""
방약합편 본초 데이터를 SQLite DB에 임포트
"""
import json
import sqlite3
import re
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "hanjadic.db"
HERBAL_JSON = Path(__file__).parent.parent / "data" / "bangyak_herbal.json"


def parse_nature_and_flavor(term: str, description_hanja: str) -> tuple[str, str]:
    """
    term과 description_hanja에서 성질(nature)과 맛(flavor) 추출
    예: "辛寒" -> ("寒", "辛")
    """
    # term에서 먼저 추출 (예: "辛寒", "微溫", "平" 등)
    nature_chars = {'溫', '熱', '寒', '涼', '平'}
    flavor_chars = {'甘', '苦', '酸', '鹹', '辛', '淡', '澀'}

    nature = ""
    flavor = ""

    # term에서 찾기
    if term:
        for char in nature_chars:
            if char in term:
                nature = char
                break
        for char in flavor_chars:
            if char in term:
                flavor = char
                break

    # description_hanja에서도 찾기 (term이 없거나 부족한 경우)
    if description_hanja:
        if not nature:
            for char in nature_chars:
                if char in description_hanja:
                    nature = char
                    break
        if not flavor:
            for char in flavor_chars:
                if char in description_hanja:
                    flavor = char
                    break

    return nature, flavor


def parse_meridians(details: list) -> str:
    """
    details에서 귀경(meridian_tropism) 정보 추출
    예: "○腎經本藥, 入足陽明ㆍ手太陰氣分." -> "足陽明 手太陰"
    """
    meridians = []
    meridian_keywords = {
        '手太陰': '수태음폐경',
        '手陽明': '수양명대장경',
        '足陽明': '족양명위경',
        '足太陰': '족태음비경',
        '手少陰': '수소음심경',
        '手太陽': '수태양소장경',
        '足少陽': '족소양담경',
        '足太陽': '족태양방광경',
        '手厥陰': '수궐음심포경',
        '手少陽': '수소양삼초경',
        '足厥陰': '족궐음간경',
        '足少陰': '족소음신경',
    }

    for detail in details:
        for hanja, korean in meridian_keywords.items():
            if hanja in detail:
                if korean not in meridians:
                    meridians.append(korean)

    return ' '.join(meridians) if meridians else ""


def build_efficacy(entry: dict) -> str:
    """
    모든 정보를 종합하여 효능(efficacy) 문자열 작성
    """
    lines = []

    # 한글 설명
    if entry['description_korean']:
        desc = entry['description_korean'].strip()
        lines.append(f"【설명】 {desc}")

    # term (성미)
    if entry['term']:
        lines.append(f"【성미】 {entry['term']}")

    # 상세 정보
    if entry['details']:
        lines.append("【효능】")
        for detail in entry['details'][:5]:  # 처음 5개만
            # ○ 제거하고 정리
            clean = detail.lstrip('○').strip()
            if clean:
                lines.append(f"  · {clean}")
        if len(entry['details']) > 5:
            lines.append(f"  ... 외 {len(entry['details']) - 5}개")

    # 한문 설명 (참고용)
    if entry['description_hanja']:
        lines.append(f"【원문】 {entry['description_hanja']}")

    return '\n'.join(lines) if lines else ""


def main():
    # JSON 데이터 로드
    with open(HERBAL_JSON) as f:
        entries = json.load(f)

    print(f"로드된 본초 데이터: {len(entries)}개\n")

    # DB 연결
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 기존 데이터 확인
    cursor.execute("SELECT COUNT(*) FROM herbal")
    existing_count = cursor.fetchone()[0]
    print(f"기존 DB 본초: {existing_count}개")

    # 새 데이터 추가/업데이트
    added_count = 0
    updated_count = 0
    skipped_count = 0

    for entry in entries:
        name_hanja = entry['name_hanja']
        name_korean = entry['name_korean']

        # 성질과 맛 파싱
        nature, flavor = parse_nature_and_flavor(entry['term'], entry['description_hanja'])

        # 귀경 파싱
        meridian_tropism = parse_meridians(entry['details'])

        # 효능 종합
        efficacy = build_efficacy(entry)

        # 기존 데이터 확인
        cursor.execute("SELECT id FROM herbal WHERE name_hanja = ?", (name_hanja,))
        existing = cursor.fetchone()

        if existing:
            # 업데이트
            cursor.execute("""
                UPDATE herbal
                SET name_korean = ?, nature = ?, flavor = ?,
                    meridian_tropism = ?, efficacy = ?
                WHERE name_hanja = ?
            """, (name_korean, nature, flavor, meridian_tropism, efficacy, name_hanja))
            updated_count += 1
        else:
            # 새 항목 추가
            try:
                cursor.execute("""
                    INSERT INTO herbal
                    (name_hanja, name_korean, nature, flavor, meridian_tropism, efficacy)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (name_hanja, name_korean, nature, flavor, meridian_tropism, efficacy))
                added_count += 1
            except sqlite3.IntegrityError:
                skipped_count += 1

    conn.commit()
    conn.close()

    print(f"\n결과:")
    print(f"  추가: {added_count}개")
    print(f"  업데이트: {updated_count}개")
    print(f"  스킵: {skipped_count}개")
    print(f"  최종 합계: {existing_count + added_count}개")


if __name__ == "__main__":
    main()
