"""
SFT 학습 데이터 가공 스크립트
DB에 있는 본초/방제/침구 데이터 + 수동 의서 병렬 데이터를 
Qwen SFT 포맷(ChatML)으로 변환

출력: data/sft_train.jsonl
"""

import json
import sqlite3
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DATA_DIR / "hanjadic.db"
OUTPUT_PATH = DATA_DIR / "sft_train.jsonl"

SYSTEM = "너는 동양의학(한의학/중의학) 전문 번역가다. 한문 의서 원문을 받으면 독음을 달고, 한의학적 맥락을 살려 한국어로 해설해줘."


def make_chatml(instruction, input_text, output_text):
    """Qwen ChatML 포맷"""
    return {
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"{instruction}\n{input_text}"},
            {"role": "assistant", "content": output_text},
        ]
    }


def generate_herbal_data(conn):
    """본초 데이터 → 약재 해설 학습 데이터"""
    c = conn.cursor()
    c.execute("SELECT name_hanja, name_korean, nature, flavor, meridian_tropism, efficacy FROM herbal")
    samples = []
    for h in c.fetchall():
        name_h, name_k, nature, flavor, meridian, efficacy = h
        input_text = f"{name_h}"
        output_text = (
            f"[독음] {name_k}\n\n"
            f"[한의학적 해설]\n"
            f"- 성미(性味): {nature}, {flavor}\n"
            f"- 귀경(歸經): {meridian}\n"
            f"- 효능: {efficacy}"
        )
        samples.append(make_chatml("다음 한약재를 한의학적으로 해설해줘.", input_text, output_text))
    return samples


def generate_formula_data(conn):
    """방제 데이터 → 처방 해설 학습 데이터"""
    c = conn.cursor()
    c.execute("SELECT name_hanja, name_korean, source_text, composition, indication FROM formula")
    samples = []
    for f in c.fetchall():
        name_h, name_k, source, comp, indication = f
        # 처방 구성 문장을 입력으로
        input_text = comp
        output_text = (
            f"[처방명] {name_h}({name_k})\n"
            f"[출전] {source}\n\n"
            f"[한의학적 해설]\n"
            f"- 구성: {comp}\n"
            f"- 주치: {indication}"
        )
        samples.append(make_chatml("다음 처방 구성을 보고 어떤 방제인지 해설해줘.", input_text, output_text))

        # 처방명 자체를 입력으로
        input_text2 = name_h
        output_text2 = (
            f"[독음] {name_k}\n"
            f"[출전] {source}\n\n"
            f"[한의학적 해설]\n"
            f"- 구성: {comp}\n"
            f"- 주치: {indication}"
        )
        samples.append(make_chatml("다음 한문 의서 구절을 해석해줘.", input_text2, output_text2))
    return samples


def generate_acupoint_data(conn):
    """경혈 데이터 → 혈위 해설 학습 데이터"""
    c = conn.cursor()
    c.execute("SELECT name_hanja, name_korean, meridian, code, location, properties, indication FROM acupuncture WHERE category='혈위'")
    samples = []
    for p in c.fetchall():
        name_h, name_k, meridian, code, location, properties, indication = p
        input_text = name_h
        output_text = (
            f"[독음] {name_k} ({code})\n"
            f"[소속경맥] {meridian}\n\n"
            f"[한의학적 해설]\n"
            f"- 위치: {location}\n"
            f"- 특성: {properties}\n"
            f"- 주치: {indication}"
        )
        samples.append(make_chatml("다음 경혈을 한의학적으로 해설해줘.", input_text, output_text))
    return samples


