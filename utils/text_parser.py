"""
テキストパーサー・JSONバリデーションモジュール

Gemini生成JSONおよび保存JSONの読み込み・検証を行う。
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from utils.coord_utils import validate_rel_coords, VALID_ANNOTATION_TYPES


# バリデーション結果の型定義
class ValidationResult:
    """バリデーション結果を保持するクラス"""

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.data: Optional[Dict[str, Any]] = None

    @property
    def is_valid(self) -> bool:
        """エラーがない場合True"""
        return len(self.errors) == 0

    def add_error(self, message: str) -> None:
        """エラーを追加"""
        self.errors.append(message)

    def add_warning(self, message: str) -> None:
        """警告を追加"""
        self.warnings.append(message)


def parse_json(json_text: str) -> ValidationResult:
    """
    JSON文字列をパースし、基本的な構文チェックを行う

    Args:
        json_text: JSON形式の文字列

    Returns:
        ValidationResult: パース結果
    """
    result = ValidationResult()

    try:
        data = json.loads(json_text)
        result.data = data
    except json.JSONDecodeError as e:
        result.add_error(f"JSON構文エラー: {str(e)}")

    return result


def validate_gemini_json(
    data: Dict[str, Any],
    video_duration: Optional[float] = None
) -> ValidationResult:
    """
    Gemini生成JSONのバリデーション

    Args:
        data: パース済みJSONデータ
        video_duration: 動画の長さ（秒）。Noneの場合はtimestamp動画長チェックをスキップ（プレビューモード）

    Returns:
        ValidationResult: バリデーション結果
    """
    result = ValidationResult()
    result.data = data.copy()

    # project_name のチェック・補完
    if "project_name" not in data or not isinstance(data.get("project_name"), str):
        result.add_warning("project_name が欠落しています。「無題のプロジェクト」で補完します")
        result.data["project_name"] = "無題のプロジェクト"

    # video_path の補完（Gemini出力には含まれないため警告なし）
    if "video_path" not in data or not isinstance(data.get("video_path"), str):
        result.data["video_path"] = ""

    # steps配列のチェック（必須）
    if "steps" not in data:
        result.add_error("steps 配列が存在しません")
        return result

    if not isinstance(data["steps"], list):
        result.add_error("steps はリストである必要があります")
        return result

    if len(data["steps"]) == 0:
        result.add_warning("steps 配列が空です")

    # 各ステップのバリデーション
    seen_ids = set()
    validated_steps = []

    for idx, step in enumerate(data["steps"]):
        step_errors = []
        step_warnings = []
        step_data = step.copy() if isinstance(step, dict) else {}

        if not isinstance(step, dict):
            result.add_error(f"steps[{idx}]: ステップはオブジェクトである必要があります")
            continue

        # id のチェック
        if "id" not in step:
            result.add_error(f"steps[{idx}]: id フィールドが存在しません")
            continue

        step_id = step["id"]
        if not isinstance(step_id, int) or step_id < 1:
            result.add_error(f"steps[{idx}]: id は1以上の整数である必要があります（現在値: {step_id}）")
            continue

        if step_id in seen_ids:
            result.add_error(f"steps[{idx}]: id={step_id} が重複しています")
            continue

        seen_ids.add(step_id)

        # timestamp のチェック
        if "timestamp" not in step:
            result.add_error(f"steps[{idx}] (id={step_id}): timestamp フィールドが存在しません")
            continue

        timestamp = step["timestamp"]
        if not isinstance(timestamp, (int, float)):
            result.add_error(f"steps[{idx}] (id={step_id}): timestamp は数値である必要があります")
            continue

        if timestamp < 0:
            result.add_error(f"steps[{idx}] (id={step_id}): timestamp は0以上である必要があります（現在値: {timestamp}）")
            continue

        # timestamp動画長チェック（video_durationが指定されている場合のみ）
        if video_duration is not None and timestamp > video_duration:
            result.add_warning(
                f"steps[{idx}] (id={step_id}): timestamp ({timestamp}秒) が動画長 ({video_duration}秒) を超えています"
            )

        # title のチェック
        if "title" in step:
            if not isinstance(step["title"], str):
                step_warnings.append(f"steps[{idx}] (id={step_id}): title は文字列である必要があります")
                step_data["title"] = str(step["title"])
        else:
            step_data["title"] = ""

        # description のチェック
        if "description" in step:
            if not isinstance(step["description"], str):
                step_warnings.append(f"steps[{idx}] (id={step_id}): description は文字列である必要があります")
                step_data["description"] = str(step["description"])
        else:
            step_data["description"] = ""

        # annotations 初期化（Gemini出力では空の場合あり）
        if "annotations" not in step_data:
            step_data["annotations"] = []

        for warning in step_warnings:
            result.add_warning(warning)

        validated_steps.append(step_data)

    result.data["steps"] = validated_steps
    return result


def validate_saved_json(
    data: Dict[str, Any],
    video_duration: Optional[float] = None
) -> ValidationResult:
    """
    保存済みJSONのバリデーション（annotations含む）

    Args:
        data: パース済みJSONデータ
        video_duration: 動画の長さ（秒）。Noneの場合はプレビューモード

    Returns:
        ValidationResult: バリデーション結果
    """
    # まずGemini JSONとしてバリデーション
    result = validate_gemini_json(data, video_duration)

    if not result.is_valid:
        return result

    # video_info のチェック（null許容）
    if "video_info" in data:
        video_info = data["video_info"]
        if video_info is not None and not isinstance(video_info, dict):
            result.add_error("video_info はオブジェクトまたはnullである必要があります")
        result.data["video_info"] = video_info
    else:
        result.data["video_info"] = None

    # metadata のチェック
    if "metadata" in data:
        if not isinstance(data["metadata"], dict):
            result.add_warning("metadata はオブジェクトである必要があります。無視します")
            result.data["metadata"] = _create_default_metadata()
        else:
            result.data["metadata"] = data["metadata"]
            # app_version チェック（将来のマイグレーション用）
            if "app_version" in data["metadata"]:
                # 現在は警告のみ
                pass
    else:
        result.data["metadata"] = _create_default_metadata()

    # 各ステップのannotationsバリデーション
    for idx, step in enumerate(result.data["steps"]):
        step_id = step["id"]

        if "annotations" not in step:
            step["annotations"] = []
            continue

        if not isinstance(step["annotations"], list):
            result.add_error(f"steps[{idx}] (id={step_id}): annotations はリストである必要があります")
            step["annotations"] = []
            continue

        validated_annotations = []
        for ann_idx, ann in enumerate(step["annotations"]):
            if not isinstance(ann, dict):
                result.add_warning(
                    f"steps[{idx}] (id={step_id}): annotations[{ann_idx}] はオブジェクトである必要があります。スキップします"
                )
                continue

            # type チェック
            if "type" not in ann:
                result.add_warning(
                    f"steps[{idx}] (id={step_id}): annotations[{ann_idx}] に type がありません。スキップします"
                )
                continue

            ann_type = ann["type"]
            if ann_type not in VALID_ANNOTATION_TYPES:
                result.add_warning(
                    f"steps[{idx}] (id={step_id}): annotations[{ann_idx}] の type '{ann_type}' は無効です。スキップします"
                )
                continue

            # polygon注釈のフィルタリング（VideoProcessorが未サポートのため）
            if ann_type == "polygon":
                result.add_warning(
                    f"steps[{idx}] (id={step_id}): annotations[{ann_idx}] の polygon 注釈はサポート対象外のためスキップします"
                )
                continue

            # rel_coords チェック
            if "rel_coords" not in ann:
                result.add_warning(
                    f"steps[{idx}] (id={step_id}): annotations[{ann_idx}] に rel_coords がありません。スキップします"
                )
                continue

            is_valid, error_msg = validate_rel_coords(ann_type, ann["rel_coords"])
            if not is_valid:
                result.add_warning(
                    f"steps[{idx}] (id={step_id}): annotations[{ann_idx}] の rel_coords が無効です: {error_msg}。スキップします"
                )
                continue

            # 有効な注釈として追加
            validated_annotations.append(ann)

        step["annotations"] = validated_annotations

    return result


def validate_all_timestamps(
    steps: List[Dict[str, Any]],
    duration: float
) -> List[int]:
    """
    全ステップのtimestampを検証し、動画長を超過しているステップIDのリストを返す

    Args:
        steps: ステップのリスト
        duration: 動画の長さ（秒）

    Returns:
        超過しているstep_idのリスト
    """
    exceeded_ids = []

    for step in steps:
        if not isinstance(step, dict):
            continue

        step_id = step.get("id")
        timestamp = step.get("timestamp")

        if step_id is None or timestamp is None:
            continue

        if isinstance(timestamp, (int, float)) and timestamp > duration:
            exceeded_ids.append(step_id)

    return exceeded_ids


def _create_default_metadata() -> Dict[str, Any]:
    """デフォルトのmetadataを生成"""
    now = datetime.now(timezone.utc).isoformat()
    return {
        "created_at": now,
        "modified_at": now,
        "app_version": "1.0.0"
    }


def parse_and_validate(
    json_text: str,
    video_duration: Optional[float] = None,
    is_saved_json: bool = False
) -> ValidationResult:
    """
    JSON文字列をパースしてバリデーションを実行

    Args:
        json_text: JSON形式の文字列
        video_duration: 動画の長さ（秒）。Noneの場合はプレビューモード
        is_saved_json: 保存済みJSONかどうか（Trueの場合はannotations等も検証）

    Returns:
        ValidationResult: バリデーション結果
    """
    # JSONパース
    parse_result = parse_json(json_text)
    if not parse_result.is_valid:
        return parse_result

    # バリデーション
    if is_saved_json:
        return validate_saved_json(parse_result.data, video_duration)
    else:
        return validate_gemini_json(parse_result.data, video_duration)
