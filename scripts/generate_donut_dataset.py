"""
동의보감 원문 텍스트 → 합성 이미지 생성 (Donut fine-tuning용)
번체 + 간체 동시 생성, 정답은 번체로 통일
"""
import json
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
from opencc import OpenCC

# 번체→간체 변환기
t2s = OpenCC('t2s')

# 설정
DATA_PATH = Path(__file__).parent.parent / "data" / "dongeuibogam_raw.jsonl"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "donut_dataset"
FONT_PATH = "/System/Library/Fonts/Supplemental/Songti.ttc"

# 번체용 폰트 (TC 계열)
FONT_INDICES_TC = [2, 5, 7]  # Songti TC Bold, Light, Regular
# 간체용 폰트 (SC 계열)
FONT_INDICES_SC = [0, 1, 3, 4, 6]  # Songti SC Black/Bold/Light, STSong, SC Regular

# Donut 입력 해상도 (donut-base 기본)
IMG_W, IMG_H = 1280, 960


def load_data():
    entries = []
    with open(DATA_PATH, "r") as f:
        for line in f:
            item = json.loads(line)
            text = item.get("original", "").strip()
            if text and len(text) >= 4:  # 너무 짧은 건 제외
                entries.append(text)
    return entries


def render_text_image(text, font, img_w=IMG_W, img_h=IMG_H):
    """텍스트를 이미지로 렌더링 (가로쓰기, 자동 줄바꿈)"""
    # 배경색 변형 (흰색~약간 누런 종이색)
    bg_r = random.randint(235, 255)
    bg_g = random.randint(230, 250)
    bg_b = random.randint(220, 245)
    img = Image.new("RGB", (img_w, img_h), (bg_r, bg_g, bg_b))
    draw = ImageDraw.Draw(img)

    # 텍스트 색상 (검정~짙은 회색)
    ink = random.randint(0, 40)
    color = (ink, ink, ink)

    # 여백
    margin_x = random.randint(40, 80)
    margin_y = random.randint(40, 80)
    max_w = img_w - margin_x * 2

    # 줄바꿈 처리
    lines = []
    current_line = ""
    for char in text:
        test = current_line + char
        bbox = font.getbbox(test)
        if bbox[2] - bbox[0] > max_w:
            lines.append(current_line)
            current_line = char
        else:
            current_line = test
    if current_line:
        lines.append(current_line)

    # 줄 간격
    line_height = font.getbbox("漢")[3] - font.getbbox("漢")[1]
    spacing = random.randint(8, 20)

    # 그리기
    y = margin_y
    for line in lines:
        if y + line_height > img_h - margin_y:
            break
        draw.text((margin_x, y), line, font=font, fill=color)
        y += line_height + spacing

    return img


def augment(img):
    """간단한 augmentation"""
    # 약간의 블러 (50% 확률)
    if random.random() < 0.3:
        img = img.filter(ImageFilter.GaussianBlur(radius=random.uniform(0.3, 1.0)))

    # 약간의 회전 (30% 확률)
    if random.random() < 0.3:
        angle = random.uniform(-2, 2)
        img = img.rotate(angle, fillcolor=(250, 245, 235), expand=False)

    # JPEG 압축 노이즈 시뮬레이션 (30% 확률)
    if random.random() < 0.3:
        from io import BytesIO
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=random.randint(60, 85))
        buf.seek(0)
        img = Image.open(buf).copy()

    return img


def main():
    entries = load_data()
    print(f"Loaded {len(entries)} entries")

    # train/validation 분할 (90/10)
    random.seed(42)
    random.shuffle(entries)
    split = int(len(entries) * 0.9)
    splits = {"train": entries[:split], "validation": entries[split:]}

    # 폰트 로드
    fonts_tc = [ImageFont.truetype(FONT_PATH, s, index=i)
                for i in FONT_INDICES_TC for s in [28, 32, 36, 40, 48]]
    fonts_sc = [ImageFont.truetype(FONT_PATH, s, index=i)
                for i in FONT_INDICES_SC for s in [28, 32, 36, 40, 48]]
    print(f"Loaded {len(fonts_tc)} TC + {len(fonts_sc)} SC font variants")

    for split_name, split_entries in splits.items():
        out_dir = OUTPUT_DIR / split_name
        img_dir = out_dir / "images"
        img_dir.mkdir(parents=True, exist_ok=True)

        metadata = []
        idx = 0
        for i, text in enumerate(split_entries):
            # 정답은 항상 번체 원문
            gt = json.dumps({"gt_parse": {"text": text}}, ensure_ascii=False)

            # 1) 번체 이미지
            font = random.choice(fonts_tc)
            img = augment(render_text_image(text, font))
            fname = f"{idx:05d}.jpg"
            img.save(img_dir / fname, "JPEG", quality=92)
            metadata.append({"file_name": fname, "ground_truth": gt})
            idx += 1

            # 2) 간체 이미지 (정답은 동일하게 번체)
            simplified = t2s.convert(text)
            font = random.choice(fonts_sc)
            img = augment(render_text_image(simplified, font))
            fname = f"{idx:05d}.jpg"
            img.save(img_dir / fname, "JPEG", quality=92)
            metadata.append({"file_name": fname, "ground_truth": gt})
            idx += 1

            if (i + 1) % 1000 == 0:
                print(f"  [{split_name}] {i+1}/{len(split_entries)} ({idx} images)")

        # metadata.jsonl 저장
        with open(out_dir / "metadata.jsonl", "w") as f:
            for m in metadata:
                f.write(json.dumps(m, ensure_ascii=False) + "\n")

        print(f"[{split_name}] {idx} images saved to {out_dir}")


if __name__ == "__main__":
    main()
