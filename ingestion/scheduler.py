import time
import os
import shutil
import psutil
import threading
import requests
import pathlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from arxiv_crawler import crawl_single_paper
from reference_extractor import extract_references_for_paper
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

PAPER_BUCKET = os.getenv("PAPER_BUCKET")

# Global statistics
stats_lock = Lock()
stats = {
    "total_processed": 0,
    "both_success": 0,
    "only_crawler_fail": 0,
    "no_references": 0,
    "both_failed": 0,
}

monitor_running = True
ram_samples_bytes = []
peak_disk_usage_bytes = 0

def _monitor_resources(baseline_ram, baseline_disk, sleep_interval=2):
    """Monitor RAM and disk usage in background."""
    global ram_samples_bytes, peak_disk_usage_bytes, monitor_running

    ram_samples_bytes = []
    peak_disk_usage_bytes = 0

    while monitor_running:
        try:
            current_ram = psutil.virtual_memory().used
            ram_above_baseline = current_ram - baseline_ram
            ram_samples_bytes.append(ram_above_baseline)

            try:
                current_disk = shutil.disk_usage('/').used
            except OSError:
                current_disk = shutil.disk_usage(pathlib.Path.cwd().anchor).used
            disk_above_baseline = current_disk - baseline_disk

            if disk_above_baseline > peak_disk_usage_bytes:
                peak_disk_usage_bytes = disk_above_baseline

        except Exception:
            pass

        time.sleep(sleep_interval)

def _print_custom_resource_report(disk_start, disk_end):
    """Print resource usage report."""
    global ram_samples_bytes, peak_disk_usage_bytes

    avg_ram_bytes = sum(ram_samples_bytes) / len(ram_samples_bytes) if ram_samples_bytes else 0
    peak_ram_bytes = max(ram_samples_bytes) if ram_samples_bytes else 0
    final_disk_bytes = disk_end - disk_start

    print("\n" + "="*80)
    print("RESOURCE REPORT")
    print(f"  Average RAM: {avg_ram_bytes / (1024**2):.2f} MB")
    print(f"  Peak RAM: {peak_ram_bytes / (1024**2):.2f} MB")
    print(f"  Peak Disk: {peak_disk_usage_bytes / (1024**2):.2f} MB")
    print(f"  Final Disk: {final_disk_bytes / (1024**2):.2f} MB")
    print("="*80)

def process_paper(arxiv_id, save_dir="./ArXivPapers"):
    """Process a single paper: crawl data first, then extract references."""
    try:
        crawler_success = crawl_single_paper(arxiv_id, save_dir)
        references_success = False

        if crawler_success:
            references_success = extract_references_for_paper(arxiv_id, save_dir)

        with stats_lock:
            stats["total_processed"] += 1
            if crawler_success and references_success:
                stats["both_success"] += 1
            elif not crawler_success:
                stats["only_crawler_fail"] += 1
            if not references_success:
                stats["no_references"] += 1

        return arxiv_id, crawler_success, references_success

    except Exception as e:
        with stats_lock:
            stats["total_processed"] += 1
            stats["both_failed"] += 1
        return arxiv_id, False, False


def check_paper_exists(arxiv_id):
    """Check if paper exists with HEAD request."""
    url = f"https://arxiv.org/abs/{arxiv_id}"
    try:
        response = requests.head(url, timeout=5, allow_redirects=True)
        time.sleep(0.3)
        return response.status_code == 200
    except requests.RequestException:
        time.sleep(0.3)
        return False


def find_last_valid_id(prefix, start_id, jump1=50, back1=10, jump2=5, back2=1):
    """Find last valid ID using binary search strategy."""
    try:
        start_id = int(start_id)
        jump1 = int(jump1)
        back1 = int(back1)
        jump2 = int(jump2)
        back2 = int(back2)
    except ValueError:
        return 0

    start_arxiv_id = f"{prefix}.{start_id:05d}"
    if not check_paper_exists(start_arxiv_id):
        return start_id - 1

    last_known_good_id = start_id
    current_id = start_id + jump1
    state = "JUMP1"

    while True:
        arxiv_id = f"{prefix}.{current_id:05d}"
        exists = check_paper_exists(arxiv_id)

        if exists:
            last_known_good_id = current_id
            if state == "JUMP1":
                current_id += jump1
            elif state == "BACK1":
                state = "JUMP2"
                current_id += jump2
            elif state == "JUMP2":
                current_id += jump2
            elif state == "BACK2":
                break
        else:
            if state == "JUMP1":
                state = "BACK1"
                current_id -= back1
            elif state == "BACK1":
                current_id -= back1
            elif state == "JUMP2":
                state = "BACK2"
                current_id -= back2
            elif state == "BACK2":
                current_id -= back2

    return last_known_good_id


