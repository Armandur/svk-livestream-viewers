# svk-livestream-viewers – spec

HTTP-server som returnerar aktuellt tittarantal för SVK-livesändningar.
Primärt syfte: integreras i **Bitfocus Companion** och visas på StreamDeck-knapp.

---

## Arkitektur

```
StreamDeck → Companion (HTTP-polling) → FastAPI-server → Rackfish Socket.IO
```

Servern håller en persistent Socket.IO-anslutning per ström och uppdateras i
realtid via `stream_status`-event. Ingen SVK-sessionscookie krävs.

---

## Autentisering mot Rackfish

Rackfish kräver ett JWT i `join_stream`-eventet. JWT:t hämtas från embed-sidan:

```
GET https://livestream.rackfish.com/embed?uuid={uuid}
Headers: Referer: https://livestream.rackfish.com/
```

Embed-sidan returnerar HTML med `Main.Init(OnConnected, 'JWT_TOKEN')`.
JWT:t extraheras med regex och är giltigt i 24h. Servern hämtar nytt var 6:e timme.

**Obs:** Rackfish kontrollerar Referer-headern men kräver ingen inloggad session.
Embed-URL:en är designad för extern inbäddning och kräver bara att Referer är på
`livestream.rackfish.com`.

---

## Rackfish Socket.IO

**Server:** `https://rackfishlive-player.global.ssl.fastly.net`

### Anslutningsflöde

1. `connect` - ansluten
2. Emittera `join_stream` med `{"uuid": "...", "token": "JWT"}`
3. Ta emot `stream_status`-event

### `stream_status`-event (inkommande)

```json
{
  "users_total": 42,
  ...
}
```

`users_total` = aktuellt antal tittare. Skickas vid förändring.

---

## Endpoints

### `GET /viewers/{stream_name}`

Returnerar aktuellt tittarantal som **plain text** (för Companion).

**Response:** `42` (plain text, HTTP 200)

Returnerar `0` om strömmen inte är live eller ingen `stream_status` har tagits emot ännu.
Returnerar HTTP 404 om `stream_name` inte är konfigurerat.

### `GET /status`

JSON-svar med alla konfigurerade strömmar och deras senaste värden.

---

## Konfiguration (.env)

```
STREAM_UUIDS=c9edf4b1-d693-11e7-a385-005056be0018:svk005,uuid2:svk007
PORT=8765
```

Format: kommaseparerade `uuid:namn`-par.
UUID hittas i Rackfish player-URL:en eller via SVK admin-API:et.

---

## Companion-setup

1. Lägg till en **Generic HTTP** action eller variabel i Companion
2. URL: `http://<server-ip>:8765/viewers/svk005`
3. Polling: var 30s
4. Visa svaret på StreamDeck-knappen som text

---

## Felhantering

- Player-sidan returnerar 403: retry om 60s
- JWT saknas i HTML: retry om 60s
- Socket.IO kopplar ner: `users_total` sätts till 0, reconnect försöks upp till 10 ggr
- JWT förfaller (24h): servern hämtar nytt var 6:e timme
