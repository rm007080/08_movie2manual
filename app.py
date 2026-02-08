"""
動画マニュアル作成ツール - Streamlitアプリケーション

MP4動画から操作マニュアル（Wordドキュメント）を自動生成する。
"""

import streamlit as st
import copy
import json
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import cv2
import numpy as np
from PIL import Image
from streamlit_sortables import sort_items

from config import (
    APP_NAME,
    APP_VERSION,
    APP_DESCRIPTION,
    PAGE_LAYOUT,
    TAB_NAMES,
    SESSION_KEYS,
    DEFAULT_PROJECT_NAME,
    DEFAULT_ANNOTATION_COLOR,
    DEFAULT_STROKE_WIDTH,
    DEFAULT_DRAWING_MODE,
    ANNOTATION_COLORS,
    MIN_STROKE_WIDTH,
    MAX_STROKE_WIDTH,
    CANVAS_MIN_HEIGHT,
    SUPPORTED_VIDEO_FORMATS,
    get_initial_session_state,
    get_default_metadata,
    hex_to_bgr,
)

from utils import (
    VideoProcessor,
    TempFileManager,
    DocGenerator,
    parse_and_validate,
    validate_all_timestamps,
    ValidationResult,
)

from ui.canvas_component import AnnotationCanvas


# =============================================================================
# Session State 初期化
# =============================================================================

def init_session_state():
    """Session Stateを初期化"""
    initial_state = get_initial_session_state()
    for key, value in initial_state.items():
        if key not in st.session_state:
            st.session_state[key] = value

    # 追加のセッション変数
    if "temp_video_path" not in st.session_state:
        st.session_state.temp_video_path = None
    if "uploaded_video_name" not in st.session_state:
        st.session_state.uploaded_video_name = None
    if "exceeded_step_ids" not in st.session_state:
        st.session_state.exceeded_step_ids = []
    if "last_import_result" not in st.session_state:
        st.session_state.last_import_result = None
    if "uploaded_json_name" not in st.session_state:
        st.session_state.uploaded_json_name = None


def rebuild_steps_by_id():
    """steps配列からsteps_by_id辞書を再構築"""
    st.session_state[SESSION_KEYS["steps_by_id"]] = {
        step["id"]: step for step in st.session_state[SESSION_KEYS["steps"]]
    }


def get_next_step_id() -> int:
    """次のステップIDを取得"""
    steps = st.session_state[SESSION_KEYS["steps"]]
    if not steps:
        return 1
    return max(step["id"] for step in steps) + 1


# =============================================================================
# 動画処理
# =============================================================================

def save_uploaded_video(uploaded_file) -> Optional[str]:
    """アップロードされた動画を一時ファイルとして保存"""
    try:
        suffix = Path(uploaded_file.name).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded_file.getbuffer())
            return tmp.name
    except Exception as e:
        st.error(f"動画の保存に失敗しました: {e}")
        return None


def get_video_info(video_path: str) -> Optional[Dict[str, Any]]:
    """動画情報を取得"""
    try:
        with VideoProcessor(video_path) as vp:
            info = vp.get_video_info()
            return {
                "width": info["width"],
                "height": info["height"],
                "fps": info["fps"],
                "duration": info["duration_sec"],
            }
    except Exception as e:
        st.error(f"動画情報の取得に失敗しました: {e}")
        return None


def extract_frame_as_pil(video_path: str, timestamp: float) -> Optional[Image.Image]:
    """動画からフレームを抽出してPIL Imageとして返す"""
    try:
        with VideoProcessor(video_path) as vp:
            frame = vp.extract_frame(timestamp)
            if frame is not None:
                # BGR -> RGB変換
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                return Image.fromarray(frame_rgb)
    except Exception as e:
        st.error(f"フレーム抽出に失敗しました: {e}")
    return None


