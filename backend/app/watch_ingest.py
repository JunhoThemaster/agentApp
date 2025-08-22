# backend/app/watch_ingest.py
import time
import subprocess
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

CSV_PATH = Path("/home/user2/문서/agentApp/backend/app/data/all_labs_merged.csv")

class CsvChangeHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith(CSV_PATH.name):
            print(f"[INFO] CSV changed: {event.src_path}")
            self.run_ingest()

    def run_ingest(self):
        try:
            print("[RUN] ingest_stats.py ...")
            subprocess.run(["python", "backend/app/ingest_stats.py"], check=True)

            print("[RUN] ingest_embeddings.py ...")
            subprocess.run(["python", "backend/app/ingest_embeddings.py"], check=True)

            print("[OK] Ingestion finished.\n")
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] ingestion failed: {e}")

def start_watch():
    event_handler = CsvChangeHandler()
    observer = Observer()
    observer.schedule(event_handler, str(CSV_PATH.parent), recursive=False)
    observer.start()

    print(f"[WATCHING] {CSV_PATH} for changes...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    start_watch()
