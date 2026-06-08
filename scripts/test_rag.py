"""
RAG 방식 테스트: DB 기반 분절 + 독음 → 프롬프트에 주입 후 생성
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


# --- DB 기반 분절기 ---

# Yale 로마자 → 한글 변환
YALE_TO_HANGUL = {
    "ka": "가", "kak": "각", "kan": "간", "kal": "갈", "kam": "감", "kap": "갑", "kang": "강",
    "kay": "개", "kayk": "객", "ke": "거", "ken": "건", "kel": "걸", "kem": "검", "kep": "겁",
    "kyeng": "경", "kye": "계", "ko": "고", "kok": "곡", "kon": "곤", "kol": "골", "kong": "공",
    "kwa": "과", "kwan": "관", "kwal": "괄", "kwang": "광", "kwey": "괘", "koy": "괴",
    "kwu": "구", "kwuk": "국", "kwun": "군", "kwul": "굴", "kwung": "궁", "kwi": "귀",
    "kyun": "균", "kuk": "극", "kun": "근", "kul": "글", "kum": "금", "kup": "급",
    "kung": "긍", "ki": "기", "kil": "길", "kim": "김",
    "na": "나", "nak": "낙", "nan": "난", "nal": "날", "nam": "남", "nap": "납", "nang": "낭",
    "nay": "내", "nayng": "냉", "nye": "녀", "nyen": "년", "nyem": "념", "nyeng": "녕",
    "no": "노", "nok": "녹", "non": "논", "nong": "농", "noy": "뇌", "nwu": "누",
    "nwuk": "눅", "nung": "능", "ni": "니", "nik": "닉", "nin": "닌", "nil": "닐",
    "ta": "다", "tak": "닥", "tan": "단", "tal": "달", "tam": "담", "tap": "답", "tang": "당",
    "tay": "대", "tek": "덕", "to": "도", "tok": "독", "ton": "돈", "tol": "돌", "tong": "동",
    "twu": "두", "twun": "둔", "tung": "등", "ti": "디",
    "la": "라", "lak": "락", "lan": "란", "lam": "람", "lang": "랑",
    "lay": "래", "layng": "랭", "lyang": "량", "lye": "려", "lyek": "력", "lyen": "련",
    "lyel": "렬", "lyem": "렴", "lyep": "렵", "lyeng": "령", "lyey": "례",
    "lo": "로", "lok": "록", "lon": "론", "long": "롱", "loy": "뢰",
    "lwu": "루", "lwuk": "룩", "lyuk": "육", "lyun": "륜", "lyul": "률", "lyung": "융",
    "luk": "륙", "li": "리", "lik": "릭", "lin": "린", "lim": "림", "lip": "립",
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
    "ssang": "쌍",
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
    "phay": "패", "phayng": "팽", "phyen": "편", "phyeng": "평", "pho": "포", "phok": "폭",
    "phyo": "표", "phwung": "풍", "phi": "피", "phik": "픽", "phil": "필", "phip": "핍",
    "ha": "하", "hak": "학", "han": "한", "hal": "할", "ham": "함", "hap": "합", "hang": "항",
    "hay": "해", "hayk": "핵", "hayng": "행", "hyang": "향", "he": "허", "hen": "헌",
    "hel": "헐", "hem": "험", "hyel": "혈", "hyep": "협", "hyeng": "형", "hyey": "혜",
    "ho": "호", "hok": "혹", "hon": "혼", "hong": "홍", "hwa": "화", "hwan": "환",
    "hwal": "활", "hwang": "황", "hoy": "회", "hoyk": "획", "hoyng": "횡", "hyo": "효",
    "hwu": "후", "hwun": "훈", "hwul": "훌", "hwi": "휘", "hyu": "휴", "hyung": "흉",
    "huk": "흑", "hun": "흔", "hul": "흘", "hum": "흠", "hung": "흥", "hui": "희",
    # 추가
    "sup": "습", "pyeng": "병", "sel": "설", "sol": "솔",
    "kyey": "계", "mong": "몽", "lon": "론", "lyun": "륜",
    "wal": "왈", "wol": "월",
}


def yale_to_hangul(yale_str):
    """Yale 로마자를 한글로 변환"""
    key = yale_str.lower().strip()
    return YALE_TO_HANGUL.get(key, yale_str)


class HanjaSegmenter:
    def __init__(self, db_path):
        conn = sqlite3.connect(db_path)
        c = conn.cursor()

        # 복합어 사전 (의학 용어: 2자 이상)
        self.terms = {}  # hanja -> korean reading

        # herbal
        c.execute("SELECT name_hanja, name_korean FROM herbal")
        for h, k in c.fetchall():
            if h:
                self.terms[h] = k

        # formula
        c.execute("SELECT name_hanja, name_korean FROM formula")
        for h, k in c.fetchall():
            if h:
                self.terms[h] = k

        # acupuncture
        c.execute("SELECT name_hanja, name_korean FROM acupuncture WHERE name_hanja IS NOT NULL")
        for h, k in c.fetchall():
            if h:
                self.terms[h] = k

        # 개별 한자 독음 (Yale → 한글 변환)
        self.char_readings = {}
        c.execute("SELECT character, korean_reading FROM hanja WHERE korean_reading IS NOT NULL")
        for char, reading in c.fetchall():
            first_yale = reading.split()[0]
            self.char_readings[char] = yale_to_hangul(first_yale)

        conn.close()

        # 최장 일치를 위해 길이순 정렬
        self.term_list = sorted(self.terms.keys(), key=len, reverse=True)
        self.max_term_len = max(len(t) for t in self.term_list) if self.term_list else 4

    def segment(self, text):
        """최장 일치 분절. 반환: [(한자, 독음), ...]"""
        result = []
        i = 0
        while i < len(text):
            ch = text[i]
            if not self._is_hanja(ch):
                i += 1
                continue

            # 1) 의학 용어 사전에서 최장 일치
            matched = False
            for length in range(min(self.max_term_len, len(text) - i), 1, -1):
                candidate = text[i:i + length]
                if candidate in self.terms:
                    result.append((candidate, self.terms[candidate]))
                    i += length
                    matched = True
                    break

            if not matched:
                # 2) 2글자 복합어 시도 (독음 합성)
                if i + 1 < len(text) and self._is_hanja(text[i + 1]):
                    r1 = self.char_readings.get(text[i], "?")
                    r2 = self.char_readings.get(text[i + 1], "?")
                    if r1 != "?" and r2 != "?":
                        result.append((text[i:i + 2], f"{r1}{r2}"))
                        i += 2
                        matched = True

            if not matched:
                # 3) 개별 한자
                reading = self.char_readings.get(ch, "?")
                result.append((ch, reading))
                i += 1

        return result

    def segment_with_context(self, text):
        """분절 결과를 프롬프트용 문자열로 변환"""
        segments = self.segment(text)
        if not segments:
            return "", ""

        # 독음 목록 (중복 제거)
        readings = []
        seen = set()
        for hanja, reading in segments:
            if hanja not in seen:
                readings.append(f"{hanja}({reading})")
                seen.add(hanja)

        # 분절 표시
        seg_str = "/".join(h for h, _ in segments)

        return ", ".join(readings), seg_str

    def _is_hanja(self, ch):
        cp = ord(ch)
        return (0x4E00 <= cp <= 0x9FFF or
                0x3400 <= cp <= 0x4DBF or
                0xF900 <= cp <= 0xFAFF)


# --- 테스트 ---

SYSTEM_TEMPLATE = """너는 동양의학(한의학/중의학) 전문 번역가다. 한문 의서 원문을 받으면 한국어로 해설해줘.
규칙:
1. 한자 용어는 "한국어(漢字)" 형식으로 표기.
2. 독음 참고: {readings}
3. 분절 참고: {segmentation}
4. 의학적 맥락을 살려 자연스러운 한국어로 해설."""

TEST_CASES = [
    "補氣血 淸濕熱",
    "肝主疏泄 腎主封藏",
    "氣滯血瘀 不通則痛",
    "腎爲先天之本 脾爲後天之本",
    "風爲百病之長",
    "參同契註曰, 形氣未具曰鴻濛, 具而未離曰混淪. 易曰, 易有太極, 是生兩儀. 易猶鴻濛也. 太極猶混淪也. 乾坤者太極之變也. 合之爲太極, 分之爲乾坤. 故合乾坤而言之謂之混淪, 分乾坤而言之謂之天地. 列子曰, 太初氣之始也. 太始形之始也. 亦類此.",
]


def main():
    segmenter = HanjaSegmenter(DB_PATH)

    print("=== 분절 테스트 ===")
    for text in TEST_CASES:
        readings, seg = segmenter.segment_with_context(text)
        print(f"\n원문: {text}")
        print(f"독음: {readings}")
        print(f"분절: {seg}")
    print("\n" + "=" * 60)

    print("\n=== LLM 생성 테스트 (RAG) ===")
    model, tokenizer = load(MODEL_ID, adapter_path=ADAPTER_PATH)
    print("모델 로딩 완료\n")

    logits_proc = make_logits_processors(
        repetition_penalty=1.3,
        repetition_context_size=64,
    )

    for i, text in enumerate(TEST_CASES, 1):
        readings, seg = segmenter.segment_with_context(text)
        system = SYSTEM_TEMPLATE.format(readings=readings, segmentation=seg)

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"다음 한문 의서 구절을 해석해줘.\n{text}"},
        ]
        prompt = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

        start = time.time()
        response = generate(
            model, tokenizer, prompt=prompt,
            max_tokens=300,
            logits_processors=logits_proc,
        )
        elapsed = time.time() - start

        print(f"\n[테스트 {i}] 입력: {text}")
        print(f"[RAG 독음] {readings[:80]}...")
        print(f"[출력] ({elapsed:.1f}초)\n{response}")
        print("-" * 60)


if __name__ == "__main__":
    main()
