#!/usr/bin/env python3
import sqlite3

# 데이터베이스 연결
db_path = "/Users/chester.kim/workspace/trashcan/hanjadic/data/hanjadic.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("="*60)
print("OrientalMedDic 데이터베이스 검색 테스트")
print("="*60)

# 테스트 1: 단일 한자 검색
test_char = "구"
print(f"\n[테스트 1] 단일 한자 검색: '{test_char}'")
print("-" * 60)

# Herbal 검색
herbal_sql = "SELECT name_hanja, name_korean, nature, flavor FROM herbal WHERE name_hanja LIKE '%' || ? || '%'"
cursor.execute(herbal_sql, (test_char,))
herbal_results = cursor.fetchall()
print(f"본초(약재) 검색 결과: {len(herbal_results)}건")
for row in herbal_results[:3]:  # 최대 3개만 표시
    print(f"  - {row[0]} ({row[1]}): {row[2]}/{row[3]}")

# Formula 검색
formula_sql = "SELECT name_hanja, name_korean, source_text FROM formula WHERE name_hanja LIKE '%' || ? || '%'"
cursor.execute(formula_sql, (test_char,))
formula_results = cursor.fetchall()
print(f"방제(처방) 검색 결과: {len(formula_results)}건")
for row in formula_results[:3]:
    print(f"  - {row[0]} ({row[1]}): {row[2]}")

# Acupoint 검색 (테이블 미존재)

# 테스트 2: 여러 한자 검색
test_word = "구안와사"
print(f"\n[테스트 2] 단어 검색: '{test_word}'")
print("-" * 60)

# Herbal 검색
cursor.execute(herbal_sql, (test_word,))
herbal_results = cursor.fetchall()
print(f"본초(약재) 검색 결과: {len(herbal_results)}건")
for row in herbal_results:
    print(f"  - {row[0]} ({row[1]}): {row[2]}/{row[3]}")

# Formula 검색
cursor.execute(formula_sql, (test_word,))
formula_results = cursor.fetchall()
print(f"방제(처방) 검색 결과: {len(formula_results)}건")
for row in formula_results:
    print(f"  - {row[0]} ({row[1]}): {row[2]}")


# 테스트 3: 한글 검색도 확인
test_korean = "인삼"
print(f"\n[테스트 3] 한글 검색: '{test_korean}'")
print("-" * 60)

# 한글로 검색할 때는 다른 컬럼 필요
herbal_korean_sql = "SELECT name_hanja, name_korean FROM herbal WHERE name_korean LIKE '%' || ? || '%' LIMIT 5"
cursor.execute(herbal_korean_sql, (test_korean,))
results = cursor.fetchall()
print(f"본초(약재) 검색 결과: {len(results)}건")
for row in results:
    print(f"  - {row[0]} ({row[1]})")

# 테스트 4: 데이터베이스 테이블 확인
print(f"\n[테스트 4] 데이터베이스 테이블 및 행 수")
print("-" * 60)

tables = [
    ("herbal", "SELECT COUNT(*) FROM herbal"),
    ("formula", "SELECT COUNT(*) FROM formula"),
    ("hanja", "SELECT COUNT(*) FROM hanja"),
]

for table_name, count_sql in tables:
    cursor.execute(count_sql)
    count = cursor.fetchone()[0]
    print(f"{table_name}: {count}행")

print("\n" + "="*60)
print("테스트 완료!")
print("="*60)

conn.close()
