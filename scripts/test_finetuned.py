"""
LoRA 파인튜닝된 Qwen 0.5B 테스트
제로샷 결과와 비교용
"""

import time
from pathlib import Path

from mlx_lm import load, generate
from mlx_lm.sample_utils import make_logits_processors

MODEL_ID = "mlx-community/Qwen2.5-0.5B-Instruct-4bit"
ADAPTER_PATH = str(Path(__file__).parent.parent / "models" / "lora_adapters")

SYSTEM = "너는 동양의학(한의학/중의학) 전문 번역가다. 한문 의서 원문을 받으면 독음을 달고, 한의학적 맥락을 살려 한국어로 해설해줘."

TEST_CASES = [
    "補氣血 淸濕熱",
    "肝主疏泄 腎主封藏",
    "麻黃三兩 桂枝二兩 甘草一兩 杏仁七十箇",
    "表寒裏熱 頭痛發熱 口渴引飲",
    "氣滯血瘀 不通則痛",
    "取足三里 合谷 內關",
    "腎爲先天之本 脾爲後天之本",
    "風爲百病之長",
    "參同契註曰, 形氣未具曰鴻濛, 具而未離曰混淪. 易曰, 易有太極, 是生兩儀. 易猶鴻濛也. 太極猶混淪也. 乾坤者太極之變也. 合之爲太極, 分之爲乾坤. 故合乾坤而言之謂之混淪, 分乾坤而言之謂之天地. 列子曰, 太初氣之始也. 太始形之始也. 亦類此.",
]


def run_test():
    print(f"모델: {MODEL_ID}")
    print(f"어댑터: {ADAPTER_PATH}")
    model, tokenizer = load(MODEL_ID, adapter_path=ADAPTER_PATH)
    print("로딩 완료\n" + "=" * 60)

    for i, text in enumerate(TEST_CASES, 1):
        messages = [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"다음 한문 의서 구절을 해석해줘.\n{text}"},
        ]
        prompt = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

        start = time.time()
        response = generate(
            model, tokenizer, prompt=prompt,
            max_tokens=256,
            logits_processors=make_logits_processors(
                repetition_penalty=1.3,
                repetition_context_size=64,
            ),
        )
        elapsed = time.time() - start

        print(f"\n[테스트 {i}] 입력: {text}")
        print(f"[출력] ({elapsed:.1f}초)\n{response}")
        print("-" * 60)


if __name__ == "__main__":
    run_test()
