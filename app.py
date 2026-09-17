import asyncio
import json
import math
import random
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="2P Coop Roguelike Prototype")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

WIDTH, HEIGHT = 960, 600
TICK_RATE = 30
DT = 1.0 / TICK_RATE

CHARACTERS = {
    "jaeuk": {
        "name": "이재욱",
        "max_hp": 140,
        "speed": 220,
        "basic_damage": 18,
        "basic_cd": 0.34,
    },
    "woochan": {
        "name": "김우찬",
        "max_hp": 100,
        "speed": 245,
        "basic_damage": 14,
        "basic_cd": 0.26,
    },
}

REWARDS = {
    "power": {"title": "공격 강화", "desc": "모든 피해 +18%"},
    "vitality": {"title": "생명력", "desc": "최대 체력 +25, 즉시 25 회복"},
    "haste": {"title": "신속", "desc": "스킬 쿨다운 -12%"},
    "fleet": {"title": "기동력", "desc": "이동 속도 +12%"},
    "crit": {"title": "집중", "desc": "20% 확률로 1.6배 피해"},
    "leech": {"title": "전투 흡수", "desc": "적 처치 시 체력 8 회복"},
    "boss": {"title": "거인 사냥꾼", "desc": "보스에게 주는 피해 +25%"},
    "guard": {"title": "수호", "desc": "받는 피해 -10%"},
}

def clamp(v, a, b):
    return max(a, min(b, v))

def dist(a, b):
    return math.hypot(a["x"] - b["x"], a["y"] - b["y"])

def norm(x, y):
    d = math.hypot(x, y)
    if d < 1e-6:
        return 1.0, 0.0
    return x / d, y / d

