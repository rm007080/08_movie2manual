# 動画マニュアル作成ツール

MP4動画から操作マニュアル（Wordドキュメント）を自動生成するStreamlitアプリケーションです。

**コンセプト**: "AI x Human" - AIが下書きを作り、人間が微調整を行う

## 主な機能

- **AI連携**: Geminiで生成したJSON（手順データ）をインポート
- **注釈エディタ**: 動画フレーム上に赤枠・線などの注釈を描画
- **ステップ管理**: ドラッグ&ドロップによる並べ替え、挿入・複製・削除
- **Word出力**: 目次付きのWord形式マニュアルを自動生成
- **JSON保存/読み込み**: 作業途中のデータを保存・復元

## ワークフロー

```
1. MP4動画をアップロード
2. Geminiで手順JSONを生成 → インポート
3. 各ステップのタイムスタンプ・注釈を調整
4. Wordドキュメントを生成・ダウンロード
```

## 動作環境

- Python 3.10以上（開発環境: Python 3.13）
- Windows / WSL2

## セットアップ

```bash
# リポジトリをクローン
git clone <https://github.com/rm007080/08_movie2manual.git>

# 仮想環境を作成・有効化
python -m venv .venv
source .venv/bin/activate        # Linux / WSL
# .venv\Scripts\Activate.ps1     # Windows PowerShell

# 依存パッケージをインストール
pip install -r requirements.txt
```

## 使い方

```bash
streamlit run app.py
```

ブラウザで `http://localhost:8501` が開きます。

### 1. 動画のアップロード

サイドバーからMP4ファイルをアップロードします（AVI, MOV, MKVにも対応）。

### 2. 手順データのインポート（AI連携タブ）

「AI連携」タブにあるプロンプトテンプレートをGeminiにコピーし、動画の内容を説明してJSONを生成させます。生成されたJSONをテキストエリアに貼り付けてインポートします。

### 3. 注釈の編集（注釈エディタタブ）

各ステップについて以下の操作が可能です:

- タイムスタンプの調整（フレーム位置の変更）
- フレーム上への注釈描画（矩形・線）
- タイトル・説明文の編集
- ステップの並べ替え・挿入・複製・削除

### 4. Word出力（生成・エクスポートタブ）

「Wordドキュメントを生成」ボタンをクリックすると、注釈付きフレーム画像と手順テキストを含むWordファイルが生成されます。目次も自動で挿入されます。

## プロジェクト構成

```
08_movie2manual/
├── app.py                     # メインアプリケーション
├── config.py                  # 定数・設定値
├── requirements.txt           # 依存パッケージ
├── utils/                     # コアモジュール
│   ├── video_processor.py     # 動画処理・注釈描画
│   ├── coord_utils.py         # 座標変換（ピクセル⇔相対座標）
│   ├── temp_manager.py        # 一時ファイル管理
│   ├── doc_generator.py       # Wordドキュメント生成
│   ├── text_parser.py         # JSONパース・バリデーション
│   └── __init__.py
└── ui/                        # UIコンポーネント
    ├── canvas_component.py    # Canvas描画ラッパー
    └── __init__.py
```

## 技術スタック

| カテゴリ | ライブラリ |
|---------|-----------|
| Web UI | Streamlit |
| 動画処理 | OpenCV, Pillow |
| Canvas描画 | streamlit-drawable-canvas-fix |
| ステップ並べ替え | streamlit-sortables |
| Word生成 | python-docx |
| バリデーション | Pydantic |

## テスト

```bash
# Windows Python（-X utf8 推奨）
python -X utf8 tests/test_coord_utils.py
python -X utf8 tests/test_text_parser.py
python -X utf8 tests/test_video_processor.py
python -X utf8 tests/test_doc_generator.py
```
