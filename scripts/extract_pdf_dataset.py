"""
PDF 강의자료 → Donut 학습 데이터 추출
페이지 이미지 + 텍스트 레이어를 학습 페어로 변환
"""
import json
import glob
from pathlib import Path
import pdfplumber
from PIL import Image
from io import BytesIO

PDF_DIR = "/Users/chester.kim/Desktop"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "donut_dataset_pdf"

# 대상 PDF 파일들
PDF_FILES = [
    "02_사하제 & 화해제.pdf",
    "04_온리거한제 & 이기제.pdf",
    "1. 상한론 개론.ppt - Google Slides.pdf",
    "1. Introduction.pptx - Google Slides.pdf",
    "7. 적취_황달_고창.pptx - Google Slides.pdf",
    "8. 두통, 현훈, 이명, 이롱.pptx - Google Slides.pdf",
    "침구학 원론 1강 침구(鍼灸)의 발전(發展) 약사(略史) - 한의사 신제철.pdf",
]

MIN_TEXT_LEN = 10  # 텍스트가 너무 짧은 페이지 제외


def extract_pdf(pdf_path, img_dir, start_idx):
    """PDF에서 페이지 이미지 + 텍스트 추출"""
    entries = []
    pdf = pdfplumber.open(pdf_path)

    for i, page in enumerate(pdf.pages):
        text = page.extract_text()
        if not text or len(text.strip()) < MIN_TEXT_LEN:
            continue

        # 페이지를 이미지로 변환
        img = page.to_image(resolution=150)
        fname = f"{start_idx:05d}.jpg"
        img_path = img_dir / fname
        img.original.convert("RGB").save(str(img_path), format="JPEG", quality=90)

        # ground truth
        clean_text = text.strip().replace("\n", " ")
        gt = json.dumps({"gt_parse": {"text": clean_text}}, ensure_ascii=False)
        entries.append({"file_name": fname, "ground_truth": gt})
        start_idx += 1

    pdf.close()
    return entries, start_idx


def main():
    all_entries = []
    img_dir = OUTPUT_DIR / "images"
    img_dir.mkdir(parents=True, exist_ok=True)

    idx = 0
    for pdf_name in PDF_FILES:
        pdf_path = Path(PDF_DIR) / pdf_name
        if not pdf_path.exists():
            print(f"  [SKIP] {pdf_name} not found")
            continue

        entries, idx = extract_pdf(pdf_path, img_dir, idx)
        print(f"  [{len(entries)} pages] {pdf_name}")
        all_entries.extend(entries)

    # train/validation 분할 (90/10)
    import random
    random.seed(42)
    random.shuffle(all_entries)
    split = int(len(all_entries) * 0.9)

    for split_name, split_entries in [("train", all_entries[:split]), ("validation", all_entries[split:])]:
        out_dir = OUTPUT_DIR / split_name
        out_img_dir = out_dir / "images"
        out_img_dir.mkdir(parents=True, exist_ok=True)

        metadata = []
        for i, entry in enumerate(split_entries):
            new_fname = f"{i:05d}.jpg"
            src = img_dir / entry["file_name"]
            dst = out_img_dir / new_fname
            if not dst.exists():
                dst.symlink_to(src.resolve())
            metadata.append({"file_name": new_fname, "ground_truth": entry["ground_truth"]})

        with open(out_dir / "metadata.jsonl", "w") as f:
            for m in metadata:
                f.write(json.dumps(m, ensure_ascii=False) + "\n")

        print(f"[{split_name}] {len(split_entries)} pages")

    print(f"\nDone. Total: {len(all_entries)} pages → {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
