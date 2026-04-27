import asyncio
import logging
import re
from contextlib import asynccontextmanager
from typing import Dict, List

import httpx
import socketio
import uvicorn
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import PlainTextResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

import store

log = logging.getLogger(__name__)

PLAYER_BASE = "https://livestream.rackfish.com/player"
EMBED_BASE = "https://livestream.rackfish.com/embed"
SOCKET_URL = "https://rackfishlive-player.global.ssl.fastly.net"
REFERER = "https://livestream.rackfish.com/"
JWT_REFRESH_SECS = 6 * 3600

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    stream_uuids: str = ""  # "uuid1:namn1,uuid2:namn2"
    port: int = 8765
    log_level: str = "INFO"

    @property
    def streams_list(self) -> List[tuple[str, str]]:
        result = []
        for pair in self.stream_uuids.split(","):
            pair = pair.strip()
            if ":" in pair:
                uuid, name = pair.split(":", 1)
                result.append((uuid.strip(), name.strip()))
        return result

settings = Settings()
logging.basicConfig(level=settings.log_level.upper(), format="%(asctime)s %(levelname)s %(message)s")

class StreamCreate(BaseModel):
    uuid: str
    name: str

class StreamImport(BaseModel):
    streams: List[StreamCreate]

async def _get_jwt(client: httpx.AsyncClient, uuid: str) -> str:
    r = await client.get(
        f"{EMBED_BASE}?uuid={uuid}",
        headers={"Referer": REFERER, "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"},
    )
    r.raise_for_status()
    m = re.search(r"Main\.Init\s*\(\s*\w+\s*,\s*'([^']+)'", r.text)
    if not m:
        raise ValueError(f"JWT saknas i player-sidan för {uuid}")
    return m.group(1)

async def _run_stream(uuid: str, name: str) -> None:
    async with httpx.AsyncClient(timeout=30) as client:
        while True:
            sio = None
            try:
                log.info("Hämtar JWT för %s", name)
                jwt = await _get_jwt(client, uuid)

                sio = socketio.AsyncClient(
                    reconnection=True,
                    reconnection_attempts=10,
                    reconnection_delay=30,
                )

                @sio.event
                async def stream_status(data):
                    # Dra bort 1 för vår egen Socket.IO-anslutning som räknas som tittare
                    count = max(0, int(data.get("users_total", 0)) - 1)
                    store.record(name, count)
                    store.set_alive(name, bool(data.get("alive", 0)))
                    log.debug("%s: råvärde=%d justerat=%d alive=%s", name, data.get("users_total"), count, data.get("alive"))

                @sio.event
                async def connect():
                    log.info("Ansluten till Rackfish för %s", name)
                    await sio.emit("join_stream", (uuid, jwt))

                @sio.event
                async def disconnect():
                    store.set_alive(name, False)
                    log.info("Frånkopplad från Rackfish för %s", name)

                await sio.connect(SOCKET_URL)
                await asyncio.sleep(JWT_REFRESH_SECS)

            except asyncio.CancelledError:
                log.info("Task för %s avbruten", name)
                if sio and sio.connected:
                    await sio.disconnect()
                break
            except Exception as e:
                log.warning("Fel för %s: %s – försöker igen om 60s", name, e)
                await asyncio.sleep(60)
            finally:
                if sio and sio.connected:
                    await sio.disconnect()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup store and tasks
    store.set_run_stream_func(_run_stream)
    await store.load_streams(settings.streams_list)
    
    # Start all streams
    for s in store.get_streams():
        store.start_stream_task(s["uuid"], s["name"])
        
    yield
    
    # Shutdown all tasks
    await store.stop_all_tasks()

app = FastAPI(title="SVK Livestream Viewers", lifespan=lifespan)

# API Routes
@app.get("/api/streams")
async def api_get_streams():
    return [
        {**s, "viewers": store.smoothed(s["name"]), "alive": store.is_alive(s["name"])}
        for s in store.get_streams()
    ]

@app.post("/api/streams", status_code=status.HTTP_201_CREATED)
async def api_add_stream(stream: StreamCreate):
    await store.add_stream(stream.uuid, stream.name)
    return {"status": "ok"}

@app.delete("/api/streams/{name}", status_code=status.HTTP_204_NO_CONTENT)
async def api_remove_stream(name: str):
    await store.remove_stream(name)
    return

@app.post("/api/streams/import", status_code=status.HTTP_200_OK)
async def api_import_streams(body: StreamImport):
    added = []
    for s in body.streams:
        if not any(x["name"] == s.name for x in store.get_streams()):
            await store.add_stream(s.uuid, s.name)
            added.append(s.name)
    return {"added": added, "count": len(added)}

# Legacy / Existing Endpoints
@app.get("/viewers/{stream_name}", response_class=PlainTextResponse)
async def viewers(stream_name: str) -> str:
    # Check if stream exists in our list
    if not any(s["name"] == stream_name for s in store.get_streams()):
        raise HTTPException(status_code=404, detail=f"Ström '{stream_name}' är inte konfigurerad")
    return str(store.smoothed(stream_name))

@app.get("/status")
async def status_endpoint() -> dict:
    return {s["name"]: {"viewers": store.smoothed(s["name"])} for s in store.get_streams()}

@app.get("/player/{stream_name}")
async def player_proxy(stream_name: str):
    stream = next((s for s in store.get_streams() if s["name"] == stream_name), None)
    if not stream:
        raise HTTPException(status_code=404, detail=f"Ström '{stream_name}' är inte konfigurerad")
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(
            f"{EMBED_BASE}?uuid={stream['uuid']}",
            headers={"Referer": REFERER, "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"},
        )
        if not r.is_success:
            raise HTTPException(status_code=r.status_code, detail="Kunde inte hämta player-sidan")
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=r.text)

# Static Files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_index():
    return FileResponse("static/index.html")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=settings.port, reload=False)
