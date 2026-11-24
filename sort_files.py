import argparse
import shutil
from datetime import datetime
from pathlib import Path


def unique_dest_path(dest_dir: Path, filename: str) -> Path:
    """同名ファイルがある場合に上書きしないよう連番を振る"""
    candidate = dest_dir / filename
    if not candidate.exists():
        return candidate

    stem = Path(filename).stem
    suffix = Path(filename).suffix
    counter = 1
    while True:
        candidate = dest_dir / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def get_folder_name(entry: Path, mode: str, name_rules: list[tuple[str, str]], date_fmt: str) -> str:
    """仕分けモードに応じて振り分け先フォルダ名を決める"""
    if mode == "ext":
        ext = entry.suffix.lower().lstrip(".")
        return ext if ext else "no_extension"

    if mode == "date":
        mtime = datetime.fromtimestamp(entry.stat().st_mtime)
        return mtime.strftime(date_fmt)

    if mode == "name":
        lower_name = entry.name.lower()
        for keyword, folder in name_rules:
            if keyword.lower() in lower_name:
                return folder
        return "other"

    return "other"


def parse_name_rules(raw_rules: list[str]) -> list[tuple[str, str]]:
    """'キーワード:フォルダ名' のリストをタプルリストに変換する"""
    rules: list[tuple[str, str]] = []
    for item in raw_rules:
        if ":" in item:
            kw, folder = item.split(":", 1)
            kw = kw.strip()
            folder = folder.strip()
            if kw and folder:
                rules.append((kw, folder))
    return rules


def sort_files(
    target_dir: Path,
    mode: str = "ext",
    dry_run: bool = True,
    recursive: bool = False,
    name_rules: list[tuple[str, str]] | None = None,
    date_fmt: str = "%Y-%m",
) -> None:
    if not target_dir.exists() or not target_dir.is_dir():
        print(f"エラー: 指定されたフォルダが存在しません -> {target_dir}")
        return

    rules = name_rules or []
    iterator = target_dir.rglob("*") if recursive else target_dir.iterdir()

    for entry in iterator:
        if not entry.is_file():
            continue

        # スクリプト自身を動かさないように保護
        if entry.resolve() == Path(__file__).resolve():
            continue

        folder_name = get_folder_name(entry, mode=mode, name_rules=rules, date_fmt=date_fmt)
        dest_folder = target_dir / folder_name

        # すでに振り分け先フォルダ内にある場合はスキップ
        if entry.parent.resolve() == dest_folder.resolve():
            continue

        dest_path = unique_dest_path(dest_folder, entry.name)

        if dry_run:
            print(f"[DRY-RUN] {entry}  -->  {dest_path}")
        else:
            dest_folder.mkdir(parents=True, exist_ok=True)
            shutil.move(str(entry), str(dest_path))
            print(f"[MOVED]   {entry}  -->  {dest_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="指定フォルダ内のファイルを条件ごとに振り分けます。")
    parser.add_argument("target_dir", help="整理したいフォルダまたはドライブのパス（例: F:\\\\）")
    parser.add_argument(
        "--mode",
        choices=["ext", "date", "name"],
        default="ext",
        help="仕分け基準: ext(拡張子), date(更新日), name(ファイル名キーワード)",
    )
    parser.add_argument(
        "--date-format",
        default="%Y-%m",
        help="--mode date 時のフォルダ形式（例: %%Y-%%m で 2026-11、%%Y-%%m-%%d で日別）",
    )
    parser.add_argument(
        "--name-rule",
        action="append",
        default=[],
        metavar="KEYWORD:FOLDER",
        help="--mode name 時のルール（例: --name-rule 動画:Videos --name-rule memo:Memos）",
    )
    parser.add_argument("--apply", action="store_true", help="実際にファイルを移動する（指定しない場合は確認のみ）")
    parser.add_argument("--recursive", action="store_true", help="サブフォルダ内のファイルも対象にする")
    args = parser.parse_args()

    sort_files(
        target_dir=Path(args.target_dir),
        mode=args.mode,
        dry_run=not args.apply,
        recursive=args.recursive,
        name_rules=parse_name_rules(args.name_rule),
        date_fmt=args.date_format,
    )


if __name__ == "__main__":
    main()