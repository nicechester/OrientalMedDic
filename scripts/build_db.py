"""
한의학 통합 한자 사전 SQLite DB 구축 스크립트
1. UniHan DB 다운로드 (유니코드 공식)
2. 한자 자전 테이블 파싱 및 적재
3. 본초/방제 테이블 스키마 생성 (데이터는 추후 적재)
"""

import sqlite3
import zipfile
import urllib.request
import os
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DATA_DIR / "hanjadic.db"
UNIHAN_URL = "https://unicode.org/Public/UCD/latest/ucd/Unihan.zip"
UNIHAN_ZIP = DATA_DIR / "Unihan.zip"


def download_unihan():
    if UNIHAN_ZIP.exists():
        print("UniHan.zip 이미 존재, 스킵")
        return
    print("UniHan DB 다운로드 중...")
    urllib.request.urlretrieve(UNIHAN_URL, UNIHAN_ZIP)
    print("다운로드 완료")


def parse_unihan_readings(zip_path):
    """UniHan에서 한국어 음독(kKorean), 훈독(kDefinition), 중국어 음(kMandarin) 추출"""
    entries = {}  # codepoint -> {field: value}

    with zipfile.ZipFile(zip_path) as zf:
        for filename in zf.namelist():
            if not filename.endswith(".txt"):
                continue
            with zf.open(filename) as f:
                for line in f:
                    line = line.decode("utf-8").strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split("\t")
                    if len(parts) < 3:
                        continue
                    cp, field, value = parts[0], parts[1], parts[2]
                    if field in ("kKorean", "kHangul", "kDefinition", "kMandarin",
                                 "kJapaneseOn", "kTotalStrokes", "kRSUnicode"):
                        if cp not in entries:
                            entries[cp] = {}
                        entries[cp][field] = value
    return entries


def create_db(entries):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 한자 자전 테이블
    c.execute("""
        CREATE TABLE IF NOT EXISTS hanja (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            character TEXT NOT NULL UNIQUE,
            codepoint TEXT NOT NULL,
            korean_reading TEXT,
            hangul_reading TEXT,
            mandarin TEXT,
            definition TEXT,
            stroke_count INTEGER,
            radical TEXT
        )
    """)

    # 본초(약재) 테이블
    c.execute("""
        CREATE TABLE IF NOT EXISTS herbal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name_hanja TEXT NOT NULL,
            name_korean TEXT,
            name_pinyin TEXT,
            nature TEXT,
            flavor TEXT,
            meridian_tropism TEXT,
            efficacy TEXT
        )
    """)

    # 방제(처방) 테이블
    c.execute("""
        CREATE TABLE IF NOT EXISTS formula (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name_hanja TEXT NOT NULL,
            name_korean TEXT,
            source_text TEXT,
            composition TEXT,
            indication TEXT
        )
    """)

    # 한자 데이터 적재
    rows = []
    for cp_str, fields in entries.items():
        # U+XXXX -> 실제 문자
        cp_int = int(cp_str[2:], 16)
        char = chr(cp_int)
        korean = fields.get("kKorean")
        hangul_raw = fields.get("kHangul")
        mandarin = fields.get("kMandarin")
        definition = fields.get("kDefinition")
        strokes = fields.get("kTotalStrokes")
        radical = fields.get("kRSUnicode")

        # kHangul: "혜:0E" or "부:0N 불:0E" → 첫 번째 한글만 추출
        hangul = None
        if hangul_raw:
            hangul = hangul_raw.split()[0].split(":")[0]

        stroke_int = None
        if strokes:
            stroke_int = int(strokes.split()[0])

        rows.append((char, cp_str, korean, hangul, mandarin, definition, stroke_int, radical))

    c.executemany("""
        INSERT OR IGNORE INTO hanja (character, codepoint, korean_reading, hangul_reading, mandarin, definition, stroke_count, radical)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)

    conn.commit()
    print(f"한자 {len(rows)}자 적재 완료")
    print(f"DB 경로: {DB_PATH}")
    print(f"DB 크기: {DB_PATH.stat().st_size / 1024 / 1024:.1f}MB")
    conn.close()


if __name__ == "__main__":
    download_unihan()
    print("UniHan 파싱 중...")
    entries = parse_unihan_readings(UNIHAN_ZIP)
    print(f"파싱 완료: {len(entries)}자")
    create_db(entries)
