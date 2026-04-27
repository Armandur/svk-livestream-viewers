import asyncio
import json
import logging
import os
import time
from typing import Dict, List, Optional

log = logging.getLogger(__name__)

STREAMS_FILE = "streams.json"
NONZERO_TTL = 20.0

# state
_streams: List[Dict[str, str]] = []  # List of {uuid, name}
_last_nonzero: Dict[str, int] = {}
_last_nonzero_ts: Dict[str, float] = {}
_alive: Dict[str, bool] = {}
_tasks: Dict[str, asyncio.Task] = {}

# We need a reference to the run_stream function which will be in main.py
# To avoid circular imports, we can set it later or pass it.
# Actually, the prompt says "Importera allt state från store.py" in main.py.
# So main.py will import store.
_run_stream_func = None

def set_run_stream_func(func):
    global _run_stream_func
    _run_stream_func = func

def get_streams() -> List[Dict[str, str]]:
    return _streams

def smoothed(name: str) -> int:
    if name not in _last_nonzero_ts:
        return 0
    if time.monotonic() - _last_nonzero_ts[name] < NONZERO_TTL:
        return _last_nonzero.get(name, 0)
    return 0

def is_alive(name: str) -> bool:
    return _alive.get(name, False)

def set_alive(name: str, alive: bool) -> None:
    _alive[name] = alive

def record(name: str, count: int) -> None:
    if count > 0:
        _last_nonzero[name] = count
        _last_nonzero_ts[name] = time.monotonic()

async def load_streams(initial_streams: List[tuple[str, str]] = None):
    global _streams
    if os.path.exists(STREAMS_FILE):
        try:
            with open(STREAMS_FILE, "r") as f:
                _streams = json.load(f)
                log.info("Laddade %d strömmar från %s", len(_streams), STREAMS_FILE)
        except Exception as e:
            log.error("Kunde inte läsa %s: %s", STREAMS_FILE, e)
            _streams = []
    
    if not _streams and initial_streams:
        log.info("Använder initiala strömmar från inställningar")
        _streams = [{"uuid": uuid, "name": name} for uuid, name in initial_streams]
        await save_streams()

def _save_streams_sync():
    with open(STREAMS_FILE, "w") as f:
        json.dump(_streams, f, indent=2)

async def save_streams():
    # Use run_in_executor for I/O if needed, but for small files sync is fine
    # Prompt didn't specify aiofiles for this, but main.py needs it for StaticFiles
    _save_streams_sync()

async def add_stream(uuid: str, name: str):
    if any(s["name"] == name for s in _streams):
        return
    _streams.append({"uuid": uuid, "name": name})
    await save_streams()
    start_stream_task(uuid, name)

async def remove_stream(name: str):
    global _streams
    _streams = [s for s in _streams if s["name"] != name]
    await save_streams()
    stop_stream_task(name)
    _last_nonzero.pop(name, None)
    _last_nonzero_ts.pop(name, None)
    _alive.pop(name, None)

def start_stream_task(uuid: str, name: str):
    if name in _tasks:
        return
    if _run_stream_func:
        _tasks[name] = asyncio.create_task(_run_stream_func(uuid, name))
        log.info("Startade task för %s", name)

def stop_stream_task(name: str):
    task = _tasks.pop(name, None)
    if task:
        task.cancel()
        log.info("Stoppade task för %s", name)
    return task

async def stop_all_tasks():
    tasks = []
    names = list(_tasks.keys())
    for name in names:
        task = stop_stream_task(name)
        if task:
            tasks.append(task)
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
