"""
一時ファイル管理モジュール
"""

import tempfile
import os
from pathlib import Path
from typing import Optional
import numpy as np
import cv2


class TempFileManager:
    """一時ファイルを管理するクラス"""

    def __init__(self, prefix: str = "m2m_", suffix: str = ".jpg"):
        """
        初期化

        Args:
            prefix: 一時ファイルのプレフィックス
            suffix: 一時ファイルのサフィックス（拡張子）
        """
        self.prefix = prefix
        self.suffix = suffix
        self.temp_dir: Optional[Path] = None
        self.created_files: list = []

    def create_temp_dir(self) -> Path:
        """
        一時ディレクトリを作成

        Returns:
            作成された一時ディレクトリのパス
        """
        if self.temp_dir is None:
            self.temp_dir = Path(tempfile.mkdtemp(prefix=self.prefix))
        return self.temp_dir

    def save_frame(self, frame: np.ndarray, filename: str) -> Path:
        """
        フレームを一時ファイルとして保存

        Args:
            frame: 保存するフレーム画像（numpy配列）
            filename: 保存するファイル名

        Returns:
            保存されたファイルのパス
        """
        if self.temp_dir is None:
            self.create_temp_dir()

        filepath = self.temp_dir / filename
        cv2.imwrite(str(filepath), frame)
        self.created_files.append(filepath)
        return filepath

    def get_temp_path(self, filename: str) -> Path:
        """
        一時ファイルのパスを取得（ファイルを作成せずにパスだけ取得）

        Args:
            filename: ファイル名

        Returns:
            一時ファイルのパス
        """
        if self.temp_dir is None:
            self.create_temp_dir()
        return self.temp_dir / filename

    def cleanup(self):
        """一時ファイルを削除"""
        # 作成したファイルを削除
        for filepath in self.created_files:
            try:
                if filepath.exists():
                    filepath.unlink()
            except Exception as e:
                print(f"Warning: ファイル '{filepath}' の削除に失敗しました: {e}")

        self.created_files.clear()

        # 一時ディレクトリを削除
        if self.temp_dir is not None and self.temp_dir.exists():
            try:
                self.temp_dir.rmdir()
            except Exception as e:
                print(f"Warning: ディレクトリ '{self.temp_dir}' の削除に失敗しました: {e}")
            finally:
                self.temp_dir = None

    def __enter__(self):
        """コンテキストマネージャーのエントリ"""
        self.create_temp_dir()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャーの終了"""
        self.cleanup()
