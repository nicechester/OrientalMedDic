"""각 체크포인트별 출력 비교"""

import time
from pathlib import Path
from mlx_lm import load, generate
from mlx_lm.sample_utils import make_logits_processors

MODEL_ID = "mlx-community/Qwen2.5-0.5B-Instruct-4bit"
ADAPTER_DIR = Path(__file__).parent.parent / "models" / "lora_adapters"

SYSTEM = "너는 동양의학(한의학/중의학) 전문 번역가다. 한문 의서 원문을 받으면 독음을 달고, 한의학적 맥락을 살려 한국어로 해설해줘."
TEXT = "參同契註曰, 形氣未具曰鴻濛, 具而未離曰混淪. 易曰, 易有太極, 是生兩儀. 易猶鴻濛也. 太極猶混淪也. 乾坤者太極之變也. 合之爲太極, 分之爲乾坤. 故合乾坤而言之謂之混淪, 分乾坤而言之謂之天地. 列子曰, 太初氣之始也. 太始形之始也. 亦類此."

CHECKPOINTS = [1000, 2000, 3000, 4000, 5000]


def run():
    for step in CHECKPOINTS:
        adapter_path = str(ADAPTER_DIR / f"{step:07d}_adapters.safetensors")
        print(f"\n{'='*60}")
        print(f"체크포인트: {step} steps")
        print(f"{'='*60}")

        model, tokenizer = load(MODEL_ID, adapter_path=str(ADAPTER_DIR))
        # mlx_lm은 디렉토리 기반이라 개별 파일 지정 불가 — 심볼릭 링크로 우회
        import shutil, os
        target = ADAPTER_DIR / "adapters.safetensors"
        source = ADAPTER_DIR / f"{step:07d}_adapters.safetensors"
        target.unlink(missing_ok=True)
        shutil.copy2(source, target)

        model, tokenizer = load(MODEL_ID, adapter_path=str(ADAPTER_DIR))

        messages = [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"다음 한문 의서 구절을 해석해줘.\n{TEXT}"},
        ]
        prompt = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

        start = time.time()
        response = generate(
            model, tokenizer, prompt=prompt,
            max_tokens=300,
            logits_processors=make_logits_processors(
                repetition_penalty=1.3,
                repetition_context_size=64,
            ),
        )
        elapsed = time.time() - start

        print(f"({elapsed:.1f}초)")
        print(response)

    # 원래 어댑터 복원 (5000)
    source = ADAPTER_DIR / "0005000_adapters.safetensors"
    target = ADAPTER_DIR / "adapters.safetensors"
    target.unlink(missing_ok=True)
    shutil.copy2(source, target)


if __name__ == "__main__":
    run()
