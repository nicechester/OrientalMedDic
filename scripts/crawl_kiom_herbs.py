#!/usr/bin/env python3
"""
한국한의학연구원(KIOM) OASIS 본초 DB 크롤러
https://oasis.kiom.re.kr/oasis/herb/monoSearch.jsp
"""

import json
import re
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode, quote
from html.parser import HTMLParser

DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_PATH = DATA_DIR / "herbal_kiom.json"

BASE_URL = "https://oasis.kiom.re.kr/oasis/herb/monoSearch.jsp"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9",
}


class HerbParser(HTMLParser):
    """본초 목록 파싱"""
    def __init__(self):
        super().__init__()
        self.herbs = []
        self.in_table = False
        self.in_row = False
        self.current_row = []
        self.tag_stack = []

    def handle_starttag(self, tag, attrs):
        self.tag_stack.append(tag)
        if tag == "table":
            self.in_table = True
        elif tag == "tr" and self.in_table:
            self.in_row = True
            self.current_row = []
        elif tag == "a":
            for attr, value in attrs:
                if attr == "href" and "herbSeq=" in value:
                    self.current_row.append(("link", value))

    def handle_endtag(self, tag):
        if self.tag_stack and self.tag_stack[-1] == tag:
            self.tag_stack.pop()

        if tag == "tr" and self.in_row and len(self.current_row) > 0:
            self.in_row = False
            self.herbs.append(self.current_row)
            self.current_row = []

    def handle_data(self, data):
        if self.in_row:
            text = data.strip()
            if text and len(text) > 1:
                self.current_row.append(text)


def fetch_list():
    """본초 목록 페이지 크롤링"""
    print("본초 목록 페이지에서 크롤링 중...")

    try:
        req = Request(BASE_URL, headers=HEADERS)
        with urlopen(req, timeout=10) as resp:
            html = resp.read().decode('utf-8', errors='ignore')

        parser = HerbParser()
        parser.feed(html)
        return parser.herbs
    except Exception as e:
        print(f"오류: {e}")
        return []


def extract_herb_seq(link):
    """링크에서 herbSeq 추출"""
    match = re.search(r'herbSeq=(\d+)', link)
    return match.group(1) if match else None


def fetch_herb_detail(herb_seq):
    """개별 본초 상세 정보 페이지 크롤링"""
    url = f"https://oasis.kiom.re.kr/oasis/herb/monoView.jsp?herbSeq={herb_seq}"

    try:
        req = Request(url, headers=HEADERS)
        with urlopen(req, timeout=10) as resp:
            html = resp.read().decode('utf-8', errors='ignore')

        # 정보 추출
        herb_data = {
            "name_hanja": "",
            "name_korean": "",
            "name_pinyin": "",
            "nature": "",
            "flavor": "",
            "meridian_tropism": "",
            "efficacy": "",
            "source_url": url
        }

        # 한문명
        hanja_match = re.search(r'<span[^>]*>한문명[^<]*</span>[^<]*<span[^>]*>([^<]+)</span>', html)
        if hanja_match:
            herb_data["name_hanja"] = hanja_match.group(1).strip()

        # 한글명
        korean_match = re.search(r'<span[^>]*>한글명[^<]*</span>[^<]*<span[^>]*>([^<]+)</span>', html)
        if korean_match:
            herb_data["name_korean"] = korean_match.group(1).strip()

        # 중문명 (병음)
        pinyin_match = re.search(r'<span[^>]*>중문명[^<]*</span>[^<]*<span[^>]*>([^<]+)</span>', html)
        if pinyin_match:
            pinyin_text = pinyin_match.group(1).strip()
            herb_data["name_pinyin"] = pinyin_text

        # 성질
        nature_match = re.search(r'<span[^>]*>성질[^<]*</span>[^<]*<span[^>]*>([^<]+)</span>', html)
        if nature_match:
            herb_data["nature"] = nature_match.group(1).strip()

        # 맛
        flavor_match = re.search(r'<span[^>]*>맛[^<]*</span>[^<]*<span[^>]*>([^<]+)</span>', html)
        if flavor_match:
            herb_data["flavor"] = flavor_match.group(1).strip()

        # 귀경
        meridian_match = re.search(r'<span[^>]*>귀경[^<]*</span>[^<]*<span[^>]*>([^<]+)</span>', html)
        if meridian_match:
            meridian_text = meridian_match.group(1).strip()
            herb_data["meridian_tropism"] = meridian_text

        # 효능
        efficacy_match = re.search(r'<span[^>]*>효능[^<]*</span>[^<]*<span[^>]*>([^<]+)</span>', html)
        if efficacy_match:
            herb_data["efficacy"] = efficacy_match.group(1).strip()

        return herb_data
    except Exception as e:
        print(f"  상세 페이지 오류 (seq={herb_seq}): {e}")
        return None


def crawl():
    """메인 크롤링"""
    # 목록 페이지에서 링크 수집 (주의: OASIS는 동적 로딩이므로 제한적)
    # 대신 직접 seq 번호로 요청

    print("KIOM OASIS 본초 데이터 크롤링 시작...")
    print("(주: OASIS는 JavaScript 렌더링 필요하므로 완전한 크롤링은 제한적입니다)")
    print()

    herbs = []

    # 알려진 본초 seq 범위 테스트 (1~200)
    # 실제로는 더 많을 수 있음
    print("본초 상세 페이지 크롤링 중...")
    for herb_seq in range(1, 101):  # 처음 100개만 시도
        print(f"  seq={herb_seq}...", end="", flush=True)

        herb_data = fetch_herb_detail(herb_seq)
        if herb_data and herb_data["name_hanja"]:
            herbs.append(herb_data)
            print(f" OK - {herb_data['name_korean']}")
        else:
            print(" SKIP")

        time.sleep(0.5)  # 서버 부하 경감

    print()
    print(f"총 {len(herbs)}종 수집 완료")

    # JSON 저장
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(herbs, f, ensure_ascii=False, indent=2)

    print(f"저장: {OUTPUT_PATH}")

    return herbs


if __name__ == "__main__":
    herbs = crawl()

    # 요약 출력
    print("\n수집된 본초:")
    for herb in herbs[:10]:
        print(f"  {herb['name_hanja']} ({herb['name_korean']})")
    if len(herbs) > 10:
        print(f"  ... 외 {len(herbs) - 10}종")
