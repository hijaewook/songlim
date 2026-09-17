import json
import uuid
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"

app = FastAPI(title="PROJECT WRECKED Online")
app.mount("/static", StaticFiles(directory=STATIC), name="static")

PLAYABLE = {"woochan", "hyochang", "piljae", "jihwan"}
MAX_PLAYERS = 4

class Room:
    def __init__(self, code: str):
        self.code = code
        self.clients = {}  # id -> {"ws": ws, "character": None}
        self.host_id = None
        self.started = False
        self.last_snapshot = None

    def roster(self):
        return [
            {
                "client_id": cid,
                "character": info.get("character"),
                "is_host": cid == self.host_id,
            }
            for cid, info in self.clients.items()
        ]

    async def send(self, cid, payload):
        info = self.clients.get(cid)
        if not info:
            return
        try:
            await info["ws"].send_text(json.dumps(payload, ensure_ascii=False))
        except Exception:
            pass

    async def broadcast(self, payload, exclude=None):
        text = json.dumps(payload, ensure_ascii=False)
        dead = []
        for cid, info in list(self.clients.items()):
            if cid == exclude:
                continue
            try:
                await info["ws"].send_text(text)
            except Exception:
                dead.append(cid)
        for cid in dead:
            self.clients.pop(cid, None)

    async def broadcast_roster(self):
        await self.broadcast({
            "type": "roster",
            "host_id": self.host_id,
            "roster": self.roster(),
        })

rooms = {}

@app.get("/")
async def root():
    return FileResponse(STATIC / "index.html")

@app.get("/health")
async def health():
    return {
        "ok": True,
        "rooms": len(rooms),
        "players": sum(len(r.clients) for r in rooms.values()),
    }

@app.websocket("/ws/{room_code}")
async def ws_endpoint(ws: WebSocket, room_code: str):
    await ws.accept()
    code = room_code.strip().upper()[:20] or "WRECKED"
    room = rooms.setdefault(code, Room(code))

    if room.started:
        await ws.send_text(json.dumps({
            "type": "error",
            "code": "ROOM_STARTED",
            "message": "이미 원정이 시작된 방입니다.",
        }, ensure_ascii=False))
        await ws.close(code=1008)
        return

    if len(room.clients) >= MAX_PLAYERS:
        await ws.send_text(json.dumps({
            "type": "error",
            "code": "ROOM_FULL",
            "message": "이 방은 이미 4명이 참가 중입니다.",
        }, ensure_ascii=False))
        await ws.close(code=1008)
        return

    cid = uuid.uuid4().hex[:8]
    room.clients[cid] = {"ws": ws, "character": None}
    if room.host_id is None:
        room.host_id = cid

    await room.send(cid, {
        "type": "welcome",
        "client_id": cid,
        "is_host": cid == room.host_id,
        "room": code,
        "roster": room.roster(),
    })
    await room.broadcast_roster()

    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            typ = msg.get("type")

            if typ == "select":
                character = msg.get("character")
                if character not in PLAYABLE:
                    await room.send(cid, {
                        "type": "error",
                        "code": "CHARACTER_LOCKED",
                        "message": "온라인 플레이는 현재 기본 4인 캐릭터를 사용합니다.",
                    })
                    continue
                duplicate = any(
                    other != cid and info.get("character") == character
                    for other, info in room.clients.items()
                )
                if duplicate:
                    await room.send(cid, {
                        "type": "error",
                        "code": "DUPLICATE_CHARACTER",
                        "message": "이미 다른 플레이어가 선택한 캐릭터입니다.",
                    })
                    continue
                room.clients[cid]["character"] = character
                await room.broadcast_roster()

            elif typ == "start":
                if cid != room.host_id:
                    continue
                missing = [x for x, info in room.clients.items() if not info.get("character")]
                if missing:
                    await room.send(cid, {
                        "type": "error",
                        "code": "NOT_READY",
                        "message": "아직 캐릭터를 선택하지 않은 참가자가 있습니다.",
                    })
                    continue
                room.started = True
                await room.broadcast({
                    "type": "start",
                    "host_id": room.host_id,
                    "roster": room.roster(),
                })

            elif typ == "input":
                if room.started and cid != room.host_id and room.host_id in room.clients:
                    await room.send(room.host_id, {
                        "type": "input",
                        "client_id": cid,
                        "input": msg.get("input", {}),
                    })

            elif typ == "snapshot":
                if room.started and cid == room.host_id:
                    room.last_snapshot = msg.get("payload")
                    await room.broadcast({
                        "type": "snapshot",
                        "payload": room.last_snapshot,
                    }, exclude=cid)

    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        was_host = cid == room.host_id
        room.clients.pop(cid, None)

        if not room.clients:
            rooms.pop(code, None)
            return

        if was_host:
            # Promote the first remaining player. Give them the latest snapshot
            # before announcing host promotion so simulation can continue.
            new_host = next(iter(room.clients))
            if room.started and room.last_snapshot is not None:
                await room.send(new_host, {
                    "type": "snapshot",
                    "payload": room.last_snapshot,
                })
            room.host_id = new_host
            await room.broadcast({
                "type": "host",
                "host_id": new_host,
            })

        await room.broadcast_roster()
