# Watson STT Comparison

目的: IBM Watson Speech to Text の **従来モデル** と **大規模モデル** を比較するためのサンプルコード集。

- `stt_run.py` : 音声ファイルを Watson に投げて JSON とテキストを出力
- `evaluate.py` : WER を算出
- Codespaces 用の devcontainer 構成を含む

## セットアップ

### 1. 仮想環境作成（Codespaces / Ubuntu / WSL）
```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. パッケージインストール
```bash
pip install --upgrade pip
pip install ibm-watson ibm-cloud-sdk-core python-dotenv jiwer tqdm
```

### 3. 環境変数設定
- `.env` ファイルを作成：
```
WATSON_API_KEY=your_api_key
WATSON_URL=https://api.jp-tok.speech-to-text.watson.cloud.ibm.com
```
- `.gitignore` に `.env` を追加して公開しない

### 4. 音声ファイル実行例
```bash
python stt_run.py samples/NHKラジオニュース_20251108_1400_1.wav
```

使い方:
1. WATSON_API_KEY, WATSON_URL を環境変数に設定
2. `samples/` に音声と参照テキストを置く
3. `stt_run.py` を実行 → `output_*.txt` が作られる
4. `evaluate.py` で WER を計算
