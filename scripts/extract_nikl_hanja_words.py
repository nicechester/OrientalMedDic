"""국립국어원 표준국어대사전에서 한자어 항목을 추출하여 JSON으로 저장"""
import xml.etree.ElementTree as ET
import glob, json, re, os

SRC_DIR = "/Users/chester.kim/workspace/trashcan/korean-dict-nikl-stdict"
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "nikl_hanja_words.json")

entries = []
for f in sorted(glob.glob(os.path.join(SRC_DIR, "*.xml"))):
    tree = ET.parse(f)
    root = tree.getroot()
    for item in root.findall("item"):
        wi = item.find("word_info")
        oli = wi.find("original_language_info")
        if oli is None:
            continue
        lt = oli.find("language_type")
        if lt is None or lt.text is None or "한자" not in lt.text:
            continue

        orig_el = oli.find("original_language")
        orig = orig_el.text.strip() if orig_el is not None and orig_el.text else ""
        if not orig:
            continue

        # 명사만 추출
        pos_info = wi.find("pos_info")
        if pos_info is None:
            continue
        pos_el = pos_info.find("pos")
        if pos_el is None or pos_el.text is None or "명사" not in pos_el.text:
            continue

        # 한글 읽기 추출 (번호/접사 표시 제거)
        word_el = wi.find("word")
        word = word_el.text.strip() if word_el is not None and word_el.text else ""
        reading = re.sub(r"\d+$", "", word).strip("-")

        # 뜻 수집
        defs = []
        for cp in pos_info.findall("comm_pattern_info"):
            for si in cp.findall("sense_info"):
                d = si.find("definition")
                if d is not None and d.text:
                    defs.append(d.text.strip())

        if not defs:
            continue

        entries.append({
            "hanja": orig,
            "reading": reading,
            "meaning": defs if len(defs) > 1 else defs[0],
        })

# 저장
os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(entries, f, ensure_ascii=False)

print(f"Saved {len(entries)} entries to {OUT_PATH}")
