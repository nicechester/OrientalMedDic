"""
GLM-OCR 테스트 - 한글+한자 혼용 이미지 OCR
Usage: python scripts/test_glm_ocr.py <image_path>
"""
import sys
from pathlib import Path
from mlx_vlm import load, generate
from mlx_vlm.prompt_utils import apply_chat_template
from mlx_vlm.utils import load_config

MODEL_ID = "mlx-community/GLM-OCR-4bit"

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_glm_ocr.py <image_path>")
        sys.exit(1)

    image_path = sys.argv[1]
    if not Path(image_path).exists():
        print(f"파일 없음: {image_path}")
        sys.exit(1)

    print(f"모델 로드: {MODEL_ID}")
    model, processor = load(MODEL_ID)
    config = load_config(MODEL_ID)

    prompt = "OCR this image."

    formatted = apply_chat_template(processor, config, prompt, num_images=1)

    print(f"\n이미지: {image_path}")
    print("=" * 60)

    result = generate(
        model,
        processor,
        formatted,
        image=[image_path],
        max_tokens=2048,
        verbose=False,
    )

    print(result.text)
    print("=" * 60)
    print(f"생성 토큰: {result.generation_tokens}, 속도: {result.generation_tps:.1f} tok/s")


if __name__ == "__main__":
    main()
