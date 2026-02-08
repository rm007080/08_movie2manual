"""
Canvas コンポーネントモジュール

streamlit-drawable-canvas のラッパークラスを提供し、
座標変換・状態管理・プレビューモードをサポートする。
"""

from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import json
import streamlit as st
from PIL import Image
import numpy as np

try:
    from streamlit_drawable_canvas import st_canvas
    CANVAS_AVAILABLE = True
except ImportError:
    CANVAS_AVAILABLE = False


from config import (
    CANVAS_MIN_HEIGHT,
    DEFAULT_DRAWING_MODE,
    DEFAULT_ANNOTATION_COLOR,
    DEFAULT_STROKE_WIDTH,
    ANNOTATION_TYPES,
)
from utils.coord_utils import (
    pixel_to_relative,
    relative_to_pixel,
    validate_rel_coords,
    VALID_ANNOTATION_TYPES,
)


def _annotations_equal(
    old: List[Dict[str, Any]],
    new: List[Dict[str, Any]],
    tolerance: float = 0.005,
) -> bool:
    """
    注釈リストが実質的に同じかを判定（座標の丸め誤差を許容）

    Args:
        old: 前回の注釈リスト
        new: 新しい注釈リスト
        tolerance: 座標の許容誤差
    """
    if len(old) != len(new):
        return False
    for o, n in zip(old, new):
        if o.get("type") != n.get("type"):
            return False
        oc = o.get("rel_coords", [])
        nc = n.get("rel_coords", [])
        if isinstance(oc, list) and oc and isinstance(oc[0], list):
            # polygon: ネスト配列
            if len(oc) != len(nc):
                return False
            for op, np_ in zip(oc, nc):
                if len(op) != len(np_):
                    return False
                for ov, nv in zip(op, np_):
                    if abs(ov - nv) > tolerance:
                        return False
        else:
            # rect/line: フラット配列
            if len(oc) != len(nc):
                return False
            for ov, nv in zip(oc, nc):
                if abs(ov - nv) > tolerance:
                    return False
    return True


@dataclass
class CanvasAnnotation:
    """Canvas上の注釈データ"""
    type: str  # "rect", "line"
    rel_coords: List[float]  # 相対座標
    color: str = DEFAULT_ANNOTATION_COLOR
    stroke_width: int = DEFAULT_STROKE_WIDTH

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "type": self.type,
            "rel_coords": self.rel_coords,
            "color": self.color,
            "stroke_width": self.stroke_width,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CanvasAnnotation":
        """辞書から生成"""
        return cls(
            type=data.get("type", "rect"),
            rel_coords=data.get("rel_coords", []),
            color=data.get("color", DEFAULT_ANNOTATION_COLOR),
            stroke_width=data.get("stroke_width", DEFAULT_STROKE_WIDTH),
        )


