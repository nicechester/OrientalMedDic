"""
데이터 증강 v2: 번역 품질 향상을 위한 증강
- 장문 분할 (긴 원문을 문장 단위로 쪼개기)
- 독음 집중 학습 데이터
- 질문 형식 다양화
- 핵심 패턴 반복 강화

출력: data/sft_augmented_v2.jsonl
"""

import json
import re
import random
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_PATH = DATA_DIR / "sft_augmented_v2.jsonl"

random.seed(42)

SYSTEM = "너는 동양의학(한의학/중의학) 전문 번역가다. 한문 의서 원문을 받으면 독음을 달고, 한의학적 맥락을 살려 한국어로 해설해줘."

USER_TEMPLATES = [
    "다음 한문 의서 구절을 해석해줘.\n{text}",
    "다음 한문을 한의학적 맥락에서 번역해줘.\n{text}",
    "아래 의서 원문의 독음과 해설을 부탁해.\n{text}",
    "이 한문 구절을 해석해줘.\n{text}",
    "{text}\n위 구절을 한국어로 풀이해줘.",
]


def load_raw_pairs():
    """dongeuibogam_raw에서 원문-번역 쌍 로드"""
    pairs = []
    with open(DATA_DIR / "dongeuibogam_raw.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            orig = d["original"].strip()
            kr = d["korean"].strip()
            if orig and kr and len(orig) >= 10:
                # HTML 태그 제거
                orig = re.sub(r"<[^>]+>", "", orig)
                kr = re.sub(r"<[^>]+>", "", kr)
                pairs.append((orig, kr))
    return pairs


def split_sentences(text):
    """한문을 문장 단위로 분할 (마침표/쉼표 기준)"""
    # 句讀 기준 분할
    parts = re.split(r"(?<=[.。])\s*", text)
    if len(parts) <= 1:
        parts = re.split(r"(?<=[,，])\s*", text)
    return [p.strip() for p in parts if p.strip()]


def make_msg(user_content, assistant_content):
    return {
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": assistant_content},
        ]
    }


def gen_sentence_split_samples(pairs):
    """장문을 2~4 문장 단위로 잘라서 부분 번역 샘플 생성"""
    samples = []
    for orig, kr in pairs:
        if len(orig) < 60:
            continue
        # 원문을 . 기준으로 분할
        orig_sents = [s.strip() for s in orig.split(".") if s.strip()]
        kr_sents = [s.strip() for s in kr.split(".") if s.strip()]

        if len(orig_sents) < 3:
            # , 기준으로 분할
            orig_sents = [s.strip() for s in orig.split(",") if s.strip()]
            kr_sents = [s.strip() for s in kr.split(",") if s.strip()]

        if len(orig_sents) < 2:
            continue

        # 2~3 문장씩 묶어서 샘플 생성
        chunk_size = random.choice([2, 3])
        for i in range(0, len(orig_sents) - chunk_size + 1, chunk_size):
            chunk_orig = ", ".join(orig_sents[i:i + chunk_size])
            # 번역은 대응 인덱스가 정확하지 않을 수 있으므로 비율로 추정
            ratio = len(kr)  / max(len(orig), 1)
            chunk_kr_start = int(len(kr) * (i / len(orig_sents)))
            chunk_kr_end = int(len(kr) * ((i + chunk_size) / len(orig_sents)))
            chunk_kr = kr[chunk_kr_start:chunk_kr_end].strip()

            if chunk_orig and chunk_kr and len(chunk_orig) >= 10:
                tmpl = random.choice(USER_TEMPLATES)
                q = tmpl.format(text=chunk_orig)
                a = f"[한의학적 해설]\n{chunk_kr}"
                samples.append(make_msg(q, a))

    return samples


def gen_question_variations(pairs):
    """같은 원문에 대해 다양한 질문 형식으로 변형"""
    samples = []
    # 중간 길이 원문 선택 (20~100자)
    mid_pairs = [(o, k) for o, k in pairs if 20 <= len(o) <= 100]
    random.shuffle(mid_pairs)

    for orig, kr in mid_pairs[:2000]:
        # 2~3개 질문 변형
        templates = random.sample(USER_TEMPLATES, k=min(3, len(USER_TEMPLATES)))
        for tmpl in templates:
            q = tmpl.format(text=orig)
            a = f"[한의학적 해설]\n{kr}"
            samples.append(make_msg(q, a))

    return samples


def gen_reading_focused(pairs):
    """독음 집중 학습: 짧은 구절의 독음만 답하는 샘플"""
    samples = []
    short_pairs = [(o, k) for o, k in pairs if 4 <= len(o) <= 30]
    random.shuffle(short_pairs)

    reading_templates = [
        "다음 한자의 독음을 알려줘.\n{text}",
        "{text}\n위 한자의 한국어 독음은?",
        "독음: {text}",
    ]

    for orig, kr in short_pairs[:1500]:
        tmpl = random.choice(reading_templates)
        q = tmpl.format(text=orig)
        # 번역에서 괄호 안 독음 추출 또는 전체 번역 사용
        a = f"[독음] {kr}"
        samples.append(make_msg(q, a))

    return samples


def gen_key_pattern_reinforcement(pairs):
    """핵심 번역 패턴 강화: 자주 나오는 의학 용어/구문 반복"""
    samples = []

    # 핵심 패턴: 曰 (가로되), 者...也 (...은 ...이다), 故 (그러므로) 등
    patterns = {
        "曰": "~이 말하기를",
        "者": "~은/는",
        "故": "그러므로",
        "則": "~하면",
        "若": "만약",
        "皆": "모두",
        "蓋": "대개",
        "凡": "무릇",
    }

    for orig, kr in pairs:
        if len(orig) < 15 or len(orig) > 150:
            continue
        # 핵심 패턴이 포함된 문장 선별
        for pat in patterns:
            if pat in orig:
                tmpl = random.choice(USER_TEMPLATES[:3])
                q = tmpl.format(text=orig)
                a = f"[한의학적 해설]\n{kr}"
                samples.append(make_msg(q, a))
                break  # 한 문장당 한 번만

    random.shuffle(samples)
    return samples[:3000]


def main():
    pairs = load_raw_pairs()
    print(f"원본 쌍: {len(pairs)}건")

    all_samples = []

    s1 = gen_sentence_split_samples(pairs)
    print(f"문장 분할: {len(s1)}건")
    all_samples.extend(s1)

    s2 = gen_question_variations(pairs)
    print(f"질문 변형: {len(s2)}건")
    all_samples.extend(s2)

    s3 = gen_reading_focused(pairs)
    print(f"독음 집중: {len(s3)}건")
    all_samples.extend(s3)

    s4 = gen_key_pattern_reinforcement(pairs)
    print(f"패턴 강화: {len(s4)}건")
    all_samples.extend(s4)

    random.shuffle(all_samples)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        for sample in all_samples:
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")

    print(f"\n총 {len(all_samples)}건 → {OUTPUT_PATH}")
    print(f"파일 크기: {OUTPUT_PATH.stat().st_size / 1024 / 1024:.2f}MB")


if __name__ == "__main__":
    main()
