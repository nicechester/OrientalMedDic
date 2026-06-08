"""
synthetic 동의보감 데이터셋 + 중국침구학 실제 스캔 데이터셋 병합 (셔플)
"""
import json
import random
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent / "data"
DS1 = BASE_DIR / "donut_dataset"        # 한문 (번체+간체) synthetic
DS2 = BASE_DIR / "donut_dataset_acu"     # 중국침구학 실제 스캔
OUT = BASE_DIR / "donut_dataset_combined"

random.seed(42)


def merge_split(split_name):
    out_dir = OUT / split_name
    img_dir = out_dir / "images"
    img_dir.mkdir(parents=True, exist_ok=True)

    entries = []

    for src in [DS1, DS2]:
        src_split = src / split_name
        if not src_split.exists():
            continue
        src_imgs = src_split / "images"
        with open(src_split / "metadata.jsonl") as f:
            for line in f:
                entry = json.loads(line)
                old_fname = entry["file_name"].replace("images/", "")
                src_path = src_imgs / old_fname
                entries.append({"src_path": src_path, "ground_truth": entry["ground_truth"]})

    # Shuffle
    random.shuffle(entries)

    # Write symlinks + metadata
    metadata = []
    for idx, e in enumerate(entries):
        new_fname = f"{idx:06d}.jpg"
        dst_path = img_dir / new_fname
        if dst_path.exists() or dst_path.is_symlink():
            dst_path.unlink()
        dst_path.symlink_to(e["src_path"].resolve())
        metadata.append({"file_name": new_fname, "ground_truth": e["ground_truth"]})

    with open(out_dir / "metadata.jsonl", "w") as f:
        for m in metadata:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")

    print(f"[{split_name}] {len(entries)} images merged (shuffled)")


def main():
    for split in ["train", "validation"]:
        merge_split(split)
    print(f"\nDone. Combined dataset: {OUT}")


if __name__ == "__main__":
    main()
