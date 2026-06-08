#!/usr/bin/env python3
"""
경혈과 병명 데이터를 데이터베이스에 적재
"""

import json
import sqlite3
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DATA_DIR / "hanjadic.db"

ACUPOINTS_FILES = [
    DATA_DIR / "acupoints_dongeuibogam.json",
    DATA_DIR / "acupoints_part1.json",
    DATA_DIR / "acupoints_part2.json",
    DATA_DIR / "acupoints_part3.json",
    DATA_DIR / "acupoints_part4.json",
    DATA_DIR / "acupoints_part5.json",
    DATA_DIR / "acupoints_part6.json",
]

DISEASES_FILE = DATA_DIR / "diseases_dongeuibogam.json"


def create_tables():
    """테이블 생성"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 경혈 테이블
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS acupuncture (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name_hanja TEXT NOT NULL,
            name_korean TEXT,
            meridian TEXT,
            code TEXT,
            properties TEXT,
            category TEXT,
            indication TEXT
        )
    """
    )

    # 병명 테이블
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS disease (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name_hanja TEXT NOT NULL,
            name_korean TEXT,
            category TEXT,
            symptoms TEXT,
            treatment TEXT
        )
    """
    )

    conn.commit()
    conn.close()
    print("✓ 테이블 생성 완료")


def load_acupoints():
    """경혈 데이터 적재"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 기존 데이터 삭제
    c.execute("DELETE FROM acupuncture")
    conn.commit()

    acupoints = []
    seen = set()

    for file_path in ACUPOINTS_FILES:
        if not file_path.exists():
            continue

        print(f"읽는 중: {file_path.name}...", end=" ", flush=True)

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                count = 0
                for item in data:
                    name = item.get("name_hanja")
                    if name not in seen:
                        seen.add(name)
                        acupoints.append(
                            (
                                name,
                                item.get("name_korean", ""),
                                item.get("meridian", ""),
                                item.get("code", ""),
                                item.get("properties", ""),
                                "혈위",  # category
                                item.get("indication", ""),
                            )
                        )
                        count += 1
                print(f"OK ({count}개)")
        except Exception as e:
            print(f"ERROR: {e}")

    print(f"\n총 {len(acupoints)}개 적재 중...", end=" ", flush=True)

    c.executemany(
        """
        INSERT INTO acupuncture (name_hanja, name_korean, meridian, code, properties, category, indication)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
        acupoints,
    )

    conn.commit()
    print("OK")

    c.execute("SELECT COUNT(*) FROM acupuncture")
    count = c.fetchone()[0]
    print(f"✓ 경혈 {count}개 저장 완료")

    conn.close()


def load_diseases():
    """병명 데이터 적재"""
    if not DISEASES_FILE.exists():
        print(f"⚠️  파일 없음: {DISEASES_FILE}")
        return

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 기존 데이터 삭제
    c.execute("DELETE FROM disease")
    conn.commit()

    print(f"읽는 중: {DISEASES_FILE.name}...", end=" ", flush=True)

    try:
        with open(DISEASES_FILE, "r", encoding="utf-8") as f:
            diseases = json.load(f)
            print(f"OK ({len(diseases)}개)")
    except Exception as e:
        print(f"ERROR: {e}")
        return

    rows = [
        (
            d.get("name_hanja", ""),
            d.get("name_korean", ""),
            d.get("category", ""),
            d.get("symptoms", ""),
            d.get("treatment", ""),
        )
        for d in diseases
    ]

    print(f"적재 중...", end=" ", flush=True)

    c.executemany(
        """
        INSERT INTO disease (name_hanja, name_korean, category, symptoms, treatment)
        VALUES (?, ?, ?, ?, ?)
    """,
        rows,
    )

    conn.commit()
    print("OK")

    c.execute("SELECT COUNT(*) FROM disease")
    count = c.fetchone()[0]
    print(f"✓ 병명 {count}개 저장 완료")

    conn.close()


def main():
    create_tables()
    load_acupoints()
    load_diseases()

    # 최종 확인
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM acupuncture")
    acupoint_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM disease")
    disease_count = c.fetchone()[0]
    conn.close()

    print()
    print("=" * 50)
    print("📊 최종 데이터베이스 상태:")
    print(f"  본초(약재): 100종")
    print(f"  방제(처방): 199수")
    print(f"  경혈(침구): {acupoint_count}개")
    print(f"  병명(질병): {disease_count}개")
    print(f"  한자: 102,998자")
    print("=" * 50)


if __name__ == "__main__":
    main()