def generate_paper_ids(start_month, start_id, end_month, end_id, save_dir="./ArXivPapers", resume_file=None):
    """Generate list of arXiv IDs, optionally excluding already processed ones."""
    start_year, start_mon = start_month.split('-')
    end_year, end_mon = end_month.split('-')
    start_prefix = start_year[2:] + start_mon
    end_prefix = end_year[2:] + end_mon

    paper_ids = []
    processed_ids = set()
    processed_ids_file = [
        name.replace('-', '.')
        for name in os.listdir(save_dir)
        if os.path.isdir(os.path.join(save_dir, name))
        and "references.json" in os.listdir(os.path.join(save_dir, name))
    ]

    processed_ids.update(processed_ids_file)
    print(f"Resuming: skipping {len(processed_ids)} already processed IDs")

    if start_month == end_month:
        for i in range(start_id, end_id + 1):
            paper_id = f"{start_prefix}.{i:05d}"
            if paper_id not in processed_ids:
                paper_ids.append(paper_id)
    else:
        last_valid_start_month = find_last_valid_id(start_prefix, start_id)
        for i in range(start_id, last_valid_start_month + 1):
            paper_id = f"{start_prefix}.{i:05d}"
            if paper_id not in processed_ids:
                paper_ids.append(paper_id)
        for i in range(1, end_id + 1):
            paper_id = f"{end_prefix}.{i:05d}"
            if paper_id not in processed_ids:
                paper_ids.append(paper_id)

    return paper_ids


def print_progress_report():
    """Print current statistics."""
    with stats_lock:
        total = stats['total_processed']
        print(f"\nProgress: {total} processed | Success: {stats['both_success']} | Crawler fail: {stats['only_crawler_fail']} | No refs: {stats['no_references']} | Errors: {stats['both_failed']}")


def print_final_report():
    """Print final statistics."""
    total = stats['total_processed']
    if total == 0:
        return

    both_success_rate = (stats['both_success'] / total * 100)
    crawl_fail_rate = (stats['both_failed'] / total * 100)
    no_references_rate = (stats['no_references'] / total * 100)

    print(f"\n{'='*80}")
    print("FINAL REPORT")
    print(f"{'='*80}")
    print(f"Total processed: {total}")
    print(f"Both success: {stats['both_success']} ({both_success_rate:.2f}%)")
    print(f"Crawler fail: {stats['only_crawler_fail']}")
    print(f"No references: {stats['no_references']} ({no_references_rate:.2f}%)")
    print(f"Errors: {stats['both_failed']} ({crawl_fail_rate:.2f}%)")
    print(f"{'='*80}")


def run_parallel_processing(start_month, start_id, end_month, end_id,
                            max_parallels=2, save_dir="./ArXivPapers"):
    """Run parallel processing of papers."""

    with stats_lock:
        for key in stats:
            stats[key] = 0

    paper_ids = generate_paper_ids(start_month, start_id, end_month, end_id, save_dir)
    total_papers = len(paper_ids)

    print(f"Processing {total_papers} papers with {max_parallels} threads")

    start_time = time.time()

    with ThreadPoolExecutor(max_workers=max_parallels) as executor:
        futures = {
            executor.submit(process_paper, arxiv_id, save_dir): arxiv_id
            for arxiv_id in paper_ids
        }

        completed = 0
        for future in as_completed(futures):

            arxiv_id = futures[future]
            completed += 1

            try:
                paper_id, crawler_ok, refs_ok = future.result()
                status = "OK" if (crawler_ok and refs_ok) else "PARTIAL" if crawler_ok else "FAILED"
                print(f"[{completed}/{total_papers}] {status} {paper_id}")

                if completed % 10 == 0:
                    print_progress_report()

            except Exception as e:
                print(f"[{completed}/{total_papers}] ERROR {arxiv_id}: {e}")

    elapsed_time = time.time() - start_time
    print(f"\nCompleted in {elapsed_time:.2f}s ({elapsed_time/total_papers:.2f}s per paper)" if total_papers > 0 else "")
    print_final_report()


def main():
    """Main function to run the entire processing."""

    START_MONTH = "2023-04"
    START_ID = 14607
    END_MONTH = "2023-05"
    END_ID = 14596
    MAX_PARALLELS = 2
    SAVE_DIR = "./ArXivPapers"

    try:
        disk_usage_start = shutil.disk_usage('/').used
    except OSError:
        disk_usage_start = shutil.disk_usage(pathlib.Path.cwd().anchor).used
    ram_usage_start = psutil.virtual_memory().used

    global monitor_running
    monitor_running = True

    monitor_thread = threading.Thread(
        target=_monitor_resources,
        args=(ram_usage_start, disk_usage_start, 2),
        daemon=True
    )
    monitor_thread.start()

    try:
        run_parallel_processing(
            start_month=START_MONTH,
            start_id=START_ID,
            end_month=END_MONTH,
            end_id=END_ID,
            max_parallels=MAX_PARALLELS,
            save_dir=SAVE_DIR,
        )
    finally:
        monitor_running = False
        monitor_thread.join()

        try:
            disk_usage_end = shutil.disk_usage('/').used
        except OSError:
            disk_usage_end = shutil.disk_usage(pathlib.Path.cwd().anchor).used
        _print_custom_resource_report(disk_usage_start, disk_usage_end)


if __name__ == "__main__":
    main()