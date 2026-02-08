"""
動画処理モジュール

動画からのフレーム抽出、注釈描画（焼き込み）を行う。
"""

import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional


class VideoProcessor:
    """動画処理クラス"""

    def __init__(self, video_path: str):
        """
        初期化

        Args:
            video_path: 動画ファイルのパス
        """
        self.video_path = video_path
        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            raise IOError(f"動画ファイル '{video_path}' が開けません。")

        # 動画情報を取得
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))

    def get_video_info(self) -> Dict:
        """
        動画情報を取得

        Returns:
            動画情報を含む辞書
            {
                'width': 幅（ピクセル）,
                'height': 高さ（ピクセル）,
                'fps': フレームレート,
                'total_frames': 総フレーム数,
                'duration_sec': 再生時間（秒）
            }
        """
        duration_sec = self.total_frames / self.fps if self.fps > 0 else 0
        return {
            'width': self.width,
            'height': self.height,
            'fps': self.fps,
            'total_frames': self.total_frames,
            'duration_sec': duration_sec
        }

    def extract_frame(self, time_sec: float) -> Optional[np.ndarray]:
        """
        指定秒数のフレームを抽出

        Args:
            time_sec: 抽出するフレームの時間（秒）

        Returns:
            フレーム画像（numpy配列）。失敗した場合はNone。
        """
        target_frame = int(time_sec * self.fps)
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)

        ret, frame = self.cap.read()
        if not ret:
            return None
        return frame

    def draw_rect(self, frame: np.ndarray, rel_coords: Tuple,
                  color: Tuple = (0, 0, 255), thickness: int = 3) -> np.ndarray:
        """
        相対座標で矩形を描画

        Args:
            frame: フレーム画像（numpy配列）
            rel_coords: 相対座標 (rx1, ry1, rx2, ry2)
            color: 色（B, G, R）のタプル。デフォルトは赤 (0, 0, 255)
            thickness: 線の太さ。デフォルトは3

        Returns:
            矩形が描画されたフレーム画像
        """
        rx1, ry1, rx2, ry2 = rel_coords
        x1 = int(self.width * rx1)
        y1 = int(self.height * ry1)
        x2 = int(self.width * rx2)
        y2 = int(self.height * ry2)

        # フレームのコピーを作成（元のフレームを変更しないため）
        frame_copy = frame.copy()
        cv2.rectangle(frame_copy, (x1, y1), (x2, y2), color, thickness)
        return frame_copy

    def draw_line(self, frame: np.ndarray, rel_coords: Tuple,
                  color: Tuple = (0, 0, 255), thickness: int = 3) -> np.ndarray:
        """
        相対座標で直線を描画（矢じりなし）

        Args:
            frame: フレーム画像（numpy配列）
            rel_coords: 相対座標 (rx1, ry1, rx2, ry2) - 始点から終点へ
            color: 色（B, G, R）のタプル。デフォルトは赤 (0, 0, 255)
            thickness: 線の太さ。デフォルトは3

        Returns:
            直線が描画されたフレーム画像
        """
        rx1, ry1, rx2, ry2 = rel_coords
        x1 = int(self.width * rx1)
        y1 = int(self.height * ry1)
        x2 = int(self.width * rx2)
        y2 = int(self.height * ry2)

        frame_copy = frame.copy()
        cv2.line(frame_copy, (x1, y1), (x2, y2), color, thickness,
                 lineType=cv2.LINE_AA)
        return frame_copy

    def draw_arrow(self, frame: np.ndarray, rel_coords: Tuple,
                   color: Tuple = (0, 0, 255), thickness: int = 4) -> np.ndarray:
        """
        相対座標で矢印を描画

        Args:
            frame: フレーム画像（numpy配列）
            rel_coords: 相対座標 (rx1, ry1, rx2, ry2) - 始点から終点へ
            color: 色（B, G, R）のタプル。デフォルトは赤 (0, 0, 255)
            thickness: 線の太さ。デフォルトは4

        Returns:
            矢印が描画されたフレーム画像
        """
        rx1, ry1, rx2, ry2 = rel_coords
        x1 = int(self.width * rx1)
        y1 = int(self.height * ry1)
        x2 = int(self.width * rx2)
        y2 = int(self.height * ry2)

        # フレームのコピーを作成（元のフレームを変更しないため）
        frame_copy = frame.copy()
        # tipLengthは矢印の先端の大きさを調整します
        cv2.arrowedLine(frame_copy, (x1, y1), (x2, y2), color, thickness,
                       line_type=cv2.LINE_AA, tipLength=0.3)
        return frame_copy

    def draw_annotations(self, frame: np.ndarray, annotations: List[Dict]) -> np.ndarray:
        """
        複数の注釈を描画

        Args:
            frame: フレーム画像（numpy配列）
            annotations: 注釈リスト。各注釈は以下の形式：
                {
                    'type': 'rect', 'line', または 'arrow',
                    'rel_coords': (rx1, ry1, rx2, ry2),
                    'color': (B, G, R),  # オプション、デフォルトは赤
                    'thickness': int     # オプション、デフォルトは3（rect/line）または4（arrow）
                }

        Returns:
            すべての注釈が描画されたフレーム画像
        """
        result_frame = frame.copy()

        for annotation in annotations:
            if annotation['type'] == 'rect':
                color = annotation.get('color', (0, 0, 255))
                thickness = annotation.get('thickness', 3)
                result_frame = self.draw_rect(result_frame, annotation['rel_coords'],
                                             color, thickness)
            elif annotation['type'] == 'line':
                color = annotation.get('color', (0, 0, 255))
                thickness = annotation.get('thickness', 3)
                result_frame = self.draw_line(result_frame, annotation['rel_coords'],
                                             color, thickness)
            elif annotation['type'] == 'arrow':
                color = annotation.get('color', (0, 0, 255))
                thickness = annotation.get('thickness', 4)
                result_frame = self.draw_arrow(result_frame, annotation['rel_coords'],
                                              color, thickness)
            else:
                print(f"Warning: 不明な注釈タイプ '{annotation['type']}' はスキップされます。")

        return result_frame

    def process_step(self, time_sec: float, annotations: List[Dict]) -> Optional[np.ndarray]:
        """
        ステップのフレームに注釈を描画して返す

        Args:
            time_sec: 抽出するフレームの時間（秒）
            annotations: 注釈リスト（draw_annotationsメソッドと同じ形式）

        Returns:
            注釈付きのフレーム画像。失敗した場合はNone。
        """
        frame = self.extract_frame(time_sec)
        if frame is None:
            return None
        return self.draw_annotations(frame, annotations)

    def close(self):
        """リソースを解放"""
        if self.cap.isOpened():
            self.cap.release()

    def __enter__(self):
        """コンテキストマネージャーのエントリ"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャーの終了"""
        self.close()
