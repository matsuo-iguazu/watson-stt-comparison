# ベースは軽めの Python イメージ
FROM mcr.microsoft.com/vscode/devcontainers/python:0-3.11

# 必要なら追加ツール（ffmpeg など）
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# 作業ディレクトリ
WORKDIR /workspace
