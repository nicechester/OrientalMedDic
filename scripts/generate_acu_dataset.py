"""
generate_acu_dataset.py
중국침구학 PDF → 2-pass Vision OCR → Donut fine-tuning dataset

Pipeline:
1. Extract PDF pages as 300dpi images
2. Run Swift 2-pass OCR (ko + zh-Hant ROI) per page
3. Crop line images using bounding boxes
4. Save (line_crop, ground_truth) pairs

Output: data/donut_dataset_acu/
"""

import fitz
import json
import os
import subprocess
import sys
from pathlib import Path
from PIL import Image

PDF_DIR = os.path.expanduser("~/Desktop/chinese_acu/")
OUTPUT_DIR = "data/donut_dataset_acu"
TEMP_DIR = "data/donut_dataset_acu/temp_pages"
SWIFT_SCRIPT = "scripts/vision_ocr_2pass.swift"
DPI = 300

def setup_dirs():
    for split in ["train", "validation"]:
        os.makedirs(f"{OUTPUT_DIR}/{split}/images", exist_ok=True)
    os.makedirs(TEMP_DIR, exist_ok=True)

def extract_page_image(pdf_path, page_idx, out_path):
    doc = fitz.open(pdf_path)
    page = doc[page_idx]
    pix = page.get_pixmap(dpi=DPI)
    pix.save(out_path)
    doc.close()
    return pix.width, pix.height

def run_vision_ocr(image_path):
    """Run Swift 2-pass OCR, return list of {text, bbox}"""
    result = subprocess.run(
        ["swift", SWIFT_SCRIPT, image_path],
        capture_output=True, text=True, timeout=120
    )
    if result.returncode != 0:
        return []
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return []

def crop_line(image_path, bbox, img_w, img_h):
    """Crop a line from image using normalized bbox [x, y, w, h] (bottom-left origin)"""
    img = Image.open(image_path)
    x, y, w, h = bbox
    # Convert from bottom-left normalized to pixel coords (top-left origin)
    left = int(x * img_w)
    right = int((x + w) * img_w)
    top = int((1 - y - h) * img_h)  # flip Y
    bottom = int((1 - y) * img_h)
    # Add small padding
    pad = 5
    left = max(0, left - pad)
    top = max(0, top - pad)
    right = min(img_w, right + pad)
    bottom = min(img_h, bottom + pad)
    return img.crop((left, top, right, bottom))

def main():
    setup_dirs()
    
    import time
    
    # Collect all PDFs
    pdfs = sorted([f for f in os.listdir(PDF_DIR) if f.endswith('.pdf')])
    
    # Count total pages
    total_page_count = 0
    for pdf_name in pdfs:
        doc = fitz.open(os.path.join(PDF_DIR, pdf_name))
        total_page_count += len(doc)
        doc.close()
    print(f"📚 Total: {len(pdfs)} PDFs, {total_page_count} pages")
    
    all_samples = []
    total_pages = 0
    start_time = time.time()
    
    for pdf_name in pdfs:
        pdf_path = os.path.join(PDF_DIR, pdf_name)
        doc = fitz.open(pdf_path)
        n_pages = len(doc)
        doc.close()
        
        print(f"\n📖 {pdf_name} ({n_pages} pages)")
        
        for page_idx in range(n_pages):
            total_pages += 1
            page_img = os.path.join(TEMP_DIR, f"page_{total_pages:04d}.jpg")
            
            # Extract page
            img_w, img_h = extract_page_image(pdf_path, page_idx, page_img)
            
            # Run 2-pass OCR
            lines = run_vision_ocr(page_img)
            
            page_hanja = 0
            if lines:
                for line_idx, line in enumerate(lines):
                    text = line["text"]
                    bbox = line["bbox"]
                    
                    if "(" not in text and "\uff08" not in text:
                        continue
                    has_cjk = any(
                        '\u4e00' <= c <= '\u9fff' or '\u3400' <= c <= '\u4dbf'
                        for c in text
                    )
                    if not has_cjk:
                        continue
                    
                    all_samples.append({
                        "page_img": page_img,
                        "text": text,
                        "bbox": bbox,
                        "img_w": img_w,
                        "img_h": img_h,
                        "page_id": total_pages,
                        "line_idx": line_idx
                    })
                    page_hanja += 1
            
            # Progress every page
            elapsed = time.time() - start_time
            per_page = elapsed / total_pages
            eta = per_page * (total_page_count - total_pages)
            eta_min = int(eta // 60)
            print(f"  [{total_pages}/{total_page_count}] +{page_hanja} lines | total: {len(all_samples)} | {per_page:.1f}s/page | ETA: {eta_min}min", flush=True)
    
    print(f"\n✅ Total pages processed: {total_pages}")
    print(f"✅ Total clean samples: {len(all_samples)}")
    
    # Split train/val (90/10)
    import random
    random.seed(42)
    random.shuffle(all_samples)
    split_idx = int(len(all_samples) * 0.9)
    train_samples = all_samples[:split_idx]
    val_samples = all_samples[split_idx:]
    
    # Save crops and metadata
    for split, samples in [("train", train_samples), ("validation", val_samples)]:
        metadata = []
        for i, sample in enumerate(samples):
            crop = crop_line(
                sample["page_img"], sample["bbox"],
                sample["img_w"], sample["img_h"]
            )
            fname = f"acu_{i:05d}.jpg"
            crop.save(f"{OUTPUT_DIR}/{split}/images/{fname}", quality=95)
            metadata.append({
                "file_name": f"images/{fname}",
                "ground_truth": json.dumps({"text": sample["text"]}, ensure_ascii=False)
            })
        
        # Save metadata.jsonl
        with open(f"{OUTPUT_DIR}/{split}/metadata.jsonl", "w", encoding="utf-8") as f:
            for m in metadata:
                f.write(json.dumps(m, ensure_ascii=False) + "\n")
        
        print(f"  {split}: {len(samples)} samples")
    
    # Cleanup temp
    import shutil
    shutil.rmtree(TEMP_DIR, ignore_errors=True)
    
    print(f"\n🎉 Dataset saved to {OUTPUT_DIR}/")
    print(f"   Train: {len(train_samples)}, Val: {len(val_samples)}")

if __name__ == "__main__":
    main()
