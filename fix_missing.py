import os
import shutil
from pathlib import Path
import time
import re
from typing import Tuple
from dotenv import load_dotenv
from pymongo import MongoClient
from supabase import create_client, Client


# Đường dẫn mặc định (có thể sửa lại nếu cần)
ARXIV_ROOT = Path(r"D:\Documents\GitHub\ScholarHub\ArXivPapers")
TEMPLATE_PAPER_DIR = Path(r"D:\Documents\GitHub\Milestone_2\23127238")
OUTPUT_DIR = Path(r"D:\Documents\23127238_output")

# Load environment variables for MongoDB and Supabase
load_dotenv()

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Initialize MongoDB client
MONGO_URL = os.getenv("MONGO_URL")
DATABASE_NAME = os.getenv("DATABASE_NAME")
COLLECTION_NAME = os.getenv("DOCUMENT_CONTENTS_COLLECTION")

mongo_client = MongoClient(MONGO_URL)
mongo_db = mongo_client[DATABASE_NAME]
mongo_collection = mongo_db[COLLECTION_NAME]


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


def copy_json_and_bibtex_from_output(target_paper_dir: Path, output_dir: Path) -> Tuple[bool, bool]:
    """
    Copy paper_id.json và paper_id_bibtex.bib từ output_dir sang target_paper_dir.
    
    Args:
        target_paper_dir: Thư mục đích (ví dụ: ArXivPapers/2304-14610)
        output_dir: Thư mục nguồn chứa các folder paper (ví dụ: D:\Documents\23127238_output)
    
    Returns:
        Tuple (copied_json, copied_bibtex) - True nếu đã copy thành công
    """
    paper_id = target_paper_dir.name
    source_paper_dir = output_dir / paper_id
    
    if not source_paper_dir.is_dir():
        return False, False
    
    # copied_json = False
    copied_bibtex = False
    
    # Copy paper_id.json
    # source_json = source_paper_dir / f"{paper_id}.json"
    # target_json = target_paper_dir / f"{paper_id}.json"
    
    # if source_json.is_file():
    #     try:
    #         shutil.copy2(source_json, target_json)
    #         print(f"[INFO] Copy {paper_id}.json -> {target_json}")
    #         copied_json = True
    #     except Exception as e:
    #         print(f"[ERROR] Lỗi khi copy {paper_id}.json: {e}")
    # else:
    #     print(f"[WARN] Không tìm thấy {source_json}")
    
    # Copy paper_id_bibtex.bib
    source_bibtex = source_paper_dir / f"{paper_id}_bibtex.bib"
    target_bibtex = target_paper_dir / f"{paper_id}_bibtex.bib"
    
    if source_bibtex.is_file():
        try:
            shutil.copy2(source_bibtex, target_bibtex)
            print(f"[INFO] Copy {paper_id}_bibtex.bib -> {target_bibtex}")
            copied_bibtex = True
        except Exception as e:
            print(f"[ERROR] Lỗi khi copy {paper_id}_bibtex.bib: {e}")
    else:
        print(f"[WARN] Không tìm thấy {source_bibtex}")
    
    return copied_bibtex


def copy_all_json_bibtex_from_output(arxiv_root: Path, output_dir: Path) -> None:
    """
    Copy tất cả paper_id.json và paper_id_bibtex.bib từ output_dir sang các paper trong arxiv_root.
    
    Args:
        arxiv_root: Thư mục chứa các paper (ví dụ: ArXivPapers)
        output_dir: Thư mục nguồn chứa các folder paper (ví dụ: D:\Documents\23127238_output)
    """
    if not arxiv_root.is_dir():
        print(f"[ERROR] Không tìm thấy thư mục ArXivPapers: {arxiv_root}")
        return
    
    if not output_dir.is_dir():
        print(f"[ERROR] Không tìm thấy thư mục output: {output_dir}")
        return
    
    print(f"[INFO] Duyệt thư mục: {arxiv_root}")
    print(f"[INFO] Thư mục nguồn: {output_dir}")
    
    count_total = 0
    count_json_copied = 0
    count_bibtex_copied = 0
    
    for entry in sorted(arxiv_root.iterdir()):
        if not entry.is_dir():
            continue
        
        paper_dir = entry
        count_total += 1
        
        copied_bibtex = copy_json_and_bibtex_from_output(paper_dir, output_dir)
        
        # if copied_json:
        #     count_json_copied += 1
        if copied_bibtex:
            count_bibtex_copied += 1
        
        # time.sleep(2)
    
    print("\n[SUMMARY]")
    print(f"- Tổng số paper duyệt: {count_total}")
    # print(f"- Số file JSON đã copy: {count_json_copied}")
    print(f"- Số file BibTeX đã copy: {count_bibtex_copied}")


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


