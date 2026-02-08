"""
座標変換ユーティリティモジュール

Canvasのピクセル座標と動画の相対座標（0.0-1.0）の変換を行う。
バリデーション機能も提供する。
"""

from typing import Tuple, List, Union


# 許容される注釈タイプ
VALID_ANNOTATION_TYPES = {"rect", "line", "polygon"}


def pixel_to_relative(x: int, y: int, canvas_width: int, canvas_height: int) -> Tuple[float, float]:
    """
    ピクセル座標から相対座標へ変換

    Args:
        x: ピクセルX座標
        y: ピクセルY座標
        canvas_width: キャンバスの幅（ピクセル）
        canvas_height: キャンバスの高さ（ピクセル）

    Returns:
        (相対X座標, 相対Y座標) のタプル（0.0-1.0の範囲）

    Example:
        >>> pixel_to_relative(100, 50, 1000, 500)
        (0.1, 0.1)
    """
    if canvas_width <= 0 or canvas_height <= 0:
        raise ValueError("Canvas width and height must be positive values")
    rx = x / canvas_width
    ry = y / canvas_height
    return (rx, ry)


def relative_to_pixel(rx: float, ry: float, video_width: int, video_height: int) -> Tuple[int, int]:
    """
    相対座標からピクセル座標へ変換

    Args:
        rx: 相対X座標（0.0-1.0）
        ry: 相対Y座標（0.0-1.0）
        video_width: 動画の幅（ピクセル）
        video_height: 動画の高さ（ピクセル）

    Returns:
        (ピクセルX座標, ピクセルY座標) のタプル

    Example:
        >>> relative_to_pixel(0.1, 0.1, 1000, 500)
        (100, 50)
    """
    if video_width <= 0 or video_height <= 0:
        raise ValueError("Video width and height must be positive values")
    if not (0.0 <= rx <= 1.0) or not (0.0 <= ry <= 1.0):
        raise ValueError("Relative coordinates must be between 0.0 and 1.0")
    x = round(video_width * rx)
    y = round(video_height * ry)
    return (x, y)


def rect_to_relative(rect_coords: List[int], canvas_width: int, canvas_height: int) -> Tuple[float, float, float, float]:
    """
    矩形のピクセル座標[x1,y1,x2,y2]を相対座標へ変換

    Args:
        rect_coords: 矩形のピクセル座標 [x1, y1, x2, y2]
                     (x1,y1): 左上座標, (x2,y2): 右下座標
        canvas_width: キャンバスの幅（ピクセル）
        canvas_height: キャンバスの高さ（ピクセル）

    Returns:
        (相対x1, 相対y1, 相対x2, 相対y2) のタプル（0.0-1.0の範囲）

    Example:
        >>> rect_to_relative([100, 50, 200, 100], 1000, 500)
        (0.1, 0.1, 0.2, 0.2)
    """
    if len(rect_coords) != 4:
        raise ValueError("rect_coords must be a list of 4 integers [x1, y1, x2, y2]")
    x1, y1, x2, y2 = rect_coords
    rx1 = x1 / canvas_width
    ry1 = y1 / canvas_height
    rx2 = x2 / canvas_width
    ry2 = y2 / canvas_height
    return (rx1, ry1, rx2, ry2)


def rect_to_pixel(rel_coords: Tuple[float, float, float, float], video_width: int, video_height: int) -> Tuple[int, int, int, int]:
    """
    矩形の相対座標をピクセル座標へ変換

    Args:
        rel_coords: 矩形の相対座標 (rx1, ry1, rx2, ry2)
                    (rx1,ry1): 左上座標, (rx2,ry2): 右下座標
        video_width: 動画の幅（ピクセル）
        video_height: 動画の高さ（ピクセル）

    Returns:
        (x1, y1, x2, y2) のタプル

    Example:
        >>> rect_to_pixel((0.1, 0.1, 0.2, 0.2), 1000, 500)
        (100, 50, 200, 100)
    """
    if len(rel_coords) != 4:
        raise ValueError("rel_coords must be a tuple of 4 floats (rx1, ry1, rx2, ry2)")
    rx1, ry1, rx2, ry2 = rel_coords
    x1 = round(video_width * rx1)
    y1 = round(video_height * ry1)
    x2 = round(video_width * rx2)
    y2 = round(video_height * ry2)
    return (x1, y1, x2, y2)


