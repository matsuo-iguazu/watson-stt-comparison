#!/usr/bin/env python3
"""stt_run.py

使い方（例）:
  python stt_run.py samples/NHKラジオニュース_20251108_1400_1.wav
  python stt_run.py --all samples/  # samples/ 配下の .wav をすべて処理

出力:
  output/<timestamp>/<basename>_<model>.json
  output/<timestamp>/<basename>_<model>.txt
  output/<timestamp>/<basename>_times.txt  # 各モデルの実行時間を記録
"""

import os
import sys
import json
import argparse
import time
from datetime import datetime
from ibm_watson import SpeechToTextV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from dotenv import load_dotenv

# .env を読み込む（存在すれば）
load_dotenv()

# デフォルト設定
DEFAULT_BROADBAND = "ja-JP_BroadbandModel"
DEFAULT_LARGE = "ja-JP"
OUTPUT_DIR = "output"


def recognize_file(api_key, url, audio_path, model=None, content_type="audio/wav"):
    """Watson Speech to Text に audio_path を投げて JSON を返す。"""
    auth = IAMAuthenticator(api_key)
    stt = SpeechToTextV1(authenticator=auth)
    stt.set_service_url(url)

    with open(audio_path, "rb") as audio_file:
        kwargs = {"audio": audio_file, "content_type": content_type}
        if model:
            kwargs["model"] = model
        resp = stt.recognize(**kwargs).get_result()
    return resp


def best_text_from_result(result_json):
    transcripts = []
    for r in result_json.get("results", []):
        alt = r.get("alternatives", [])
        if alt:
            transcripts.append(alt[0].get("transcript", "").strip())
    return " ".join(transcripts)


def save_outputs(base_out_dir, basename, model_name, result_json, text):
    os.makedirs(base_out_dir, exist_ok=True)
    safe_model = model_name.replace("/", "_")
    json_path = os.path.join(base_out_dir, "{}_{}.json".format(basename, safe_model))
    txt_path = os.path.join(base_out_dir, "{}_{}.txt".format(basename, safe_model))
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result_json, f, ensure_ascii=False, indent=2)
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(text)
    return json_path, txt_path


def write_time_summary(base_out_dir, basename, times):
    os.makedirs(base_out_dir, exist_ok=True)
    summary_path = os.path.join(base_out_dir, f"{basename}_times.txt")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(f"Execution times for {basename}\n")
        f.write("# model, status, duration_s, json_path, txt_path, note\n")
        for t in times:
            dur = t.get("duration_s", 0.0)
            line = "{}, {}, {:.3f}, {}, {}, {}\n".format(
                t.get("model", ""),
                t.get("status", ""),
                dur,
                t.get("json_path", ""),
                t.get("txt_path", ""),
                t.get("note", ""),
            )
            f.write(line)
    return summary_path


def process_file(api_key, url, audio_path, models, out_dir):
    basename = os.path.splitext(os.path.basename(audio_path))[0]
    print("Processing: {} -> basename={}".format(audio_path, basename))

    times = []

    for model in models:
        print("  -> model: {}".format(model))
        start = time.perf_counter()
        try:
            res = recognize_file(api_key, url, audio_path, model=model)
            text = best_text_from_result(res)
            json_path, txt_path = save_outputs(out_dir, basename, model, res, text)
            duration = time.perf_counter() - start
            times.append(
                {
                    "model": model,
                    "status": "OK",
                    "duration_s": duration,
                    "json_path": json_path,
                    "txt_path": txt_path,
                    "note": "",
                }
            )
            print("    saved: {}, {} (duration: {:.3f}s)".format(json_path, txt_path, duration))
        except Exception as e:
            duration = time.perf_counter() - start
            times.append(
                {
                    "model": model,
                    "status": "ERROR",
                    "duration_s": duration,
                    "json_path": "",
                    "txt_path": "",
                    "note": str(e),
                }
            )
            print("    ERROR recognizing with model={}: {} (duration: {:.3f}s)".format(model, e, duration))

    summary_path = write_time_summary(out_dir, basename, times)
    print("  time summary saved: {}".format(summary_path))


def find_wav_files(path):
    if os.path.isfile(path):
        return [path]
    files = []
    for entry in os.listdir(path):
        full = os.path.join(path, entry)
        if os.path.isfile(full) and entry.lower().endswith(".wav"):
            files.append(full)
    files.sort()
    return files


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Run Watson STT on audio files with Broadband and Large models "
            "and record execution times"
        )
    )
    parser.add_argument("audio", help="Path to .wav file or directory (if --all) or single file")
    parser.add_argument("--all", action="store_true", help="If set and audio is a dir, process all .wav in the dir")
    parser.add_argument("--out", default=OUTPUT_DIR, help="Output directory (default: output)")
    parser.add_argument("--broadband", default=DEFAULT_BROADBAND, help="Broadband model name")
    parser.add_argument("--large", default=DEFAULT_LARGE, help="Large model name")

    args = parser.parse_args()

    API_KEY = os.environ.get("WATSON_API_KEY")
    URL = os.environ.get("WATSON_URL")

    if not API_KEY or not URL:
        print("ERROR: Please set WATSON_API_KEY and WATSON_URL in .env or environment variables.")
        sys.exit(1)

    models = [args.broadband, args.large]

    targets = []
    if args.all and os.path.isdir(args.audio):
        targets = find_wav_files(args.audio)
    else:
        if not os.path.exists(args.audio):
            print("ERROR: audio path not found: {}".format(args.audio))
            sys.exit(1)
        targets = [args.audio]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir_with_ts = os.path.join(args.out, timestamp)

    for t in targets:
        process_file(API_KEY, URL, t, models, out_dir_with_ts)

    print("All done.")


if __name__ == "__main__":
    main()
