#!/usr/bin/env python3
"""
normalize_tokenize.py (updated)

- Input reference files expected as: <basename>_ref.txt  (this rule is kept)
- Output reference token files: <basename>_ref.token.txt
- Hypothesis token files: <basename>_<model>.token.txt (as before)

Usage:
  python normalize_tokenize.py --samples samples --out output/<timestamp>
"""
import os
import re
import argparse
import unicodedata
from fugashi import Tagger

# Simple punctuation set to remove (common Japanese/ASCII punctuation)
PUNCT_SIMPLE = re.compile(
    r'[、。．，・：；！？ー―〜…“”「」『』（）\(\)\[\]{}〈〉《》<>\"\'\`\-–—:;.,!?·]'
)

# control chars
CONTROL_RE = re.compile(r'[\x00-\x1F\x7F]')

def normalize_text(s: str) -> str:
    s = unicodedata.normalize('NFKC', s)
    s = s.replace('\u3000', ' ')
    s = CONTROL_RE.sub('', s)
    s = PUNCT_SIMPLE.sub('', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def tokenize_text(s: str, tagger: Tagger) -> str:
    tokens = [w.surface for w in tagger(s)]
    return ' '.join(tokens)

def make_ref_token_filename(orig_fname: str) -> str:
    # Expect orig_fname like "<basename>_ref.txt"
    name = os.path.splitext(orig_fname)[0]
    # if endswith _ref or _reference, keep base accordingly
    if name.endswith('_ref'):
        base = name[:-4]
        return base + '_ref.token.txt'
    if name.endswith('_reference'):
        base = name[:-10]
        return base + '_ref.token.txt'
    # fallback: replace .txt with _ref.token.txt
    return name + '_ref.token.txt'

def process_samples(samples_dir: str, tagger: Tagger):
    for fname in sorted(os.listdir(samples_dir)):
        if not fname.lower().endswith('.txt'):
            continue
        # skip already tokenized (ref.token.txt)
        if fname.endswith('_ref.token.txt') or fname.endswith('_reference.token.txt'):
            continue
        path = os.path.join(samples_dir, fname)
        with open(path, 'r', encoding='utf-8') as f:
            raw = f.read().strip()
        norm = normalize_text(raw)
        tokenized = tokenize_text(norm, tagger)
        out_name = make_ref_token_filename(fname)
        out_path = os.path.join(samples_dir, out_name)
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(tokenized + '\n')
        print('wrote', out_path)

def process_hypotheses(out_dir: str, tagger: Tagger):
    for fname in sorted(os.listdir(out_dir)):
        # consider .txt hypothesis files (created by extract_transcripts.py)
        if not fname.lower().endswith('.txt'):
            continue
        # skip token files already present
        if fname.endswith('.token.txt'):
            continue
        path = os.path.join(out_dir, fname)
        with open(path, 'r', encoding='utf-8') as f:
            raw = f.read().strip()
        # remove spaces inserted by STT, then normalize and re-tokenize
        nospace = raw.replace(' ', '')
        norm = normalize_text(nospace)
        tokenized = tokenize_text(norm, tagger)
        out_name = os.path.splitext(fname)[0] + '.token.txt'
        out_path = os.path.join(out_dir, out_name)
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(tokenized + '\n')
        print('wrote', out_path)

def main():
    parser = argparse.ArgumentParser(description='Normalize and tokenize reference and hypothesis texts (ref files expected as *_ref.txt)')
    parser.add_argument('--samples', default='samples', help='samples directory (contains reference .txt files)')
    parser.add_argument('--out', required=True, help='output/<timestamp> directory (contains hypothesis .txt files)')
    args = parser.parse_args()

    samples_dir = args.samples
    out_dir = args.out

    if not os.path.isdir(samples_dir):
        print('samples dir not found:', samples_dir)
        return
    if not os.path.isdir(out_dir):
        print('out dir not found:', out_dir)
        return

    tagger = Tagger('-Owakati')

    process_samples(samples_dir, tagger)
    process_hypotheses(out_dir, tagger)

if __name__ == '__main__':
    main()
