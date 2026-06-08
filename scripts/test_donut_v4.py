from transformers import DonutProcessor, VisionEncoderDecoderModel
from PIL import Image
import torch

model_path = "models/donut-hanjadic-v4"
processor = DonutProcessor.from_pretrained(model_path)
model = VisionEncoderDecoderModel.from_pretrained(model_path)
model.to("mps").eval()

image = Image.open("scripts/test_acu2.jpg").convert("RGB")
pixel_values = processor(images=image, return_tensors="pt").pixel_values.to("mps")

with torch.no_grad():
    outputs = model.generate(
        pixel_values,
        max_length=256,
        num_beams=3,
        repetition_penalty=1.5,
        no_repeat_ngram_size=3,
        decoder_input_ids=torch.tensor([[processor.tokenizer.convert_tokens_to_ids("<s_hanjadic>")]]).to("mps"),
    )
result = processor.tokenizer.decode(outputs[0], skip_special_tokens=True)
print(result)
