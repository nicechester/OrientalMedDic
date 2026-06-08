"""
국립국어원 한자어 사전 데이터를 hanjadic.db에 적재
"""

import json
import sqlite3
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DATA_DIR / "hanjadic.db"
JSON_PATH = DATA_DIR / "nikl_hanja_words.json"


def load_hanja_words():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS hanja_word (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hanja TEXT NOT NULL,
            reading TEXT NOT NULL,
            meaning TEXT NOT NULL
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_hanja_word_hanja ON hanja_word (hanja)")

    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    rows = [
        (e["hanja"], e["reading"],
         e["meaning"] if isinstance(e["meaning"], str) else " / ".join(e["meaning"]))
        for e in data
    ]

    c.executemany("INSERT INTO hanja_word (hanja, reading, meaning) VALUES (?, ?, ?)", rows)
    conn.commit()
    print(f"한자어 {len(rows)}건 적재 완료")
    conn.close()


if __name__ == "__main__":
    load_hanja_words()
