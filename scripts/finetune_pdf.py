"""
Donut v3: 실제 PDF 강의자료로 추가 학습
v2 모델 위에 continual fine-tuning
"""
import json
from pathlib import Path
import torch
from torch.utils.data import Dataset, DataLoader
from PIL import Image
from transformers import DonutProcessor, VisionEncoderDecoderModel, get_scheduler
from torch.optim import AdamW
from tqdm import tqdm

BASE_MODEL = str(Path(__file__).parent.parent / "models" / "donut-hanjadic-v2")
DATASET_DIR = Path(__file__).parent.parent / "data" / "donut_dataset_pdf"
OUTPUT_DIR = Path(__file__).parent.parent / "models" / "donut-hanjadic-v3"
TASK_PROMPT = "<s_hanjadic>"

# 보수적 하이퍼파라미터 (소량 실제 데이터)
EPOCHS = 3
BATCH_SIZE = 4  # PDF 이미지가 더 복잡하므로 메모리 고려
LR = 1e-5       # 매우 낮은 학습률
MAX_LENGTH = 512  # 슬라이드 텍스트가 길 수 있음
IMG_SIZE = [480, 640]


class PDFDataset(Dataset):
    def __init__(self, split_dir, processor, max_length=MAX_LENGTH):
        self.processor = processor
        self.max_length = max_length
        self.img_dir = split_dir / "images"
        self.entries = []
        with open(split_dir / "metadata.jsonl") as f:
            for line in f:
                self.entries.append(json.loads(line))

    def __len__(self):
        return len(self.entries)

    def __getitem__(self, idx):
        entry = self.entries[idx]
        image = Image.open(self.img_dir / entry["file_name"]).convert("RGB")
        pixel_values = self.processor(images=image, return_tensors="pt").pixel_values.squeeze()

        gt = json.loads(entry["ground_truth"])
        text = TASK_PROMPT + json.dumps(gt["gt_parse"], ensure_ascii=False) + self.processor.tokenizer.eos_token
        labels = self.processor.tokenizer(
            text, max_length=self.max_length, padding="max_length", truncation=True, return_tensors="pt"
        ).input_ids.squeeze()
        labels[labels == self.processor.tokenizer.pad_token_id] = -100

        return {"pixel_values": pixel_values, "labels": labels}


def main():
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    print(f"Device: {device}")

    print(f"Loading base model: {BASE_MODEL}")
    processor = DonutProcessor.from_pretrained(BASE_MODEL)
    processor.image_processor.size = {"height": IMG_SIZE[0], "width": IMG_SIZE[1]}
    model = VisionEncoderDecoderModel.from_pretrained(BASE_MODEL).to(device)

    train_ds = PDFDataset(DATASET_DIR / "train", processor)
    val_ds = PDFDataset(DATASET_DIR / "validation", processor)
    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)
    print(f"Train: {len(train_ds)}, Val: {len(val_ds)}")

    optimizer = AdamW(model.parameters(), lr=LR, weight_decay=0.01)
    num_steps = len(train_loader) * EPOCHS
    scheduler = get_scheduler("cosine", optimizer, num_warmup_steps=num_steps // 10, num_training_steps=num_steps)

    best_val_loss = float("inf")
    for epoch in range(EPOCHS):
        model.train()
        total_loss = 0
        for batch in tqdm(train_loader, desc=f"Epoch {epoch+1}/{EPOCHS}"):
            pixel_values = batch["pixel_values"].to(device)
            labels = batch["labels"].to(device)

            outputs = model(pixel_values=pixel_values, labels=labels)
            loss = outputs.loss

            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
            optimizer.zero_grad()
            total_loss += loss.item()

        avg_train_loss = total_loss / len(train_loader)

        model.eval()
        val_loss = 0
        with torch.no_grad():
            for batch in val_loader:
                pixel_values = batch["pixel_values"].to(device)
                labels = batch["labels"].to(device)
                outputs = model(pixel_values=pixel_values, labels=labels)
                val_loss += outputs.loss.item()
        avg_val_loss = val_loss / len(val_loader)

        print(f"Epoch {epoch+1}: train_loss={avg_train_loss:.4f}, val_loss={avg_val_loss:.4f}")

        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            model.save_pretrained(OUTPUT_DIR)
            processor.save_pretrained(OUTPUT_DIR)
            print(f"  → Best model saved (val_loss={best_val_loss:.4f})")

    print(f"\nDone. Best val_loss: {best_val_loss:.4f}")
    print(f"Model saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
