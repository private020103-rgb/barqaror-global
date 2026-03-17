#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path


def load_jsonl(path: Path):
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def normalize_apostrophe(text: str) -> str:
    normalized = text.replace("ʻ", "'").replace("‘", "'").replace("`", "'").replace("ʼ", "'")
    return normalize_text(normalized)


def contains_formal_marker(text: str) -> bool:
    markers = ["hurmatli", "iltimos", "minnatdorchilik", "siz", "-ingiz", "ishingiz", "mumkinmi"]
    lowered = text.lower()
    return any(marker in lowered for marker in markers)


def contains_informal_marker(text: str) -> bool:
    markers = ["aka", "salom", "shunchaki", "-san", "bo'pti", "rahmat"]
    lowered = text.lower()
    return any(marker in lowered for marker in markers)


def evaluate_mapping(gold, pred_map):
    correct = 0
    for item in gold:
        prediction = pred_map.get(item["id"], "")
        if normalize_text(prediction) == normalize_text(item["reference"]):
            correct += 1
    return correct / len(gold) if gold else 0.0


def evaluate_apostrophe(gold, pred_map):
    correct = 0
    for item in gold:
        prediction = normalize_apostrophe(pred_map.get(item["id"], ""))
        refs = [normalize_apostrophe(r) for r in item["reference_variants"]]
        if prediction in refs:
            correct += 1
    return correct / len(gold) if gold else 0.0


def evaluate_style(gold, pred_map):
    style_hits = 0
    keyphrase_recall_total = 0.0
    for item in gold:
        prediction = pred_map.get(item["id"], "")
        target_style = item["target_style"]

        if target_style == "rasmiy":
            style_ok = contains_formal_marker(prediction) and not contains_informal_marker(prediction)
        else:
            style_ok = contains_informal_marker(prediction) or not contains_formal_marker(prediction)

        style_hits += int(style_ok)

        lowered = prediction.lower()
        keys = item.get("key_phrases", [])
        key_hit = sum(1 for key in keys if key.lower() in lowered)
        keyphrase_recall_total += key_hit / len(keys) if keys else 1.0

    style_acc = style_hits / len(gold) if gold else 0.0
    key_recall = keyphrase_recall_total / len(gold) if gold else 0.0
    blended = 0.7 * style_acc + 0.3 * key_recall
    return blended


def evaluate_dialect(gold, pred_map):
    correct = 0
    for item in gold:
        prediction = pred_map.get(item["id"], "")
        if normalize_apostrophe(prediction) == normalize_apostrophe(item["normalized_reference"]):
            correct += 1
    return correct / len(gold) if gold else 0.0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="eval/uzbek_quality_suite/data")
    parser.add_argument("--predictions-dir", required=True)
    parser.add_argument("--thresholds", default="eval/uzbek_quality_suite/metrics_thresholds.json")
    parser.add_argument("--out", default="eval/uzbek_quality_suite/results/latest_results.json")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    predictions_dir = Path(args.predictions_dir)
    thresholds = json.loads(Path(args.thresholds).read_text(encoding="utf-8"))

    specs = {
        "lotin_kirill_mapping": ("lotin_kirill_mapping.jsonl", evaluate_mapping),
        "apostrof_imlo_variants": ("apostrof_imlo_variants.jsonl", evaluate_apostrophe),
        "rasmiy_norasmiy_uslub": ("rasmiy_norasmiy_uslub.jsonl", evaluate_style),
        "sheva_robustness": ("sheva_robustness.jsonl", evaluate_dialect),
    }

    results = {}
    for subset, (file_name, scorer) in specs.items():
        gold = load_jsonl(data_dir / file_name)
        preds = load_jsonl(predictions_dir / file_name)
        pred_map = {p["id"]: p.get("prediction", "") for p in preds}
        score = scorer(gold, pred_map)
        threshold = thresholds[subset]["minimum_threshold"]
        results[subset] = {
            "metric": thresholds[subset]["metric"],
            "score": round(score, 4),
            "minimum_threshold": threshold,
            "passed": score >= threshold,
            "examples": len(gold),
        }

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