def generate_sentence_data():
    """수동 의서 문장 병렬 데이터 (핵심 학습 데이터)"""
    samples = [
        make_chatml(
            "다음 한문 의서 구절을 해석해줘.",
            "補氣血 淸濕熱",
            "[독음] 보기혈 청습열\n\n[한의학적 해설]\n기(氣)와 혈(血)을 보하고, 습열(濕熱)을 맑게 제거한다는 치법 원칙이다. 기혈이 허한 상태에서 습열이 겸한 병증에 적용한다."
        ),
        make_chatml(
            "다음 한문 의서 구절을 해석해줘.",
            "肝主疏泄 腎主封藏",
            "[독음] 간주소설 신주봉장\n\n[한의학적 해설]\n간(肝)은 소설(疏泄: 기의 소통과 발산)을 주관하고, 신(腎)은 봉장(封藏: 정기를 저장하고 밖으로 새지 않게 함)을 주관한다. 간과 신의 핵심 생리기능을 대비하여 설명한 장상학(臟象學)의 기본 명제이다."
        ),
        make_chatml(
            "다음 한문 의서 구절을 해석해줘.",
            "麻黃三兩 桂枝二兩 甘草一兩 杏仁七十箇",
            "[독음] 마황삼량 계지이량 감초일량 행인칠십개\n\n[한의학적 해설]\n이것은 《상한론》 마황탕(麻黃湯)의 처방 구성이다. 마황이 군약으로 발한해표(發汗解表)하고, 계지가 온경산한(溫經散寒)을 돕고, 행인이 선폐평천(宣肺平喘)하며, 감초가 제약을 조화시킨다. 외감풍한표실증(外感風寒表實證)에 사용한다."
        ),
        make_chatml(
            "다음 한문 의서 구절을 해석해줘.",
            "表寒裏熱 頭痛發熱 口渴引飲",
            "[독음] 표한리열 두통발열 구갈인음\n\n[한의학적 해설]\n표(表)에는 한사(寒邪)가 있고 리(裏)에는 열이 있는 표한리열(表寒裏熱) 병증이다. 두통과 발열은 표증(表證)의 증상이고, 입이 마르고 물을 당기는 것(口渴引飲)은 리열(裏熱)의 증상이다. 대청룡탕(大靑龍湯)이나 석고(石膏)를 가미한 처방을 고려한다."
        ),
        make_chatml(
            "다음 한문 의서 구절을 해석해줘.",
            "氣滯血瘀 不通則痛",
            "[독음] 기체혈어 불통즉통\n\n[한의학적 해설]\n기(氣)가 막히면 혈(血)이 어체(瘀滯)되고, 통하지 않으면 곧 통증이 생긴다(不通則痛)는 한의학 병리의 핵심 원리이다. 기체혈어(氣滯血瘀)는 통증의 가장 흔한 병기(病機)이며, 치료는 행기활혈(行氣活血)·거어지통(祛瘀止痛)을 원칙으로 한다."
        ),
        make_chatml(
            "다음 한문 의서 구절을 해석해줘.",
            "脾主運化 胃主受納",
            "[독음] 비주운화 위주수납\n\n[한의학적 해설]\n비(脾)는 운화(運化: 음식물의 소화흡수와 수액 운반)를 주관하고, 위(胃)는 수납(受納: 음식물을 받아들임)을 주관한다. 비위(脾胃)는 후천지본(後天之本)으로 기혈생화의 원천이다."
        ),
        make_chatml(
            "다음 한문 의서 구절을 해석해줘.",
            "心主血脈 肺主氣",
            "[독음] 심주혈맥 폐주기\n\n[한의학적 해설]\n심(心)은 혈맥(血脈)을 주관하여 혈액 순환을 추동하고, 폐(肺)는 기(氣)를 주관하여 호흡과 전신의 기기(氣機) 조절을 담당한다. 기와 혈은 상호의존 관계로, 기가 혈을 추동하고 혈이 기를 실어 나른다(氣爲血之帥, 血爲氣之母)."
        ),
        make_chatml(
            "다음 한문 의서 구절을 해석해줘.",
            "陰虛則熱 陽虛則寒",
            "[독음] 음허즉열 양허즉한\n\n[한의학적 해설]\n음(陰)이 허하면 허열(虛熱)이 생기고, 양(陽)이 허하면 허한(虛寒)이 생긴다. 이는 음양학설의 병리 원칙으로, 음허화왕(陰虛火旺)에는 자음강화(滋陰降火)를, 양허한성(陽虛寒盛)에는 온양산한(溫陽散寒)을 치법으로 삼는다."
        ),
        make_chatml(
            "다음 한문 의서 구절을 해석해줘.",
            "風爲百病之長",
            "[독음] 풍위백병지장\n\n[한의학적 해설]\n풍사(風邪)는 백병(百病)의 으뜸(長)이라는 뜻이다. 풍은 육음(六淫) 중 가장 활동적이며, 다른 사기(邪氣)와 쉽게 결합하여(풍한·풍열·풍습 등) 질병을 일으키므로 '백병지장'이라 한다."
        ),
        make_chatml(
            "다음 한문 의서 구절을 해석해줘.",
            "急則治其標 緩則治其本",
            "[독음] 급즉치기표 완즉치기본\n\n[한의학적 해설]\n급한 경우에는 표증(標: 겉으로 드러난 증상)을 먼저 치료하고, 완만한 경우에는 본(本: 근본 원인)을 치료한다. 이는 한의학 치료의 표본완급(標本緩急) 원칙으로, 출혈·고열 등 급증에는 대증치료를 우선하고, 안정기에는 근본 병인을 다스린다."
        ),
        make_chatml(
            "다음 한문 의서 구절을 해석해줘.",
            "寒者熱之 熱者寒之",
            "[독음] 한자열지 열자한지\n\n[한의학적 해설]\n한증(寒證)에는 열성 약물로 치료하고(溫法), 열증(熱證)에는 한량한 약물로 치료한다(清法). 이는 《황제내경》에 나오는 정치법(正治法)의 기본 원칙이다."
        ),
        make_chatml(
            "다음 한문 의서 구절을 해석해줘.",
            "取足三里 合谷 內關",
            "[독음] 취족삼리 합곡 내관\n\n[한의학적 해설]\n족삼리(ST36)·합곡(LI4)·내관(PC6) 세 혈위를 취혈한다는 뜻이다. 족삼리는 건비화위(健脾和胃)의 요혈, 합곡은 두면부 질환과 통증의 요혈, 내관은 영심안신(寧心安神)·화위강역(和胃降逆)의 요혈이다. 위장 질환이나 구토에 자주 배합하는 조합이다."
        ),
        make_chatml(
            "다음 한문 의서 구절을 해석해줘.",
            "針刺百會 四神聰 治頭痛眩暈",
            "[독음] 침자백회 사신총 치두통현훈\n\n[한의학적 해설]\n백회(GV20)와 사신총(경외기혈)에 침을 놓아 두통과 현훈(어지러움)을 치료한다는 뜻이다. 백회는 독맥의 제양지회(諸陽之會)로 승양거함(升陽擧陷)하고, 사신총은 백회 사방 1촌에 위치한 경외기혈로 두부 질환에 다용한다."
        ),
        make_chatml(
            "다음 한문 의서 구절을 해석해줘.",
            "腎爲先天之本 脾爲後天之本",
            "[독음] 신위선천지본 비위후천지본\n\n[한의학적 해설]\n신(腎)은 선천의 근본이고, 비(脾)는 후천의 근본이다. 신은 부모로부터 받은 선천지정(先天之精)을 저장하여 생장발육의 기초가 되고, 비는 음식물에서 기혈을 생성하여 후천적 생명 유지의 근본이 된다. 따라서 보신(補腎)과 건비(健脾)는 한의학 치료의 양대 축이다."
        ),
        make_chatml(
            "다음 한문 의서 구절을 해석해줘.",
            "望聞問切",
            "[독음] 망문문절\n\n[한의학적 해설]\n한의학 사진법(四診法)을 말한다. 망(望: 눈으로 관찰), 문(聞: 소리와 냄새를 듣고 맡음), 문(問: 환자에게 물어봄), 절(切: 맥을 짚음). 이 네 가지 진단법을 종합하여 변증(辨證)하는 것이 한의학 진단의 기본이다."
        ),
    ]
    return samples


def main():
    conn = sqlite3.connect(DB_PATH)

    all_samples = []
    
    herbal = generate_herbal_data(conn)
    print(f"본초 학습 데이터: {len(herbal)}건")
    all_samples.extend(herbal)

    formula = generate_formula_data(conn)
    print(f"방제 학습 데이터: {len(formula)}건")
    all_samples.extend(formula)

    acupoint = generate_acupoint_data(conn)
    print(f"경혈 학습 데이터: {len(acupoint)}건")
    all_samples.extend(acupoint)

    sentence = generate_sentence_data()
    print(f"의서 문장 학습 데이터: {len(sentence)}건")
    all_samples.extend(sentence)

    conn.close()

    # JSONL 출력
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        for sample in all_samples:
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")

    print(f"\n총 {len(all_samples)}건 → {OUTPUT_PATH}")
    print(f"파일 크기: {OUTPUT_PATH.stat().st_size / 1024:.1f}KB")


if __name__ == "__main__":
    main()
