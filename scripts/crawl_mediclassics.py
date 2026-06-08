"""
mediclassics.kr 한의학고전DB 크롤러
동의보감 원문-국역 병렬 데이터 수집 → SFT 학습 데이터 변환

API: GET /books/{book_id}/volume/{vol}/content?up_content_seq={seq}
- original: 한문 원문
- trans_2: 한국어 번역
"""

import json
import re
import time
import urllib.request
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_RAW = DATA_DIR / "mediclassics_raw.jsonl"
OUTPUT_SFT = DATA_DIR / "sft_mediclassics.jsonl"

# 동의보감 = book_id 8, 25권
BOOK_ID = 8
VOLUMES = range(1, 26)

BASE_URL = "https://mediclassics.kr/books/{book_id}/volume/{vol}/content?up_content_seq={seq}"

SYSTEM = "너는 동양의학(한의학/중의학) 전문 번역가다. 한문 의서 원문을 받으면 독음을 달고, 한의학적 맥락을 살려 한국어로 해설해줘."


def strip_html(text):
    """HTML 태그 제거"""
    return re.sub(r'<[^>]+>', '', text).strip()


# 브라우저에서 복사한 쿠키 (만료되면 브라우저에서 다시 복사)
COOKIES = "aws-waf-token=c8acf35b-8cd7-4fc7-902c-65133d815507:AQoAheEnEDAmAAAA:BizXdNnlPHPna8FZK6g8OTw3ZgCQvZTC8RknjFnkIlzczeD389AR9RjvQhiZSpObPRgyKoI+aLfwAvXZOEAKiv2tQXlGS/qDJDoJDPUdwuay5k5a9fj4kI0nXB0Dp4GLxNGNKCYKIWSvJD1ujMBbHqgDjok5xD/wjrFgGKmyVIDjgXOQviQUfJ2y6k2sUIw7LtsaEhnb2FdXqJUTJPgMWCXtp/IXjbCZlltrcuaz0l/eMC0qqG/5tAK9LPUExA==; JSESSIONID=ABC81DD3AB0F5D23924853CC04A4E40C"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.2 Safari/605.1.15",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://mediclassics.kr/books/8/volume/1",
    "Cookie": COOKIES,
}


def fetch_json(url):
    """URL에서 JSON 가져오기"""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"  에러: {e}")
        return []


def crawl_recursive(book_id, vol, up_seq, depth=0, max_depth=5):
    """재귀적으로 하위 콘텐츠 크롤링"""
    if depth > max_depth:
        return []

    url = BASE_URL.format(book_id=book_id, vol=vol, seq=up_seq)
    HEADERS["Referer"] = f"https://mediclassics.kr/books/{book_id}/volume/{vol}"
    items = fetch_json(url)
    
    pairs = []
    for item in items:
        orig = (item.get("original") or "").strip()
        ko = strip_html(item.get("trans_2") or item.get("ko") or "")
        content_seq = item.get("content_seq")

        if orig and ko and len(orig) > 5 and len(ko) > 5:
            # \r\n 정리
            orig = orig.replace("\r\n", "").replace("\r", "").replace("\n", "")
            ko = ko.replace("\r\n", " ").replace("\r", " ").replace("\n", " ").strip()
            pairs.append({"original": orig, "korean": ko, "book_id": book_id, "volume": vol})

        # 하위 항목 재귀 탐색
        if content_seq:
            time.sleep(0.3)  # 서버 부하 방지
            sub_pairs = crawl_recursive(book_id, vol, content_seq, depth + 1, max_depth)
            pairs.extend(sub_pairs)

    return pairs


def find_root_seq(book_id, vol):
    """각 권의 루트 content_seq 탐색"""
    for seq in [0, 1]:
        items = fetch_json(BASE_URL.format(book_id=book_id, vol=vol, seq=seq))
        if items:
            return items
    return []


def crawl_dongeuibogam():
    """동의보감 전권 크롤링"""
    all_pairs = []

    for vol in VOLUMES:
        print(f"권{vol} 크롤링 중...")
        root_items = find_root_seq(BOOK_ID, vol)

        for item in root_items:
            content_seq = item.get("content_seq")
            if content_seq:
                pairs = crawl_recursive(BOOK_ID, vol, content_seq, depth=0)
                all_pairs.extend(pairs)
                time.sleep(0.3)

        print(f"  권{vol}: {len(all_pairs)}건 누적")
        time.sleep(1)

    return all_pairs


def save_raw(pairs):
    """원시 데이터 저장"""
    with open(OUTPUT_RAW, "w", encoding="utf-8") as f:
        for p in pairs:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    print(f"원시 데이터: {len(pairs)}건 → {OUTPUT_RAW}")


def convert_to_sft(pairs):
    """SFT ChatML 포맷으로 변환"""
    samples = []
    for p in pairs:
        orig = p["original"]
        ko = p["korean"]

        sample = {
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": f"다음 한문 의서 구절을 해석해줘.\n{orig}"},
                {"role": "assistant", "content": f"[한의학적 해설]\n{ko}"},
            ]
        }
        samples.append(sample)

    with open(OUTPUT_SFT, "w", encoding="utf-8") as f:
        for s in samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    print(f"SFT 데이터: {len(samples)}건 → {OUTPUT_SFT}")


def main():
    print("=== mediclassics.kr 동의보감 크롤링 시작 ===")
    pairs = crawl_dongeuibogam()
    
    if pairs:
        save_raw(pairs)
        convert_to_sft(pairs)
        print(f"\n완료! 총 {len(pairs)}건 수집")
    else:
        print("데이터 수집 실패")


if __name__ == "__main__":
    main()