class CanvasComponent:
    """
    Canvas管理クラス

    Canvasの状態管理、座標変換、注釈の保存・復元を担当する。
    """

    def __init__(
        self,
        canvas_key: str = "annotation_canvas",
        min_height: int = CANVAS_MIN_HEIGHT,
    ):
        """
        Args:
            canvas_key: Streamlit Canvasのキー
            min_height: Canvas最小高さ（session_stateクリアバグ回避）
        """
        self.canvas_key = canvas_key
        self.min_height = min_height
        self._canvas_width: int = 0
        self._canvas_height: int = 0

    def _fabric_to_relative(
        self,
        obj: Dict[str, Any],
        canvas_width: int,
        canvas_height: int,
    ) -> Optional[CanvasAnnotation]:
        """
        Fabric.jsオブジェクトを相対座標の注釈に変換

        Args:
            obj: Fabric.jsオブジェクト（json_dataから取得）
            canvas_width: Canvasの幅
            canvas_height: Canvasの高さ

        Returns:
            CanvasAnnotation または None（変換失敗時）
        """
        obj_type = obj.get("type", "")

        # rect の場合
        if obj_type == "rect":
            left = obj.get("left", 0)
            top = obj.get("top", 0)
            width = obj.get("width", 0)
            height = obj.get("height", 0)
            scale_x = obj.get("scaleX", 1)
            scale_y = obj.get("scaleY", 1)

            # スケールを考慮
            actual_width = width * scale_x
            actual_height = height * scale_y

            # float のまま除算（int丸めによる精度低下を回避）
            x1 = left / canvas_width
            y1 = top / canvas_height
            x2 = (left + actual_width) / canvas_width
            y2 = (top + actual_height) / canvas_height

            rel_coords = [x1, y1, x2, y2]
            is_valid, _ = validate_rel_coords("rect", rel_coords)
            if not is_valid:
                return None

            return CanvasAnnotation(
                type="rect",
                rel_coords=rel_coords,
                color=obj.get("stroke", DEFAULT_ANNOTATION_COLOR),
                stroke_width=int(obj.get("strokeWidth", DEFAULT_STROKE_WIDTH)),
            )

        # line の場合
        elif obj_type == "line":
            left = obj.get("left", 0)
            top = obj.get("top", 0)
            x1_offset = obj.get("x1", 0)
            y1_offset = obj.get("y1", 0)
            x2_offset = obj.get("x2", 0)
            y2_offset = obj.get("y2", 0)

            # 実際の座標を計算
            px1 = left + x1_offset
            py1 = top + y1_offset
            px2 = left + x2_offset
            py2 = top + y2_offset

            # float のまま除算（int丸めによる精度低下を回避）
            rx1 = px1 / canvas_width
            ry1 = py1 / canvas_height
            rx2 = px2 / canvas_width
            ry2 = py2 / canvas_height

            rel_coords = [rx1, ry1, rx2, ry2]
            is_valid, _ = validate_rel_coords("line", rel_coords)
            if not is_valid:
                return None

            return CanvasAnnotation(
                type="line",
                rel_coords=rel_coords,
                color=obj.get("stroke", DEFAULT_ANNOTATION_COLOR),
                stroke_width=int(obj.get("strokeWidth", DEFAULT_STROKE_WIDTH)),
            )

        # path（polygon）の場合
        elif obj_type == "path":
            path_data = obj.get("path", [])
            if not path_data:
                return None

            # pathコマンドから点を抽出
            points = []
            for cmd in path_data:
                if len(cmd) >= 3 and cmd[0] in ("M", "L"):
                    px, py = cmd[1], cmd[2]
                    # float のまま除算（int丸めによる精度低下を回避）
                    rx = px / canvas_width
                    ry = py / canvas_height
                    points.append([rx, ry])

            # 最小3点必要
            if len(points) < 3:
                return None

            is_valid, _ = validate_rel_coords("polygon", points)
            if not is_valid:
                return None

            return CanvasAnnotation(
                type="polygon",
                rel_coords=points,
                color=obj.get("stroke", DEFAULT_ANNOTATION_COLOR),
                stroke_width=int(obj.get("strokeWidth", DEFAULT_STROKE_WIDTH)),
            )

        return None

    def _relative_to_fabric(
        self,
        annotation: CanvasAnnotation,
        canvas_width: int,
        canvas_height: int,
    ) -> Optional[Dict[str, Any]]:
        """
        相対座標の注釈をFabric.jsオブジェクトに変換

        Args:
            annotation: CanvasAnnotation
            canvas_width: Canvasの幅
            canvas_height: Canvasの高さ

        Returns:
            Fabric.jsオブジェクト辞書 または None
        """
        ann_type = annotation.type
        coords = annotation.rel_coords

        # rect の場合
        if ann_type == "rect":
            if len(coords) != 4:
                return None

            x1, y1 = relative_to_pixel(coords[0], coords[1], canvas_width, canvas_height)
            x2, y2 = relative_to_pixel(coords[2], coords[3], canvas_width, canvas_height)

            return {
                "type": "rect",
                "left": x1,
                "top": y1,
                "width": x2 - x1,
                "height": y2 - y1,
                "fill": "rgba(0, 0, 0, 0)",  # 透明
                "stroke": annotation.color,
                "strokeWidth": annotation.stroke_width,
                "scaleX": 1,
                "scaleY": 1,
            }

        # line の場合
        elif ann_type == "line":
            if len(coords) != 4:
                return None

            x1, y1 = relative_to_pixel(coords[0], coords[1], canvas_width, canvas_height)
            x2, y2 = relative_to_pixel(coords[2], coords[3], canvas_width, canvas_height)

            # Fabric.js lineオブジェクトの座標計算
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2

            return {
                "type": "line",
                "left": center_x,
                "top": center_y,
                "x1": x1 - center_x,
                "y1": y1 - center_y,
                "x2": x2 - center_x,
                "y2": y2 - center_y,
                "originX": "center",
                "originY": "center",
                "stroke": annotation.color,
                "strokeWidth": annotation.stroke_width,
            }

        # polygon の場合
        elif ann_type == "polygon":
            if not isinstance(coords, list) or len(coords) < 3:
                return None

            # pathコマンドを生成
            path_commands = []
            for i, point in enumerate(coords):
                if len(point) != 2:
                    return None
                px, py = relative_to_pixel(point[0], point[1], canvas_width, canvas_height)
                cmd = "M" if i == 0 else "L"
                path_commands.append([cmd, px, py])

            # パスを閉じる
            if path_commands:
                first_point = path_commands[0]
                path_commands.append(["L", first_point[1], first_point[2]])

            return {
                "type": "path",
                "path": path_commands,
                "stroke": annotation.color,
                "strokeWidth": annotation.stroke_width,
                "fill": "rgba(0, 0, 0, 0)",
            }

        return None

    def create_initial_drawing(
        self,
        annotations: List[Dict[str, Any]],
        canvas_width: int,
        canvas_height: int,
    ) -> Dict[str, Any]:
        """
        保存された注釈からinitial_drawingデータを生成

        Args:
            annotations: 注釈リスト（dictのリスト）
            canvas_width: Canvasの幅
            canvas_height: Canvasの高さ

        Returns:
            initial_drawing用の辞書
        """
        objects = []

        for ann_dict in annotations:
            # 元の Fabric.js オブジェクトがあればそのまま再利用（座標ずれを完全に回避）
            stored_fabric = ann_dict.get("_fabric_obj")
            if stored_fabric is not None:
                objects.append(stored_fabric)
            else:
                # JSON インポート等で _fabric_obj がない場合のみ相対座標から変換
                annotation = CanvasAnnotation.from_dict(ann_dict)
                fabric_obj = self._relative_to_fabric(annotation, canvas_width, canvas_height)
                if fabric_obj:
                    objects.append(fabric_obj)

        return {
            "version": "4.4.0",  # Fabric.jsバージョン
            "objects": objects,
        }

    def parse_canvas_result(
        self,
        json_data: Optional[Dict[str, Any]],
        canvas_width: int,
        canvas_height: int,
    ) -> List[Dict[str, Any]]:
        """
        Canvas結果から注釈リストを抽出

        Args:
            json_data: st_canvasの戻り値のjson_data
            canvas_width: Canvasの幅
            canvas_height: Canvasの高さ

        Returns:
            注釈辞書のリスト
        """
        if not json_data or "objects" not in json_data:
            return []

        annotations = []
        for obj in json_data.get("objects", []):
            annotation = self._fabric_to_relative(obj, canvas_width, canvas_height)
            if annotation:
                d = annotation.to_dict()
                # 元の Fabric.js オブジェクトを保持（Canvas再構築時に再利用）
                d["_fabric_obj"] = obj
                annotations.append(d)

        return annotations


