import os
import shutil
from pathlib import Path
import time
import re


# Đường dẫn mặc định (có thể sửa lại nếu cần)
ARXIV_ROOT = Path(r"D:\Documents\GitHub\ScholarHub\ArXivPapers")
TEMPLATE_PAPER_DIR = Path(r"D:\Documents\GitHub\Milestone_2\23127238")


def copy_tex_if_missing(target_paper_dir: Path, template_paper_dir: Path) -> bool:
    """
    Đảm bảo target_paper_dir có cấu trúc:
        tex/
          └─ paperidvN/

    - Nếu template có tex/ → copy toàn bộ
    - Nếu template KHÔNG có tex/ nhưng có paperidvN/ → copy các folder đó vào tex/
    """

    target_tex = target_paper_dir / "tex"

    # Nếu tex đã tồn tại và không rỗng → không làm gì
    if target_tex.exists():
        if target_tex.is_dir() and any(target_tex.iterdir()):
            return False
        # tex rỗng → xóa để copy lại
        shutil.rmtree(target_tex)

    # ===== CASE 1: TEMPLATE CÓ tex/ =====
    source_tex = template_paper_dir / "tex"
    if source_tex.is_dir():
        print(f"[INFO] Copy tex trực tiếp -> {target_tex}")
        shutil.copytree(source_tex, target_tex)
        return True

    # ===== CASE 2: TEMPLATE KHÔNG CÓ tex/, TÌM paperidvN/ =====
    print(f"[WARN] Không có tex/, tìm paperidvN/...")

    # normalized_id = template_paper_dir.name.replace("-", ".")
    pattern = re.compile(rf"^{re.escape(template_paper_dir.name)}v\d+$")

    candidate_folders = []
    for entry in template_paper_dir.iterdir():
        if entry.is_dir() and pattern.fullmatch(entry.name):
            candidate_folders.append(entry)

    if not candidate_folders:
        print(f"[WARN] Không tìm thấy folder version cho {template_paper_dir.name}")
        return False

    # Sắp xếp version, lấy mới nhất
    def version_num(p: Path) -> int:
        return int(p.name.split("v")[-1])

    candidate_folders.sort(key=version_num, reverse=True)

    # ===== TẠO tex/ và copy paperidvN/ vào =====
    target_tex.mkdir(parents=True, exist_ok=True)

    try:
        for folder in candidate_folders:
            dest = target_tex / folder.name
            print(f"[INFO] Copy {folder.name} -> tex/{folder.name}")
            shutil.copytree(folder, dest, dirs_exist_ok=True)

        return True

    except Exception as e:
        print(f"[ERROR] Lỗi khi copy paperidvN vào tex: {e}")
        return False


def copy_references_if_missing(target_paper_dir: Path, template_paper_dir: Path) -> bool:
    """Copy references.json từ paper mẫu nếu paper hiện tại bị thiếu."""
    target_ref = target_paper_dir / "references.json"
    if target_ref.exists():
        return False

    source_ref = template_paper_dir / "references.json"
    if not source_ref.is_file():
        print(f"[WARN] File references.json mẫu không tồn tại: {source_ref}")
        return False

    print(f"[INFO] Copy references.json -> {target_ref}")
    shutil.copy2(source_ref, target_ref)
    # print(f"[INFO] Copied references.json to {target_ref}")
    return True


def process_all_papers(arxiv_root: Path, template_paper_dir: Path) -> None:
    if not arxiv_root.is_dir():
        print(f"[ERROR] Không tìm thấy thư mục ArXivPapers: {arxiv_root}")
        return

    if not template_paper_dir.is_dir():
        print(f"[ERROR] Không tìm thấy thư mục paper mẫu: {template_paper_dir}")
        return

    print(f"[INFO] Duyệt thư mục: {arxiv_root}")
    print(f"[INFO] Thư mục mẫu: {template_paper_dir}")

    count_total = 0
    count_modified = 0

    for entry in sorted(arxiv_root.iterdir()):
        if not entry.is_dir():
            continue

        paper_dir = entry
        count_total += 1

        has_tex = (paper_dir / "tex").is_dir()
        has_ref = (paper_dir / "references.json").is_file()

        if has_tex and has_ref and any((paper_dir / "tex").iterdir()):
            # Không thiếu gì và thư mục tex không rỗng
            continue

        print(f"\n[PROCESS] {paper_dir.name}")
        changed_tex = copy_tex_if_missing(paper_dir, template_paper_dir / paper_dir.name)
        changed_ref = copy_references_if_missing(paper_dir, template_paper_dir / paper_dir.name)

        if changed_tex or changed_ref:
            count_modified += 1
        time.sleep(0.2)

    print("\n[SUMMARY]")
    print(f"- Tổng số paper duyệt: {count_total}")
    print(f"- Số paper đã được bổ sung tex/references: {count_modified}")


if __name__ == "__main__":
    process_all_papers(ARXIV_ROOT, TEMPLATE_PAPER_DIR)

