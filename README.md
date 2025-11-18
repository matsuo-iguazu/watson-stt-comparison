# Watson Speech to Text Comparison

IBM Watson Speech to Text の日本語モデル（旧モデルと新モデル）を比較評価するための自動評価パイプラインです。
音声入力から文字起こし、正解テキストとの照合、WER（Word Error Rate）算出までを一貫して実行できます。

## 🧭 プロジェクト概要

本リポジトリは、IBM Watson Speech to Text の
- `ja-JP_BroadbandModel`（旧モデル）
- `ja-JP`（新モデル）
を比較評価する目的で作成されたものです。

ただし、`stt_run.py` 内のパラメータを変更することで、他のモデル（英語モデルなど）を対象に実行することも可能です。

---

## 📁 ディレクトリ構成

| ファイル / ディレクトリ | 説明 |
|--------------------------|------|
| `stt_run.py` | 指定した音声ファイルをIBM STT APIに送信し、認識結果を取得するメインスクリプト。`--help` オプションで使用法を確認可能。 |
| `normalize_tokenize.py` | テキストの正規化と日本語トークン化処理（Fugashi使用）。`--help` オプションで利用方法を確認可能。 |
| `evaluate_pipeline.py` | 音声→認識→WER算出の一連の流れを制御する評価スクリプト。`--help` で実行例を表示。 |
| `run_full_pipeline.py` | 全工程をまとめて実行するための統合スクリプト。`--help` でパラメータ一覧を表示。 |
| `samples/` | 音声ファイルと正解テキストのサンプル置き場。 |
| `output/` | 実行結果（認識結果・WER計算結果など）の出力先。 |

---

## ⚙️ セットアップ手順

1. **環境構築**
   ```bash
   python -m venv venv
   source venv/bin/activate   # Windowsの場合: venv\Scriptsctivate
   pip install -r requirements.txt
   ```

2. **資格情報設定**

   `.env` ファイルをリポジトリ直下に作成し、以下の内容を記述します。

   ```
   IBM_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxx
   IBM_URL=https://api.xx-xxx.speech-to-text.watson.cloud.ibm.com/instances/xxxx
   ```

---

## ▶️ 使用方法

1. **サンプルの準備**
   `samples/` に以下を配置します。
   - 音声ファイル（`.wav` 形式）*STTがサポートする音声ファイル形式であれば他も可能と思われます
   - 正解テキスト（同名 `_ref.txt`）

2. **実行例**

   ```bash
   python run_full_pipeline.py --samples samples/test1
   ```

3. **モデル指定（任意）**

   `stt_run.py` の `MODEL_ID` パラメータを変更することで利用モデルを切り替え可能です。

   ```python
   MODEL_ID = "ja-JP"  # 新モデル（デフォルト）
   # MODEL_ID = "ja-JP_BroadbandModel"  # 旧モデル
   ```

---

## 📊 出力ファイルの説明

| ファイル名 | 内容 |
|-------------|------|
| `*_transcript.txt` | 音声から認識されたテキスト |
| `*_alignment.csv` | 各トークンごとの照合結果 |
| `*_eval.txt` | 評価結果（WER・正解数・誤り数など） |
| `evaluation_summary.csv` | 全サンプルの評価結果をまとめた集計ファイル |
| `*_times.txt` | 各処理ステップの実行時間 |

---

## 💡 技術的ポイント

- **日本語トークン化**：`fugashi`（MeCabラッパー）を使用
- **WER算出**：`jiwer` ライブラリで評価
- **再現性の確保**：正規化ルール（全角→半角、句読点除去など）を統一して比較
- **モジュール構成**：各スクリプトは独立しており、個別に実行・検証可能

---

## 🧩 実装上の補足

- すべてのコードは ChatGPT によって自動生成されました。
- 各スクリプトは人手でのコードレビューや静的検査を行っていません。
- ただし、実際のテストケースを通して、以下を確認済みです：
  - 音声ファイルの処理が正常に完了すること
  - 認識テキストおよび WER の算出結果が想定通りであること
  - 実行時間（`time` 計測）が安定して出力されること

---

## 📚 参考情報

- [Watson Speech to Text リリースノート 2025/5/28](https://cloud.ibm.com/docs/speech-to-text?topic=speech-to-text-release-notes&locale=ja#speech-to-text-28may2025)
- [Qiitaブログ: 生成AI時代の音声認識（Watson STT）— 日本語STT評価：大型音声モデル（Large）対 前世代モデル](https://qiita.com/IG_Matsuo/a24e81c074c8a548db8c)

---

## 🪪 ライセンス

MIT License
© 2025 Kenji Matsuo
