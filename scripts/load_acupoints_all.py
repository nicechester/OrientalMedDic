"""
전체 경혈(361혈) + 기경팔맥 + 특수침법 데이터를 hanjadic.db에 적재
기존 acupuncture 테이블에 meridian, code, location, properties 컬럼 추가
"""

import json
import sqlite3
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DATA_DIR / "hanjadic.db"

PART_FILES = [
    "acupoints_part1.json",
    "acupoints_part2.json",
    "acupoints_part3.json",
    "acupoints_part4.json",
    "acupoints_part5.json",
    "acupoints_part6.json",
]


def rebuild_acupuncture_table():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 기존 테이블 삭제 후 확장된 스키마로 재생성
    c.execute("DROP TABLE IF EXISTS acupuncture")
    c.execute("""
        CREATE TABLE acupuncture (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            meridian TEXT,
            name_hanja TEXT NOT NULL,
            name_korean TEXT,
            code TEXT,
            location TEXT,
            properties TEXT,
            indication TEXT
        )
    """)

    total = 0
    for filename in PART_FILES:
        filepath = DATA_DIR / filename
        with open(filepath, "r", encoding="utf-8") as f:
            items = json.load(f)

        rows = [
            (i["category"], i.get("meridian", ""), i["name_hanja"], i["name_korean"],
             i.get("code", ""), i.get("location", ""), i.get("properties", ""),
             i.get("indication", i.get("description", "")))
            for i in items
        ]

        c.executemany("""
            INSERT INTO acupuncture (category, meridian, name_hanja, name_korean, code, location, properties, indication)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, rows)
        total += len(rows)
        print(f"  {filename}: {len(rows)}건")

    conn.commit()

    # 집계
    print(f"\n총 {total}건 적재 완료")
    c.execute("SELECT category, COUNT(*) FROM acupuncture GROUP BY category ORDER BY COUNT(*) DESC")
    for cat, cnt in c.fetchall():
        print(f"  - {cat}: {cnt}건")

    # 경맥별 혈위 수
    print("\n[경맥별 혈위 수]")
    c.execute("SELECT meridian, COUNT(*) FROM acupuncture WHERE category='혈위' GROUP BY meridian ORDER BY COUNT(*) DESC")
    for mer, cnt in c.fetchall():
        print(f"  {mer}: {cnt}혈")

    conn.close()


if __name__ == "__main__":
    rebuild_acupuncture_table()
