"""
LoRA 어댑터를 베이스 모델에 fuse하여 단일 모델로 만들기
출력: models/hanjadic-0.5b-4bit/ (HuggingFace 포맷)

사용법: python scripts/fuse_model.py
"""

import subprocess
from pathlib import Path

MODEL_ID = "mlx-community/Qwen2.5-0.5B-Instruct-4bit"
ADAPTER_PATH = Path(__file__).parent.parent / "models" / "lora_adapters"
OUTPUT_PATH = Path(__file__).parent.parent / "models" / "hanjadic-0.5b-4bit"


def main():
    print("=== LoRA Fuse ===")
    print(f"베이스: {MODEL_ID}")
    print(f"어댑터: {ADAPTER_PATH}")
    print(f"출력: {OUTPUT_PATH}")

    cmd = [
        "python", "-m", "mlx_lm", "fuse",
        "--model", MODEL_ID,
        "--adapter-path", str(ADAPTER_PATH),
        "--save-path", str(OUTPUT_PATH),
    ]

    print(f"\n실행: {' '.join(cmd)}\n")
    subprocess.run(cmd)

    if OUTPUT_PATH.exists():
        size_mb = sum(f.stat().st_size for f in OUTPUT_PATH.rglob("*")) / 1024 / 1024
        print(f"\n완료! 모델 크기: {size_mb:.0f}MB")
        print(f"경로: {OUTPUT_PATH}")
    else:
        print("fuse 실패")


if __name__ == "__main__":
    main()
