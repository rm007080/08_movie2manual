"""
シンプルなWordドキュメント生成例

実際の画像を使用してマニュアルを生成するシンプルな例。
"""

import sys
from pathlib import Path

# 親ディレクトリをパスに追加
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

# 直接インポート
import importlib.util
spec = importlib.util.spec_from_file_location("doc_generator", parent_dir / "utils" / "doc_generator.py")
doc_generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(doc_generator)

DocGenerator = doc_generator.DocGenerator


def main():
    """メイン処理"""

    # 既存の画像を検索
    images_dir = parent_dir / "manual_images_output_v2"

    # 出力先
    output_dir = parent_dir / "examples" / "output"
    output_dir.mkdir(exist_ok=True)

    print("=" * 60)
    print("Wordドキュメント生成 - シンプルデモ")
    print("=" * 60)

    if images_dir.exists():
        # 実画像を使用
        image_files = sorted(list(images_dir.glob("*.jpg")) + list(images_dir.glob("*.png")))

        if len(image_files) >= 2:
            print(f"見つかった画像: {len(image_files)}個")

            gen = DocGenerator("サンプルマニュアル")
            gen.add_title("アプリ操作手順")

            for i, img_path in enumerate(image_files[:5], 1):
                gen.add_step(
                    step_num=i,
                    title=f"手順{i} - {img_path.stem}",
                    image_path=str(img_path),
                    description=f"画像「{img_path.name}」に対応する操作手順を実行します。"
                )

            output_path = output_dir / "sample_manual.docx"
            result_path = gen.save(str(output_path))
            print(f"\n生成完了: {result_path}")
            print("Wordファイルを開いてレイアウトを確認してください。")
            return

    print(f"実画像が見つかりません: {images_dir}")
    print("\nプレースホルダー画像でサンプルを作成します...")

    # プレースホルダー版を作成
    gen = DocGenerator("サンプルマニュアル")
    gen.add_title("アプリ操作手順（サンプル）")

    steps = [
        ("起動", "アプリを起動します"),
        ("設定", "設定メニューを開きます"),
        ("完了", "設定を完了します")
    ]

    for i, (title, desc) in enumerate(steps, 1):
        gen.add_step(
            step_num=i,
            title=f"{title}",
            image_path=f"placeholder_{i}.png",  # 存在しない画像パス
            description=desc
        )

    output_path = output_dir / "sample_manual_placeholder.docx"
    result_path = gen.save(str(output_path))
    print(f"\n生成完了（プレースホルダー版）: {result_path}")


if __name__ == "__main__":
    main()
