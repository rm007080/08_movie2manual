#!/usr/bin/env python3
"""
新しいutilsモジュールの使用例

このスクリプトは、utilsモジュールの使い方を示します。
既存のcapture_images.pyと同じ処理を新しいモジュールで実装します。
"""

import os
import sys

# utilsモジュールのインポート
from utils import VideoProcessor, TempFileManager, rect_to_pixel


def example_1_basic_usage():
    """例1: 基本的な使い方"""
    print("\n=== 例1: 基本的な使い方 ===")

    video_path = "テスト-20260115_131708-会議の録音.mp4"
    output_dir = "example_output"

    if not os.path.exists(video_path):
        print(f"動画ファイルが見つかりません: {video_path}")
        return

    # 出力ディレクトリの作成
    os.makedirs(output_dir, exist_ok=True)

    # VideoProcessorの使用
    with VideoProcessor(video_path) as processor:
        # 動画情報の表示
        info = processor.get_video_info()
        print(f"動画サイズ: {info['width']}x{info['height']}")
        print(f"FPS: {info['fps']:.2f}")
        print(f"再生時間: {info['duration_sec']:.2f}秒")

        # フレームの抽出
        frame = processor.extract_frame(13.0)
        if frame is not None:
            print(f"フレーム抽出成功: {frame.shape}")


def example_2_draw_annotations():
    """例2: 注釈の描画"""
    print("\n=== 例2: 注釈の描画 ===")

    video_path = "テスト-20260115_131708-会議の録音.mp4"

    if not os.path.exists(video_path):
        print(f"動画ファイルが見つかりません: {video_path}")
        return

    # 注釈の定義
    annotations = [
        {
            "type": "rect",
            "rel_coords": (0.253, 0.281, 0.443, 0.311),
            "color": (0, 0, 255),  # 赤
            "thickness": 3
        },
        {
            "type": "arrow",
            "rel_coords": (0.203, 0.296, 0.253, 0.296),
            "color": (0, 0, 255),  # 赤
            "thickness": 4
        }
    ]

    # フレームの処理
    with VideoProcessor(video_path) as processor:
        frame = processor.process_step(13.0, annotations)
        if frame is not None:
            print("注釈付きフレームの作成に成功")


def example_3_coordinate_conversion():
    """例3: 座標変換"""
    print("\n=== 例3: 座標変換 ===")

    from utils import (
        pixel_to_relative,
        relative_to_pixel,
        rect_to_relative,
        arrow_to_relative
    )

    # ピクセル座標 → 相対座標
    canvas_width, canvas_height = 1000, 500
    x, y = 100, 50
    rx, ry = pixel_to_relative(x, y, canvas_width, canvas_height)
    print(f"ピクセル座標 ({x}, {y}) → 相対座標 ({rx:.3f}, {ry:.3f})")

    # 相対座標 → ピクセル座標
    video_width, video_height = 1920, 1080
    rx1, ry1 = 0.253, 0.281
    x1, y1 = relative_to_pixel(rx1, ry1, video_width, video_height)
    print(f"相対座標 ({rx1}, {ry1}) → ピクセル座標 ({x1}, {y1})")

    # 矩形の座標変換
    rect_pixels = [100, 50, 200, 100]
    rect_rel = rect_to_relative(rect_pixels, canvas_width, canvas_height)
    print(f"矩形 {rect_pixels} → 相対座標 {tuple(round(v, 3) for v in rect_rel)}")


