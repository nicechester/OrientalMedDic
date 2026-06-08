"""
Fine-tuned Donut-HanjaDic 모델 테스트
"""
import torch
from PIL import Image
from transformers import DonutProcessor, VisionEncoderDecoderModel
import json
import sys

MODEL_DIR = "../models/donut-hanjadic-v2"
TASK_PROMPT = "<s_hanjadic>"


def test(image_path):
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    print(f"Device: {device}")

    processor = DonutProcessor.from_pretrained(MODEL_DIR)
    model = VisionEncoderDecoderModel.from_pretrained(MODEL_DIR).to(device)
    model.eval()

    image = Image.open(image_path).convert("RGB")
    pixel_values = processor(images=image, return_tensors="pt").pixel_values.to(device)

    decoder_input_ids = processor.tokenizer(
        TASK_PROMPT, add_special_tokens=False, return_tensors="pt"
    ).input_ids.to(device)

    with torch.no_grad():
        outputs = model.generate(
            pixel_values,
            decoder_input_ids=decoder_input_ids,
            max_length=256,
            early_stopping=True,
            pad_token_id=processor.tokenizer.pad_token_id,
            eos_token_id=processor.tokenizer.eos_token_id,
            use_cache=True,
            num_beams=3,
            repetition_penalty=2.0,
            no_repeat_ngram_size=10,
        )

    result = processor.batch_decode(outputs, skip_special_tokens=True)[0]

    print("\n" + "=" * 50)
    print("Donut-HanjaDic Result:")
    print("=" * 50)
    print(result if result.strip() else "[결과 없음]")
    print("=" * 50)


if __name__ == "__main__":
    image_path = sys.argv[1] if len(sys.argv) > 1 else "source3.jpg"
    test(image_path)
