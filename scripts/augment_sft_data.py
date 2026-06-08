"""
SFT 학습 데이터 자동 증강 (Augmentation) 스크립트
DB 데이터를 다양한 질문 템플릿과 조합하여 5000건+ 생성

출력: data/sft_train_augmented.jsonl
"""

import json
import sqlite3
import random
from pathlib import Path
from itertools import combinations

DATA_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DATA_DIR / "hanjadic.db"
OUTPUT_PATH = DATA_DIR / "sft_train_augmented.jsonl"

random.seed(42)

SYSTEM = "너는 동양의학(한의학/중의학) 전문 번역가다. 한문 의서 원문을 받으면 독음을 달고, 한의학적 맥락을 살려 한국어로 해설해줘."

# 질문 템플릿들
HERBAL_Q = [
    "다음 한약재를 한의학적으로 해설해줘.\n{name_h}",
    "{name_h}의 성미, 귀경, 효능을 알려줘.",
    "{name_h}은(는) 어떤 약재인가?",
    "한약재 {name_h}에 대해 설명해줘.",
    "다음 한문 의서 구절을 해석해줘.\n{name_h} {nature} {flavor}",
    "{name_h}의 귀경은?",
]

FORMULA_Q = [
    "다음 처방 구성을 보고 어떤 방제인지 해설해줘.\n{comp}",
    "다음 한문 의서 구절을 해석해줘.\n{comp}",
    "{name_h}의 구성과 주치를 설명해줘.",
    "{name_h}은(는) 어떤 처방인가?",
    "다음 처방의 출전과 적응증을 알려줘.\n{name_h}",
]

ACUPOINT_Q = [
    "다음 경혈을 한의학적으로 해설해줘.\n{name_h}",
    "{name_h}({code})의 위치와 주치를 알려줘.",
    "{name_h}은(는) 어떤 혈위인가?",
    "경혈 {name_h}에 대해 설명해줘.",
    "{meridian}의 {name_h} 혈위를 해설해줘.",
]

# 의서 문체 합성 템플릿
SENTENCE_TEMPLATES = [
    # 치법 문장
    ("{herb1} {herb2} 合用 治{indication}", 
     "[독음] {herb1_k} {herb2_k} 합용 치{indication_k}\n\n[한의학적 해설]\n{herb1}({herb1_k})과 {herb2}({herb2_k})를 함께 사용하여 {indication_desc}을(를) 치료한다. {herb1_k}은 {eff1}하고, {herb2_k}은 {eff2}하여 상호 협력하는 배합이다."),
    # 귀경 문장
    ("{herb1} 入{meridian}經",
     "[독음] {herb1_k} 입{meridian_k}경\n\n[한의학적 해설]\n{herb1}({herb1_k})은 {meridian}경에 들어간다(歸經)는 뜻이다. 즉 {herb1_k}의 약효가 {meridian_k}에 해당하는 장부에 주로 작용함을 의미한다."),
    # 처방 적응증
    ("{formula} 主治 {indication}",
     "[독음] {formula_k} 주치 {indication_k}\n\n[한의학적 해설]\n{formula}({formula_k})의 주된 치료 대상(主治)은 {indication_desc}이다."),
    # 침구 배혈
    ("取{point1} {point2} 治{indication}",
     "[독음] 취{point1_k} {point2_k} 치{indication_k}\n\n[한의학적 해설]\n{point1}({point1_k}, {code1})과 {point2}({point2_k}, {code2})를 취혈하여 {indication_desc}을(를) 치료한다. {point1_k}은 {prop1}이고, {point2_k}은 {prop2}이다."),
    # 보사법
    ("{point1} 用補法 {point2} 用瀉法",
     "[독음] {point1_k} 용보법 {point2_k} 용사법\n\n[한의학적 해설]\n{point1}({point1_k})에는 보법(補法)을 쓰고, {point2}({point2_k})에는 사법(瀉法)을 쓴다. 보법은 정기를 보하는 수기법이고, 사법은 사기를 제거하는 수기법이다."),
]

MERIDIAN_KR = {
    "脾": "비", "肺": "폐", "心": "심", "肝": "간", "腎": "신",
    "胃": "위", "大腸": "대장", "小腸": "소장", "膀胱": "방광",
    "膽": "담", "三焦": "삼초", "心包": "심포",
}

