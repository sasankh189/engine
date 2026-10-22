"""Simple cross-platform live terminal monitor helper."""
import time

def show_progress(processed, total, trades, started):
    elapsed = max(time.perf_counter() - started, 1e-9)
    rate = processed / elapsed