"""
사이버서당 국한문 혼용 데이터 → 합성 이미지 생성
기존 donut-hanjadic 모델에 추가 학습용
"""
import json
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from io import BytesIO

DATA_PATH = Path(__file__).parent.parent / "data" / "cyberseodang_noneo.jsonl"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "donut_dataset_mixed"
FONT_PATH = "/System/Library/Fonts/Supplemental/Songti.ttc"
# 한글 폰트 (AppleGothic, AppleMyungjo)
HANGUL_FONTS = [
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "/Library/Fonts/NanumMyeongjo.ttc",
]

IMG_W, IMG_H = 1280, 960
MAX_TEXT_LEN = 200  # 이미지당 최대 글자 수


def load_fonts():
    fonts = []
    # Songti (한자 + 한글 혼용 가능)
    for idx in [0, 2, 4, 6, 7]:
        for size in [28, 32, 36, 40]:
            fonts.append(ImageFont.truetype(FONT_PATH, size, index=idx))
    # 한글 폰트 추가
    for fpath in HANGUL_FONTS:
        try:
            for size in [28, 32, 36, 40]:
                fonts.append(ImageFont.truetype(fpath, size, index=0))
        except:
            pass
    return fonts


def load_data():
    entries = []
    with open(DATA_PATH, "r") as f:
        for line in f:
            item = json.loads(line)
            content = item.get("content", "").strip()
            if len(content) < 15:
                continue
            # 긴 텍스트는 문장 단위로 분할
            if len(content) > MAX_TEXT_LEN:
                # 마침표, 쉼표 등으로 분할
                chunks = []
                current = ""
                for char in content:
                    current += char
                    if char in "。.니라다요며고" and len(current) >= 30:
                        chunks.append(current.strip())
                        current = ""
                if current.strip() and len(current) >= 15:
                    chunks.append(current.strip())
                entries.extend([c[:MAX_TEXT_LEN] for c in chunks if len(c) >= 15])
            else:
                entries.append(content)
    return entries


def render_text_image(text, font, img_w=IMG_W, img_h=IMG_H):
    bg_r = random.randint(235, 255)
    bg_g = random.randint(230, 250)
    bg_b = random.randint(220, 245)
    img = Image.new("RGB", (img_w, img_h), (bg_r, bg_g, bg_b))
    draw = ImageDraw.Draw(img)

    ink = random.randint(0, 40)
    color = (ink, ink, ink)

    margin_x = random.randint(40, 80)
    margin_y = random.randint(40, 80)
    max_w = img_w - margin_x * 2

    # 줄바꿈
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

    line_height = font.getbbox("漢가")[3] - font.getbbox("漢가")[1]
    spacing = random.randint(8, 20)

    y = margin_y
    for line in lines:
        if y + line_height > img_h - margin_y:
            break
        draw.text((margin_x, y), line, font=font, fill=color)
        y += line_height + spacing

    return img


def augment(img):
    if random.random() < 0.3:
        img = img.filter(ImageFilter.GaussianBlur(radius=random.uniform(0.3, 1.0)))
    if random.random() < 0.3:
        angle = random.uniform(-2, 2)
        img = img.rotate(angle, fillcolor=(250, 245, 235), expand=False)
    if random.random() < 0.3:
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=random.randint(60, 85))
        buf.seek(0)
        img = Image.open(buf).copy()
    return img


def main():
    entries = load_data()
    print(f"Loaded {len(entries)} text chunks")

    random.seed(42)
    random.shuffle(entries)
    split = int(len(entries) * 0.9)
    splits = {"train": entries[:split], "validation": entries[split:]}

    fonts = load_fonts()
    print(f"Loaded {len(fonts)} font variants")

    for split_name, split_entries in splits.items():
        out_dir = OUTPUT_DIR / split_name
        img_dir = out_dir / "images"
        img_dir.mkdir(parents=True, exist_ok=True)

        metadata = []
        for i, text in enumerate(split_entries):
            font = random.choice(fonts)
            img = augment(render_text_image(text, font))

            fname = f"{i:05d}.jpg"
            img.save(img_dir / fname, "JPEG", quality=92)

            gt = json.dumps({"gt_parse": {"text": text}}, ensure_ascii=False)
            metadata.append({"file_name": fname, "ground_truth": gt})

            if (i + 1) % 500 == 0:
                print(f"  [{split_name}] {i+1}/{len(split_entries)}")

        with open(out_dir / "metadata.jsonl", "w") as f:
            for m in metadata:
                f.write(json.dumps(m, ensure_ascii=False) + "\n")

        print(f"[{split_name}] {len(split_entries)} images saved to {out_dir}")


if __name__ == "__main__":
    main()