def cleanup_mongodb_keep_latest(keep_count: int = 500) -> None:
    """
    Xóa bớt papers trong MongoDB document_contents collection, chỉ giữ lại N papers mới nhất.
    Đồng thời cập nhật Supabase để set mongo_doc_id thành null cho các papers đã xóa.
    
    Args:
        keep_count: Số lượng papers muốn giữ lại (mặc định 500)
    """
    print(f"[INFO] Bắt đầu cleanup MongoDB, giữ lại {keep_count} papers mới nhất...")
    
    # Lấy tất cả papers từ MongoDB, sắp xếp theo created_at (mới nhất trước)
    all_papers = list(mongo_collection.find(
        {},
        {"paper_id": 1, "created_at": 1, "_id": 1}
    ).sort("created_at", -1))
    
    total_count = len(all_papers)
    print(f"[INFO] Tổng số papers trong MongoDB: {total_count}")
    
    if total_count <= keep_count:
        print(f"[INFO] Số papers hiện tại ({total_count}) <= số cần giữ ({keep_count}), không cần xóa")
        return
    
    # Chọn papers cần xóa (bỏ qua N papers đầu tiên)
    papers_to_delete = all_papers[keep_count:]
    delete_count = len(papers_to_delete)
    
    print(f"[INFO] Sẽ xóa {delete_count} papers cũ nhất")
    
    deleted_paper_ids = []
    
    # Thu thập paper_id của các papers cần xóa
    for paper in papers_to_delete:
        paper_id = paper.get("paper_id")
        if paper_id:
            deleted_paper_ids.append(paper_id)
    
    # Xóa hàng loạt trong MongoDB
    if deleted_paper_ids:
        delete_result = mongo_collection.delete_many({"paper_id": {"$in": deleted_paper_ids}})
        print(f"[INFO] Đã xóa {delete_result.deleted_count} papers từ MongoDB")
    
    # Cập nhật Supabase: set mongo_doc_id thành null cho các papers đã xóa
    if deleted_paper_ids and supabase:
        print(f"[INFO] Đang cập nhật Supabase cho {len(deleted_paper_ids)} papers...")
        
        updated_count = 0
        failed_count = 0
        
        # Cập nhật từng paper theo arxiv_id
        # Supabase có thể không hỗ trợ .in_() với danh sách lớn, nên cập nhật từng cái một
        for paper_id in deleted_paper_ids:
            try:
                # Tìm paper trong Supabase theo arxiv_id
                result = (
                    supabase
                    .table("papers")
                    .select("id, arxiv_id, mongo_doc_id")
                    .eq("arxiv_id", paper_id)
                    .execute()
                )
                
                if result.data and len(result.data) > 0:
                    paper_data = result.data[0]
                    paper_db_id = paper_data.get("id")
                    current_mongo_doc_id = paper_data.get("mongo_doc_id")
                    
                    # Chỉ cập nhật nếu có mongo_doc_id (không null)
                    if current_mongo_doc_id:
                        try:
                            supabase.table("papers").update({
                                "mongo_doc_id": None
                            }).eq("id", paper_db_id).execute()
                            updated_count += 1
                        except Exception as e:
                            print(f"[ERROR] Lỗi khi cập nhật paper {paper_id} (id: {paper_db_id}): {e}")
                            failed_count += 1
                    else:
                        # Paper đã có mongo_doc_id = null, không cần cập nhật
                        pass
                else:
                    # Paper không tìm thấy trong Supabase
                    print(f"[WARN] Paper {paper_id} không tìm thấy trong Supabase")
                    
            except Exception as e:
                print(f"[ERROR] Lỗi khi query paper {paper_id} từ Supabase: {e}")
                failed_count += 1
            
            # Thêm delay nhỏ để tránh rate limit
            if (updated_count + failed_count) % 100 == 0:
                time.sleep(0.1)
        
        print(f"[INFO] Đã cập nhật {updated_count} papers trên Supabase")
        if failed_count > 0:
            print(f"[WARN] {failed_count} papers không thể cập nhật trên Supabase")
    
    print("\n[SUMMARY]")
    print(f"- Tổng số papers ban đầu: {total_count}")
    print(f"- Số papers giữ lại: {keep_count}")
    print(f"- Số papers đã xóa: {delete_count}")
    print(f"- Số papers đã cập nhật trên Supabase: {updated_count if deleted_paper_ids else 0}")


if __name__ == "__main__":
    # process_all_papers(ARXIV_ROOT, TEMPLATE_PAPER_DIR)
    # copy_all_json_bibtex_from_output(ARXIV_ROOT, OUTPUT_DIR)
    # cleanup_mongodb_keep_latest(keep_count=500)
    mongo_papers = list(mongo_collection.find({}, {"paper_id": 1}))
    mongo_paper_ids = {paper["paper_id"] for paper in mongo_papers}

    result = supabase.table("papers").select("id, arxiv_id, mongo_doc_id").not_.is_("mongo_doc_id", "null").execute()
    supabase_papers = result.data

    papers_to_update = []
    
    for paper in supabase_papers:
        arxiv_id = paper.get("arxiv_id")
        if arxiv_id not in mongo_paper_ids:
            papers_to_update.append(paper)

    updated_count = 0
    failed_count = 0
    
    for paper in papers_to_update:
        paper_id = paper.get("id")
        arxiv_id = paper.get("arxiv_id")
        
        try:
            supabase.table("papers").update({
                "mongo_doc_id": None
            }).eq("id", paper_id).execute()
            
            updated_count += 1
            print(f"[INFO] Đã cập nhật paper {arxiv_id} (id: {paper_id})")
            
        except Exception as e:
            print(f"[ERROR] Lỗi khi cập nhật paper {arxiv_id}: {e}")
            failed_count += 1