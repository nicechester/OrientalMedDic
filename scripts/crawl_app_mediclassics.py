"""
app.mediclassics.kr 동의보감 크롤러
서버사이드 렌더링으로 원문(OR)/국역(KO) 쌍 직접 추출
WAF/인증 불필요

사용법: python scripts/crawl_app_mediclassics.py
"""

import json
import re
import time
import urllib.request
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_RAW = DATA_DIR / "dongeuibogam_raw.jsonl"
OUTPUT_SFT = DATA_DIR / "sft_dongeuibogam.jsonl"

BASE_URL = "https://app.mediclassics.kr/books/%EB%8F%99%EC%9D%98%EB%B3%B4%EA%B0%90/pages/{page}"
MAX_PAGE = 1100  # 여유있게
SYSTEM = "너는 동양의학(한의학/중의학) 전문 번역가다. 한문 의서 원문을 받으면 독음을 달고, 한의학적 맥락을 살려 한국어로 해설해줘."


def fetch_page(page):
    url = BASE_URL.format(page=page)
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15"
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8")
    except Exception as e:
        print(f"  페이지 {page} 에러: {e}")
        return ""


def extract_pairs(html):
    """OR/KO 클래스에서 원문-국역 쌍 추출"""
    or_blocks = re.findall(r'<p[^>]*class="OR"[^>]*>(.*?)</p>', html, re.DOTALL)
    ko_blocks = re.findall(r'<p[^>]*class="KO"[^>]*>(.*?)</p>', html, re.DOTALL)

    pairs = []
    for i in range(min(len(or_blocks), len(ko_blocks))):
        orig = re.sub(r'<[^>]+>', '', or_blocks[i]).strip()
        orig = re.sub(r'\s+', ' ', orig).strip()
        # 앞에 붙는 숫자 인덱스 제거
        orig = re.sub(r'^\d+\s*', '', orig).strip()

        ko = re.sub(r'<[^>]+>', '', ko_blocks[i]).strip()
        ko = re.sub(r'\s+', ' ', ko).strip()

        if orig and ko and len(orig) > 3 and len(ko) > 3:
            pairs.append({"original": orig, "korean": ko})

    return pairs


def main():
    print("=== app.mediclassics.kr 동의보감 크롤링 ===")
    all_pairs = []
    empty_count = 0

    for page in range(1, MAX_PAGE + 1):
        html = fetch_page(page)
        if not html:
            empty_count += 1
            if empty_count > 10:
                print(f"연속 실패 — 페이지 {page}에서 종료")
                break
            continue

        pairs = extract_pairs(html)
        if not pairs:
            empty_count += 1
            if empty_count > 10:
                print(f"빈 페이지 연속 — 페이지 {page}에서 종료")
                break
            continue

        empty_count = 0
        all_pairs.extend(pairs)

        if page % 50 == 0:
            print(f"  페이지 {page}: 누적 {len(all_pairs)}건")

        time.sleep(0.5)  # 서버 부하 방지

    # 원시 데이터 저장
    with open(OUTPUT_RAW, "w", encoding="utf-8") as f:
        for p in all_pairs:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    print(f"\n원시 데이터: {len(all_pairs)}건 → {OUTPUT_RAW}")

    # SFT 포맷 변환
    samples = []
    for p in all_pairs:
        sample = {
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": f"다음 한문 의서 구절을 해석해줘.\n{p['original']}"},
                {"role": "assistant", "content": f"[한의학적 해설]\n{p['korean']}"},
            ]
        }
        samples.append(sample)

    with open(OUTPUT_SFT, "w", encoding="utf-8") as f:
        for s in samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    print(f"SFT 데이터: {len(samples)}건 → {OUTPUT_SFT}")
    print(f"\n완료!")


if __name__ == "__main__":
    main()
