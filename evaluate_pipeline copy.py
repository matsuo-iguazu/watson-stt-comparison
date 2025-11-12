#!/usr/bin/env python3
# evaluate_pipeline.py (robust: exclude times files, prefer tokenized refs/hyps)
import os
import sys
import csv
import argparse
from glob import glob

DEFAULT_SAMPLES_DIR = "samples"
REF_TOKEN_SUFFIXES = ("_ref.token.txt", "_reference.token.txt", "_ref.txt")

def _basename_from_ref_filename(fname):
    for suf in REF_TOKEN_SUFFIXES:
        if fname.endswith(suf):
            return fname[:-len(suf)]
    return os.path.splitext(fname)[0]

def build_reference_map(samples_dir):
    """
    Return dict: basename -> chosen reference path.
    Preference: *_ref.token.txt > *_reference.token.txt > *_ref.txt
    """
    refs = {}
    if not os.path.isdir(samples_dir):
        return refs
    # tokenized first
    for p in glob(os.path.join(samples_dir, "*_ref.token.txt")):
        name = os.path.basename(p)
        b = _basename_from_ref_filename(name)
        refs[b] = p
    # alternative reference token
    for p in glob(os.path.join(samples_dir, "*_reference.token.txt")):
        name = os.path.basename(p)
        b = _basename_from_ref_filename(name)
        if b not in refs:
            refs[b] = p
    # fallback _ref.txt
    for p in glob(os.path.join(samples_dir, "*_ref.txt")):
        name = os.path.basename(p)
        b = _basename_from_ref_filename(name)
        if b not in refs:
            refs[b] = p
    return refs

def collect_hypotheses_by_model(out_dir, basename):
    """
    Collect hypothesis files for a given basename under out_dir.
    Return dict: model_name -> path, preferring .token.txt over .txt.
    EXCLUDE any file that corresponds to times/_times/_eval.
    """
    candidates = {}
    if not os.path.isdir(out_dir):
        return candidates
    prefix = basename + "_"
    for fname in sorted(os.listdir(out_dir)):
        if not fname.lower().endswith(".txt"):
            continue
        if not fname.startswith(prefix):
            continue
        # skip obvious ref files
        if fname.endswith("_ref.token.txt") or fname.endswith("_reference.token.txt") or fname.endswith("_ref.txt"):
            continue

        model_part = fname[len(prefix):]  # e.g. "ja-JP.token.txt" or "times.txt"

        # Determine raw model name (without .token.txt or .txt)
        raw_model_name = None
        is_tokenized = False
        if model_part.endswith(".token.txt"):
            raw_model_name = model_part[:-len(".token.txt")]
            is_tokenized = True
        elif model_part.endswith(".txt"):
            raw_model_name = model_part[:-len(".txt")]
        else:
            continue

        # Exclude any times/eval artifacts explicitly
        rm_lower = raw_model_name.lower()
        if rm_lower == "times" or rm_lower.endswith("_times") or rm_lower.startswith("times") or "_times" in rm_lower or "_eval" in rm_lower or rm_lower == "time":
            # skip times/eval files (these are metadata/time summaries, not models)
            continue

        # Now prefer tokenized form
        model_name = raw_model_name
        if is_tokenized:
            candidates[model_name] = os.path.join(out_dir, fname)
        else:
            # only set if tokenized not already present
            if model_name not in candidates:
                candidates[model_name] = os.path.join(out_dir, fname)

    return candidates

def read_tokens(path):
    with open(path, "r", encoding="utf-8") as f:
        txt = f.read().strip()
    return txt.split() if txt else []

def compute_measures_local(ref_tokens, hyp_tokens):
    """
    Compute edit-distance token-level measures.
    Backtrace preference: match -> insertion -> deletion -> substitution
    (so insertions/deletions surface rather than being swallowed by substitutions).
    Returns dict with counts and alignment list.
    """
    r = ref_tokens
    h = hyp_tokens
    n = len(r); m = len(h)
    # build dp
    dp = [[0] * (m+1) for _ in range(n+1)]
    for i in range(1, n+1): dp[i][0] = i
    for j in range(1, m+1): dp[0][j] = j
    for i in range(1, n+1):
        for j in range(1, m+1):
            cost = 0 if r[i-1] == h[j-1] else 1
            dp[i][j] = min(dp[i-1][j] + 1, dp[i][j-1] + 1, dp[i-1][j-1] + cost)

    # backtrace
    i, j = n, m
    subs = ins = dels = hits = 0
    alignment = []
    while i > 0 or j > 0:
        if i > 0 and j > 0 and dp[i][j] == dp[i-1][j-1] and r[i-1] == h[j-1]:
            alignment.append((r[i-1], h[j-1], "OK"))
            hits += 1
            i -= 1; j -= 1
        elif j > 0 and dp[i][j] == dp[i][j-1] + 1:
            alignment.append(("", h[j-1], "I"))
            ins += 1
            j -= 1
        elif i > 0 and dp[i][j] == dp[i-1][j] + 1:
            alignment.append((r[i-1], "", "D"))
            dels += 1
            i -= 1
        elif i > 0 and j > 0 and dp[i][j] == dp[i-1][j-1] + 1:
            alignment.append((r[i-1], h[j-1], "S"))
            subs += 1
            i -= 1; j -= 1
        else:
            # fallback safety
            if i > 0:
                alignment.append((r[i-1], "", "D")); dels += 1; i -= 1
            elif j > 0:
                alignment.append(("", h[j-1], "I")); ins += 1; j -= 1

    alignment.reverse()
    truth_len = n
    wer = (subs + ins + dels) / truth_len if truth_len > 0 else 0.0
    return {
        "substitutions": subs,
        "insertions": ins,
        "deletions": dels,
        "hits": hits,
        "truth_length": truth_len,
        "wer": wer,
        "alignment": alignment
    }

