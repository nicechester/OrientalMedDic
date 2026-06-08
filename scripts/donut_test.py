import torch
from PIL import Image
from transformers import DonutProcessor, VisionEncoderDecoderModel

def test_donut_cord(image_path):
    """CORD (영수증 파싱) fine-tuned 모델로 문서 구조 추출 테스트"""
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    print(f"Using device: {device}")

    model_name = "naver-clova-ix/donut-base-finetuned-cord-v2"
    print(f"Loading {model_name}...")
    processor = DonutProcessor.from_pretrained(model_name)
    model = VisionEncoderDecoderModel.from_pretrained(model_name).to(device)

    image = Image.open(image_path).convert("RGB")
    pixel_values = processor(images=image, return_tensors="pt").pixel_values.to(device)

    # CORD 모델은 태스크 프롬프트로 "<s_cord-v2>"를 사용
    task_prompt = "<s_cord-v2>"
    decoder_input_ids = processor.tokenizer(
        task_prompt, add_special_tokens=False, return_tensors="pt"
    ).input_ids.to(device)

    model.eval()
    with torch.no_grad():
        outputs = model.generate(
            pixel_values,
            decoder_input_ids=decoder_input_ids,
            max_length=768,
            early_stopping=True,
            pad_token_id=processor.tokenizer.pad_token_id,
            eos_token_id=processor.tokenizer.eos_token_id,
            use_cache=True,
            num_beams=3,
        )

    result = processor.batch_decode(outputs, skip_special_tokens=True)[0]

    print("\n" + "="*40)
    print("Donut CORD-v2 Result:")
    print("="*40)
    print(result if result.strip() else "[결과 없음]")
    print("="*40)


if __name__ == "__main__":
    test_donut_cord("source3.jpg")