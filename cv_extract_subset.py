#!/usr/bin/env python3
"""
cv_extract_subset.py

- Hugging Face 上の fsicoli/common_voice_22_0 日本語データセットを利用
- サンプル件数を指定して cv_samples フォルダに抽出
- 音声ファイル(.mp3) とテキスト(.txt) を保存

Usage:
  python cv_extract_subset.py --split train --num 100 --out cv_samples
"""

import os
import argparse
from datasets import load_dataset
import random
import shutil

def main():
    parser = argparse.ArgumentParser(description="Extract subset of Common Voice Japanese dataset")
    parser.add_argument('--split', default='train', help='train/validation/test')
    parser.add_argument('--num', type=int, default=100, help='Number of samples to extract')
    parser.add_argument('--out', default='cv_samples', help='Output folder')
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)
    os.makedirs(os.path.join(args.out, 'clips'), exist_ok=True)

    print(f"Loading dataset from Hugging Face (Japanese, split={args.split})...")
    dataset = load_dataset("fsicoli/common_voice_22_0", "Japanese", split=args.split)

    total = len(dataset)
    n = min(args.num, total)
    print(f"Dataset has {total} samples. Sampling {n} samples.")

    indices = random.sample(range(total), n)

    for idx in indices:
        item = dataset[idx]
        audio_path = item['path']  # ローカルに自動ダウンロードされる
        text = item['sentence']

        # コピー先のパス
        fname = os.path.basename(audio_path)
        dst_audio = os.path.join(args.out, 'clips', fname)
        shutil.copy(audio_path, dst_audio)

        # 書き起こしテキスト
        txt_name = os.path.splitext(fname)[0] + '.txt'
        dst_txt = os.path.join(args.out, txt_name)
        with open(dst_txt, 'w', encoding='utf-8') as f:
            f.write(text + '\n')

    print(f"Finished. {n} samples saved to {args.out}")

if __name__ == "__main__":
    main()
