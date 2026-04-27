# svk-livestream-viewers

HTTP-server som visar realtids-tittarantal för SVK-livesändningar via Rackfish
Socket.IO. Ingen SVK-sessionscookie krävs.

Primärt avsedd för **Bitfocus Companion** / StreamDeck-integration, men
inkluderar också ett webb-UI för strömhantering.

## Endpoints

| Endpoint | Svar | Beskrivning |
|----------|------|-------------|
| `GET /` | HTML | Webb-UI för strömhantering |
| `GET /viewers/{namn}` | `42` (plain text) | Aktuellt tittarantal (för Companion) |
| `GET /player/{namn}` | HTML | Proxad Rackfish-spelare |
| `GET /status` | JSON | Alla strömmar med tittarantal och live-status |
| `GET /api/streams` | JSON | CRUD-API – lista strömmar |
| `POST /api/streams` | JSON | Lägg till ström `{uuid, name}` |
| `POST /api/streams/import` | JSON | Bulk-import `{streams: [{uuid, name}]}` |
| `DELETE /api/streams/{namn}` | 204 | Ta bort ström |

## Installation

```bash
cp .env.example .env
uv run main.py
```

Öppna `http://localhost:8765/` för att hantera strömmar via webb-UI:t.

## Lägga till strömmar

### Via webb-UI + bookmarklet

1. Kör bookmarkleten på `admin.svenskakyrkan.se` för att hämta alla strömmar
2. Välj strömmar i dialogen, klicka "Kopiera markerade"
3. Öppna webb-UI:t, expandera "Importera strömmar", klistra in och importera

Bookmarkleten finns inbäddad i webb-UI:t under "Importera strömmar".

### Via .env (seed vid första start)

```
STREAM_UUIDS=c9edf4b1-d693-11e7-a385-005056be0018:svk005,other-uuid:svk007
```

Används bara om `streams.json` är tom. Strömmar sparas sedan i `streams.json`.

## Companion-setup

1. Lägg till en **Variable** med typ **HTTP** i Companion
2. URL: `http://<server-ip>:8765/viewers/svk005`
3. Polling: var 5–10s
4. Referera till variabeln på StreamDeck-knappen

## Konfiguration (.env)

```
STREAM_UUIDS=       # seed-UUID:n vid första start (valfritt)
PORT=8765
LOG_LEVEL=INFO      # DEBUG visar per-event-detaljer
```

## Obs

Varje ström som läggs till ökar det synliga tittarantalet med +1 eftersom
serveranslutningen räknas som en tittare av Rackfish. Servern kompenserar
automatiskt, men undvik att köra flera instanser mot samma UUID.
