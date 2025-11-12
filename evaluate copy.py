#!/usr/bin/env python3
# evaluate.py
# Usage:
#   python evaluate.py            # uses latest folder under output/
#   python evaluate.py --out output/20251108_142530
#
# Outputs:
#   <basename>_<model>_eval.txt
#   evaluation_summary.csv

import os
import sys
import csv
import argparse
from glob import glob

# Try to import jiwer.wer (optional). If absent, use local WER computation.
try:
    from jiwer import wer as jiwer_wer
    HAVE_JIWER = True
except Exception:
    HAVE_JIWER = False

REF_SUFFIXES = ("_reference.txt", "_ref.txt")
DEFAULT_OUTPUT_PARENT = "output"
DEFAULT_SAMPLES_DIR = "samples"


def find_latest_output_dir(parent=DEFAULT_OUTPUT_PARENT):
    if not os.path.isdir(parent):
        return None
    dirs = [os.path.join(parent, d) for d in os.listdir(parent) if os.path.isdir(os.path.join(parent, d))]
    if not dirs:
        return None
    dirs.sort(key=lambda x: os.path.getmtime(x))
    return dirs[-1]


def find_reference_files(samples_dir):
    refs = []
    if not os.path.isdir(samples_dir):
        return refs
    for pattern in ["*_reference.txt", "*_ref.txt"]:
        for p in glob(os.path.join(samples_dir, pattern)):
            refs.append(p)
    return sorted(refs)


def basename_from_ref(ref_path):
    name = os.path.basename(ref_path)
    for suf in REF_SUFFIXES:
        if name.endswith(suf):
            return name[:-len(suf)]
    return None


def find_hypotheses_for_basename(out_dir, basename):
    candidates = []
    for fname in os.listdir(out_dir):
        if not fname.lower().endswith(".txt"):
            continue
        if fname.startswith(basename + "_") and not fname.endswith("_times.txt") and not fname.endswith("_eval.txt"):
            candidates.append(os.path.join(out_dir, fname))
    candidates.sort()
    return candidates


def read_text_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


# Local edit-distance based measures (word-level)
def compute_measures_local(ref_text, hyp_text):
    r = ref_text.split()
    h = hyp_text.split()
    n = len(r); m = len(h)
    # dp
    dp = [[0]*(m+1) for _ in range(n+1)]
    for i in range(1, n+1): dp[i][0] = i
    for j in range(1, m+1): dp[0][j] = j
    for i in range(1, n+1):
        for j in range(1, m+1):
            cost = 0 if r[i-1] == h[j-1] else 1
            dp[i][j] = min(dp[i-1][j] + 1, dp[i][j-1] + 1, dp[i-1][j-1] + cost)
    # backtrace
    i, j = n, m
    subs = ins = dels = hits = 0
    while i > 0 or j > 0:
        if i > 0 and j > 0 and dp[i][j] == dp[i-1][j-1] and r[i-1] == h[j-1]:
            hits += 1; i -= 1; j -= 1
        elif i > 0 and j > 0 and dp[i][j] == dp[i-1][j-1] + 1:
            subs += 1; i -= 1; j -= 1
        elif j > 0 and dp[i][j] == dp[i][j-1] + 1:
            ins += 1; j -= 1
        else:
            dels += 1; i -= 1
    truth_len = n
    wer_val = (subs + ins + dels) / truth_len if truth_len > 0 else 0.0
    return {"substitutions": subs, "insertions": ins, "deletions": dels, "hits": hits, "truth_length": truth_len, "wer": wer_val}


def compute_and_save(ref_path, hyp_path, out_dir):
    ref_text = read_text_file(ref_path)
    hyp_text = read_text_file(hyp_path)

    # WER (prefer jiwer if available)
    if HAVE_JIWER:
        try:
            w = jiwer_wer(ref_text, hyp_text)
        except Exception:
            w = compute_measures_local(ref_text, hyp_text)["wer"]
            measures = compute_measures_local(ref_text, hyp_text)
    else:
        measures = compute_measures_local(ref_text, hyp_text)
        w = measures["wer"]

    if HAVE_JIWER:
        # we may not have detailed measures from jiwer here; use local for counts as fallback
        measures = compute_measures_local(ref_text, hyp_text)

    subs = measures["substitutions"]
    ins = measures["insertions"]
    dels = measures["deletions"]
    hits = measures["hits"]
    truth_len = measures["truth_length"]

    hyp_fname = os.path.basename(hyp_path)
    eval_fname = hyp_fname.rsplit(".txt", 1)[0] + "_eval.txt"
    eval_path = os.path.join(out_dir, eval_fname)

    with open(eval_path, "w", encoding="utf-8") as f:
        f.write(f"Reference: {ref_path}\n")
        f.write(f"Hypothesis: {hyp_path}\n")
        f.write(f"WER: {w:.6f}\n")
        f.write(f"Substitutions: {subs}\n")
        f.write(f"Insertions: {ins}\n")
        f.write(f"Deletions: {dels}\n")
        f.write(f"Hits: {hits}\n")
        f.write(f"Truth length (words): {truth_len}\n\n")
        f.write("=== Reference ===\n")
        f.write(ref_text + "\n\n")
        f.write("=== Hypothesis ===\n")
        f.write(hyp_text + "\n")

    return {
        "hypothesis": hyp_path,
        "reference": ref_path,
        "eval_file": eval_path,
        "wer": w,
        "substitutions": subs,
        "insertions": ins,
        "deletions": dels,
        "hits": hits,
        "truth_length": truth_len,
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate STT outputs against references (WER + measures)")
    parser.add_argument("--out", help="Path to output/<timestamp> directory. If omitted, the latest directory under output/ is used.")
    parser.add_argument("--samples", default=DEFAULT_SAMPLES_DIR, help="Samples directory containing reference files (default: samples)")
    args = parser.parse_args()

    out_dir = args.out if args.out else find_latest_output_dir()
    if not out_dir:
        print("ERROR: output directory not found. Either create outputs or specify --out.")
        sys.exit(1)
    if not os.path.isdir(out_dir):
        print(f"ERROR: specified out directory does not exist: {out_dir}")
        sys.exit(1)

    refs = find_reference_files(args.samples)
    if not refs:
        print(f"ERROR: no reference files found in samples dir: {args.samples}")
        sys.exit(1)

    summary_rows = []
    for ref in refs:
        basename = basename_from_ref(ref)
        if not basename:
            continue
        hyps = find_hypotheses_for_basename(out_dir, basename)
        if not hyps:
            print(f"Warning: no hypothesis files found for basename {basename} in {out_dir}")
            continue
        for hyp in hyps:
            result = compute_and_save(ref, hyp, out_dir)
            hyp_fname = os.path.basename(hyp)
            model_name = hyp_fname[len(basename)+1:-4] if hyp_fname.startswith(basename + "_") else hyp_fname[:-4]
            summary_rows.append([
                basename, model_name, result["wer"],
                result["substitutions"], result["insertions"], result["deletions"],
                result["reference"], result["hypothesis"], result["eval_file"]
            ])
            print(f"Evaluated: {basename} / {model_name} -> WER {result['wer']:.3f}")

    csv_path = os.path.join(out_dir, "evaluation_summary.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as csvf:
        writer = csv.writer(csvf)
        writer.writerow(["basename", "model", "wer", "substitutions", "insertions", "deletions", "reference", "hypothesis", "eval_file"])
        writer.writerows(summary_rows)

    print(f"Done. Summary: {csv_path}")


if __name__ == "__main__":
    main()
