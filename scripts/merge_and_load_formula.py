#!/usr/bin/env python3
"""
모든 처방 파일을 병합하고 데이터베이스에 적재
"""

import json
import sqlite3
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DATA_DIR / "hanjadic.db"
FORMULA_FILES = [
    DATA_DIR / "formula_seed.json",
    DATA_DIR / "formula_dongeuibogam.json",
]


def merge_formulas():
    """모든 처방 파일 병합"""
    formulas = []
    seen = set()

    for file_path in FORMULA_FILES:
        if not file_path.exists():
            print(f"⚠️  파일 없음: {file_path}")
            continue

        print(f"읽는 중: {file_path.name}...", end=" ", flush=True)

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                count = 0
                for formula in data:
                    name = formula.get("name_hanja")
                    if name not in seen:
                        seen.add(name)
                        formulas.append(formula)
                        count += 1
                print(f"OK ({count}수)")
        except Exception as e:
            print(f"ERROR: {e}")

    print(f"\n총 {len(formulas)}수 병합 완료")
    return formulas


def load_to_db(formulas):
    """데이터베이스에 적재"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 기존 테이블 삭제 후 재생성 (모든 데이터 적재하기 위해)
    print("기존 formula 테이블 정리 중...")
    c.execute("DELETE FROM formula")
    conn.commit()

    rows = [
        (
            f.get("name_hanja", ""),
            f.get("name_korean", ""),
            f.get("source_text", ""),
            f.get("composition", ""),
            f.get("indication", ""),
        )
        for f in formulas
    ]

    print(f"{len(rows)}수 적재 중...", end=" ", flush=True)

    c.executemany(
        """
        INSERT INTO formula (name_hanja, name_korean, source_text, composition, indication)
        VALUES (?, ?, ?, ?, ?)
    """,
        rows,
    )

    conn.commit()
    print(f"OK")
    print(f"✓ 방제 {len(rows)}수 적재 완료")

    # 확인
    c.execute("SELECT COUNT(*) FROM formula")
    count = c.fetchone()[0]
    print(f"✓ 데이터베이스 확인: {count}수 저장됨")

    conn.close()


def main():
    formulas = merge_formulas()
    load_to_db(formulas)


if __name__ == "__main__":
    main()
