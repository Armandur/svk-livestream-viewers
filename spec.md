# svk-livestream-viewers – spec

HTTP-server som visar realtids-tittarantal för SVK-livesändningar.
Primärt syfte: integreras i **Bitfocus Companion** och visas på StreamDeck-knapp.

---

## Arkitektur

```
StreamDeck → Companion (HTTP-polling) → FastAPI-server → Rackfish Socket.IO
                                              ↑
                                        Webb-UI (browser)
```

Servern håller en persistent Socket.IO-anslutning per ström och uppdateras i
realtid via `stream_status`-event. Ingen SVK-sessionscookie krävs.

Strömkonfiguration sparas i `streams.json` och hanteras via webb-UI eller API.

---

## Autentisering mot Rackfish

JWT hämtas från Rackfish embed-sidan:

```
GET https://livestream.rackfish.com/embed?uuid={uuid}
Headers: Referer: https://livestream.rackfish.com/
```

Embed-sidan returnerar HTML med `Main.Init(OnConnected, 'JWT_TOKEN')`.
JWT:t extraheras med regex och är giltigt i 24h. Servern hämtar nytt var 6:e timme.

Vissa strömmar har Referer-restriktioner konfigurerade – embed-URL:en med
`Referer: https://livestream.rackfish.com/` fungerar universellt.

---

## Rackfish Socket.IO

**Server:** `https://rackfishlive-player.global.ssl.fastly.net`

### Anslutningsflöde

1. Anslut till Socket.IO-servern
2. Emittera `join_stream` med **två separata argument**: `(uuid, jwt)`
   (inte ett objekt – detta är avgörande)
3. Ta emot `stream_status`-events

### `stream_status`-event

Rackfish skickar **delta-events** – bara förändrade fält. Det första eventet
efter `join_stream` är ett fullständigt snapshot; därefter skickas bara det som
ändrats. Fält som saknas i ett event ska tolkas som oförändrade.

```json
// Fullständigt snapshot (första eventet)
{"alive": 1, "post_event": 0, "users_total": 3, "manifest_valid": true,
 "manifest_status": 200, "manifest_count": 158}

// Deltaevents (efterföljande)
{"users_total": 2}
{"manifest_count": 159}
```

| Fält | Beskrivning |
|------|-------------|
| `alive` | `1` = encoder aktivt ansluten och sänder |
| `users_total` | Antal Socket.IO-anslutningar (inkl. vår server = +1) |
| `manifest_valid` | HLS-manifestet är tillgängligt |
| `manifest_count` | Räknare för manifest-hämtningar (uppdateras ~var 3s av Rackfish) |

**`alive`-logik:** `alive=True` om Rackfish-fältet är `1` ELLER om
`users_total > 1` (fler än bara vår server tittar).

**Tittarkorrigering:** `users_total - 1` (kompenserar för vår egen anslutning).
Räknaren smoothas med 20s TTL för att filtrera bort Rackfishs oscillationer.

---

## Endpoints

### `GET /viewers/{stream_name}`
Plain text, för Companion. Returnerar smoothat tittarantal.

### `GET /player/{stream_name}`
Proxar Rackfish embed-sidan via servern med korrekt Referer-header.

### `GET /status`
```json
{"svk005": {"viewers": 3}}
```

### `GET /api/streams`
```json
[{"uuid": "...", "name": "svk005", "viewers": 3, "alive": true}]
```

### `POST /api/streams`
Body: `{"uuid": "...", "name": "svk005"}`. Startar Socket.IO-task direkt.

### `POST /api/streams/import`
Body: `{"streams": [{"uuid": "...", "name": "svk005"}]}`.
Hoppar över strömmar som redan finns.

### `DELETE /api/streams/{name}`
Stoppar Socket.IO-task och tar bort från `streams.json`.

---

## Konfiguration (.env)

```
STREAM_UUIDS=uuid1:svk005,uuid2:svk007   # seed vid första start om streams.json saknas
PORT=8765
LOG_LEVEL=INFO                            # DEBUG loggar per-event-detaljer
```

---

## Companion-setup

1. Lägg till en **Generic HTTP**-variabel i Companion
2. URL: `http://<server-ip>:8765/viewers/svk005`
3. Polling: var 5–10s
4. Visa svaret på StreamDeck-knappen

---

## Felhantering

- Embed-sidan returnerar 403 eller JWT saknas: retry om 60s
- Socket.IO kopplar ner: tittarantal och alive behåller senaste kända värde,
  reconnect försöks upp till 10 ggr med 30s fördröjning
- JWT förfaller (24h): servern hämtar nytt var 6:e timme