def arrow_to_relative(arrow_coords: List[int], canvas_width: int, canvas_height: int) -> Tuple[float, float, float, float]:
    """
    矢印のピクセル座標[x1,y1,x2,y2]を相対座標へ変換

    Args:
        arrow_coords: 矢印のピクセル座標 [x1, y1, x2, y2]
                      (x1,y1): 始点座標, (x2,y2): 終点座標
        canvas_width: キャンバスの幅（ピクセル）
        canvas_height: キャンバスの高さ（ピクセル）

    Returns:
        (相対x1, 相対y1, 相対x2, 相対y2) のタプル（0.0-1.0の範囲）

    Example:
        >>> arrow_to_relative([100, 50, 200, 100], 1000, 500)
        (0.1, 0.1, 0.2, 0.2)
    """
    if len(arrow_coords) != 4:
        raise ValueError("arrow_coords must be a list of 4 integers [x1, y1, x2, y2]")
    x1, y1, x2, y2 = arrow_coords
    rx1 = x1 / canvas_width
    ry1 = y1 / canvas_height
    rx2 = x2 / canvas_width
    ry2 = y2 / canvas_height
    return (rx1, ry1, rx2, ry2)


def arrow_to_pixel(rel_coords: Tuple[float, float, float, float], video_width: int, video_height: int) -> Tuple[int, int, int, int]:
    """
    矢印の相対座標をピクセル座標へ変換

    Args:
        rel_coords: 矢印の相対座標 (rx1, ry1, rx2, ry2)
                    (rx1,ry1): 始点座標, (rx2,ry2): 終点座標
        video_width: 動画の幅（ピクセル）
        video_height: 動画の高さ（ピクセル）

    Returns:
        (x1, y1, x2, y2) のタプル

    Example:
        >>> arrow_to_pixel((0.1, 0.1, 0.2, 0.2), 1000, 500)
        (100, 50, 200, 100)
    """
    if len(rel_coords) != 4:
        raise ValueError("rel_coords must be a tuple of 4 floats (rx1, ry1, rx2, ry2)")
    rx1, ry1, rx2, ry2 = rel_coords
    x1 = round(video_width * rx1)
    y1 = round(video_height * ry1)
    x2 = round(video_width * rx2)
    y2 = round(video_height * ry2)
    return (x1, y1, x2, y2)


def _is_valid_relative_value(value: float) -> bool:
    """相対座標値が0.0-1.0の範囲内かチェック"""
    return isinstance(value, (int, float)) and 0.0 <= value <= 1.0


def validate_rel_coords(annotation_type: str, coords: Union[List, Tuple]) -> Tuple[bool, str]:
    """
    相対座標のバリデーション

    Args:
        annotation_type: "rect", "line", または "polygon"
        coords: 座標データ
            - rect/line: [x1, y1, x2, y2] フラット配列（要素数4）
            - polygon: [[x1,y1], [x2,y2], ...] ネスト配列（3点以上）

    Returns:
        (is_valid, error_message) - 有効ならis_valid=True, error_message=""

    Examples:
        >>> validate_rel_coords("rect", [0.1, 0.2, 0.5, 0.6])
        (True, "")
        >>> validate_rel_coords("polygon", [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]])
        (True, "")
        >>> validate_rel_coords("rect", [0.1, 0.2])
        (False, "rect requires exactly 4 coordinates, got 2")
    """
    # 注釈タイプのチェック
    if annotation_type not in VALID_ANNOTATION_TYPES:
        return (False, f"Invalid annotation type: {annotation_type}. Must be one of {VALID_ANNOTATION_TYPES}")

    # coordsがリストまたはタプルかチェック
    if not isinstance(coords, (list, tuple)):
        return (False, f"coords must be a list or tuple, got {type(coords).__name__}")

    # rect/line の場合：フラット配列 [x1, y1, x2, y2]
    if annotation_type in ("rect", "line"):
        if len(coords) != 4:
            return (False, f"{annotation_type} requires exactly 4 coordinates, got {len(coords)}")

        for i, val in enumerate(coords):
            if not isinstance(val, (int, float)):
                return (False, f"Coordinate at index {i} must be a number, got {type(val).__name__}")
            if not _is_valid_relative_value(val):
                return (False, f"Coordinate at index {i} must be between 0.0 and 1.0, got {val}")

        return (True, "")

    # polygon の場合：ネスト配列 [[x1,y1], [x2,y2], ...]
    if annotation_type == "polygon":
        # 最小3点必要
        if len(coords) < 3:
            return (False, f"polygon requires at least 3 points, got {len(coords)}")

        for i, point in enumerate(coords):
            # 各点が2要素のリスト/タプルかチェック
            if not isinstance(point, (list, tuple)):
                return (False, f"Point at index {i} must be a list or tuple, got {type(point).__name__}")
            if len(point) != 2:
                return (False, f"Point at index {i} must have exactly 2 coordinates, got {len(point)}")

            # 各座標値のチェック
            for j, val in enumerate(point):
                if not isinstance(val, (int, float)):
                    return (False, f"Coordinate at point {i}, index {j} must be a number, got {type(val).__name__}")
                if not _is_valid_relative_value(val):
                    return (False, f"Coordinate at point {i}, index {j} must be between 0.0 and 1.0, got {val}")

        return (True, "")

    # ここに到達することはないが、念のため
    return (False, f"Unknown annotation type: {annotation_type}")