class AnnotationCanvas:
    """
    注釈Canvas UIコンポーネント

    Streamlitアプリ内で使用する高レベルなCanvasコンポーネント。
    プレビューモード、ステップ管理、自動保存機能を提供する。
    """

    def __init__(
        self,
        session_state_key_prefix: str = "canvas",
    ):
        """
        Args:
            session_state_key_prefix: Session Stateキーのプレフィックス
        """
        self.key_prefix = session_state_key_prefix
        self.canvas_component = CanvasComponent()

    def _get_session_key(self, name: str) -> str:
        """Session Stateキーを生成"""
        return f"{self.key_prefix}_{name}"

    def render(
        self,
        background_image: Optional[Image.Image],
        step_id: int,
        steps_by_id: Dict[int, Dict[str, Any]],
        preview_mode: bool = False,
        drawing_mode: str = DEFAULT_DRAWING_MODE,
        stroke_color: str = DEFAULT_ANNOTATION_COLOR,
        stroke_width: int = DEFAULT_STROKE_WIDTH,
        canvas_height: int = CANVAS_MIN_HEIGHT,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Canvasをレンダリング

        Args:
            background_image: 背景画像（PIL Image）
            step_id: 現在のステップID
            steps_by_id: ステップ辞書（ID→ステップデータ）
            preview_mode: プレビューモードフラグ
            drawing_mode: 描画モード（"rect", "line"）
            stroke_color: 線の色
            stroke_width: 線の幅
            canvas_height: Canvasの高さ

        Returns:
            更新された注釈リスト、または None（変更なし/プレビューモード時）
        """
        if not CANVAS_AVAILABLE:
            st.error("streamlit-drawable-canvas がインストールされていません")
            return None

        # プレビューモードの場合
        if preview_mode:
            st.warning("動画をアップロードすると注釈機能が有効になります")
            st.info("プレビューモード: Canvas描画は無効です")
            return None

        # 背景画像がない場合
        if background_image is None:
            st.warning("フレーム画像がありません")
            return None

        # Canvas サイズ計算
        img_width, img_height = background_image.size
        aspect_ratio = img_width / img_height
        canvas_width = int(canvas_height * aspect_ratio)

        # 最小高さを確保
        if canvas_height < CANVAS_MIN_HEIGHT:
            canvas_height = CANVAS_MIN_HEIGHT
            canvas_width = int(canvas_height * aspect_ratio)

        # 背景画像をリサイズ
        resized_image = background_image.resize((canvas_width, canvas_height))

        # 現在のステップの注釈を取得
        current_step = steps_by_id.get(step_id, {})
        current_annotations = current_step.get("annotations", [])

        # Canvas再初期化フラグ（初回 or 明示的な再初期化要求時のみTrue）
        reinit_key = f"{self.key_prefix}_reinit_{step_id}"
        cache_key = f"{self.key_prefix}_cached_drawing_{step_id}"
        needs_reinit = st.session_state.get(reinit_key, True)

        if needs_reinit:
            # 再初期化が必要 → 新しい initial_drawing を生成してキャッシュ
            use_initial_drawing = self.canvas_component.create_initial_drawing(
                current_annotations,
                canvas_width,
                canvas_height,
            )
            st.session_state[cache_key] = use_initial_drawing
            st.session_state[reinit_key] = False
        else:
            # 通常のリラン → キャッシュされた initial_drawing を使用
            # （同じJSON内容 → Reactが変更なしと判断 → Canvasリセットなし）
            use_initial_drawing = st.session_state.get(cache_key)
            if use_initial_drawing is None:
                use_initial_drawing = self.canvas_component.create_initial_drawing(
                    current_annotations,
                    canvas_width,
                    canvas_height,
                )
                st.session_state[cache_key] = use_initial_drawing

        # 描画モードのマッピング
        mode_mapping = {
            "rect": "rect",
            "line": "line",
        }
        canvas_mode = mode_mapping.get(drawing_mode, "rect")

        # Canvas レンダリング
        canvas_result = st_canvas(
            fill_color="rgba(0, 0, 0, 0)",  # 透明
            stroke_width=stroke_width,
            stroke_color=stroke_color,
            background_image=resized_image,
            update_streamlit=True,
            height=canvas_height,
            width=canvas_width,
            drawing_mode=canvas_mode,
            initial_drawing=use_initial_drawing,
            key=f"{self.key_prefix}_canvas_{step_id}",
        )

        # 再初期化直後はCanvasの json_data が不安定（loadFromJSON未完了）のため、
        # session state の注釈をそのまま返す
        if needs_reinit:
            return current_annotations

        # 通常時：結果の解析
        if canvas_result and canvas_result.json_data:
            new_annotations = self.canvas_component.parse_canvas_result(
                canvas_result.json_data,
                canvas_width,
                canvas_height,
            )

            # 往復変換ガード:
            # Canvas再構築後の toJSON → parse で座標がずれるのを防止。
            # 注釈数が増えた場合のみ更新（＝ユーザーが新規描画した）。
            if len(new_annotations) > len(current_annotations):
                # 既存注釈の座標は保持し、新規描画分のみ Canvas から取得
                preserved = list(current_annotations)
                new_items = new_annotations[len(current_annotations):]
                return preserved + new_items

            # 注釈数が同じ or 減った → 往復変換の誤差を排除
            return current_annotations

        return None

    def render_annotation_list(
        self,
        annotations: List[Dict[str, Any]],
        on_delete: Optional[callable] = None,
    ) -> None:
        """
        注釈一覧を表示

        Args:
            annotations: 注釈リスト
            on_delete: 削除コールバック（引数: index）
        """
        if not annotations:
            st.info("注釈がありません")
            return

        for i, ann in enumerate(annotations):
            col1, col2, col3 = st.columns([2, 4, 1])

            with col1:
                st.write(f"**{ann.get('type', 'unknown')}**")

            with col2:
                coords = ann.get("rel_coords", [])
                if ann.get("type") == "polygon":
                    st.write(f"{len(coords)}点")
                else:
                    st.write(f"[{', '.join(f'{c:.2f}' for c in coords[:4])}]")

            with col3:
                if on_delete:
                    if st.button("削除", key=f"del_ann_{i}"):
                        on_delete(i)