class Room:
    def __init__(self, code):
        self.code = code
        self.players = {}
        self.stage = 1
        self.mode = "waiting"
        self.enemies = []
        self.projectiles = []
        self.enemy_seq = 1
        self.projectile_seq = 1
        self.reward_choices = {}
        self.reward_selected = set()
        self.task = None
        self.last_time = time.monotonic()
        self.message = "플레이어를 기다리는 중"
        self.stage_started_at = time.monotonic()

    def public_state(self):
        now = time.monotonic()
        players = {}
        for pid, p in self.players.items():
            players[pid] = {
                "id": pid,
                "character": p["character"],
                "name": p["name"],
                "x": p["x"], "y": p["y"],
                "hp": p["hp"], "max_hp": p["max_hp"],
                "alive": p["alive"],
                "unlocked": p["unlocked"],
                "guardian_until": p.get("guardian_until", 0),
                "parry_until": p.get("parry_until", 0),
                "counter_until": p.get("counter_until", 0),
                "reward": p.get("reward", {}),
            }
        return {
            "type": "state",
            "stage": self.stage,
            "mode": self.mode,
            "message": self.message,
            "players": players,
            "enemies": self.enemies,
            "projectiles": self.projectiles,
            "reward_choices": self.reward_choices,
            "reward_selected": list(self.reward_selected),
            "rewards": REWARDS,
            "server_time": now,
        }

    async def broadcast(self):
        if not self.players:
            return
        msg = json.dumps(self.public_state(), ensure_ascii=False)
        dead = []
        for pid, p in list(self.players.items()):
            try:
                await p["ws"].send_text(msg)
            except Exception:
                dead.append(pid)
        for pid in dead:
            self.players.pop(pid, None)

    def add_player(self, pid, character, ws):
        cfg = CHARACTERS[character]
        spawn_x = 250 if character == "jaeuk" else 710
        spawn_y = 450 if character == "jaeuk" else 470
        self.players[pid] = {
            "id": pid,
            "ws": ws,
            "character": character,
            "name": cfg["name"],
            "x": spawn_x, "y": spawn_y,
            "hp": cfg["max_hp"], "max_hp": cfg["max_hp"],
            "speed": cfg["speed"],
            "base_damage": cfg["basic_damage"],
            "basic_cd": cfg["basic_cd"],
            "input": {
                "up": False, "down": False, "left": False, "right": False,
                "attack": False, "s1": False, "s2": False, "s3": False,
                "dash": False, "aim_x": 1.0, "aim_y": 0.0,
            },
            "prev_buttons": {"s1": False, "s2": False, "s3": False, "dash": False},
            "attack_ready": 0.0,
            "skill_ready": [0.0, 0.0, 0.0],
            "dash_ready": 0.0,
            "unlocked": min(3, max(0, self.stage - 1)),
            "alive": True,
            "parry_until": 0.0,
            "counter_until": 0.0,
            "guardian_until": 0.0,
            "reward": {
                "damage_mult": 1.0,
                "cooldown_mult": 1.0,
                "speed_mult": 1.0,
                "crit": 0.0,
                "leech": 0,
                "boss_mult": 1.0,
                "damage_taken_mult": 1.0,
            },
        }
        if self.mode == "waiting":
            self.start_stage(1)
        elif self.mode == "reward":
            self.players[pid]["unlocked"] = min(3, self.stage)
            self.reward_choices[pid] = random.sample(list(REWARDS.keys()), 3)

    def remove_player(self, pid):
        self.players.pop(pid, None)
        self.reward_selected.discard(pid)
        self.reward_choices.pop(pid, None)

    def spawn_enemy(self, etype, x=None, y=None, hp=None):
        if x is None:
            side = random.choice(["top", "left", "right"])
            if side == "top":
                x, y = random.randint(80, 880), random.randint(70, 130)
            elif side == "left":
                x, y = random.randint(60, 120), random.randint(100, 430)
            else:
                x, y = random.randint(840, 900), random.randint(100, 430)

        stats = {
            "grunt": {"hp": 48, "speed": 85, "damage": 9, "radius": 18},
            "runner": {"hp": 36, "speed": 135, "damage": 8, "radius": 16},
            "shooter": {"hp": 42, "speed": 55, "damage": 8, "radius": 17},
            "elite": {"hp": 115, "speed": 75, "damage": 15, "radius": 23},
            "boss": {"hp": 780, "speed": 72, "damage": 22, "radius": 42},
        }[etype]
        scale = 1.0 + (self.stage - 1) * 0.14
        self.enemies.append({
            "id": self.enemy_seq,
            "type": etype,
            "x": float(x), "y": float(y),
            "hp": float(hp or stats["hp"] * scale),
            "max_hp": float(hp or stats["hp"] * scale),
            "speed": stats["speed"],
            "damage": stats["damage"],
            "radius": stats["radius"],
            "attack_ready": 0.0,
            "skill_ready": 0.0,
            "stun_until": 0.0,
            "marked_until": 0.0,
            "vulnerable_until": 0.0,
            "boss": etype == "boss",
        })
        self.enemy_seq += 1

    def start_stage(self, stage):
        self.stage = stage
        self.mode = "playing"
        self.message = f"{stage} 스테이지"
        self.enemies = []
        self.projectiles = []
        self.reward_choices = {}
        self.reward_selected = set()
        self.stage_started_at = time.monotonic()

        for p in self.players.values():
            p["alive"] = True
            p["hp"] = max(1, min(p["max_hp"], p["hp"] + p["max_hp"] * 0.22))
            p["x"] = 300 if p["character"] == "jaeuk" else 660
            p["y"] = 500

        if stage == 1:
            for _ in range(5): self.spawn_enemy("grunt")
            self.spawn_enemy("shooter")
        elif stage == 2:
            for _ in range(4): self.spawn_enemy("grunt")
            for _ in range(3): self.spawn_enemy("runner")
            for _ in range(2): self.spawn_enemy("shooter")
        elif stage == 3:
            for _ in range(4): self.spawn_enemy("runner")
            for _ in range(3): self.spawn_enemy("shooter")
            self.spawn_enemy("elite")
        elif stage == 4:
            for _ in range(4): self.spawn_enemy("grunt")
            for _ in range(4): self.spawn_enemy("runner")
            for _ in range(3): self.spawn_enemy("shooter")
            for _ in range(2): self.spawn_enemy("elite")
        elif stage == 5:
            self.spawn_enemy("boss", 480, 170, 900)
            for _ in range(2): self.spawn_enemy("shooter")
            self.message = "보스 라운드 - 심연 기사 바르칸"

    def begin_reward(self):
        self.mode = "reward"
        self.message = "보상을 선택하세요"
        keys = list(REWARDS.keys())
        for pid, p in self.players.items():
            if p["alive"]:
                self.reward_choices[pid] = random.sample(keys, 3)
            if self.stage <= 3:
                p["unlocked"] = max(p["unlocked"], self.stage)

    def apply_reward(self, pid, reward_id):
        p = self.players.get(pid)
        if not p or reward_id not in REWARDS:
            return
        r = p["reward"]
        if reward_id == "power":
            r["damage_mult"] *= 1.18
        elif reward_id == "vitality":
            p["max_hp"] += 25
            p["hp"] = min(p["max_hp"], p["hp"] + 25)
        elif reward_id == "haste":
            r["cooldown_mult"] *= 0.88
        elif reward_id == "fleet":
            r["speed_mult"] *= 1.12
        elif reward_id == "crit":
            r["crit"] = min(0.65, r["crit"] + 0.20)
        elif reward_id == "leech":
            r["leech"] += 8
        elif reward_id == "boss":
            r["boss_mult"] *= 1.25
        elif reward_id == "guard":
            r["damage_taken_mult"] *= 0.90

    def damage_enemy(self, enemy, amount, source_pid):
        p = self.players.get(source_pid)
        if not p:
            return
        now = time.monotonic()
        mult = p["reward"]["damage_mult"]
        if enemy.get("boss"):
            mult *= p["reward"]["boss_mult"]
        if enemy.get("marked_until", 0) > now:
            mult *= 1.20
        if enemy.get("vulnerable_until", 0) > now:
            mult *= 1.18
        if p.get("counter_until", 0) > now:
            mult *= 1.45
            p["counter_until"] = 0.0
        if random.random() < p["reward"]["crit"]:
            mult *= 1.6
        enemy["hp"] -= amount * mult

    def heal_on_kill(self, source_pid):
        p = self.players.get(source_pid)
        if p and p["reward"]["leech"] > 0:
            p["hp"] = min(p["max_hp"], p["hp"] + p["reward"]["leech"])

    def add_projectile(self, owner, x, y, vx, vy, damage, radius=6, lifetime=1.7,
                       source_pid=None, pierce=0, marked_explosion=False):
        self.projectiles.append({
            "id": self.projectile_seq,
            "owner": owner,
            "x": x, "y": y, "vx": vx, "vy": vy,
            "damage": damage, "radius": radius,
            "life": lifetime,
            "source_pid": source_pid,
            "pierce": pierce,
            "marked_explosion": marked_explosion,
            "hit_ids": [],
        })
        self.projectile_seq += 1

    def basic_attack(self, p, now):
        if now < p["attack_ready"] or not p["alive"] or self.mode != "playing":
            return
        p["attack_ready"] = now + p["basic_cd"]
        ax, ay = norm(p["input"]["aim_x"], p["input"]["aim_y"])
        if p["character"] == "jaeuk":
            for e in self.enemies:
                dx, dy = e["x"] - p["x"], e["y"] - p["y"]
                d = math.hypot(dx, dy)
                if d <= 82:
                    nx, ny = norm(dx, dy)
                    if nx * ax + ny * ay > 0.15:
                        self.damage_enemy(e, p["base_damage"], p["id"])
        else:
            speed = 540
            self.add_projectile(
                "player", p["x"] + ax * 20, p["y"] + ay * 20,
                ax * speed, ay * speed, p["base_damage"],
                source_pid=p["id"]
            )

    def cast_skill(self, p, idx, now):
        if idx >= p["unlocked"] or not p["alive"] or self.mode != "playing":
            return
        if now < p["skill_ready"][idx]:
            return

        ax, ay = norm(p["input"]["aim_x"], p["input"]["aim_y"])
        cd_base = [5.0, 7.0, 10.0][idx]
        p["skill_ready"][idx] = now + cd_base * p["reward"]["cooldown_mult"]

        if p["character"] == "jaeuk":
            if idx == 0:
                p["parry_until"] = now + 0.62
            elif idx == 1:
                p["x"] = clamp(p["x"] + ax * 115, 30, WIDTH - 30)
                p["y"] = clamp(p["y"] + ay * 115, 30, HEIGHT - 30)
                for e in self.enemies:
                    if dist(p, e) < 90:
                        self.damage_enemy(e, 28, p["id"])
                        e["vulnerable_until"] = now + 3.5
            elif idx == 2:
                p["guardian_until"] = now + 4.5
        else:
            if idx == 0:
                candidates = sorted(
                    [e for e in self.enemies if dist(p, e) < 420],
                    key=lambda e: dist(p, e)
                )
                if candidates:
                    candidates[0]["marked_until"] = now + 7.0
            elif idx == 1:
                base_ang = math.atan2(ay, ax)
                for off in (-0.20, 0.0, 0.20):
                    ang = base_ang + off
                    self.add_projectile(
                        "player", p["x"], p["y"],
                        math.cos(ang) * 560, math.sin(ang) * 560,
                        20, source_pid=p["id"]
                    )
            elif idx == 2:
                self.add_projectile(
                    "player", p["x"], p["y"],
                    ax * 850, ay * 850, 62,
                    radius=9, lifetime=1.4, source_pid=p["id"],
                    pierce=4, marked_explosion=True
                )

    def do_dash(self, p, now):
        if now < p["dash_ready"] or not p["alive"] or self.mode != "playing":
            return
        p["dash_ready"] = now + 1.15
        mx = (1 if p["input"]["right"] else 0) - (1 if p["input"]["left"] else 0)
        my = (1 if p["input"]["down"] else 0) - (1 if p["input"]["up"] else 0)
        if mx == 0 and my == 0:
            mx, my = norm(p["input"]["aim_x"], p["input"]["aim_y"])
        else:
            mx, my = norm(mx, my)
        p["x"] = clamp(p["x"] + mx * 92, 25, WIDTH - 25)
        p["y"] = clamp(p["y"] + my * 92, 25, HEIGHT - 25)

    def damage_player(self, p, amount, enemy=None):
        if not p["alive"]:
            return
        now = time.monotonic()
        if p.get("parry_until", 0) > now:
            p["counter_until"] = now + 2.0
            if enemy is not None:
                enemy["stun_until"] = now + 1.1
                enemy["hp"] -= 12
            return

        reduced = False
        for ally in self.players.values():
            if ally["alive"] and ally.get("guardian_until", 0) > now and dist(p, ally) < 135:
                amount *= 0.60
                reduced = True
                break
        amount *= p["reward"]["damage_taken_mult"]
        p["hp"] -= amount
        if p["hp"] <= 0:
            p["hp"] = 0
            p["alive"] = False

    def update_players(self, dt, now):
        for p in self.players.values():
            if not p["alive"]:
                continue
            inp = p["input"]
            mx = (1 if inp["right"] else 0) - (1 if inp["left"] else 0)
            my = (1 if inp["down"] else 0) - (1 if inp["up"] else 0)
            if mx or my:
                mx, my = norm(mx, my)
                spd = p["speed"] * p["reward"]["speed_mult"]
                p["x"] = clamp(p["x"] + mx * spd * dt, 24, WIDTH - 24)
                p["y"] = clamp(p["y"] + my * spd * dt, 45, HEIGHT - 24)

            if inp["attack"]:
                self.basic_attack(p, now)

            for i, key in enumerate(("s1", "s2", "s3")):
                if inp[key] and not p["prev_buttons"][key]:
                    self.cast_skill(p, i, now)
                p["prev_buttons"][key] = bool(inp[key])

            if inp["dash"] and not p["prev_buttons"]["dash"]:
                self.do_dash(p, now)
            p["prev_buttons"]["dash"] = bool(inp["dash"])

    def update_enemies(self, dt, now):
        alive_players = [p for p in self.players.values() if p["alive"]]
        if not alive_players:
            return

        for e in self.enemies:
            if e["hp"] <= 0 or e.get("stun_until", 0) > now:
                continue
            target = min(alive_players, key=lambda p: dist(e, p))
            dx, dy = target["x"] - e["x"], target["y"] - e["y"]
            d = math.hypot(dx, dy)
            nx, ny = norm(dx, dy)

            if e["type"] == "shooter":
                if d < 180:
                    e["x"] -= nx * e["speed"] * dt
                    e["y"] -= ny * e["speed"] * dt
                elif d > 330:
                    e["x"] += nx * e["speed"] * dt
                    e["y"] += ny * e["speed"] * dt
                if now >= e["attack_ready"]:
                    e["attack_ready"] = now + 1.55
                    self.add_projectile(
                        "enemy", e["x"], e["y"], nx * 310, ny * 310,
                        e["damage"], radius=7, lifetime=2.4
                    )
            elif e["type"] == "boss":
                if d > 95:
                    e["x"] += nx * e["speed"] * dt
                    e["y"] += ny * e["speed"] * dt
                if d <= 105 and now >= e["attack_ready"]:
                    e["attack_ready"] = now + 1.15
                    self.damage_player(target, e["damage"], e)
                if now >= e["skill_ready"]:
                    e["skill_ready"] = now + 2.4
                    for i in range(12):
                        ang = i * (math.tau / 12.0)
                        self.add_projectile(
                            "enemy", e["x"], e["y"],
                            math.cos(ang) * 245, math.sin(ang) * 245,
                            11, radius=8, lifetime=2.8
                        )
            else:
                if d > e["radius"] + 22:
                    e["x"] += nx * e["speed"] * dt
                    e["y"] += ny * e["speed"] * dt
                if d <= e["radius"] + 28 and now >= e["attack_ready"]:
                    e["attack_ready"] = now + (0.85 if e["type"] == "runner" else 1.1)
                    self.damage_player(target, e["damage"], e)

            e["x"] = clamp(e["x"], 20, WIDTH - 20)
            e["y"] = clamp(e["y"], 45, HEIGHT - 20)

    def update_projectiles(self, dt, now):
        kept = []
        for pr in self.projectiles:
            pr["x"] += pr["vx"] * dt
            pr["y"] += pr["vy"] * dt
            pr["life"] -= dt
            remove = pr["life"] <= 0 or pr["x"] < -30 or pr["x"] > WIDTH + 30 or pr["y"] < -30 or pr["y"] > HEIGHT + 30

            if not remove and pr["owner"] == "player":
                for e in self.enemies:
                    if e["hp"] <= 0 or e["id"] in pr["hit_ids"]:
                        continue
                    if math.hypot(pr["x"] - e["x"], pr["y"] - e["y"]) <= pr["radius"] + e["radius"]:
                        marked = e.get("marked_until", 0) > now
                        self.damage_enemy(e, pr["damage"], pr["source_pid"])
                        pr["hit_ids"].append(e["id"])
                        if pr["marked_explosion"] and marked:
                            for other in self.enemies:
                                if other["hp"] > 0 and dist(e, other) < 95:
                                    self.damage_enemy(other, 24, pr["source_pid"])
                        if pr["pierce"] > 0:
                            pr["pierce"] -= 1
                        else:
                            remove = True
                            break

            elif not remove and pr["owner"] == "enemy":
                for p in self.players.values():
                    if p["alive"] and math.hypot(pr["x"] - p["x"], pr["y"] - p["y"]) <= pr["radius"] + 15:
                        self.damage_player(p, pr["damage"])
                        remove = True
                        break

            if not remove:
                kept.append(pr)
        self.projectiles = kept

    def cleanup_and_progress(self):
        dead_enemies = [e for e in self.enemies if e["hp"] <= 0]
        if dead_enemies:
            for e in dead_enemies:
                # Give kill-heal to the nearest alive player as an MVP simplification.
                alive_players = [p for p in self.players.values() if p["alive"]]
                if alive_players:
                    nearest = min(alive_players, key=lambda p: dist(p, e))
                    self.heal_on_kill(nearest["id"])
            self.enemies = [e for e in self.enemies if e["hp"] > 0]

        if self.mode == "playing":
            if self.players and all(not p["alive"] for p in self.players.values()):
                self.mode = "gameover"
                self.message = "전멸했습니다. 새로고침하여 다시 시작하세요."
                return

            if not self.enemies:
                if self.stage >= 5:
                    self.mode = "victory"
                    self.message = "보스 격파! RUN CLEAR"
                else:
                    self.begin_reward()

    async def loop(self):
        try:
            while self.players:
                start = time.monotonic()
                now = start
                if self.mode == "playing":
                    self.update_players(DT, now)
                    if now - self.stage_started_at >= 1.8:
                        self.update_enemies(DT, now)
                        self.update_projectiles(DT, now)
                    self.cleanup_and_progress()
                await self.broadcast()
                elapsed = time.monotonic() - start
                await asyncio.sleep(max(0.001, DT - elapsed))
        finally:
            self.task = None

    def ensure_loop(self):
        if self.task is None or self.task.done():
            self.task = asyncio.create_task(self.loop())

