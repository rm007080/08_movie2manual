"""
アプリケーション設定モジュール

アプリケーション定数、色定義、フォント設定、デフォルト値を管理する。
"""

from typing import Dict, Any

# =============================================================================
# アプリケーション情報
# =============================================================================

APP_NAME = "動画マニュアル作成ツール"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "MP4動画から操作マニュアル（Wordドキュメント）を自動生成します"

# =============================================================================
# 色定義
# =============================================================================

# 注釈の色（Hex形式）
ANNOTATION_COLORS = {
    "red": "#FF0000",
    "blue": "#0000FF",
    "green": "#00FF00",
    "yellow": "#FFFF00",
    "orange": "#FFA500",
    "purple": "#800080",
}

# デフォルト注釈色
DEFAULT_ANNOTATION_COLOR = "#FF0000"  # 赤

# OpenCV BGR形式の色（動画処理用）
ANNOTATION_COLORS_BGR = {
    "red": (0, 0, 255),
    "blue": (255, 0, 0),
    "green": (0, 255, 0),
    "yellow": (0, 255, 255),
    "orange": (0, 165, 255),
    "purple": (128, 0, 128),
}

DEFAULT_ANNOTATION_COLOR_BGR = (0, 0, 255)  # 赤

# =============================================================================
# フォント設定
# =============================================================================

# Wordドキュメント用フォント
WORD_FONT_NAME = "MS Mincho"  # 日本語フォント
WORD_FONT_SIZE_HEADING = 14  # 見出しフォントサイズ（pt）
WORD_FONT_SIZE_BODY = 10.5  # 本文フォントサイズ（pt）

# =============================================================================
# 注釈設定
# =============================================================================

# 注釈タイプ
ANNOTATION_TYPES = ["rect", "line"]

# デフォルト線幅
DEFAULT_STROKE_WIDTH = 3

# 線幅の範囲
MIN_STROKE_WIDTH = 1
MAX_STROKE_WIDTH = 10

# =============================================================================
# Canvas設定
# =============================================================================

# Canvas最小高さ（Streamlit session_stateクリアバグ回避のため）
CANVAS_MIN_HEIGHT = 300

# デフォルトCanvas描画モード
DEFAULT_DRAWING_MODE = "rect"

# =============================================================================
# 動画処理設定
# =============================================================================

# サポートする動画形式
SUPPORTED_VIDEO_FORMATS = [".mp4", ".avi", ".mov", ".mkv"]

# デフォルトFPS（情報取得失敗時）
DEFAULT_FPS = 30.0

# =============================================================================
# ファイル設定
# =============================================================================

# 出力ファイル形式
OUTPUT_DOCX_EXTENSION = ".docx"
OUTPUT_JSON_EXTENSION = ".json"

# 画像フォーマット設定
IMAGE_FORMAT_JPEG = "jpeg"
IMAGE_FORMAT_PNG = "png"
DEFAULT_IMAGE_FORMAT = IMAGE_FORMAT_JPEG
JPEG_QUALITY = 95  # 0-100（高いほど高画質・大容量）

# 一時ファイルディレクトリ名
TEMP_DIR_NAME = "temp"

# =============================================================================
# デフォルト値
# =============================================================================

# プロジェクト名デフォルト
DEFAULT_PROJECT_NAME = "無題のプロジェクト"

# デフォルトのステップタイトル
DEFAULT_STEP_TITLE = ""

# デフォルトのステップ説明
DEFAULT_STEP_DESCRIPTION = ""

# =============================================================================
# Session State キー
# =============================================================================

SESSION_KEYS = {
    "project_name": "project_name",
    "video_path": "video_path",
    "video_info": "video_info",
    "steps": "steps",
    "steps_by_id": "steps_by_id",
    "preview_mode": "preview_mode",
    "current_step_id": "current_step_id",
}

# =============================================================================
# バリデーション設定
# =============================================================================

# ステップIDの最小値
MIN_STEP_ID = 1

# 座標の有効範囲
COORD_MIN = 0.0
COORD_MAX = 1.0

# polygonの最小点数
MIN_POLYGON_POINTS = 3

# =============================================================================
# UI設定
# =============================================================================

# タブ名
TAB_NAMES = ["AI連携", "注釈エディタ", "生成・エクスポート"]

# ページレイアウト
PAGE_LAYOUT = "wide"

# =============================================================================
# ヘルパー関数
# =============================================================================


def hex_to_bgr(hex_color: str) -> tuple:
    """
    Hex色コードをOpenCV BGR形式に変換

    Args:
        hex_color: "#RRGGBB" 形式の色コード

    Returns:
        (B, G, R) タプル
    """
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return (b, g, r)


def bgr_to_hex(bgr_color: tuple) -> str:
    """
    OpenCV BGR形式をHex色コードに変換

    Args:
        bgr_color: (B, G, R) タプル

    Returns:
        "#RRGGBB" 形式の色コード
    """
    b, g, r = bgr_color
    return f"#{r:02X}{g:02X}{b:02X}"


def get_default_metadata() -> Dict[str, Any]:
    """
    デフォルトのmetadataを取得

    Returns:
        metadata辞書
    """
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()
    return {
        "created_at": now,
        "modified_at": now,
        "app_version": APP_VERSION,
    }


def get_initial_session_state() -> Dict[str, Any]:
    """
    Session Stateの初期値を取得

    Returns:
        初期化用辞書
    """
    return {
        SESSION_KEYS["project_name"]: DEFAULT_PROJECT_NAME,
        SESSION_KEYS["video_path"]: "",
        SESSION_KEYS["video_info"]: None,
        SESSION_KEYS["steps"]: [],
        SESSION_KEYS["steps_by_id"]: {},
        SESSION_KEYS["preview_mode"]: True,  # 動画未選択時はプレビューモード
        SESSION_KEYS["current_step_id"]: None,
    }