def write_eval_and_alignment(ref_path, hyp_path, measures, out_dir):
    hyp_fname = os.path.basename(hyp_path)
    base = hyp_fname.rsplit(".txt", 1)[0]
    eval_fname = base + "_eval.txt"
    align_fname = base + "_alignment.csv"
    eval_path = os.path.join(out_dir, eval_fname)
    align_path = os.path.join(out_dir, align_fname)

    with open(eval_path, "w", encoding="utf-8") as f:
        f.write(f"Reference: {ref_path}\n")
        f.write(f"Hypothesis: {hyp_path}\n")
        f.write(f"WER: {measures['wer']:.6f}\n")
        f.write(f"Substitutions: {measures['substitutions']}\n")
        f.write(f"Insertions: {measures['insertions']}\n")
        f.write(f"Deletions: {measures['deletions']}\n")
        f.write(f"Hits: {measures['hits']}\n")
        f.write(f"Truth length (tokens): {measures['truth_length']}\n\n")
        f.write("=== Reference Tokens ===\n")
        f.write(" ".join(read_tokens(ref_path)) + "\n\n")
        f.write("=== Hypothesis Tokens ===\n")
        f.write(" ".join(read_tokens(hyp_path)) + "\n\n")

    with open(align_path, "w", newline="", encoding="utf-8") as csvf:
        writer = csv.writer(csvf)
        writer.writerow(["ref_token", "hyp_token", "op"])
        for r, h, op in measures["alignment"]:
            writer.writerow([r, h, op])

    return eval_path, align_path

def main():
    parser = argparse.ArgumentParser(description="Evaluate tokenized STT outputs against tokenized references")
    parser.add_argument("--out", required=True, help="output dir (contains hypothesis .txt/.token.txt files)")
    parser.add_argument("--samples", default=DEFAULT_SAMPLES_DIR, help="samples dir containing reference token files")
    args = parser.parse_args()

    out_dir = args.out
    samples_dir = args.samples

    if not os.path.isdir(out_dir):
        print(f"ERROR: specified out directory does not exist: {out_dir}")
        sys.exit(1)
    if not os.path.isdir(samples_dir):
        print(f"ERROR: samples dir not found: {samples_dir}")
        sys.exit(1)

    # build reference mapping (prefer tokenized refs)
    ref_map = build_reference_map(samples_dir)
    if not ref_map:
        print(f"ERROR: no reference files found in samples dir: {samples_dir}")
        sys.exit(1)

    summary_map = {}

    for basename in sorted(ref_map.keys()):
        ref_path = ref_map[basename]
        hyps_by_model = collect_hypotheses_by_model(out_dir, basename)
        if not hyps_by_model:
            print(f"Warning: no hypothesis files found for basename {basename} in {out_dir}")
            continue
        for model_name, hyp_path in sorted(hyps_by_model.items()):
            ref_tokens = read_tokens(ref_path)
            hyp_tokens = read_tokens(hyp_path)
            measures = compute_measures_local(ref_tokens, hyp_tokens)
            eval_path, align_path = write_eval_and_alignment(ref_path, hyp_path, measures, out_dir)
            key = (basename, model_name)
            row = [basename, model_name, measures["wer"], measures["substitutions"], measures["insertions"], measures["deletions"], ref_path, hyp_path, eval_path, align_path]
            summary_map[key] = row
            print(f"Evaluated: {basename} / {model_name} -> WER {measures['wer']:.6f}")

    csv_path = os.path.join(out_dir, "evaluation_summary.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as csvf:
        writer = csv.writer(csvf)
        writer.writerow(["basename","model","wer","substitutions","insertions","deletions","reference","hypothesis","eval_file","alignment_csv"])
        for key in sorted(summary_map.keys()):
            writer.writerow(summary_map[key])

    print(f"Done. Summary: {csv_path}")

if __name__ == "__main__":
    main()
