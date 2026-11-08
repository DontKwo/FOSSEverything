import subprocess
import sys
import time

def test_api_import_latency() -> None:
    start_time = time.perf_counter()
    subprocess.run([sys.executable, "-c", "import app.web.api"], check=True)
    end_time = time.perf_counter()
    latency = end_time - start_time
    print(f"API import latency: {latency:.4f} seconds")
    assert latency < 0.35, f"API import latency ({latency:.4f}s) exceeded 0.35s budget"
