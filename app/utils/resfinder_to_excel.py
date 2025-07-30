import os
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime
import pandas as pd

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
TMP_DIR = BASE_DIR / "tmp"
OUTPUT_DIR = TMP_DIR / "output"
EXCEL_PATH = OUTPUT_DIR / "RESFINDER_summary.xlsx"
excel_sheet_name = "AMR"

# Class label mapping
class_map = {
    "folate pathway antagonist": "Trimethoprim",
    "sulphonamide": "Sulphonamide",
    "macrolide": "MLS - Macrolide, Lincosamide and Streptogramin B",
    "lincosamide": "MLS - Macrolide, Lincosamide and Streptogramin B",
    "streptogramin b": "MLS - Macrolide, Lincosamide and Streptogramin B",
    "rifamycin": "Rifampicin",
    "amphenicol": "Phenicol",
    "aminoglycoside": "Aminoglycoside",
    "beta-lactam": "Beta-lactam",
    "quinolone": "Fluoroquinolone",
    "tetracycline": "Tetracycline",
    "fosfomycin": "Fosfomycin"
}

def debug(msg):
    print(f"[ResF-Excel] {msg}")

def collect_json_paths(src: str) -> list[str]:
    return [str(f) for f in Path(src).glob("*.json") if f.is_file()]

def parse_json(json_path):
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    acc = Path(json_path).stem
    genus = "Unknown"

    for region in data.get("seq_regions", {}).values():
        acc = region.get("ref_acc") or region.get("seq_id") or acc
        qid = region.get("query_id", "") or region.get("id", "")
        if qid:
            parts = qid.split()
            if len(parts) >= 2:
                genus = " ".join(parts[1:3]) if len(parts) >= 3 else parts[1]
        break

    if not genus or genus == "Unknown":
        genus = data.get("provided_species") or data.get("organism") or "N/A"

    hits = defaultdict(list)
    for pheno in data.get("phenotypes", {}).values():
        if isinstance(pheno, dict):
            for drug_class in pheno.get("amr_classes", []):
                label = class_map.get(drug_class.lower())
                if not label:
                    continue
                genes = [
                    seg.split(";;")[0]
                    for seg in pheno.get("seq_regions", [])
                    if isinstance(seg, str) and ";;" in seg
                ]
                hits[label].extend(genes)

    return acc, genus, hits

def determine_max_genes(hits_list, classes):
    max_genes = {cls: 0 for cls in classes}
    for _, _, hits in hits_list:
        for cls in classes:
            max_genes[cls] = max(max_genes[cls], len(hits.get(cls, [])))
    return max_genes

def build_row_dynamic(acc, genus, hits, max_genes):
    row = {
        "DATE": datetime.now().isoformat(timespec="seconds"),
        "ACCESSION No.": acc,
        "GENUS": genus
    }
    for cls, max_count in max_genes.items():
        genes = hits.get(cls, [])
        for i in range(max_count):
            col_name = f"{cls} {i + 1}"
            row[col_name] = genes[i] if i < len(genes) else "N/A"
    return row

def generate_resfinder_excel(json_folder: str) -> str | None:
    files = collect_json_paths(json_folder)
    if not files:
        debug("No JSON files found.")
        return None

    debug(f"Parsing {len(files)} JSON files from {json_folder}")
    parsed = [parse_json(f) for f in files]

    all_classes = sorted(set(class_map.values()))
    max_genes = determine_max_genes(parsed, all_classes)

    # Determine full dynamic column set
    columns = ["DATE", "ACCESSION No.", "GENUS"]
    for cls in all_classes:
        for i in range(max_genes[cls]):
            columns.append(f"{cls} {i + 1}")

    new_rows = [
        build_row_dynamic(acc, genus, hits, max_genes)
        for acc, genus, hits in parsed
    ]
    df_new = pd.DataFrame(new_rows, columns=columns)

    if EXCEL_PATH.exists():
        df_old = pd.read_excel(EXCEL_PATH, sheet_name=excel_sheet_name)
        df_merged = pd.concat([df_old, df_new], ignore_index=True)
        df_merged.drop_duplicates(subset=["ACCESSION No."], keep="first", inplace=True)
    else:
        df_merged = df_new

    debug(f"Final rows after deduplication: {len(df_merged)}")
    df_merged.to_excel(EXCEL_PATH, sheet_name=excel_sheet_name, index=False)
    debug(f"Wrote Excel → {EXCEL_PATH}")
    return str(EXCEL_PATH)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("json_folder", help="Folder with ResFinder JSON files")
    args = parser.parse_args()
    generate_resfinder_excel(args.json_folder)
