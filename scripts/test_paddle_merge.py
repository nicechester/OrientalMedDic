"""
PaddleOCR 두 패스 병합 - 한글은 korean 모델, 한자는 chinese 모델에서 가져옴
Usage: python scripts/test_paddle_merge.py <image_path>
"""
import sys
from pathlib import Path
from paddleocr import PaddleOCR


def is_hanja(ch):
    v = ord(ch)
    return (0x4E00 <= v <= 0x9FFF) or (0x3400 <= v <= 0x4DBF) or (0xF900 <= v <= 0xFAFF)


def is_hangul(ch):
    v = ord(ch)
    return (0xAC00 <= v <= 0xD7AF) or (0x3131 <= v <= 0x318E)


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_paddle_merge.py <image_path>")
        sys.exit(1)

    image_path = sys.argv[1]
    if not Path(image_path).exists():
        print(f"파일 없음: {image_path}")
        sys.exit(1)

    # 두 모델 로드
    print("Korean 모델 로드...")
    ocr_ko = PaddleOCR(lang="korean")
    print("Chinese 모델 로드...")
    ocr_zh = PaddleOCR(lang="chinese_cht")

    # 각각 OCR 수행
    print("\nKorean OCR 수행...")
    ko_result = ocr_ko.predict(image_path)
    print("Chinese OCR 수행...")
    zh_result = ocr_zh.predict(image_path)

    # 결과에서 텍스트+bbox 추출
    def extract_lines(result):
        lines = []
        for res in result:
            texts = res.get('rec_texts', [])
            scores = res.get('rec_scores', [])
            boxes = res.get('dt_polys', [])
            for i, text in enumerate(texts):
                box = boxes[i] if i < len(boxes) else None
                score = scores[i] if i < len(scores) else 0
                lines.append({'text': text, 'box': box, 'score': score})
        return lines

    ko_lines = extract_lines(ko_result)
    zh_lines = extract_lines(zh_result)

    print(f"\nKorean lines: {len(ko_lines)}, Chinese lines: {len(zh_lines)}")

    # 줄 매칭 (y좌표 기준) 후 글자 병합
    # 간단한 접근: 같은 인덱스의 줄끼리 매칭
    print("\n" + "=" * 60)
    print("병합 결과 (한자=zh, 한글=ko)")
    print("=" * 60)

    line_count = min(len(ko_lines), len(zh_lines))
    for i in range(line_count):
        ko_text = ko_lines[i]['text']
        zh_text = zh_lines[i]['text']

        # 글자 단위 병합: zh에서 한자, ko에서 한글
        merged = ""
        ko_idx = 0
        zh_idx = 0

        # 두 텍스트를 동시에 순회하며 병합
        while ko_idx < len(ko_text) or zh_idx < len(zh_text):
            # zh에서 한자면 한자 사용
            if zh_idx < len(zh_text) and is_hanja(zh_text[zh_idx]):
                merged += zh_text[zh_idx]
                zh_idx += 1
                ko_idx += 1  # ko도 같이 전진
            # ko에서 한글이면 한글 사용
            elif ko_idx < len(ko_text) and is_hangul(ko_text[ko_idx]):
                merged += ko_text[ko_idx]
                ko_idx += 1
                zh_idx += 1  # zh도 같이 전진
            # 공백/기호 등
            elif ko_idx < len(ko_text):
                merged += ko_text[ko_idx]
                ko_idx += 1
                zh_idx += 1
            else:
                zh_idx += 1

        print(f"  ko: {ko_text}")
        print(f"  zh: {zh_text}")
        print(f"  => {merged}")
        print()


if __name__ == "__main__":
    main()
