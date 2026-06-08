"""
절 단위 번역 테스트:
1. 원문을 쉼표/마침표로 쪼갬
2. 각 절에 독음 붙임
3. 절 하나씩 모델에 보내서 번역
4. 결과 이어붙이기
"""

import sqlite3
import time
from pathlib import Path

from mlx_lm import load, generate
from mlx_lm.sample_utils import make_logits_processors

DATA_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DATA_DIR / "hanjadic.db"
MODEL_ID = "mlx-community/Qwen2.5-0.5B-Instruct-4bit"
ADAPTER_PATH = str(Path(__file__).parent.parent / "models" / "lora_adapters")


# --- Yale → 한글 변환 (주요 음절만) ---

YALE_TO_HANGUL = {
    "ka": "가", "kak": "각", "kan": "간", "kal": "갈", "kam": "감", "kap": "갑", "kang": "강",
    "kay": "개", "kayk": "객", "ke": "거", "ken": "건", "kel": "걸", "kem": "검", "kep": "겁",
    "kyeng": "경", "kye": "계", "ko": "고", "kok": "곡", "kon": "곤", "kol": "골", "kong": "공",
    "kwa": "과", "kwan": "관", "kwal": "괄", "kwang": "광", "kwey": "궤", "koy": "괴",
    "kwu": "구", "kwuk": "국", "kwun": "군", "kwul": "굴", "kwung": "궁", "kwi": "귀",
    "kyun": "균", "kuk": "극", "kun": "근", "kul": "글", "kum": "금", "kup": "급", "kung": "긍",
    "ki": "기", "kil": "길", "kim": "김",
    "na": "나", "nak": "낙", "nan": "난", "nal": "날", "nam": "남", "nap": "납", "nang": "낭",
    "nay": "내", "nayng": "냉", "nye": "녀", "nyen": "년", "nyem": "념", "nyeng": "녕",
    "no": "노", "nok": "녹", "non": "논", "nong": "농", "noy": "뇌", "nwu": "누",
    "nwuk": "눅", "nung": "능", "ni": "니", "nik": "닉", "nin": "닌", "nil": "닐",
    "ta": "다", "tak": "탁", "tan": "단", "tal": "달", "tam": "담", "tap": "답", "tang": "당",
    "tay": "대", "tek": "덕", "to": "도", "tok": "독", "ton": "돈", "tol": "돌", "tong": "동",
    "twu": "두", "twun": "둔", "tung": "등", "ti": "디",
    "la": "라", "lak": "락", "lan": "란", "lam": "람", "lang": "랑",
    "lay": "래", "layng": "랭", "lyang": "량", "lye": "려", "lyek": "력", "lyen": "련",
    "lyel": "렬", "lyem": "렴", "lyep": "렵", "lyeng": "령", "lyey": "례",
    "lo": "로", "lok": "록", "lon": "론", "long": "롱", "loy": "뢰",
    "lwu": "루", "lwuk": "룩", "lyuk": "육", "lyun": "륜", "lyul": "률", "lyung": "융",
    "li": "리", "lik": "릭", "lin": "린", "lim": "림", "lip": "립",
    "ma": "마", "mak": "막", "man": "만", "mal": "말", "mang": "망",
    "may": "매", "mayk": "맥", "meng": "맹", "mye": "며", "myen": "면", "myel": "멸",
    "myeng": "명", "mo": "모", "mok": "목", "mon": "문", "mong": "몽", "mwu": "무",
    "mwuk": "묵", "mwun": "문", "mwul": "물", "mi": "미", "mik": "믹", "min": "민", "mil": "밀",
    "pa": "바", "pak": "박", "pan": "반", "pal": "발", "pang": "방",
    "pay": "배", "payk": "백", "pen": "번", "pel": "벌", "pem": "범", "pep": "법",
    "pyel": "별", "pyeng": "병", "po": "보", "pok": "복", "pon": "본", "pong": "봉",
    "pwu": "부", "pwuk": "북", "pwun": "분", "pwul": "불", "pung": "붕",
    "pi": "비", "pik": "빅", "pin": "빈", "ping": "빙",
    "sa": "사", "sak": "삭", "san": "산", "sal": "살", "sam": "삼", "sang": "상",
    "say": "새", "sayk": "색", "sayng": "생", "se": "서", "sek": "석", "sen": "선",
    "sel": "설", "sem": "섬", "sep": "섭", "seng": "성", "sey": "세", "seyk": "섹",
    "so": "소", "sok": "속", "son": "손", "sol": "솔", "song": "송",
    "swu": "수", "swuk": "숙", "swun": "순", "swul": "술", "swung": "숭",
    "si": "시", "sik": "식", "sin": "신", "sil": "실", "sim": "심", "sip": "십",
    "a": "아", "ak": "악", "an": "안", "al": "알", "am": "암", "ap": "압", "ang": "앙",
    "ay": "애", "ayk": "액", "ya": "야", "yak": "약", "yang": "양",
    "e": "어", "ek": "억", "en": "언", "el": "얼", "em": "엄", "ep": "업",
    "ye": "여", "yek": "역", "yen": "연", "yel": "열", "yem": "염", "yep": "엽",
    "yeng": "영", "yey": "예", "o": "오", "ok": "옥", "on": "온", "ol": "올", "ong": "옹",
    "wa": "와", "wan": "완", "wal": "왈", "wang": "왕", "way": "외",
    "yo": "요", "yok": "욕", "yong": "용",
    "wu": "우", "wun": "운", "wul": "울", "wung": "웅", "wen": "원", "wel": "월", "wi": "위",
    "yu": "유", "yuk": "육", "yun": "윤", "yul": "율", "yung": "융",
    "un": "은", "ul": "을", "um": "음", "up": "읍", "ung": "응",
    "uy": "의", "i": "이", "ik": "익", "in": "인", "il": "일", "im": "임", "ip": "입",
    "ca": "자", "cak": "작", "can": "잔", "cam": "잠", "cap": "잡", "cang": "장",
    "cay": "재", "cayk": "적", "ce": "저", "cek": "적", "cen": "전", "cel": "절",
    "cem": "점", "cep": "접", "ceng": "정", "cey": "제", "co": "조", "cok": "족",
    "con": "존", "cong": "종", "cwa": "좌", "cwu": "주", "cwuk": "죽", "cwun": "준",
    "cwung": "중", "cung": "증", "ci": "지", "cik": "직", "cin": "진", "cil": "질",
    "cim": "짐", "cip": "집",
    "cha": "차", "chak": "착", "chan": "찬", "cham": "참", "chang": "창",
    "chay": "채", "chayk": "책", "che": "처", "chek": "척", "chen": "천", "chel": "철",
    "chem": "첨", "chep": "첩", "cheng": "청", "chey": "체", "cho": "초", "chok": "촉",
    "chon": "촌", "chong": "총", "chwu": "추", "chwuk": "축", "chwun": "춘",
    "chwung": "충", "chwi": "취", "chi": "치", "chik": "칙", "chin": "친", "chil": "칠",
    "chim": "침", "chip": "칩",
    "tha": "타", "thak": "탁", "than": "탄", "thal": "탈", "tham": "탐", "thap": "탑", "thang": "탕",
    "thay": "태", "thayk": "택", "the": "터", "tho": "토", "thong": "통", "thoy": "퇴",
    "thwu": "투", "thuk": "특",
    "pha": "파", "phak": "팍", "phan": "판", "phal": "팔", "phang": "팡",
    "phay": "패", "phyen": "편", "phyeng": "평", "pho": "포", "phok": "폭",
    "phyo": "표", "phwung": "풍", "phi": "피", "phik": "픽", "phil": "필", "phip": "핍",
    "ha": "하", "hak": "학", "han": "한", "hal": "할", "ham": "함", "hap": "합", "hang": "항",
    "hay": "해", "hayk": "핵", "hayng": "행", "hyang": "향", "he": "허", "hen": "헌",
    "hel": "헐", "hem": "험", "hyel": "혈", "hyep": "협", "hyeng": "형", "hyey": "혜",
    "ho": "호", "hok": "혹", "hon": "혼", "hong": "홍", "hwa": "화", "hwan": "환",
    "hwal": "활", "hwang": "황", "hoy": "회", "hoyk": "획", "hoyng": "횡", "hyo": "효",
    "hwu": "후", "hwun": "훈", "hwul": "훌", "hwi": "휘", "hyu": "휴", "hyung": "흉",
    "huk": "흑", "hun": "흔", "hul": "흘", "hum": "흠", "hung": "흥", "hui": "희",
    "sup": "습", "pyen": "변", "kyey": "계",
}