INDICATION_MAP = {
    "頭痛": ("두통", "머리가 아픈 증상"),
    "腰痛": ("요통", "허리가 아픈 증상"),
    "咳嗽": ("해수", "기침하는 증상"),
    "失眠": ("실면", "잠을 이루지 못하는 증상"),
    "腹痛": ("복통", "배가 아픈 증상"),
    "泄瀉": ("설사", "대변이 묽은 증상"),
    "嘔吐": ("구토", "토하는 증상"),
    "眩暈": ("현훈", "어지러운 증상"),
    "月經不調": ("월경불조", "월경이 고르지 못한 증상"),
    "水腫": ("수종", "몸이 붓는 증상"),
    "便秘": ("변비", "대변이 통하지 않는 증상"),
    "心悸": ("심계", "가슴이 두근거리는 증상"),
    "胸痛": ("흉통", "가슴이 아픈 증상"),
    "喘息": ("천식", "숨이 가쁜 증상"),
    "耳鳴": ("이명", "귀에서 소리가 나는 증상"),
    "目赤": ("목적", "눈이 충혈되는 증상"),
    "鼻塞": ("비색", "코가 막히는 증상"),
    "咽痛": ("인통", "목이 아픈 증상"),
    "不孕": ("불임", "임신이 되지 않는 증상"),
    "遺精": ("유정", "정액이 저절로 나오는 증상"),
}


def load_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT name_hanja, name_korean, nature, flavor, meridian_tropism, efficacy FROM herbal")
    herbs = c.fetchall()

    c.execute("SELECT name_hanja, name_korean, source_text, composition, indication FROM formula")
    formulas = c.fetchall()

    c.execute("SELECT name_hanja, name_korean, meridian, code, location, properties, indication FROM acupuncture WHERE category='혈위' AND code != ''")
    points = c.fetchall()

    conn.close()
    return herbs, formulas, points


def make_msg(user_content, assistant_content):
    return {
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": assistant_content},
        ]
    }


def gen_herbal_variations(herbs):
    """본초 데이터 질문 변형"""
    samples = []
    for h in herbs:
        name_h, name_k, nature, flavor, meridian, efficacy = h
        answer = (
            f"[독음] {name_k}\n\n"
            f"[한의학적 해설]\n"
            f"- 성미(性味): {nature}, {flavor}\n"
            f"- 귀경(歸經): {meridian}\n"
            f"- 효능: {efficacy}"
        )
        for tmpl in HERBAL_Q:
            q = tmpl.format(name_h=name_h, nature=nature, flavor=flavor)
            samples.append(make_msg(q, answer))
    return samples


def gen_formula_variations(formulas):
    """방제 데이터 질문 변형"""
    samples = []
    for f in formulas:
        name_h, name_k, source, comp, indication = f
        answer = (
            f"[처방명] {name_h}({name_k})\n"
            f"[출전] {source}\n\n"
            f"[한의학적 해설]\n"
            f"- 구성: {comp}\n"
            f"- 주치: {indication}"
        )
        for tmpl in FORMULA_Q:
            q = tmpl.format(name_h=name_h, name_k=name_k, comp=comp)
            samples.append(make_msg(q, answer))
    return samples


def gen_acupoint_variations(points):
    """경혈 데이터 질문 변형"""
    samples = []
    for p in points:
        name_h, name_k, meridian, code, location, properties, indication = p
        answer = (
            f"[독음] {name_k} ({code})\n"
            f"[소속경맥] {meridian}\n\n"
            f"[한의학적 해설]\n"
            f"- 위치: {location}\n"
            f"- 특성: {properties}\n"
            f"- 주치: {indication}"
        )
        for tmpl in ACUPOINT_Q:
            q = tmpl.format(name_h=name_h, name_k=name_k, code=code, meridian=meridian)
            samples.append(make_msg(q, answer))
    return samples


