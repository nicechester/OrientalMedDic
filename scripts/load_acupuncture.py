"""
침구학(경락, 혈위, 침법, 구법, 이론) 시드 데이터를 hanjadic.db에 적재
"""

import json
import sqlite3
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DATA_DIR / "hanjadic.db"
SEED_PATH = DATA_DIR / "acupuncture_seed.json"


def load_acupuncture_seed():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS acupuncture (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            name_hanja TEXT NOT NULL,
            name_korean TEXT,
            description TEXT
        )
    """)

    with open(SEED_PATH, "r", encoding="utf-8") as f:
        items = json.load(f)

    rows = [(i["category"], i["name_hanja"], i["name_korean"], i["description"]) for i in items]

    c.executemany("""
        INSERT OR IGNORE INTO acupuncture (category, name_hanja, name_korean, description)
        VALUES (?, ?, ?, ?)
    """, rows)

    conn.commit()
    print(f"침구학 {c.rowcount}건 적재 완료 (총 {len(rows)}건)")

    # 카테고리별 집계
    c.execute("SELECT category, COUNT(*) FROM acupuncture GROUP BY category")
    for cat, cnt in c.fetchall():
        print(f"  - {cat}: {cnt}건")

    conn.close()


if __name__ == "__main__":
    load_acupuncture_seed()