def yale_to_hangul(yale_str):
    return YALE_TO_HANGUL.get(yale_str.lower().strip(), yale_str)


# --- 독음 DB 로드 ---

def load_char_readings():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT character, korean_reading FROM hanja WHERE korean_reading IS NOT NULL")
    readings = {}
    for char, reading in c.fetchall():
        readings[char] = yale_to_hangul(reading.split()[0])
    conn.close()
    return readings


def is_hanja(ch):
    cp = ord(ch)
    return 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF or 0xF900 <= cp <= 0xFAFF


def get_reading(clause, char_readings):
    """절(clause)의 독음을 한글로 생성"""
    result = []
    for ch in clause:
        if is_hanja(ch):
            result.append(char_readings.get(ch, "?"))
        # 비한자는 무시
    return "".join(result)


def split_clauses(text):
    """원문을 쉼표/마침표/공백 기준으로 절 단위로 분할"""
    import re
    # 쉼표, 마침표, 공백으로 분할
    parts = re.split(r"[,，.。\s]+", text)
    return [p.strip() for p in parts if p.strip()]


# --- 메인 ---

# SYSTEM = "너는 한의학 전문 번역가다. 한문 구절과 독음이 주어지면, 한국어로 자연스럽게 번역해줘. 간결하게 한 문장으로 답해."
SYSTEM = "한문 구절과 독음이 주어지면, 영어로 자연스럽게 번역해줘."

TEST = "聖惠方曰, 天地之精氣化萬物之形, 父之精氣爲魂, 母之精氣爲魄."


def main():
    char_readings = load_char_readings()

    # 1. 절 분할 + 독음
    clauses = split_clauses(TEST)
    print(f"원문: {TEST}\n")
    print("=== 절 분할 + 독음 ===")
    for clause in clauses:
        reading = get_reading(clause, char_readings)
        print(f"  {clause} → {reading}")

    # 2. 모델 로드
    print("\n=== LLM 절 단위 번역 ===")
    model, tokenizer = load(MODEL_ID, adapter_path=ADAPTER_PATH)
    logits_proc = make_logits_processors(repetition_penalty=1.3, repetition_context_size=64)

    # 3. 절 하나씩 번역
    translations = []
    for clause in clauses:
        reading = get_reading(clause, char_readings)

        messages = [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"{clause}\n독음: {reading}"},
        ]
        prompt = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

        response = generate(
            model, tokenizer, prompt=prompt,
            max_tokens=80,
            logits_processors=logits_proc,
        )
        # 첫 줄만 사용
        # first_line = response.strip().split("\n")[0]
        # translations.append(first_line)
        first_line = response
        translations.append(first_line)
        print(f"  {clause}({reading}) → {first_line}")

    # 4. 최종 결과
    print(f"\n=== 최종 번역 ===")
    print(" ".join(translations))


if __name__ == "__main__":
    main()
