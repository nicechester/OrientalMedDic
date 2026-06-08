"""
PaddleOCR 테스트 - 한글+한자 혼용 이미지 OCR
Usage: python scripts/test_paddle_ocr.py <image_path>
"""
import sys
from pathlib import Path
from paddleocr import PaddleOCR

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_paddle_ocr.py <image_path>")
        sys.exit(1)

    image_path = sys.argv[1]
    if not Path(image_path).exists():
        print(f"파일 없음: {image_path}")
        sys.exit(1)

    # 한국어 + 중국어 번체
    configs = [
        ("korean", "korean"),
        ("chinese_cht", "chinese_cht"),
        ("korean+chinese_cht", "korean"),  # korean 모델이 한자도 어느정도 처리
    ]

    for name, lang in configs:
        print(f"\n{'='*60}")
        print(f"[{name}] lang={lang}")
        print("=" * 60)

        ocr = PaddleOCR(lang=lang)
        result = ocr.predict(image_path)

        for res in result:
            for line in res.get('rec_texts', []):
                print(f"  {line}")
            # fallback: print raw if structure differs
            if 'rec_texts' not in res:
                print(f"  {res}")


if __name__ == "__main__":
    main()
