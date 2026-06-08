"""
Fine-tuned Donut 모델 → CoreML 변환
Encoder와 Decoder를 분리하여 각각 .mlpackage로 변환
"""
import torch
import numpy as np
from pathlib import Path
from transformers import DonutProcessor, VisionEncoderDecoderModel
import coremltools as ct

MODEL_DIR = Path(__file__).parent.parent / "models" / "donut-hanjadic"
OUTPUT_DIR = Path(__file__).parent.parent / "models" / "coreml"


class EncoderWrapper(torch.nn.Module):
    def __init__(self, encoder):
        super().__init__()
        self.encoder = encoder

    def forward(self, pixel_values):
        return self.encoder(pixel_values).last_hidden_state


class DecoderWrapper(torch.nn.Module):
    def __init__(self, decoder, lm_head):
        super().__init__()
        self.decoder = decoder
        self.lm_head = lm_head

    def forward(self, input_ids, encoder_hidden_states):
        outputs = self.decoder(
            input_ids=input_ids,
            encoder_hidden_states=encoder_hidden_states,
            use_cache=False,
        )
        logits = self.lm_head(outputs.last_hidden_state)
        return logits


def convert_encoder(model, processor):
    print("Converting Encoder...")
    encoder = EncoderWrapper(model.encoder)
    encoder.eval()

    # 더미 입력 (1280x960)
    dummy_pixel = torch.randn(1, 3, 960, 1280)

    traced = torch.jit.trace(encoder, dummy_pixel)
    mlmodel = ct.convert(
        traced,
        inputs=[ct.TensorType(name="pixel_values", shape=dummy_pixel.shape)],
        outputs=[ct.TensorType(name="encoder_hidden_states")],
        compute_precision=ct.precision.FLOAT16,
        minimum_deployment_target=ct.target.iOS16,
    )

    out_path = OUTPUT_DIR / "DonutEncoder.mlpackage"
    mlmodel.save(str(out_path))
    print(f"  → Saved: {out_path}")
    return mlmodel


def convert_decoder(model, processor):
    print("Converting Decoder...")
    decoder = DecoderWrapper(model.decoder, model.lm_head)
    decoder.eval()

    # 더미 입력
    dummy_ids = torch.randint(0, 1000, (1, 1))  # 1 token at a time
    dummy_encoder_states = torch.randn(1, 600, 1024)  # encoder output shape

    traced = torch.jit.trace(decoder, (dummy_ids, dummy_encoder_states))
    mlmodel = ct.convert(
        traced,
        inputs=[
            ct.TensorType(name="input_ids", shape=ct.Shape(shape=(1, ct.RangeDim(1, 256)))),
            ct.TensorType(name="encoder_hidden_states", shape=dummy_encoder_states.shape),
        ],
        outputs=[ct.TensorType(name="logits")],
        compute_precision=ct.precision.FLOAT16,
        minimum_deployment_target=ct.target.iOS16,
    )

    out_path = OUTPUT_DIR / "DonutDecoder.mlpackage"
    mlmodel.save(str(out_path))
    print(f"  → Saved: {out_path}")
    return mlmodel


def export_tokenizer(processor):
    """토크나이저 vocab을 JSON으로 내보내기 (Swift에서 사용)"""
    vocab = processor.tokenizer.get_vocab()
    import json
    out_path = OUTPUT_DIR / "tokenizer_vocab.json"
    with open(out_path, "w") as f:
        json.dump(vocab, f, ensure_ascii=False)
    print(f"  → Tokenizer vocab saved: {out_path} ({len(vocab)} tokens)")


def main():
    print(f"Loading model from {MODEL_DIR}...")
    processor = DonutProcessor.from_pretrained(MODEL_DIR)
    model = VisionEncoderDecoderModel.from_pretrained(MODEL_DIR)
    model.eval()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    convert_encoder(model, processor)
    convert_decoder(model, processor)
    export_tokenizer(processor)

    print(f"\nDone. CoreML models saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
