#!/usr/bin/env python3
# extract_transcripts.py
# JSON -> plain transcript .txt
# Usage:
#   python extract_transcripts.py --out output/20251108_085456

import os
import argparse
import json

def extract_from_json(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        j = json.load(f)
    # collect top alternative transcripts, join with space
    texts = []
    for r in j.get('results', []):
        alts = r.get('alternatives', [])
        if alts:
            texts.append(alts[0].get('transcript', '').strip())
    return ' '.join(texts)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True, help='output/<timestamp> dir')
    args = parser.parse_args()

    out = args.out
    if not os.path.isdir(out):
        print('out dir not found:', out)
        return

    for fname in os.listdir(out):
        if not fname.lower().endswith('.json'):
            continue
        jpath = os.path.join(out, fname)
        txt = extract_from_json(jpath)
        # create txt filename: replace .json -> .txt
        tpath = os.path.join(out, fname[:-5] + '.txt')
        with open(tpath, 'w', encoding='utf-8') as f:
            f.write(txt + '\n')
        print('wrote', tpath)

if __name__ == '__main__':
    main()
