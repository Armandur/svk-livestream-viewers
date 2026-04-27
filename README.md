# svk-livestream-viewers

HTTP-server som returnerar aktuellt tittarantal för SVK-livesändningar via
Rackfish Socket.IO. Primärt avsedd för **Bitfocus Companion** / StreamDeck-integration.

Ingen SVK-sessionscookie krävs - servern hämtar JWT direkt från Rackfish
player-sidan och prenumererar på realtidsuppdateringar via Socket.IO.

## Endpoints

| Endpoint | Svar | Beskrivning |
|----------|------|-------------|
| `GET /viewers/{stream_name}` | `42` (plain text) | Aktuellt tittarantal |
| `GET /status` | JSON | Alla konfigurerade strömmar |

## Installation

```bash
cp .env.example .env
# Fyll i STREAM_UUIDS i .env (se nedan)
uv run main.py
```

## Hitta stream-UUID

UUID:t finns på tre ställen:

1. I Rackfish player-URL:en: `https://livestream.rackfish.com/player/{uuid}`
2. I player-HTML:en inbäddad på SVK-sidan (sök efter `uuid:`)
3. Via SVK admin-API:et: `GET /webapi/api-v1/media/streams` (kräver inloggning)

## Konfiguration

```
STREAM_UUIDS=c9edf4b1-d693-11e7-a385-005056be0018:svk005,other-uuid:svk007
PORT=8765
```

Format: kommaseparerade `uuid:namn`-par. `namn` används i `/viewers/{namn}`-endpointen.

## Companion-setup

1. Lägg till en **Variable** med typ **HTTP** i Companion
2. URL: `http://<server-ip>:8765/viewers/svk005`
3. Polling: var 30s
4. Referera till variabeln på StreamDeck-knappen

## Hur det fungerar

Servern ansluter till Rackfish Socket.IO-server (`rackfishlive-player.global.ssl.fastly.net`)
för varje konfigurerad ström. JWT hämtas periodvis från Rackfish player-sidan
(kräver bara `Referer: https://admin.svenskakyrkan.se/`). Vid anslutning skickas
`join_stream`-eventet och servern lyssnar på `stream_status` med `users_total`.

JWT:t förfaller efter 24h - servern hämtar nytt var 6:e timme.
