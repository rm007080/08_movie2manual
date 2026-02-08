# 動画マニュアル作成ツール - モジュール実装

## 概要

既存の `capture_images.py` をベースに、座標変換ロジックと動画処理モジュールをリファクタリングして実装しました。

## モジュール構成

```
utils/
├── __init__.py              # モジュールエクスポート設定
├── coord_utils.py           # 座標変換ユーティリティ
├── video_processor.py       # 動画処理クラス
└── temp_manager.py          # 一時ファイル管理クラス

tests/
├── test_video_processor.py  # 完全なテストスイート
└── test_video_processor_simple.sh  # シンプルな検証スクリプト
```

## 実装内容

### 1. coord_utils.py - 座標変換ユーティリティ

Canvasのピクセル座標と動画の相対座標（0.0-1.0）の変換を行います。

#### 主な関数

- `pixel_to_relative(x, y, canvas_width, canvas_height)` - ピクセル座標から相対座標へ変換
- `relative_to_pixel(rx, ry, video_width, video_height)` - 相対座標からピクセル座標へ変換
- `rect_to_relative(rect_coords, canvas_width, canvas_height)` - 矩形のピクセル座標を相対座標へ変換
- `rect_to_pixel(rel_coords, video_width, video_height)` - 矩形の相対座標をピクセル座標へ変換
- `arrow_to_relative(arrow_coords, canvas_width, canvas_height)` - 矢印のピクセル座標を相対座標へ変換
- `arrow_to_pixel(rel_coords, video_width, video_height)` - 矢印の相対座標をピクセル座標へ変換

#### 使用例

```python
from utils import rect_to_pixel

# 相対座標 (0.253, 0.281, 0.443, 0.311) を1920x1080の動画のピクセル座標に変換
x1, y1, x2, y2 = rect_to_pixel((0.253, 0.281, 0.443, 0.311), 1920, 1080)
# 結果: (485, 303, 850, 335)
```

### 2. video_processor.py - 動画処理モジュール

動画からのフレーム抽出、注釈描画（焼き込み）を行います。

#### VideoProcessorクラス

```python
from utils import VideoProcessor

# 初期化（コンテキストマネージャー使用推奨）
with VideoProcessor("video.mp4") as processor:
    # 動画情報を取得
    info = processor.get_video_info()
    print(f"サイズ: {info['width']}x{info['height']}")
    print(f"FPS: {info['fps']}")

    # フレームを抽出
    frame = processor.extract_frame(13.0)  # 13秒のフレーム

    # 注釈を描画
    annotations = [
        {
            "type": "rect",
            "rel_coords": (0.253, 0.281, 0.443, 0.311),
            "color": (0, 0, 255),  # BGR形式で赤
            "thickness": 3
        },
        {
            "type": "arrow",
            "rel_coords": (0.203, 0.296, 0.253, 0.296),
            "color": (0, 0, 255),
            "thickness": 4
        }
    ]
    annotated_frame = processor.draw_annotations(frame, annotations)

    # または、1行で処理
    result_frame = processor.process_step(13.0, annotations)
```

#### 主なメソッド

- `get_video_info()` - 動画情報を取得（幅、高さ、FPS、総フレーム数）
- `extract_frame(time_sec)` - 指定秒数のフレームを抽出
- `draw_rect(frame, rel_coords, color, thickness)` - 矩形を描画
- `draw_arrow(frame, rel_coords, color, thickness)` - 矢印を描画
- `draw_annotations(frame, annotations)` - 複数の注釈を描画
- `process_step(time_sec, annotations)` - フレーム抽出と注釈描画を一度に実行

### 3. temp_manager.py - 一時ファイル管理モジュール

一時ファイルの作成と削除を管理します。

#### TempFileManagerクラス

```python
from utils import TempFileManager

# コンテキストマネージャー使用推奨（自動的にクリーンアップ）
with TempFileManager(prefix="m2m_", suffix=".jpg") as temp_mgr:
    temp_dir = temp_mgr.create_temp_dir()
    temp_path = temp_mgr.save_frame(frame, "step1.jpg")
    # スコープを抜けると自動的に一時ファイルが削除される

# パスだけを取得したい場合
temp_mgr = TempFileManager()
path = temp_mgr.get_temp_path("output.jpg")
temp_mgr.cleanup()  # 手動でクリーンアップ
```

## 既存コードとの互換性

この実装は既存の `capture_images.py` のロジックを完全に保持しています。

### 既存コードの座標変換ロジック（93-95行目）

```python
rx1, ry1, rx2, ry2 = drawing["rel_coords"]
x1, y1 = int(width * rx1), int(height * ry1)
x2, y2 = int(width * rx2), int(height * ry2)
```

### 新しいモジュールでの実装

```python
from utils import rect_to_pixel

x1, y1, x2, y2 = rect_to_pixel((rx1, ry1, rx2, ry2), width, height)
```

両者は全く同じ結果になります。

## 使用例: capture_images.py のリファクタリング版

既存の `capture_images.py` は新しいモジュールを使って以下のように書き換えられます：

```python
from utils import VideoProcessor

def create_manual_images(video_path, output_dir):
    """動画からマニュアル用画像を生成"""
    import os
    os.makedirs(output_dir, exist_ok=True)

    tasks = [
        {
            "time_sec": 13.0,
            "filename": "step1_select_menu_v2.jpg",
            "drawings": [
                {"type": "rect", "rel_coords": (0.253, 0.281, 0.443, 0.311)},
                {"type": "arrow", "rel_coords": (0.203, 0.296, 0.253, 0.296)}
            ]
        },
        # ... 他のタスク
    ]

    with VideoProcessor(video_path) as processor:
        for task in tasks:
            frame = processor.process_step(task["time_sec"], task["drawings"])
            if frame is not None:
                output_path = os.path.join(output_dir, task["filename"])
                cv2.imwrite(output_path, frame)
                print(f"Saved: {output_path}")
```

## テスト

テストスクリプトを実行して動作を確認してください：

```bash
# PowerShellの場合
.venv\Scripts\python.exe tests\test_video_processor.py

# Bashの場合
.venv/bin/python tests/test_video_processor.py
```

テスト内容：

1. **座標変換テスト** - 既存のロジックと同じ結果になるか確認
2. **動画処理テスト** - フレーム抽出と注釈描画の動作確認
3. **統合テスト** - 既存の `capture_images.py` と同じ処理結果になるか確認

## 技術仕様

### 相対座標システム

- 範囲: 0.0 から 1.0
- 原点: 左上 (0.0, 0.0)
- 終点: 右下 (1.0, 1.0)
- 形式: `(rx1, ry1, rx2, ry2)` のタプル

### 色指定

- OpenCVのBGR形式: `(B, G, R)` のタプル
- 例: `(0, 0, 255)` は赤、`(255, 0, 0)` は青

### エラーハンドリング

- 不正な座標値に対しては `ValueError` をスロー
- 動画ファイルの読み込みエラーには `IOError` をスロー
- フレーム抽出失敗時は `None` を返却

## ファイルパス

- `/mnt/c/Users/littl/app-dev/08_movie2manual/utils/` - ユーティリティモジュール
- `/mnt/c/Users/littl/app-dev/08_movie2manual/tests/` - テストスクリプト

## 次のステップ

1. Streamlitアプリケーションからこれらのモジュールを呼び出す
2. GAS化のためのAPIエンドポイントを実装
3. Word文書生成モジュールと統合
