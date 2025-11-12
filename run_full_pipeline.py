#!/usr/bin/env python3
"""
run_full_pipeline.py (robust)

Runs full pipeline:
  1) stt_run.py  (calls STT per audio file)
  2) extract_transcripts.py
  3) normalize_tokenize.py
  4) evaluate_pipeline.py

This version detects all subdirectories under the STT output folder that contain
.hypothesis files (.json/.txt) and runs downstream steps for each detected directory.

Usage examples:
  # process all audio in samples/
  python run_full_pipeline.py --samples samples --out output/test_run

  # process only one file (basename relative to samples/)
  python run_full_pipeline.py --samples samples --file testcase.wav --out output/test_run

  # skip STT (if you already have output/<timestamp> files)
  python run_full_pipeline.py --samples samples --out output/test_run --skip-stt
"""
import argparse
import subprocess
import sys
import os
from datetime import datetime
from glob import glob

AUDIO_EXTS = ('.wav', '.mp3', '.flac', '.m4a', '.ogg')

def run_cmd(cmd):
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)

def find_audio_files(samples_dir, specific_file=None):
    if specific_file:
        p = os.path.join(samples_dir, specific_file)
        if os.path.isfile(p):
            return [p]
        # try with extensions if basename given
        for ext in AUDIO_EXTS:
            p2 = p + ext
            if os.path.isfile(p2):
                return [p2]
        raise FileNotFoundError(f"Specified file not found under samples: {specific_file}")
    # collect by extensions, non-recursive
    files = []
    for ext in AUDIO_EXTS:
        files.extend(sorted(glob(os.path.join(samples_dir, '*' + ext))))
    return files

def detect_output_dirs_recursive(base_out):
    """
    Find all directories under base_out that contain .json or .txt files.
    Returns a sorted list of unique directories. If none found, returns [base_out].
    """
    base_out = os.path.abspath(base_out)
    patterns = [os.path.join(base_out, '**', '*.json'), os.path.join(base_out, '**', '*.txt')]
    dirs = set()
    for pat in patterns:
        for p in glob(pat, recursive=True):
            dirs.add(os.path.dirname(p))
    if not dirs:
        # if nothing found, but base_out exists, fallback to base_out itself
        if os.path.isdir(base_out):
            return [base_out]
        return []
    return sorted(dirs)

def main():
    p = argparse.ArgumentParser(description="Run full STT -> tokenize -> evaluate pipeline (handles multi-subdir STT output)")
    p.add_argument('--samples', default='samples', help='samples directory (audio + _ref.txt)')
    p.add_argument('--out', help='output directory (if omitted, created as output/<timestamp>)')
    p.add_argument('--file', default=None, help='(optional) single audio filename in samples/ to process')
    p.add_argument('--skip-stt', action='store_true', help='skip the stt_run stage (useful if output already exists)')
    args = p.parse_args()

    samples_dir = args.samples
    if not os.path.isdir(samples_dir):
        print("samples dir not found:", samples_dir)
        sys.exit(1)

    # prepare out_dir (top-level where STT writes)
    out_dir_top = args.out if args.out else f"output/{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(out_dir_top, exist_ok=True)

    try:
        # 1) STT stage (per audio) unless skipped
        if not args.skip_stt:
            audio_files = find_audio_files(samples_dir, args.file)
            if not audio_files:
                print("No audio files found in samples (extensions: .wav .mp3 .flac .m4a .ogg).")
                sys.exit(1)
            for audio in audio_files:
                # call stt_run.py with positional audio arg and --out out_dir_top
                run_cmd(["python", "stt_run.py", audio, "--out", out_dir_top])
        else:
            print("Skipping STT stage (--skip-stt)")

        # Detect all output directories that contain hypothesis files
        out_dirs = detect_output_dirs_recursive(out_dir_top)
        if not out_dirs:
            print("No output directories detected under", out_dir_top)
            sys.exit(1)

        print("Detected output dirs to process:", out_dirs)

        # For each detected directory, run downstream steps
        for out_dir_for_next_steps in out_dirs:
            print("\n=== Processing downstream for:", out_dir_for_next_steps, "===\n")
            # 2) extract_transcripts.py
            run_cmd(["python", "extract_transcripts.py", "--out", out_dir_for_next_steps])
            # 3) normalize_tokenize.py
            run_cmd(["python", "normalize_tokenize.py", "--samples", samples_dir, "--out", out_dir_for_next_steps])
            # 4) evaluate_pipeline.py
            run_cmd(["python", "evaluate_pipeline.py", "--samples", samples_dir, "--out", out_dir_for_next_steps])

    except subprocess.CalledProcessError as e:
        print("Pipeline failed:", e)
        sys.exit(1)
    except FileNotFoundError as e:
        print("File error:", e)
        sys.exit(1)

    print("\nPipeline finished successfully. Processed output dirs:")
    for d in out_dirs:
        print(" -", d)

if __name__ == "__main__":
    main()
