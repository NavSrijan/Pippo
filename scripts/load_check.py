"""Measure local rendering pressure without contacting Discord or any provider."""
import argparse
import asyncio
import json
from pathlib import Path
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from functions import write_caption_on_image
from runtime import run_blocking


async def measure(jobs):
    running = peak = 0
    lock = threading.Lock()
    delays = []
    finished = False
    started = time.perf_counter()

    def render(number):
        nonlocal running, peak
        with lock:
            running += 1
            peak = max(peak, running)
        try:
            file = write_caption_on_image(ROOT / 'imgs/bollywood_scenes/scene_01.webp',
                                          f'Player {number} · independent game',
                                          'Concurrent rendering check', f'game-{number}.jpg')
            try:
                return len(file.fp.getbuffer())
            finally:
                file.close()
        finally:
            with lock:
                running -= 1

    async def heartbeat():
        while not finished:
            start = time.perf_counter()
            await asyncio.sleep(.005)
            delays.append(max(0, time.perf_counter() - start - .005) * 1000)

    monitor = asyncio.create_task(heartbeat())
    try:
        sizes = await asyncio.gather(*(run_blocking(render, n) for n in range(jobs)))
    finally:
        finished = True
        await monitor
    elapsed = time.perf_counter() - started
    delays.sort()
    return {
        'concurrent_render_requests': jobs,
        'completed': len(sizes),
        'peak_media_workers': peak,
        'elapsed_seconds': round(elapsed, 3),
        'p95_event_loop_delay_ms': round(delays[min(len(delays)-1, int(len(delays)*.95))], 2),
        'max_event_loop_delay_ms': round(max(delays), 2),
        'scope': 'Local CPU and file work; excludes Discord/provider network rate limits',
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jobs', type=int, default=80)
    options = parser.parse_args()
    if not 1 <= options.jobs <= 500:
        parser.error('--jobs must be between 1 and 500')
    print(json.dumps(asyncio.run(measure(options.jobs)), indent=2))
