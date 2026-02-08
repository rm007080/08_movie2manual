"""
Wordドキュメント生成のデモスクリプト

python-docxを使用したマニュアル生成の使用例を示します。
"""

import sys
from pathlib import Path

# 親ディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

# 直接インポート（依存関係回避）
import importlib.util
spec = importlib.util.spec_from_file_location("doc_generator", Path(__file__).parent.parent / "utils" / "doc_generator.py")
doc_generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(doc_generator)

create_word_manual = doc_generator.create_word_manual
DocGenerator = doc_generator.DocGenerator


def demo_basic_usage():
    """基本的な使用例

    create_word_manual関数を使用したシンプルな例
    """
    print("=" * 70)
    print("Demo 1: Basic Usage - create_word_manual関数")
    print("=" * 70)

    # ステップデータの準備
    steps_data = [
        {
            "id": 1,
            "title": "Teamsを起動する",
            "description": "デスクトップまたはスタートメニューからMicrosoft Teamsを起動します。",
            "image_path": "step1_teams_icon.png"  # 実際の画像パスに置き換えてください
        },
        {
            "id": 2,
            "title": "設定メニューを開く",
            "description": "画面右上にある「三点リーダー（...）」をクリックし、「設定」を選択します。",
            "image_path": "step2_settings_menu.png"
        },
        {
            "id": 3,
            "title": "背景画像を選択",
            "description": "「背景の効果」を選択し、任意の背景画像をクリックして適用します。",
            "image_path": "step3_background_selection.png"
        }
    ]

    # Wordドキュメントを生成
    output_path = "demo_teams_manual.docx"
    result_path = create_word_manual(
        steps_data=steps_data,
        output_path=output_path,
        project_name="Teams背景設定マニュアル"
    )

    print(f"生成されたドキュメント: {result_path}")
    print()


def demo_class_api():
    """DocGeneratorクラスの使用例

    より詳細なカスタマイズが必要な場合の例
    """
    print("=" * 70)
    print("Demo 2: Class API - DocGeneratorクラス")
    print("=" * 70)

    # DocGeneratorインスタンスを作成
    gen = DocGenerator("アプリ操作マニュアル")

    # タイトルを追加
    gen.add_title("メールアプリの基本操作")

    # セクション見出しを追加（オプション）
    gen.add_section("第1章: 初期設定")

    # ステップを追加
    gen.add_step(
        step_num=1,
        title="アカウント設定",
        image_path="mail_setup.png",
        description="メールアカウントの設定画面を開き、必要な情報を入力します。"
    )

    gen.add_step(
        step_num=2,
        title="署名の登録",
        image_path="mail_signature.png",
        description="メール署名を作成・登録します。"
    )

    # 改ページ（オプション）
    gen.add_page_break()

    # 別のセクション
    gen.add_section("第2章: メールの作成")

    gen.add_step(
        step_num=3,
        title="新規メール作成",
        image_path="new_mail.png",
        description="「新規作成」ボタンをクリックして、新しいメールを作成します。"
    )

    # 保存
    output_path = "demo_mail_manual.docx"
    result_path = gen.save(output_path)

    print(f"生成されたドキュメント: {result_path}")
    print()


def demo_with_real_images():
    """実際の画像を使用したデモ

    manual_images_output_v2ディレクトリに画像がある場合の例
    """
    print("=" * 70)
    print("Demo 3: With Real Images")
    print("=" * 70)

    # 画像ディレクトリ
    images_dir = Path(__file__).parent.parent / "manual_images_output_v2"

    if not images_dir.exists():
        print(f"画像ディレクトリが見つかりません: {images_dir}")
        print("このデモはスキップされます。")
        return

    # 画像ファイルを取得
    image_files = sorted(images_dir.glob("*.jpg")) + sorted(images_dir.glob("*.png"))

    if len(image_files) < 2:
        print(f"十分な画像ファイルがありません: {len(image_files)}個")
        print("このデモはスキップされます。")
        return

    print(f"使用する画像: {len(image_files)}個")

    # ステップデータを作成
    steps_data = [
        {
            "id": i + 1,
            "title": f"操作手順 {i + 1}",
            "description": f"画像ファイル: {img.name}\nこの操作を実行します。",
            "image_path": str(img)
        }
        for i, img in enumerate(image_files[:5])  # 最初の5枚を使用
    ]

    output_path = "demo_with_real_images.docx"
    result_path = create_word_manual(
        steps_data=steps_data,
        output_path=output_path,
        project_name="実画像を使用したマニュアル"
    )

    print(f"生成されたドキュメント: {result_path}")
    print()


def demo_streamlit_integration():
    """Streamlitでの使用例

    バイト列を取得してダウンロード機能を実装する例
    """
    print("=" * 70)
    print("Demo 4: Streamlit Integration - get_bytes()メソッド")
    print("=" * 70)

    # DocGeneratorインスタンスを作成
    gen = DocGenerator("Streamlit出力テスト")
    gen.add_title("Streamlitから出力するマニュアル")

    gen.add_step(
        step_num=1,
        title="サンプルステップ",
        image_path="sample.jpg",  # 存在しない画像
        description="この例ではバイト列を取得します。\n画像がない場合はプレースホルダーが表示されます。"
    )

    # バイト列を取得
    doc_bytes = gen.get_bytes()

    print(f"ドキュメントのバイト列サイズ: {len(doc_bytes)} bytes")
    print()
    print("Streamlitでの使用例:")
    print("-" * 40)
    print("""
import streamlit as st
from utils.doc_generator import DocGenerator

# ドキュメントを生成
gen = DocGenerator("マニュアルタイトル")
gen.add_title("操作マニュアル")
gen.add_step(1, "ステップ1", "image1.png", "説明1")
gen.add_step(2, "ステップ2", "image2.png", "説明2")

# バイト列を取得
doc_bytes = gen.get_bytes()

# ダウンロードボタンを表示
st.download_button(
    label="マニュアルをダウンロード",
    data=doc_bytes,
    file_name="manual.docx",
    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)
    """)
    print("-" * 40)

    # バイト列から保存
    output_path = "demo_streamlit_output.docx"
    with open(output_path, "wb") as f:
        f.write(doc_bytes)
    print(f"\n検証用に保存: {output_path}")
    print()


def main():
    """メイン処理"""
    print("\n" + "=" * 70)
    print("Wordドキュメント生成デモ")
    print("=" * 70)
    print()

    # デモ1: 基本的な使用例
    demo_basic_usage()

    # デモ2: クラスAPIの使用例
    demo_class_api()

    # デモ3: 実画像を使用したデモ
    demo_with_real_images()

    # デモ4: Streamlit連携
    demo_streamlit_integration()

    print("=" * 70)
    print("すべてのデモが完了しました！")
    print("=" * 70)
    print()
    print("生成されたWordファイルを開いてレイアウトを確認してください。")
    print()


if __name__ == "__main__":
    main()
