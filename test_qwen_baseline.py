"""
Qwen 2.5-0.5B-Instruct 제로샷 한의학 문헌 번역 테스트
M3 Max + MLX 환경용

1) DB에서 용어 검색 (Case A 시뮬레이션)
2) LLM 제로샷 문장 해석 (Case B 시뮬레이션)
"""

import sqlite3
import time
from pathlib import Path

from mlx_lm import load, generate

MODEL_ID = "mlx-community/Qwen2.5-0.5B-Instruct-4bit"
DB_PATH = Path(__file__).parent / "data" / "hanjadic.db"

SYSTEM_PROMPT = "너는 동양의학(한의학/중의학) 전문 번역가다. 한문 의서 원문을 받으면 독음을 달고, 한의학적 맥락을 살려 한국어로 해설해줘."

TEST_CASES = [
    "補氣血 淸濕熱",
    "肝主疏泄 腎主封藏",
    "麻黃三兩 桂枝二兩 甘草一兩 杏仁七十箇",
    "表寒裏熱 頭痛發熱 口渴引飲",
    "氣滯血瘀 不通則痛",
]


def db_lookup(text):
    """DB에서 관련 용어를 검색해 컨텍스트로 제공"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    context_parts = []

    # 본초 검색
    c.execute("SELECT name_hanja, name_korean, nature, flavor, meridian_tropism, efficacy FROM herbal")
    herbs = c.fetchall()
    for h in herbs:
        if h[0] in text:
            context_parts.append(f"[본초] {h[0]}({h[1]}): 성미={h[2]}/{h[3]}, 귀경={h[4]}, 효능={h[5]}")

    # 방제 검색
    c.execute("SELECT name_hanja, name_korean, composition, indication FROM formula")
    formulas = c.fetchall()
    for f in formulas:
        if f[0] in text or all(herb in text for herb in f[2].split()[:2]):
            context_parts.append(f"[방제] {f[0]}({f[1]}): 구성={f[2]}, 주치={f[3]}")

    # 경혈 검색
    c.execute("SELECT name_hanja, name_korean, meridian, properties, indication FROM acupuncture WHERE category='혈위'")
    points = c.fetchall()
    for p in points:
        if p[0] in text:
            context_parts.append(f"[경혈] {p[0]}({p[1]}): {p[2]}, {p[3]}, 주치={p[4]}")

    conn.close()
    return "\n".join(context_parts)


def run_test():
    print(f"모델 로딩: {MODEL_ID}")
    model, tokenizer = load(MODEL_ID)
    print("로딩 완료\n" + "=" * 60)

    for i, text in enumerate(TEST_CASES, 1):
        # DB 컨텍스트 조회
        db_context = db_lookup(text)
        context_msg = f"\n\n[참고 DB 정보]\n{db_context}" if db_context else ""

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"다음 한문 의서 구절을 해석해줘:\n{text}{context_msg}"},
        ]
        prompt = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

        start = time.time()
        response = generate(model, tokenizer, prompt=prompt, max_tokens=512)
        elapsed = time.time() - start

        print(f"\n[테스트 {i}] 입력: {text}")
        if db_context:
            print(f"[DB 히트] {db_context[:100]}..." if len(db_context) > 100 else f"[DB 히트] {db_context}")
        print(f"[출력] ({elapsed:.1f}초)\n{response}")
        print("-" * 60)


if __name__ == "__main__":
    run_test()
