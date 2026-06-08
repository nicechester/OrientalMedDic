"""
본초(약재) 시드 데이터를 hanjadic.db에 적재
"""

import json
import sqlite3
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DATA_DIR / "hanjadic.db"
SEED_PATH = DATA_DIR / "herbal_seed.json"


def load_herbal_seed():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    with open(SEED_PATH, "r", encoding="utf-8") as f:
        herbs = json.load(f)

    rows = [
        (h["name_hanja"], h["name_korean"], h["name_pinyin"],
         h["nature"], h["flavor"], h["meridian_tropism"], h["efficacy"])
        for h in herbs
    ]

    c.executemany("""
        INSERT OR IGNORE INTO herbal (name_hanja, name_korean, name_pinyin, nature, flavor, meridian_tropism, efficacy)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, rows)

    conn.commit()
    print(f"본초 {c.rowcount}종 적재 완료 (총 {len(rows)}건)")
    conn.close()


if __name__ == "__main__":
    load_herbal_seed()
