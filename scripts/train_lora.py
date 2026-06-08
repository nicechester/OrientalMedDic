"""
Qwen 2.5-0.5B-Instruct MLX LoRA 파인튜닝
M3 Max 환경용

사용법:
1. pip install mlx-lm
2. python scripts/train_lora.py
3. 학습 완료 후 python scripts/test_finetuned.py 로 검증
"""

import json
import subprocess
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_DIR = Path(__file__).parent.parent / "models" / "lora_adapters"

MODEL_ID = "mlx-community/Qwen2.5-0.5B-Instruct-4bit"

# 학습 파라미터
CONFIG = {
    "model": MODEL_ID,
    "train": True,
    "data": str(DATA_DIR),
    "adapter-path": str(OUTPUT_DIR),
    "iters": 5000,
    "batch-size": 4,
    "lora-layers": 16,
    "learning-rate": 2e-5,
    "steps-per-eval": 200,
    "save-every": 1000,
    "max-seq-length": 1024,
}


def prepare_data():
    """학습/검증 데이터 분할 (9:1)"""
    final_path = DATA_DIR / "sft_final.jsonl"

    if True:  # 항상 재생성
        print("sft_final.jsonl 생성 중...")
        files = [
            DATA_DIR / "sft_dongeuibogam.jsonl",
            DATA_DIR / "sft_train_augmented.jsonl",
            DATA_DIR / "sft_augmented_v2.jsonl",
        ]
        all_lines = []
        for f in files:
            if f.exists():
                with open(f, "r", encoding="utf-8") as fh:
                    all_lines.extend(fh.readlines())
                print(f"  {f.name}: {sum(1 for _ in open(f))}건")

        if not all_lines:
            print("학습 데이터 없음! 크롤링을 먼저 실행하세요.")
            return False

        with open(final_path, "w", encoding="utf-8") as fh:
            fh.writelines(all_lines)
        print(f"  합계: {len(all_lines)}건 → {final_path}")

    # train/valid 분할
    with open(final_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    split = int(len(lines) * 0.9)
    train_lines = lines[:split]
    valid_lines = lines[split:]

    train_path = DATA_DIR / "train.jsonl"
    valid_path = DATA_DIR / "valid.jsonl"

    with open(train_path, "w", encoding="utf-8") as f:
        f.writelines(train_lines)
    with open(valid_path, "w", encoding="utf-8") as f:
        f.writelines(valid_lines)

    print(f"\n학습: {len(train_lines)}건 → {train_path}")
    print(f"검증: {len(valid_lines)}건 → {valid_path}")
    return True


def train():
    """mlx_lm.lora로 학습 실행"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    cmd = [
        "python", "-m", "mlx_lm", "lora",
        "--model", CONFIG["model"],
        "--train",
        "--data", CONFIG["data"],
        "--adapter-path", CONFIG["adapter-path"],
        "--iters", str(CONFIG["iters"]),
        "--batch-size", str(CONFIG["batch-size"]),
        "--num-layers", str(CONFIG["lora-layers"]),
        "--learning-rate", str(CONFIG["learning-rate"]),
        "--steps-per-eval", str(CONFIG["steps-per-eval"]),
        "--save-every", str(CONFIG["save-every"]),
        "--max-seq-length", str(CONFIG["max-seq-length"]),
    ]

    print("\n=== LoRA 학습 시작 ===")
    print(f"모델: {CONFIG['model']}")
    print(f"데이터: {CONFIG['data']}")
    print(f"어댑터 저장: {CONFIG['adapter-path']}")
    print(f"Iterations: {CONFIG['iters']}")
    print(f"Batch size: {CONFIG['batch-size']}")
    print(f"LoRA layers: {CONFIG['lora-layers']}")
    print(f"Learning rate: {CONFIG['learning-rate']}")
    print(f"Max seq length: {CONFIG['max-seq-length']}")
    print("=" * 50)
    print(" ".join(cmd))
    print("=" * 50 + "\n")

    subprocess.run(cmd)


def main():
    if not prepare_data():
        return
    train()
    print(f"\n=== 학습 완료 ===")
    print(f"어댑터 저장 위치: {OUTPUT_DIR}")
    print(f"테스트: python scripts/test_finetuned.py")


if __name__ == "__main__":
    main()
