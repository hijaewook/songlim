import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent

def main():
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", "8765"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(30):
            try:
                with urlopen("http://127.0.0.1:8765/health", timeout=0.5) as r:
                    data = json.loads(r.read().decode("utf-8"))
                    assert data["ok"] is True
                    print("HTTP 서버 점검: OK")
                    print("프로토타입 실행 준비 완료")
                    return 0
            except Exception:
                time.sleep(0.1)
        print("서버가 시작되지 않았습니다.")
        return 1
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()

if __name__ == "__main__":
    raise SystemExit(main())