def example_4_batch_processing():
    """例4: バッチ処理（capture_images.pyと同等）"""
    print("\n=== 例4: バッチ処理 ===")

    import cv2

    video_path = "テスト-20260115_131708-会議の録音.mp4"
    output_dir = "example_batch_output"

    if not os.path.exists(video_path):
        print(f"動画ファイルが見つかりません: {video_path}")
        return

    # 出力ディレクトリの作成
    os.makedirs(output_dir, exist_ok=True)

    # タスク定義（既存のcapture_images.pyと同じ形式）
    tasks = [
        {
            "time_sec": 13.0,
            "filename": "step1_select_menu.jpg",
            "drawings": [
                {
                    "type": "rect",
                    "rel_coords": (0.253, 0.281, 0.443, 0.311),
                    "color": (0, 0, 255),
                    "thickness": 3
                },
                {
                    "type": "arrow",
                    "rel_coords": (0.203, 0.296, 0.253, 0.296),
                    "color": (0, 0, 255),
                    "thickness": 4
                }
            ]
        },
        {
            "time_sec": 24.0,
            "filename": "step2_search_teams.jpg",
            "drawings": [
                {
                    "type": "rect",
                    "rel_coords": (0.466, 0.473, 0.517, 0.52),
                    "color": (0, 0, 255),
                    "thickness": 3
                },
                {
                    "type": "arrow",
                    "rel_coords": (0.416, 0.496, 0.466, 0.496),
                    "color": (0, 0, 255),
                    "thickness": 4
                }
            ]
        }
    ]

    # バッチ処理の実行
    with VideoProcessor(video_path) as processor:
        for i, task in enumerate(tasks, 1):
            frame = processor.process_step(task["time_sec"], task["drawings"])
            if frame is not None:
                output_path = os.path.join(output_dir, task["filename"])
                cv2.imwrite(output_path, frame)
                print(f"✓ タスク {i}/{len(tasks)}: {task['filename']} を保存")

    print(f"\n出力ディレクトリ: {output_dir}")


def example_5_temp_file_management():
    """例5: 一時ファイル管理"""
    print("\n=== 例5: 一時ファイル管理 ===")

    import cv2

    video_path = "テスト-20260115_131708-会議の録音.mp4"

    if not os.path.exists(video_path):
        print(f"動画ファイルが見つかりません: {video_path}")
        return

    # TempFileManagerの使用
    with TempFileManager(prefix="example_", suffix=".jpg") as temp_mgr:
        # 一時ディレクトリの作成
        temp_dir = temp_mgr.create_temp_dir()
        print(f"一時ディレクトリ: {temp_dir}")

        # フレームを一時ファイルとして保存
        with VideoProcessor(video_path) as processor:
            frame = processor.extract_frame(13.0)
            if frame is not None:
                temp_path = temp_mgr.save_frame(frame, "frame.jpg")
                print(f"一時ファイル: {temp_path}")
                print(f"ファイル存在確認: {temp_path.exists()}")

    # スコープを抜けると自動的にクリーンアップ
    print("一時ファイルは自動的に削除されました")


def example_6_individual_methods():
    """例6: 個別メソッドの使用"""
    print("\n=== 例6: 個別メソッドの使用 ===")

    video_path = "テスト-20260115_131708-会議の録音.mp4"

    if not os.path.exists(video_path):
        print(f"動画ファイルが見つかりません: {video_path}")
        return

    with VideoProcessor(video_path) as processor:
        # フレームの取得
        frame = processor.extract_frame(13.0)
        if frame is None:
            print("フレームの取得に失敗")
            return

        # 矩形の描画
        frame_with_rect = processor.draw_rect(
            frame,
            rel_coords=(0.253, 0.281, 0.443, 0.311),
            color=(0, 0, 255),
            thickness=3
        )
        print("✓ 矩形を描画")

        # 矢印の描画
        frame_with_arrow = processor.draw_arrow(
            frame_with_rect,
            rel_coords=(0.203, 0.296, 0.253, 0.296),
            color=(0, 0, 255),
            thickness=4
        )
        print("✓ 矢印を描画")

        # 複数の注釈をまとめて描画
        annotations = [
            {"type": "rect", "rel_coords": (0.253, 0.281, 0.443, 0.311)},
            {"type": "arrow", "rel_coords": (0.203, 0.296, 0.253, 0.296)}
        ]
        frame_with_annotations = processor.draw_annotations(frame, annotations)
        print("✓ 複数の注釈を描画")


def main():
    """メイン関数"""
    print("=" * 60)
    print("utilsモジュール 使用例")
    print("=" * 60)

    # 例の実行
    example_1_basic_usage()
    example_2_draw_annotations()
    example_3_coordinate_conversion()
    example_4_batch_processing()
    example_5_temp_file_management()
    example_6_individual_methods()

    print("\n" + "=" * 60)
    print("すべての例が完了しました")
    print("=" * 60)


if __name__ == "__main__":
    main()