def gen_synthetic_sentences(herbs, formulas, points):
    """의서 문체 합성 문장 생성"""
    samples = []
    indications = list(INDICATION_MAP.keys())

    # 약재 조합 문장
    herb_pairs = list(combinations(range(len(herbs)), 2))
    random.shuffle(herb_pairs)
    for i, j in herb_pairs[:300]:
        h1 = herbs[i]
        h2 = herbs[j]
        ind = random.choice(indications)
        ind_k, ind_desc = INDICATION_MAP[ind]

        # 첫 번째 귀경 추출
        m1 = h1[4].split()[0] if h1[4] else "脾"
        m1_k = MERIDIAN_KR.get(m1, m1)

        eff1 = h1[5].split(",")[0].strip() if h1[5] else ""
        eff2 = h2[5].split(",")[0].strip() if h2[5] else ""

        input_text = f"{h1[0]} {h2[0]} 合用 治{ind}"
        output_text = (
            f"[독음] {h1[1]} {h2[1]} 합용 치{ind_k}\n\n"
            f"[한의학적 해설]\n"
            f"{h1[0]}({h1[1]})과 {h2[0]}({h2[1]})를 함께 사용하여 "
            f"{ind_desc}을(를) 치료한다. {h1[1]}은 {eff1}하고, "
            f"{h2[1]}은 {eff2}하여 상호 협력하는 배합이다."
        )
        samples.append(make_msg("다음 한문 의서 구절을 해석해줘.\n" + input_text, output_text))

    # 귀경 문장
    for h in herbs:
        meridians = h[4].split() if h[4] else []
        for m in meridians[:2]:
            m_k = MERIDIAN_KR.get(m, m)
            input_text = f"{h[0]} 入{m}經"
            output_text = (
                f"[독음] {h[1]} 입{m_k}경\n\n"
                f"[한의학적 해설]\n"
                f"{h[0]}({h[1]})은 {m}경에 들어간다(歸經)는 뜻이다. "
                f"즉 {h[1]}의 약효가 {m_k}에 해당하는 장부에 주로 작용함을 의미한다."
            )
            samples.append(make_msg("다음 한문 의서 구절을 해석해줘.\n" + input_text, output_text))

    # 처방 주치 문장
    for f in formulas:
        name_h, name_k, source, comp, indication = f
        # 주치에서 키워드 추출
        ind_short = indication[:10] if indication else ""
        input_text = f"{name_h} 主治 {ind_short}"
        output_text = (
            f"[독음] {name_k} 주치 {ind_short}\n\n"
            f"[한의학적 해설]\n"
            f"{name_h}({name_k})의 주된 치료 대상(主治)은 {indication}이다. "
            f"출전은 《{source}》이다."
        )
        samples.append(make_msg("다음 한문 의서 구절을 해석해줘.\n" + input_text, output_text))

    # 침구 배혈 문장
    point_pairs = list(combinations(range(min(50, len(points))), 2))
    random.shuffle(point_pairs)
    for i, j in point_pairs[:400]:
        p1 = points[i]
        p2 = points[j]
        ind = random.choice(indications)
        ind_k, ind_desc = INDICATION_MAP[ind]

        input_text = f"取{p1[0]} {p2[0]} 治{ind}"
        output_text = (
            f"[독음] 취{p1[1]} {p2[1]} 치{ind_k}\n\n"
            f"[한의학적 해설]\n"
            f"{p1[0]}({p1[1]}, {p1[3]})과 {p2[0]}({p2[1]}, {p2[3]})를 취혈하여 "
            f"{ind_desc}을(를) 치료한다. "
            f"{p1[1]}은 {p1[2]}의 혈위로 {p1[5] if p1[5] else '상용혈'}이고, "
            f"{p2[1]}은 {p2[2]}의 혈위로 {p2[5] if p2[5] else '상용혈'}이다."
        )
        samples.append(make_msg("다음 한문 의서 구절을 해석해줘.\n" + input_text, output_text))

    # 보사법 문장
    for i, j in point_pairs[:100]:
        p1 = points[i]
        p2 = points[j]
        input_text = f"{p1[0]} 用補法 {p2[0]} 用瀉法"
        output_text = (
            f"[독음] {p1[1]} 용보법 {p2[1]} 용사법\n\n"
            f"[한의학적 해설]\n"
            f"{p1[0]}({p1[1]})에는 보법(補法)을 쓰고, {p2[0]}({p2[1]})에는 사법(瀉法)을 쓴다. "
            f"보법은 정기를 보하는 수기법이고, 사법은 사기를 제거하는 수기법이다."
        )
        samples.append(make_msg("다음 한문 의서 구절을 해석해줘.\n" + input_text, output_text))

    return samples


def main():
    herbs, formulas, points = load_db()
    all_samples = []

    s1 = gen_herbal_variations(herbs)
    print(f"본초 변형: {len(s1)}건")
    all_samples.extend(s1)

    s2 = gen_formula_variations(formulas)
    print(f"방제 변형: {len(s2)}건")
    all_samples.extend(s2)

    s3 = gen_acupoint_variations(points)
    print(f"경혈 변형: {len(s3)}건")
    all_samples.extend(s3)

    s4 = gen_synthetic_sentences(herbs, formulas, points)
    print(f"합성 문장: {len(s4)}건")
    all_samples.extend(s4)

    # 셔플
    random.shuffle(all_samples)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        for sample in all_samples:
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")

    print(f"\n총 {len(all_samples)}건 → {OUTPUT_PATH}")
    print(f"파일 크기: {OUTPUT_PATH.stat().st_size / 1024 / 1024:.2f}MB")


if __name__ == "__main__":
    main()
