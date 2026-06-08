"""
방제(처방) 시드 데이터를 hanjadic.db에 적재
"""

import json
import sqlite3
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DATA_DIR / "hanjadic.db"
SEED_PATH = DATA_DIR / "formula_seed.json"


def load_formula_seed():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    with open(SEED_PATH, "r", encoding="utf-8") as f:
        formulas = json.load(f)

    rows = [
        (f["name_hanja"], f["name_korean"], f["source_text"],
         f["composition"], f["indication"])
        for f in formulas
    ]

    c.executemany("""
        INSERT OR IGNORE INTO formula (name_hanja, name_korean, source_text, composition, indication)
        VALUES (?, ?, ?, ?, ?)
    """, rows)

    conn.commit()
    print(f"방제 {c.rowcount}수 적재 완료 (총 {len(rows)}건)")
    conn.close()


if __name__ == "__main__":
    load_formula_seed()