rooms = {}

@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")

@app.get("/health")
async def health():
    return {"ok": True, "rooms": len(rooms)}

@app.websocket("/ws/{room_code}/{character}")
async def websocket_endpoint(ws: WebSocket, room_code: str, character: str):
    if character not in CHARACTERS:
        await ws.close(code=1008)
        return
    await ws.accept()
    room_code = room_code[:20].upper()
    room = rooms.setdefault(room_code, Room(room_code))
    pid = uuid.uuid4().hex[:8]

    # Prefer one of each character. Duplicate characters are allowed for testing.
    room.add_player(pid, character, ws)

    await ws.send_text(json.dumps({
        "type": "welcome",
        "player_id": pid,
        "room": room_code,
        "character": character,
    }, ensure_ascii=False))
    room.ensure_loop()

    try:
        while True:
            raw = await ws.receive_text()
            data = json.loads(raw)
            if data.get("type") == "input":
                p = room.players.get(pid)
                if p:
                    for key in p["input"]:
                        if key in data:
                            p["input"][key] = data[key]
            elif data.get("type") == "reward":
                choice = data.get("choice")
                if room.mode == "reward" and pid not in room.reward_selected:
                    if choice in room.reward_choices.get(pid, []):
                        room.apply_reward(pid, choice)
                        room.reward_selected.add(pid)
                        active = [x for x, p in room.players.items() if p["alive"]]
                        if all(x in room.reward_selected for x in active):
                            room.start_stage(room.stage + 1)
            elif data.get("type") == "restart":
                if room.mode in ("gameover", "victory"):
                    for p in room.players.values():
                        cfg = CHARACTERS[p["character"]]
                        p["max_hp"] = cfg["max_hp"]
                        p["hp"] = cfg["max_hp"]
                        p["unlocked"] = 0
                        p["reward"] = {
                            "damage_mult": 1.0, "cooldown_mult": 1.0,
                            "speed_mult": 1.0, "crit": 0.0, "leech": 0,
                            "boss_mult": 1.0, "damage_taken_mult": 1.0,
                        }
                    room.start_stage(1)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        room.remove_player(pid)
        if not room.players:
            rooms.pop(room_code, None)