def validate_timestamps_after_upload():
    """動画アップロード後にtimestampを再検証"""
    video_info = st.session_state[SESSION_KEYS["video_info"]]
    steps = st.session_state[SESSION_KEYS["steps"]]

    if video_info and steps:
        exceeded_ids = validate_all_timestamps(steps, video_info["duration"])
        st.session_state.exceeded_step_ids = exceeded_ids
        return exceeded_ids
    return []


# =============================================================================
# JSON 保存/読み込み
# =============================================================================

def create_save_json() -> str:
    """保存用JSONを生成"""
    # _fabric_obj はCanvas内部データなので JSON保存から除外
    steps_for_save = []
    for step in st.session_state[SESSION_KEYS["steps"]]:
        step_copy = {**step}
        step_copy["annotations"] = [
            {k: v for k, v in ann.items() if k != "_fabric_obj"}
            for ann in step.get("annotations", [])
        ]
        steps_for_save.append(step_copy)

    data = {
        "project_name": st.session_state[SESSION_KEYS["project_name"]],
        "video_path": st.session_state[SESSION_KEYS["video_path"]],
        "video_info": st.session_state[SESSION_KEYS["video_info"]],
        "steps": steps_for_save,
        "metadata": {
            "created_at": get_default_metadata()["created_at"],
            "modified_at": datetime.now(timezone.utc).isoformat(),
            "app_version": APP_VERSION,
        }
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def import_json_data(json_text: str, is_saved_json: bool = False) -> ValidationResult:
    """JSONデータをインポート"""
    video_info = st.session_state[SESSION_KEYS["video_info"]]
    video_duration = video_info["duration"] if video_info else None

    result = parse_and_validate(json_text, video_duration, is_saved_json)

    if result.is_valid and result.data:
        # Session Stateを更新
        st.session_state[SESSION_KEYS["project_name"]] = result.data.get(
            "project_name", DEFAULT_PROJECT_NAME
        )
        st.session_state[SESSION_KEYS["steps"]] = result.data.get("steps", [])

        # 辞書を再構築
        rebuild_steps_by_id()

        # 全ステップのCanvas再初期化フラグをセット
        for step in result.data.get("steps", []):
            st.session_state[f"canvas_reinit_{step['id']}"] = True

        # 初回表示用の静的プレビューフラグをセット
        # (非表示タブでCanvasが正しく初期化されないため)
        st.session_state["_editor_preview_pending"] = True

        # timestamp検証
        if video_duration:
            validate_timestamps_after_upload()

    return result


# =============================================================================
# Gemini プロンプト
# =============================================================================

GEMINI_PROMPT_TEMPLATE = '''添付の動画の操作手順をJSON形式で出力してください。

## 出力形式
```json
{
  "project_name": "プロジェクト名",
  "steps": [
    {
      "id": 1,
      "timestamp": 秒数（小数可）,
      "title": "手順のタイトル",
      "description": "手順の詳細説明"
    }
  ]
}
```

## ルール
- idは1から始まる連番の整数
- timestampは動画内の該当シーンの秒数
- titleは簡潔に（20文字以内推奨）
- descriptionは具体的な操作内容を記載

## 動画の説明
{video_description}
'''


# =============================================================================
# サイドバー
# =============================================================================

def render_sidebar():
    """サイドバーをレンダリング"""
    with st.sidebar:
        st.title(APP_NAME)
        st.caption(f"v{APP_VERSION}")

        # プロジェクト名
        st.subheader("プロジェクト設定")
        project_name = st.text_input(
            "プロジェクト名",
            value=st.session_state[SESSION_KEYS["project_name"]],
            key="input_project_name"
        )
        if project_name != st.session_state[SESSION_KEYS["project_name"]]:
            st.session_state[SESSION_KEYS["project_name"]] = project_name

        st.divider()

        # 動画アップロード
        st.subheader("動画ファイル")
        uploaded_video = st.file_uploader(
            "MP4ファイルをアップロード",
            type=["mp4", "avi", "mov", "mkv"],
            key="video_uploader"
        )

        if uploaded_video:
            # 新しい動画がアップロードされた場合のみ処理
            if st.session_state.uploaded_video_name != uploaded_video.name:
                with st.spinner("動画を読み込み中..."):
                    temp_path = save_uploaded_video(uploaded_video)
                    if temp_path:
                        st.session_state.temp_video_path = temp_path
                        st.session_state.uploaded_video_name = uploaded_video.name
                        video_info = get_video_info(temp_path)
                        if video_info:
                            st.session_state[SESSION_KEYS["video_info"]] = video_info
                            st.session_state[SESSION_KEYS["video_path"]] = uploaded_video.name
                            st.session_state[SESSION_KEYS["preview_mode"]] = False

                            # timestamp再検証
                            exceeded = validate_timestamps_after_upload()
                            if exceeded:
                                st.warning(f"警告: {len(exceeded)}件のステップでtimestampが動画長を超えています")

                            st.success("動画を読み込みました")

        # 動画情報表示
        video_info = st.session_state[SESSION_KEYS["video_info"]]
        if video_info:
            st.info(f"""
            **解像度**: {video_info['width']} x {video_info['height']}
            **FPS**: {video_info['fps']:.2f}
            **長さ**: {video_info['duration']:.2f} 秒
            """)

            # 動画削除ボタン
            if st.button("動画を削除", type="secondary"):
                st.session_state.temp_video_path = None
                st.session_state.uploaded_video_name = None
                st.session_state[SESSION_KEYS["video_info"]] = None
                st.session_state[SESSION_KEYS["video_path"]] = ""
                st.session_state[SESSION_KEYS["preview_mode"]] = True
                st.session_state.exceeded_step_ids = []
        else:
            st.info("動画がアップロードされていません（プレビューモード）")

        st.divider()

        # JSON保存/読み込み
        st.subheader("設定の保存/読み込み")

        # JSON保存
        if st.session_state[SESSION_KEYS["steps"]]:
            json_data = create_save_json()
            filename = f"{st.session_state[SESSION_KEYS['project_name']]}.json"
            st.download_button(
                label="JSONを保存",
                data=json_data,
                file_name=filename,
                mime="application/json",
                key="download_json"
            )

        # JSON読み込み
        uploaded_json = st.file_uploader(
            "JSONファイルを読み込み",
            type=["json"],
            key="json_uploader"
        )

        if uploaded_json:
            # 新しいJSONファイルがアップロードされた場合のみ処理
            if st.session_state.uploaded_json_name != uploaded_json.name:
                try:
                    json_text = uploaded_json.read().decode("utf-8")
                    result = import_json_data(json_text, is_saved_json=True)
                    st.session_state.uploaded_json_name = uploaded_json.name

                    if result.is_valid:
                        st.success("JSONを読み込みました")
                        if result.warnings:
                            for warning in result.warnings:
                                st.warning(warning)
                    else:
                        for error in result.errors:
                            st.error(error)
                except Exception as e:
                    st.error(f"JSONの読み込みに失敗しました: {e}")

        st.divider()

        # ステータス表示
        st.subheader("ステータス")
        steps_count = len(st.session_state[SESSION_KEYS["steps"]])
        mode = "通常モード" if not st.session_state[SESSION_KEYS["preview_mode"]] else "プレビューモード"
        st.write(f"**モード**: {mode}")
        st.write(f"**ステップ数**: {steps_count}")


# =============================================================================
# タブ1: AI連携
# =============================================================================

def render_tab_ai():
    """AI連携タブをレンダリング"""
    st.header("AI連携")
    st.write("Geminiで生成したJSONをインポートできます。")

    # プロンプトテンプレート表示
    with st.expander("Gemini用プロンプトテンプレート", expanded=False):
        st.code(GEMINI_PROMPT_TEMPLATE, language="text")
        st.caption("このプロンプトをGeminiにコピーして使用してください。")

    st.divider()

    # JSONインポート
    st.subheader("JSONインポート")

    json_input = st.text_area(
        "GeminiからのJSON出力を貼り付け",
        height=300,
        placeholder='{"project_name": "...", "steps": [...]}',
        key="json_import_area"
    )

    col1, col2 = st.columns([1, 4])
    with col1:
        import_button = st.button("インポート", type="primary", key="import_json_btn")

    if import_button and json_input.strip():
        result = import_json_data(json_input, is_saved_json=False)
        st.session_state.last_import_result = result

        if result.is_valid:
            st.success(f"インポート成功: {len(result.data.get('steps', []))}件のステップを読み込みました")

            if result.warnings:
                st.warning("警告があります:")
                for warning in result.warnings:
                    st.write(f"- {warning}")
        else:
            st.error("インポートに失敗しました:")
            for error in result.errors:
                st.write(f"- {error}")

    # インポート結果の表示
    if st.session_state.last_import_result:
        result = st.session_state.last_import_result
        if result.is_valid and result.data:
            st.divider()
            st.subheader("インポートされたステップ")

            for step in result.data.get("steps", []):
                step_id = step.get("id", "?")
                is_exceeded = step_id in st.session_state.exceeded_step_ids
                warning_mark = " ⚠️" if is_exceeded else ""

                with st.expander(f"ステップ {step_id}: {step.get('title', '無題')}{warning_mark}"):
                    st.write(f"**タイムスタンプ**: {step.get('timestamp', 0):.2f} 秒")
                    st.write(f"**説明**: {step.get('description', '')}")

                    if is_exceeded:
                        st.warning("このステップのtimestampは動画長を超えています")


# =============================================================================
# タブ2: 注釈エディタ
# =============================================================================

def render_tab_editor():
    """注釈エディタタブをレンダリング"""
    st.header("注釈エディタ")

    steps = st.session_state[SESSION_KEYS["steps"]]
    steps_by_id = st.session_state[SESSION_KEYS["steps_by_id"]]
    preview_mode = st.session_state[SESSION_KEYS["preview_mode"]]
    video_info = st.session_state[SESSION_KEYS["video_info"]]

    if not steps:
        st.info("ステップがありません。AI連携タブでJSONをインポートしてください。")

        # 手動でステップを追加
        if st.button("新しいステップを追加"):
            new_step = {
                "id": get_next_step_id(),
                "timestamp": 0.0,
                "title": "",
                "description": "",
                "annotations": []
            }
            st.session_state[SESSION_KEYS["steps"]].append(new_step)
            rebuild_steps_by_id()
            st.rerun()
        return

    # ステップ選択
    step_labels = []
    for step in steps:
        step_id = step["id"]
        is_exceeded = step_id in st.session_state.exceeded_step_ids
        warning_mark = " ⚠️" if is_exceeded else ""
        step_labels.append(f"ステップ {step_id}: {step.get('title', '無題')}{warning_mark}")

    # ドラッグ&ドロップ対応ステップ一覧
    st.subheader("ステップ一覧")
    sorted_labels = sort_items(step_labels)

    # 並び替え検知 → session state更新
    if sorted_labels != step_labels:
        label_to_idx = {label: i for i, label in enumerate(step_labels)}
        new_order = [label_to_idx[label] for label in sorted_labels]
        new_steps = [steps[i] for i in new_order]
        st.session_state[SESSION_KEYS["steps"]] = new_steps
        rebuild_steps_by_id()
        st.rerun()

    # 並び替え・挿入後の選択位置を反映
    default_index = st.session_state.pop("_pending_step_index", None)
    if default_index is not None and default_index < len(step_labels):
        # radioウィジェットの前に値を設定 → widget描画時に反映される
        st.session_state["step_selector"] = default_index
    else:
        default_index = 0

    # ステップ選択（radio）
    selected_index = st.radio(
        "編集するステップ",
        range(len(steps)),
        format_func=lambda i: step_labels[i],
        index=default_index,
        key="step_selector",
        label_visibility="collapsed"
    )

    # ステップ操作ボタン（一覧直下）
    op_col1, op_col2, op_col3, op_col4, op_col5 = st.columns(5)

    with op_col1:
        if selected_index > 0:
            if st.button("▲ 上へ", key="move_step_up_btn"):
                steps_list = st.session_state[SESSION_KEYS["steps"]]
                idx = selected_index
                steps_list[idx - 1], steps_list[idx] = steps_list[idx], steps_list[idx - 1]
                rebuild_steps_by_id()
                st.session_state["_pending_step_index"] = idx - 1
                st.rerun()
        else:
            st.button("▲ 上へ", key="move_step_up_btn", disabled=True)

    with op_col2:
        if selected_index < len(steps) - 1:
            if st.button("▼ 下へ", key="move_step_down_btn"):
                steps_list = st.session_state[SESSION_KEYS["steps"]]
                idx = selected_index
                steps_list[idx], steps_list[idx + 1] = steps_list[idx + 1], steps_list[idx]
                rebuild_steps_by_id()
                st.session_state["_pending_step_index"] = idx + 1
                st.rerun()
        else:
            st.button("▼ 下へ", key="move_step_down_btn", disabled=True)

    with op_col3:
        if st.button("+ 挿入", key="insert_step_btn"):
            current_ts = steps[selected_index].get("timestamp", 0)
            new_step = {
                "id": get_next_step_id(),
                "timestamp": current_ts + 1.0,
                "title": "",
                "description": "",
                "annotations": []
            }
            st.session_state[SESSION_KEYS["steps"]].insert(selected_index + 1, new_step)
            rebuild_steps_by_id()
            st.session_state["_pending_step_index"] = selected_index + 1
            st.rerun()

    with op_col4:
        if st.button("⧉ 複製", key="dup_step_btn"):
            source = steps[selected_index]
            new_step = {
                "id": get_next_step_id(),
                "timestamp": source.get("timestamp", 0),
                "title": source.get("title", ""),
                "description": source.get("description", ""),
                "annotations": copy.deepcopy(source.get("annotations", []))
            }
            st.session_state[SESSION_KEYS["steps"]].insert(selected_index + 1, new_step)
            rebuild_steps_by_id()
            st.session_state["_pending_step_index"] = selected_index + 1
            st.rerun()

    with op_col5:
        if len(steps) > 1:
            if st.button("✕ 削除", key="del_step_btn", type="secondary"):
                current_step_id_to_del = steps[selected_index]["id"]
                st.session_state[SESSION_KEYS["steps"]] = [
                    s for s in steps if s["id"] != current_step_id_to_del
                ]
                rebuild_steps_by_id()
                st.rerun()
        else:
            st.button("✕ 削除", key="del_step_btn", disabled=True)

    current_step = steps[selected_index]
    current_step_id = current_step["id"]

    # ステップ切り替え検知 → Canvas再初期化（保存済み注釈を initial_drawing に反映）
    prev_step_id = st.session_state.get(SESSION_KEYS["current_step_id"])
    if prev_step_id is not None and prev_step_id != current_step_id:
        st.session_state[f"canvas_reinit_{current_step_id}"] = True

    st.session_state[SESSION_KEYS["current_step_id"]] = current_step_id

    # timestamp超過警告
    if current_step_id in st.session_state.exceeded_step_ids:
        st.warning("⚠️ このステップのタイムスタンプは動画長を超えています。修正してください。")

    st.divider()

    # 2カラムレイアウト
    col_left, col_right = st.columns([3, 2])

    with col_left:
        # フレームプレビュー / Canvas
        st.subheader("フレームプレビュー")

        # タイムスタンプ調整
        max_duration = video_info["duration"] if video_info else 100.0
        raw_ts = float(current_step.get("timestamp", 0))
        safe_value = min(max(raw_ts, 0.0), max_duration)
        timestamp = st.slider(
            "タイムスタンプ（秒）",
            min_value=0.0,
            max_value=max_duration,
            value=safe_value,
            step=0.1,
            key=f"timestamp_slider_{current_step_id}"
        )

        # タイムスタンプを更新
        if timestamp != current_step.get("timestamp"):
            current_step["timestamp"] = timestamp
            # exceeded_step_idsを更新
            if video_info:
                validate_timestamps_after_upload()

        if preview_mode:
            # プレビューモード: プレースホルダー表示
            st.info("🎬 動画をアップロードするとフレームプレビューが表示されます")

            # プレースホルダー画像
            placeholder = Image.new("RGB", (640, 360), color=(50, 50, 50))
            st.image(placeholder, caption="フレームプレビュー（動画未選択）", use_container_width=True)
        else:
            # 通常モード: フレーム表示 + Canvas
            temp_video_path = st.session_state.temp_video_path
            if temp_video_path:
                frame_image = extract_frame_as_pil(temp_video_path, timestamp)

                if frame_image:
                    preview_pending = st.session_state.get("_editor_preview_pending", False)

                    if preview_pending:
                        # JSONインポート直後: 静的プレビュー表示
                        # (非表示タブでCanvas/Fabric.jsが背景画像を正しく初期化できないため)
                        st.image(frame_image, use_container_width=True)
                        st.session_state["_editor_preview_pending"] = False
                    else:
                        # 描画設定
                        st.subheader("描画設定")
                        draw_col1, draw_col2, draw_col3 = st.columns(3)

                        with draw_col1:
                            drawing_mode = st.selectbox(
                                "描画モード",
                                ["rect", "line"],
                                index=0,
                                key=f"drawing_mode_{current_step_id}"
                            )

                        with draw_col2:
                            stroke_color = st.color_picker(
                                "線の色",
                                value=DEFAULT_ANNOTATION_COLOR,
                                key=f"stroke_color_{current_step_id}"
                            )

                        with draw_col3:
                            stroke_width = st.slider(
                                "線の太さ",
                                min_value=MIN_STROKE_WIDTH,
                                max_value=MAX_STROKE_WIDTH,
                                value=DEFAULT_STROKE_WIDTH,
                                key=f"stroke_width_{current_step_id}"
                            )

                        # Canvas
                        canvas = AnnotationCanvas()
                        annotations = canvas.render(
                            background_image=frame_image,
                            step_id=current_step_id,
                            steps_by_id=steps_by_id,
                            preview_mode=False,
                            drawing_mode=drawing_mode,
                            stroke_color=stroke_color,
                            stroke_width=stroke_width,
                            canvas_height=400,
                        )

                        # 注釈を保存（変更がある場合のみ）
                        if annotations is not None:
                            old_annotations = current_step.get("annotations", [])
                            if annotations is not old_annotations:
                                current_step["annotations"] = annotations
                else:
                    st.error("フレームの抽出に失敗しました")
            else:
                st.warning("動画ファイルが見つかりません。動画を再アップロードしてください。")
                placeholder = Image.new("RGB", (640, 360), color=(50, 50, 50))
                st.image(placeholder, caption="動画を再アップロードしてください", use_container_width=True)

        # ステップ間ナビゲーションボタン
        nav_col1, nav_col2, nav_spacer = st.columns([1, 1, 8])
        with nav_col1:
            if selected_index > 0:
                if st.button("◀ 前へ", key="nav_prev_step"):
                    st.session_state["_pending_step_index"] = selected_index - 1
                    st.rerun()
            else:
                st.button("◀ 前へ", key="nav_prev_step", disabled=True)
        with nav_col2:
            if selected_index < len(steps) - 1:
                if st.button("次へ ▶", key="nav_next_step"):
                    st.session_state["_pending_step_index"] = selected_index + 1
                    st.rerun()
            else:
                st.button("次へ ▶", key="nav_next_step", disabled=True)

    with col_right:
        # テキスト編集
        st.subheader("ステップ情報")

        # タイトル
        title = st.text_input(
            "タイトル",
            value=current_step.get("title", ""),
            key=f"title_input_{current_step_id}"
        )
        if title != current_step.get("title"):
            current_step["title"] = title

        # 説明
        description = st.text_area(
            "説明",
            value=current_step.get("description", ""),
            height=150,
            key=f"desc_input_{current_step_id}"
        )
        if description != current_step.get("description"):
            current_step["description"] = description

        st.divider()

        # 注釈一覧
        st.subheader("注釈一覧")
        annotations = current_step.get("annotations", [])

        if annotations:
            for i, ann in enumerate(annotations):
                col_ann1, col_ann2, col_ann3 = st.columns([2, 3, 1])

                with col_ann1:
                    st.write(f"**{ann.get('type', 'unknown')}**")

                with col_ann2:
                    coords = ann.get("rel_coords", [])
                    if ann.get("type") == "polygon":
                        st.write(f"{len(coords)}点")
                    else:
                        coord_str = ", ".join(f"{c:.2f}" for c in coords[:4])
                        st.write(f"[{coord_str}]")

                with col_ann3:
                    if st.button("削除", key=f"del_ann_{current_step_id}_{i}"):
                        annotations.pop(i)
                        current_step["annotations"] = annotations
                        # Canvas再初期化フラグをセット（削除後の状態でCanvasを再描画）
                        st.session_state[f"canvas_reinit_{current_step_id}"] = True
                        st.rerun()
        else:
            st.info("注釈がありません")


# =============================================================================
# タブ3: 生成・エクスポート
# =============================================================================

def render_tab_export():
    """生成・エクスポートタブをレンダリング"""
    st.header("生成・エクスポート")

    steps = st.session_state[SESSION_KEYS["steps"]]
    preview_mode = st.session_state[SESSION_KEYS["preview_mode"]]
    video_info = st.session_state[SESSION_KEYS["video_info"]]
    project_name = st.session_state[SESSION_KEYS["project_name"]]

    if preview_mode:
        st.warning("⚠️ Word出力には動画のアップロードが必要です")
        st.info("プレビューモードではWord出力は利用できません。動画をアップロードしてください。")
        return

    if not steps:
        st.info("ステップがありません。AI連携タブでJSONをインポートしてください。")
        return

    # 出力プレビュー
    st.subheader("出力プレビュー")

    valid_steps = []
    skipped_steps = []

    for step in steps:
        step_id = step["id"]
        if step_id in st.session_state.exceeded_step_ids:
            skipped_steps.append(step)
        else:
            valid_steps.append(step)

    st.write(f"**出力対象**: {len(valid_steps)}件のステップ")

    if skipped_steps:
        st.warning(f"⚠️ {len(skipped_steps)}件のステップはtimestamp超過のためスキップされます")
        with st.expander("スキップされるステップ"):
            for step in skipped_steps:
                st.write(f"- ステップ {step['id']}: {step.get('title', '無題')}")

    # 出力ステップ一覧
    with st.expander("出力されるステップ", expanded=True):
        for i, step in enumerate(valid_steps):
            st.write(f"{i+1}. ステップ {step['id']}: {step.get('title', '無題')}")
            annotations_count = len(step.get("annotations", []))
            st.caption(f"   タイムスタンプ: {step.get('timestamp', 0):.2f}秒, 注釈: {annotations_count}件")

    st.divider()

    # 生成ボタン
    st.subheader("Word出力")

    if st.button("Wordドキュメントを生成", type="primary", key="generate_word_btn"):
        if not valid_steps:
            st.error("出力可能なステップがありません")
            return

        progress_bar = st.progress(0)
        status_text = st.empty()

        try:
            with TempFileManager(prefix="m2m_export_") as temp_manager:
                temp_video_path = st.session_state.temp_video_path

                # 画像生成
                steps_data = []
                total_steps = len(valid_steps)

                with VideoProcessor(temp_video_path) as vp:
                    for i, step in enumerate(valid_steps):
                        status_text.text(f"ステップ {step['id']} を処理中... ({i+1}/{total_steps})")
                        progress_bar.progress((i + 1) / (total_steps + 1))

                        # フレーム抽出
                        timestamp = step.get("timestamp", 0)
                        frame = vp.extract_frame(timestamp)

                        if frame is None:
                            st.warning(f"ステップ {step['id']} のフレーム抽出に失敗しました")
                            continue

                        # 注釈描画
                        annotations = step.get("annotations", [])
                        if annotations:
                            # 注釈形式を変換（rel_coords -> フラット座標）
                            formatted_annotations = []
                            for ann in annotations:
                                ann_type = ann.get("type", "rect")
                                rel_coords = ann.get("rel_coords", [])
                                color = hex_to_bgr(ann.get("color", DEFAULT_ANNOTATION_COLOR))
                                thickness = ann.get("stroke_width", DEFAULT_STROKE_WIDTH)

                                if ann_type == "rect" and len(rel_coords) == 4:
                                    formatted_annotations.append({
                                        "type": "rect",
                                        "rel_coords": tuple(rel_coords),
                                        "color": color,
                                        "thickness": thickness,
                                    })
                                elif ann_type == "line" and len(rel_coords) == 4:
                                    formatted_annotations.append({
                                        "type": "line",
                                        "rel_coords": tuple(rel_coords),
                                        "color": color,
                                        "thickness": thickness,
                                    })
                                # polygonは現在VideoProcessorでサポートされていないためスキップ

                            if formatted_annotations:
                                frame = vp.draw_annotations(frame, formatted_annotations)

                        # 一時ファイルに保存
                        filename = f"step_{step['id']:03d}.jpg"
                        image_path = temp_manager.save_frame(frame, filename)

                        steps_data.append({
                            "id": step["id"],
                            "title": step.get("title", ""),
                            "description": step.get("description", ""),
                            "image_path": str(image_path),
                        })

                # Word生成
                status_text.text("Wordドキュメントを生成中...")
                progress_bar.progress(0.9)

                doc_generator = DocGenerator(project_name)
                doc_generator.add_title(project_name)
                doc_generator.add_toc()

                for i, step_data in enumerate(steps_data):
                    doc_generator.add_step(
                        step_num=i + 1,
                        title=step_data["title"],
                        image_path=step_data["image_path"],
                        description=step_data["description"],
                    )

                # バイト列として取得
                doc_bytes = doc_generator.get_bytes()

                progress_bar.progress(1.0)
                status_text.text("完了!")

                st.success(f"Wordドキュメントを生成しました（{len(steps_data)}ステップ）")

                # ダウンロードボタン
                filename = f"{project_name}.docx"
                st.download_button(
                    label="📥 Wordファイルをダウンロード",
                    data=doc_bytes,
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key="download_docx"
                )

        except Exception as e:
            st.error(f"エラーが発生しました: {e}")
            import traceback
            st.code(traceback.format_exc())


# =============================================================================
# メインアプリケーション
# =============================================================================

def main():
    """メインアプリケーション"""
    st.set_page_config(
        page_title=APP_NAME,
        page_icon="🎬",
        layout=PAGE_LAYOUT,
    )

    # Session State初期化
    init_session_state()

    # サイドバー
    render_sidebar()

    # メインコンテンツ（タブ）
    tab1, tab2, tab3 = st.tabs(TAB_NAMES)

    with tab1:
        render_tab_ai()

    with tab2:
        render_tab_editor()

    with tab3:
        render_tab_export()


if __name__ == "__main__":
    main()
