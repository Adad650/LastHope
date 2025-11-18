import math
import os
import random
import sys

import pygame

width, height = 1100, 720
fps = 60
cityFloor = height - 120
maxEnemies = 50
shootAnimDuration = 0.18

darkBackdrop = (26, 26, 34)
midGray = (44, 44, 58)
lightGray = (71, 71, 88)
neonPink = (255, 105, 180)
neonBlue = (119, 233, 255)
coinGold = (254, 213, 82)
heatOrange = (255, 180, 120)

pygame.init()
pygame.font.init()
uiFont = pygame.font.Font(None, 34)
bigFont = pygame.font.Font(None, 70)
smallFont = pygame.font.Font(None, 24)


WEATHER_PATTERNS = {
    "clear": {
        "spawnFactor": 1.0,
        "enemySpeed": 1.0,
        "tint": (0, 0, 0, 0),
        "desc": "city calm"
    },
    "ion rain": {
        "spawnFactor": 1.2,
        "enemySpeed": 0.95,
        "tint": (25, 60, 110, 70),
        "desc": "extra drops, murky vision"
    },
    "ember storm": {
        "spawnFactor": 0.9,
        "enemySpeed": 1.2,
        "tint": (120, 45, 10, 80),
        "desc": "hot winds boost hostiles"
    },
    "glitch fog": {
        "spawnFactor": 1.05,
        "enemySpeed": 0.9,
        "tint": (70, 0, 90, 80),
        "desc": "scrambles enemy sensors"
    },
    "aurora surge": {
        "spawnFactor": 1.1,
        "enemySpeed": 1.05,
        "tint": (20, 90, 80, 60),
        "desc": "energized skies"
    },
}


def createPulseState():
    return {
        "charge": 0.0,
        "max": 100.0,
        "cooldown": 0.0,
        "ready": False,
        "flash": 0.0,
    }


def createWeatherState():
    preset = WEATHER_PATTERNS["clear"].copy()
    preset.setdefault("desc", "")
    return {
        "name": "clear",
        "timer": random.uniform(18, 28),
        "messageTimer": 0.0,
        **preset,
    }


def pickWeatherName(current):
    options = [name for name in WEATHER_PATTERNS.keys() if name != current]
    return random.choice(options) if options else current


def applyWeather(state, name):
    pattern = WEATHER_PATTERNS.get(name, WEATHER_PATTERNS["clear"]).copy()
    weather = state.get("weather")
    if not weather:
        return
    weather.update(pattern)
    weather["name"] = name
    weather["timer"] = random.uniform(16, 30)
    weather["messageTimer"] = 4.0
    logEvent(state, f"weather shift: {name} — {pattern.get('desc', '')}")


def updateWeather(state, dt):
    weather = state.get("weather")
    if not weather:
        return
    weather["timer"] -= dt
    weather["messageTimer"] = max(0.0, weather.get("messageTimer", 0.0) - dt)
    if weather["timer"] <= 0:
        applyWeather(state, pickWeatherName(weather["name"]))


def chargePulse(state, amount):
    pulse = state.get("pulse")
    if not pulse or pulse["ready"] or pulse["cooldown"] > 0:
        return
    pulse["charge"] = min(pulse["max"], pulse["charge"] + amount)
    if pulse["charge"] >= pulse["max"]:
        pulse["ready"] = True
        logEvent(state, "pulse charged — press E")


def activatePulse(state):
    if state.get("menu") or state.get("gameOver") or state.get("shopActive"):
        return
    pulse = state.get("pulse")
    player = state.get("player")
    if not pulse or not player or not pulse.get("ready"):
        return
    radius = 260
    pulseDamage = player["damage"] * 4 + 8
    for enemy in list(state.get("enemies", [])):
        if enemy["pos"].distance_to(player["pos"]) <= radius:
            enemy["hp"] -= pulseDamage
            enemy["speed"] *= 0.85
            enemy["mood"] += 40
    pulse["ready"] = False
    pulse["charge"] = 0.0
    pulse["cooldown"] = 6.0
    pulse["flash"] = 0.4
    logEvent(state, "resonance pulse unleashed")


def updatePulse(state, dt):
    pulse = state.get("pulse")
    if not pulse:
        return
    if pulse["flash"] > 0:
        pulse["flash"] = max(0.0, pulse["flash"] - dt)
    if pulse["cooldown"] > 0:
        pulse["cooldown"] = max(0.0, pulse["cooldown"] - dt)
    if not pulse["ready"] and pulse["cooldown"] == 0:
        chargePulse(state, dt * 10)


def drawWeatherOverlay(screen, weather):
    if not weather:
        return
    tint = weather.get("tint", (0, 0, 0, 0))
    if len(tint) < 4 or tint[3] <= 0:
        return
    overlay = pygame.Surface((width, height), pygame.SRCALPHA)
    overlay.fill(tint)
    screen.blit(overlay, (0, 0))


def drawPulseFlash(screen, state):
    pulse = state.get("pulse")
    player = state.get("player")
    if not pulse or not player or pulse["flash"] <= 0:
        return
    overlay = pygame.Surface((width, height), pygame.SRCALPHA)
    alpha = int(150 * pulse["flash"])
    radius = int(240 + 100 * (1 - pulse["flash"]))
    pygame.draw.circle(
        overlay,
        (120, 255, 255, alpha),
        (int(player["pos"].x), int(player["pos"].y)),
        radius,
        width=6,
    )
    screen.blit(overlay, (0, 0))


def createComboState():
    return {
        "value": 1,
        "timer": 0.0,
        "decay": 6.0,
        "best": 1,
        "flash": 0.0,
    }


def registerComboKill(state):
    combo = state.get("combo")
    if not combo:
        return 1
    combo["value"] = min(6, combo["value"] + 1)
    combo["timer"] = combo["decay"]
    combo["flash"] = 0.35
    if combo["value"] > combo["best"]:
        combo["best"] = combo["value"]
        logEvent(state, f"new combo record ×{combo['value']}")
    return combo["value"]


def resetCombo(state):
    combo = state.get("combo")
    if not combo or combo["value"] <= 1:
        return
    combo["value"] = 1
    combo["timer"] = 0.0
    combo["flash"] = 0.0
    logEvent(state, "combo lost")


def updateCombo(state, dt):
    combo = state.get("combo")
    if not combo:
        return
    if combo["flash"] > 0:
        combo["flash"] = max(0.0, combo["flash"] - dt * 2.5)
    if combo["value"] <= 1:
        combo["timer"] = 0.0
        return
    combo["timer"] -= dt
    if combo["timer"] <= 0:
        combo["value"] -= 1
        combo["timer"] = combo["decay"]
        if combo["value"] == 1:
            logEvent(state, "combo cooled down")


def awardScore(state, base, comboKill=False):
    combo = state.get("combo") if comboKill else None
    multiplier = combo.get("value", 1) if combo else 1
    reward = int(base * multiplier)
    state["score"] += reward
    return reward


def comboKillReward(state, base):
    registerComboKill(state)
    return awardScore(state, base, comboKill=True)


def grantCoins(state, amount):
    if amount <= 0:
        return
    state["coinsBank"] += amount
    telemetry = state.get("telemetry", {})
    telemetry["coinsCollected"] = telemetry.get("coinsCollected", 0) + amount
    milestone = telemetry.get("nextCoinMilestone")
    if milestone and telemetry["coinsCollected"] >= milestone:
        logEvent(state, f"funding milestone: {milestone} credits secured")
        telemetry["nextCoinMilestone"] = milestone + 50
    chargePulse(state, amount * 2)


def formatClock(seconds: float) -> str:
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"


def createTelemetry():
    return {
        "timeAlive": 0.0,
        "shotsFired": 0,
        "shotsHit": 0,
        "damageTaken": 0.0,
        "damageDealt": 0.0,
        "distanceTraveled": 0.0,
        "coinsCollected": 0,
        "wavesCleared": 0,
        "nextCoinMilestone": 50,
        "nextTimeMilestone": 60,
    }


def createContracts():
    return [
        {"name": "fund the safehouse", "type": "coins", "target": 120, "reward": 12, "progress": 0.0, "completed": False},
        {"name": "hold the plaza", "type": "time", "target": 90, "reward": 10, "progress": 0.0, "completed": False},
        {"name": "precision training", "type": "hits", "target": 35, "reward": 14, "progress": 0.0, "completed": False},
        {"name": "sweep the district", "type": "distance", "target": 2500, "reward": 10, "progress": 0.0, "completed": False},
    ]


def logEvent(state, text):
    if "timeline" not in state:
        state["timeline"] = []
    telemetry = state.get("telemetry", {})
    entry = {"time": telemetry.get("timeAlive", 0.0), "text": text}
    state["timeline"].append(entry)
    if len(state["timeline"]) > 20:
        state["timeline"] = state["timeline"][-20:]

def loadBackgroundImage():
    path = os.path.join("assets", "background", "background.png")
    if not os.path.isfile(path):
        return None
    try:
        image = pygame.image.load(path).convert()
        return pygame.transform.scale(image, (width, height))
    except pygame.error:
        return None


def loadAnimationFrames(subfolder, allow_placeholder=True):
    folder_path = os.path.join("assets", subfolder)
    frames = []
    if os.path.isdir(folder_path):
        for filename in sorted(os.listdir(folder_path)):
            if not filename.lower().endswith(".png"):
                continue
            frame = pygame.image.load(os.path.join(folder_path, filename)).convert_alpha()
            frames.append(frame)
    if not frames and allow_placeholder:
        # fallback circle sprite so the game can still run without assets
        placeholder = pygame.Surface((48, 48), pygame.SRCALPHA)
        pygame.draw.circle(placeholder, neonBlue, (24, 24), 22)
        frames.append(placeholder)
    return frames


def createPlayer():
    # Scale factor for the player
    scale_factor = 3
    
    # Load animations first
    idle_frames = loadAnimationFrames("idle")
    run_frames = loadAnimationFrames("run")
    reload_frames = loadAnimationFrames("reload")
    dead_frames = loadAnimationFrames("dead")
    shot_frames = loadAnimationFrames("shot", allow_placeholder=False)
    if not shot_frames:
        shot_frames = loadAnimationFrames("shoot", allow_placeholder=False)
    if not shot_frames:
        shot_frames = loadAnimationFrames("shot")
    
    # Scale each frame in the animations
    def scale_frames(frames):
        scaled = []
        for frame in frames:
            original_size = frame.get_size()
            new_size = (int(original_size[0] * scale_factor), int(original_size[1] * scale_factor))
            scaled_frame = pygame.transform.scale(frame, new_size)
            scaled.append(scaled_frame)
        return scaled
    
    # Calculate hitbox size (slightly smaller than the visual representation)
    base_radius = 16  # Base radius for hitbox (before scaling)
    
    return {
        "pos": pygame.Vector2(width / 2, height / 2),
        "radius": base_radius * scale_factor,  # Scale the hitbox to match player size
        "speed": 360,
        "maxHealth": 130,
        "health": 130,
        "cool": 0.0,  # Cooldown between shots
        "heat": 0.0,  # Heat from sprinting
        "reload": 0.0,  # Reload timer
        "isReloading": False,  # Whether the player is currently reloading
        "ammo": 10,  # Current ammo count
        "maxAmmo": 10,  # Maximum ammo capacity
        "dash": 0.0,
        "damage": 1,
        "coolRate": 0.8,
        "fireDelay": 0.18,
        "animations": {
            "idle": scale_frames(idle_frames) if idle_frames[0].get_size() != (48 * scale_factor, 48 * scale_factor) else idle_frames,
            "run": scale_frames(run_frames) if run_frames and run_frames[0].get_size() != (48 * scale_factor, 48 * scale_factor) else run_frames,
            "reload": scale_frames(reload_frames) if reload_frames and reload_frames[0].get_size() != (48 * scale_factor, 48 * scale_factor) else reload_frames,
            "death": scale_frames(dead_frames) if dead_frames and dead_frames[0].get_size() != (48 * scale_factor, 48 * scale_factor) else dead_frames,
            "shoot": scale_frames(shot_frames) if shot_frames and shot_frames[0].get_size() != (48 * scale_factor, 48 * scale_factor) else shot_frames,
        },
        "animState": "idle",
        "animFrame": 0,
        "animTimer": 0.0,
        "animSpeeds": {"idle": 0.22, "run": 0.08, "reload": 0.12, "shoot": 0.12, "death": 0.28},
        "isMoving": False,
        "facing": 1,
        "shootTimer": 0.0,
        "isDead": False,
        "deathPlayed": False,
    }


def createShot(player, target):
    # Can't shoot while cooling down, reloading, or out of ammo
    if player["cool"] > 0 or player["isReloading"] or player["ammo"] <= 0:
        return None
        
    direction = target - player["pos"]
    if direction.length_squared() == 0:
        direction = pygame.Vector2(1, 0)
    direction = direction.normalize()
    
    # Base speed with slight variation based on movement
    speed = 650 + (player["heat"] * 30 if player["isMoving"] else 0)
    
    shot = {
        "pos": player["pos"].copy(),
        "vel": direction * speed,
        "damage": player["damage"],
        "life": 1.3,
        "radius": 6,
    }
    
    player["cool"] = player["fireDelay"]
    player["ammo"] -= 1
    player["shootTimer"] = shootAnimDuration
    
    # Start reloading if out of ammo
    if player["ammo"] <= 0:
        player["isReloading"] = True
        player["reload"] = 1.5  # 1.5 second reload time
    
    return shot


def createEnemy(wave):
    if random.random() < 0.25:
        edge = "top"
    else:
        edge = random.choice(["bottom", "left", "right"])
    padding = 80
    if edge == "top":
        pos = pygame.Vector2(random.randint(0, width), -padding)
    elif edge == "bottom":
        pos = pygame.Vector2(random.randint(0, width), height + padding)
    elif edge == "left":
        pos = pygame.Vector2(-padding, random.randint(0, height))
    else:
        pos = pygame.Vector2(width + padding, random.randint(0, height))
    return {
        "pos": pos,
        "speed": random.uniform(100, 190) + wave * 7,
        "hp": 2 + wave // 3,
        "size": random.randint(18, 32),
        "mood": 0.0,
    }


def createCoin(position):
    return {
        "pos": position.copy(),
        "vel": pygame.Vector2(random.uniform(-120, 120), random.uniform(-260, -120)),
        "value": random.choice([1, 1, 2]),
        "radius": 10,
    }


def createIntelCache():
    return {
        "pos": pygame.Vector2(random.randint(80, width - 80), random.randint(120, cityFloor - 160)),
        "radius": 18,
        "life": random.uniform(18, 30),
        "phase": random.uniform(0, math.tau),
        "pulse": random.randint(12, 20),
        "coins": random.randint(8, 16),
        "heal": random.randint(8, 18),
        "bob": 0.0,
    }


def buildGameState():
    screen = pygame.display.set_mode((width, height))
    background = loadBackgroundImage()
    pygame.display.set_caption("Last Hope")
    state = {
        "screen": screen,
        "background": background,
        "clock": pygame.time.Clock(),
        "player": createPlayer(),
        "shots": [],
        "enemies": [],
        "coins": [],
        "spawnTimer": 0.5,
        "wave": 1,
        "score": 0,
        "coinsBank": 0,
        "menu": True,
        "gameOver": False,
        "shopActive": False,
        "shopMessage": "",
        "shopTimer": 20,
        "shopCards": [],
        "coinBonus": 1,
        "shopNoteTimer": 0.0,
        "dialog": [
            "dear dystopia journal: still no pizza",
            "i coded this resistance sim so people remember",
            "press SPACE to patrol the lunch plaza",
        ],
        "shopPool": [
            {"name": "heat sink", "desc": "vents faster cool down", "cost": 6, "effect": "heatSink"},
            {"name": "side hustle", "desc": "+1 shot damage", "cost": 8, "effect": "damage"},
            {"name": "restock", "desc": "+35 hp instantly", "cost": 5, "effect": "heal"},
            {"name": "armor plating", "desc": "+15 max hp (and heal)", "cost": 7, "effect": "maxHealth"},
            {"name": "espresso skates", "desc": "+45 move speed", "cost": 6, "effect": "speed"},
            {"name": "trigger tweak", "desc": "faster fire rate", "cost": 7, "effect": "fireRate"},
            {"name": "coin printer", "desc": "coins drop x2 value", "cost": 10, "effect": "coinBonus"},
        ],
        "telemetry": createTelemetry(),
        "timeline": [],
        "timelineVisible": False,
        "contracts": createContracts(),
        "pulse": createPulseState(),
        "weather": createWeatherState(),
        "combo": createComboState(),
        "intelCaches": [],
        "intelTimer": random.uniform(18, 26),
    }
    logEvent(state, "simulation booted in neon dusk")
    logEvent(state, "tab toggles the resistance log")
    logEvent(state, "pulse recharges as you move & loot")
    logEvent(state, "combo kills boost score")
    return state


# drawing helpers

def drawBackground(screen, background, weather=None):
    if background:
        screen.blit(background, (0, 0))
    else:
        screen.fill(darkBackdrop)
        pygame.draw.rect(screen, midGray, pygame.Rect(0, cityFloor, width, height - cityFloor))
        for i in range(7):
            buildingWidth = 90
            gap = 110
            baseX = (i * gap + (i % 2) * 30) % width
            buildingHeight = 120 + (i * 27 % 180)
            pygame.draw.rect(screen, lightGray, pygame.Rect(baseX, cityFloor - buildingHeight, 70, buildingHeight))
            pygame.draw.rect(screen, (90, 90, 120), pygame.Rect(baseX + 15, cityFloor - buildingHeight - 16, 40, 18))
    drawWeatherOverlay(screen, weather)


def drawPlayer(screen, player):
    frames = player["animations"].get(player["animState"], [])
    if frames:
        base_frame = frames[player["animFrame"] % len(frames)]
        sprite = base_frame if player["facing"] >= 0 else pygame.transform.flip(base_frame, True, False)
        rect = sprite.get_rect(center=(int(player["pos"].x), int(player["pos"].y)))
        screen.blit(sprite, rect)
    else:
        pygame.draw.circle(screen, neonBlue, (int(player["pos"].x), int(player["pos"].y)), player["radius"])
    if player["dash"] > 0:
        pygame.draw.circle(
            screen,
            (180, 255, 255),
            (int(player["pos"].x), int(player["pos"].y)),
            player["radius"],
            width=2,
        )


def drawEnemies(screen, enemies):
    for enemy in enemies:
        tint = min(150, int(enemy["mood"] * 20))
        color = (min(255, 120 + tint), 40, 60)
        pygame.draw.circle(screen, color, (int(enemy["pos"].x), int(enemy["pos"].y)), enemy["size"])
        pygame.draw.circle(screen, (0, 0, 0), (int(enemy["pos"].x), int(enemy["pos"].y)), 4)


def drawShots(screen, shots):
    for shot in shots:
        pygame.draw.circle(screen, neonPink, (int(shot["pos"].x), int(shot["pos"].y)), shot["radius"])


def drawCoins(screen, coins):
    for coin in coins:
        pygame.draw.circle(screen, coinGold, (int(coin["pos"].x), int(coin["pos"].y)), coin["radius"])
        pygame.draw.circle(screen, (255, 255, 255), (int(coin["pos"].x), int(coin["pos"].y)), 4)


def drawIntelCaches(screen, caches):
    for cache in caches:
        x = int(cache["pos"].x)
        y = int(cache["pos"].y + cache.get("bob", 0.0))
        outer_radius = cache["radius"] + 8
        glow_surface = pygame.Surface((outer_radius * 2, outer_radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surface, (80, 200, 255, 90), (outer_radius, outer_radius), outer_radius)
        pygame.draw.circle(glow_surface, (120, 255, 255, 160), (outer_radius, outer_radius), cache["radius"])
        screen.blit(glow_surface, (x - outer_radius, y - outer_radius))
        pygame.draw.circle(screen, (255, 255, 255), (x, y), 6)


def drawHud(screen, state):
    player = state["player"]
    
    # Health bar
    pygame.draw.rect(screen, (55, 35, 45), pygame.Rect(30, 30, 340, 26), border_radius=8)
    health_ratio = player["health"] / player["maxHealth"]
    pygame.draw.rect(screen, neonPink, pygame.Rect(30, 30, 340 * health_ratio, 26), border_radius=8)
    screen.blit(uiFont.render(f"HP {int(player['health'])}/{player['maxHealth']}", True, (255, 255, 255)), (40, 32))
    
    # Ammo counter
    ammo_text = f"{player['ammo']}/{player['maxAmmo']}"
    ammo_surface = uiFont.render(ammo_text, True, (255, 255, 255))
    screen.blit(ammo_surface, (40, 65))
    
    # Reload indicator
    if player["isReloading"]:
        reload_progress = 1 - (player["reload"] / 1.5)  # 1.5 second reload time
        reload_width = 100
        pygame.draw.rect(screen, (50, 50, 60), pygame.Rect(120, 70, reload_width, 10), border_radius=5)
        pygame.draw.rect(screen, neonBlue, pygame.Rect(120, 70, int(reload_width * reload_progress), 10), border_radius=5)
    
    # Heat meter
    heat_width = 100
    heat_ratio = player["heat"] / 3.0
    pygame.draw.rect(screen, (50, 40, 45), pygame.Rect(40, 90, heat_width, 8), border_radius=4)
    if heat_ratio > 0:
        heat_color = (
            min(255, 150 + int(heat_ratio * 105)),  # R: 150-255
            max(0, 100 - int(heat_ratio * 100)),    # G: 100-0
            40                                      # B: 40
        )
        pygame.draw.rect(screen, heat_color, pygame.Rect(40, 90, int(heat_width * heat_ratio), 8), border_radius=4)
    
    # Game info
    screen.blit(uiFont.render(f"score {state['score']}", True, (215, 255, 200)), (width - 230, 34))
    screen.blit(uiFont.render(f"coins {state['coinsBank']}", True, coinGold), (width - 230, 66))
    screen.blit(uiFont.render(f"wave {state['wave']}", True, (200, 220, 255)), (width - 230, 98))
    
    # Shop message
    if state["shopMessage"]:
        note = smallFont.render(state["shopMessage"], True, (255, 255, 255))
        screen.blit(note, (width // 2 - note.get_width() // 2, 20))

    # Overheat warning
    if player["heat"] > 2.5:
        warning = smallFont.render("OVERHEAT! SLOWED", True, heatOrange)
        screen.blit(warning, (40, 110))

    telemetry = state.get("telemetry", {})
    accuracy = 0.0
    if telemetry.get("shotsFired"):
        accuracy = (telemetry.get("shotsHit", 0) / telemetry["shotsFired"]) * 100
    statsPanel = pygame.Rect(30, height - 150, 320, 110)
    pygame.draw.rect(screen, (25, 20, 28), statsPanel, border_radius=10)
    pygame.draw.rect(screen, neonBlue, statsPanel, width=2, border_radius=10)
    statLines = [
        f"time {formatClock(telemetry.get('timeAlive', 0.0))}",
        f"accuracy {accuracy:04.1f}%",
        f"distance {int(telemetry.get('distanceTraveled', 0))}m",
        f"coins {telemetry.get('coinsCollected', 0)} | hits {telemetry.get('shotsHit', 0)}",
    ]
    for idx, text in enumerate(statLines):
        label = smallFont.render(text, True, (230, 230, 230))
        screen.blit(label, (statsPanel.x + 16, statsPanel.y + 12 + idx * 24))

    pulse = state.get("pulse")
    if pulse:
        pulseRect = pygame.Rect(width // 2 - 130, height - 70, 260, 22)
        pygame.draw.rect(screen, (20, 25, 36), pulseRect, border_radius=12)
        pygame.draw.rect(screen, (30, 60, 90), pulseRect, width=2, border_radius=12)
        ratio = pulse["charge"] / pulse["max"] if pulse["max"] else 0
        inner = pulseRect.inflate(-6, -6)
        if ratio > 0:
            fill = inner.copy()
            fill.width = int(inner.width * min(1.0, ratio))
            pygame.draw.rect(
                screen,
                (110, 220, 255) if not pulse["ready"] else (150, 255, 190),
                fill,
                border_radius=10,
            )
        text = "PULSE READY [E]" if pulse["ready"] else "charging resonance"
        text_surface = smallFont.render(text, True, (220, 235, 255))
        screen.blit(text_surface, (pulseRect.x + 14, pulseRect.y - 18))
        cooldown_text = "cooldown" if pulse["cooldown"] > 0 else "charge"
        info_text = smallFont.render(cooldown_text, True, (170, 200, 230))
        screen.blit(info_text, (pulseRect.x + pulseRect.width - info_text.get_width() - 10, pulseRect.y + pulseRect.height + 4))

    weather = state.get("weather")
    if weather:
        label = smallFont.render(f"weather: {weather['name']}", True, (190, 220, 255))
        screen.blit(label, (width - label.get_width() - 30, 130))
        if weather.get("messageTimer", 0) > 0:
            desc = smallFont.render(weather.get("desc", ""), True, (170, 200, 255))
            screen.blit(desc, (width - desc.get_width() - 30, 154))

    combo = state.get("combo")
    if combo:
        panel = pygame.Rect(width - 280, height - 150, 230, 90)
        pygame.draw.rect(screen, (24, 18, 28), panel, border_radius=10)
        pygame.draw.rect(screen, (255, 180, 60), panel, width=2, border_radius=10)
        combo_text = smallFont.render(f"combo ×{combo['value']}", True, (255, 220, 160))
        screen.blit(combo_text, (panel.x + 16, panel.y + 12))
        best_text = smallFont.render(f"best ×{combo['best']}", True, (220, 200, 180))
        screen.blit(best_text, (panel.x + 16, panel.y + 34))
        timer_ratio = max(0.0, min(1.0, combo.get("timer", 0.0) / combo.get("decay", 1.0)))
        bar = pygame.Rect(panel.x + 16, panel.y + 60, panel.width - 32, 12)
        pygame.draw.rect(screen, (40, 25, 35), bar, border_radius=6)
        if combo["value"] > 1 and timer_ratio > 0:
            fill = bar.copy()
            fill.width = int(bar.width * timer_ratio)
            pygame.draw.rect(screen, (255, 140, 105), fill, border_radius=6)
        if combo.get("flash", 0) > 0:
            glow = pygame.Surface((panel.width, panel.height), pygame.SRCALPHA)
            glow.fill((255, 200, 150, int(90 * combo["flash"])) )
            screen.blit(glow, panel.topleft)

    drawContracts(screen, state)

    timelineHint = "TAB → hide log" if state.get("timelineVisible") else "TAB → open log"
    hintSurface = smallFont.render(timelineHint, True, (180, 190, 210))
    screen.blit(hintSurface, (width - hintSurface.get_width() - 30, height - 40))


def drawMenu(screen, dialog):
    title = bigFont.render("LAST HOPE", True, neonBlue)
    screen.blit(title, (width // 2 - title.get_width() // 2, 160))
    for idx, line in enumerate(dialog):
        txt = uiFont.render(line, True, (230, 230, 230))
        screen.blit(txt, (width // 2 - txt.get_width() // 2, 260 + 40 * idx))


def drawGameOver(screen, state):
    msg = bigFont.render("system failure", True, heatOrange)
    tip = uiFont.render("press R to reboot the rebellion", True, (255, 255, 255))
    screen.blit(msg, (width // 2 - msg.get_width() // 2, height // 2 - 60))
    screen.blit(tip, (width // 2 - tip.get_width() // 2, height // 2 - 12))
    telemetry = state.get("telemetry", {})
    accuracy = 0.0
    if telemetry.get("shotsFired"):
        accuracy = (telemetry.get("shotsHit", 0) / telemetry["shotsFired"]) * 100
    summary = [
        f"time alive {formatClock(telemetry.get('timeAlive', 0.0))}",
        f"wave cleared {state.get('wave', 1) - 1}",
        f"damage dealt {int(telemetry.get('damageDealt', 0))}",
        f"damage taken {int(telemetry.get('damageTaken', 0))}",
        f"combo best ×{state.get('combo', {}).get('best', 1)}",
        f"accuracy {accuracy:04.1f}%",
    ]
    for idx, text in enumerate(summary):
        label = smallFont.render(text, True, (235, 220, 220))
        screen.blit(label, (width // 2 - label.get_width() // 2, height // 2 + 40 + idx * 24))


def drawShop(screen, state):
    cards = state["shopCards"]
    optionCount = len(cards)
    panelWidth, panelHeight = 520, 70 + optionCount * 60
    px = state["player"]["pos"].x - panelWidth / 2
    px = max(40, min(width - panelWidth - 40, px))
    py = max(80, state["player"]["pos"].y - state["player"]["radius"] - panelHeight - 20)
    panel = pygame.Rect(px, py, panelWidth, panelHeight)
    pygame.draw.rect(screen, (30, 30, 40), panel, border_radius=12)
    pygame.draw.rect(screen, neonBlue, panel, width=3, border_radius=12)
    skipValue = optionCount + 1
    title = uiFont.render(f"pop-up shop: pick (1-{optionCount}) or skip ({skipValue})", True, (255, 255, 255))
    screen.blit(title, (panel.x + 18, panel.y + 18))
    for idx, card in enumerate(cards):
        affordable = state["coinsBank"] >= card["cost"]
        label = uiFont.render(
            f"{idx + 1}) {card['name']} [{card['cost']}c]",
            True,
            (200, 255, 220) if affordable else (130, 130, 130),
        )
        screen.blit(label, (panel.x + 24, panel.y + 60 + idx * 60))
        detail = smallFont.render(card["desc"], True, (180, 180, 200))
        screen.blit(detail, (panel.x + 32, panel.y + 90 + idx * 60))
    skipText = uiFont.render(f"{skipValue}) close shop", True, (255, 255, 255))
    screen.blit(skipText, (panel.x + 24, panel.y + panelHeight - 40))


def drawContracts(screen, state):
    contracts = state.get("contracts", [])
    if not contracts:
        return
    visible = contracts[:3]
    panelHeight = 50 + len(visible) * 52
    panel = pygame.Rect(width - 300, 150, 250, panelHeight)
    pygame.draw.rect(screen, (18, 18, 26), panel, border_radius=12)
    pygame.draw.rect(screen, (80, 100, 150), panel, width=2, border_radius=12)
    header = smallFont.render("contracts", True, (210, 210, 255))
    screen.blit(header, (panel.x + 16, panel.y + 12))
    for idx, contract in enumerate(visible):
        y = panel.y + 40 + idx * 52
        nameColor = (110, 255, 170) if contract.get("completed") else (220, 220, 230)
        label = smallFont.render(contract["name"], True, nameColor)
        screen.blit(label, (panel.x + 16, y))
        target = contract.get("target", 1) or 1
        progress = contract.get("progress", 0.0)
        ratio = min(1.0, progress / target)
        bar = pygame.Rect(panel.x + 16, y + 18, panel.width - 32, 12)
        pygame.draw.rect(screen, (30, 30, 42), bar, border_radius=6)
        fill = bar.copy()
        fill.width = int(bar.width * ratio)
        pygame.draw.rect(screen, (110, 200, 255) if not contract.get("completed") else (110, 255, 170), fill, border_radius=6)
        detailText = f"{int(min(progress, target))}/{target}  +{contract.get('reward', 0)}c"
        detail = smallFont.render(detailText, True, (160, 180, 200))
        screen.blit(detail, (panel.x + 16, y + 34))


def drawTimeline(screen, state):
    if not state.get("timelineVisible"):
        return
    entries = state.get("timeline", [])
    overlay = pygame.Surface((width - 120, 200), pygame.SRCALPHA)
    overlay.fill((10, 10, 18, 220))
    pygame.draw.rect(overlay, (60, 110, 150), overlay.get_rect(), width=2, border_radius=14)
    lines = list(reversed(entries[-7:]))
    for idx, entry in enumerate(lines):
        timestamp = formatClock(entry.get("time", 0.0))
        text = entry.get("text", "")
        caption = smallFont.render(f"{timestamp} — {text}", True, (220, 220, 230))
        overlay.blit(caption, (28, 20 + idx * 24))
    footer = smallFont.render("log open — press TAB to close", True, (150, 190, 230))
    overlay.blit(footer, (overlay.get_width() - footer.get_width() - 24, overlay.get_height() - 32))
    screen.blit(overlay, (60, height - 230))


# logic

def movePlayer(player, dt, keys):
    direction = pygame.Vector2(0, 0)
    
    # Handle movement input
    if keys[pygame.K_w] or keys[pygame.K_UP]:
        direction.y -= 1
    if keys[pygame.K_s] or keys[pygame.K_DOWN]:
        direction.y += 1
    if keys[pygame.K_a] or keys[pygame.K_LEFT]:
        direction.x -= 1
    if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
        direction.x += 1
    
    # Handle sprinting (left shift)
    isSprinting = (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]) and direction.length_squared() > 0
    
    if direction.length_squared() > 0:
        direction = direction.normalize()
        player["isMoving"] = True
        if abs(direction.x) > 0.05:
            player["facing"] = 1 if direction.x > 0 else -1
            
        # Apply sprinting effects
        if isSprinting:
            player["heat"] = min(3.0, player["heat"] + dt * 2)  # Build up heat when sprinting
        else:
            player["heat"] = max(0, player["heat"] - dt * player["coolRate"])  # Cool down when not sprinting
    else:
        player["isMoving"] = False
        player["heat"] = max(0, player["heat"] - dt * player["coolRate"])  # Cool down when not moving
    
    # Apply movement speed (reduced when overheated)
    speed_multiplier = 1.0
    if player["heat"] > 2.5:  # Overheat penalty
        speed_multiplier = 0.6
    elif isSprinting:
        speed_multiplier = 1.5  # Sprint speed boost
    
    dash_speed = 1.65 if player["dash"] > 0 else 1.0
    move_speed = player["speed"] * speed_multiplier * dash_speed * dt
    
    if direction.length_squared() > 0:
        player["pos"] += direction * move_speed
    
    # Keep player in bounds
    player["pos"].x = max(player["radius"], min(width - player["radius"], player["pos"].x))
    player["pos"].y = max(player["radius"], min(cityFloor - player["radius"], player["pos"].y))
    
    # Update cooldowns
    player["cool"] = max(0, player["cool"] - dt)
    player["dash"] = max(0, player["dash"] - dt)
    
    # Handle reloading
    if player["isReloading"]:
        player["reload"] -= dt
        if player["reload"] <= 0:
            player["isReloading"] = False
            player["ammo"] = player["maxAmmo"]


def dashPlayer(player):
    if player["heat"] > 2.7 or player["dash"] > 0:
        return
    player["dash"] = 0.3
    player["heat"] += 0.5


def updateShot(shot, dt):
    shot["pos"] += shot["vel"] * dt
    shot["life"] -= dt
    return shot["life"] > 0 and -60 < shot["pos"].x < width + 60 and -60 < shot["pos"].y < height + 60


def updateEnemy(enemy, dt, playerPos):
    direction = playerPos - enemy["pos"]
    if direction.length_squared() == 0:
        direction = pygame.Vector2(1, 0)
    enemy["pos"] += direction.normalize() * enemy["speed"] * dt
    enemy["mood"] += dt * 3


def updateCoin(coin, dt):
    coin["vel"].y += 250 * dt
    coin["pos"] += coin["vel"] * dt
    if coin["pos"].y > cityFloor - coin["radius"]:
        coin["pos"].y = cityFloor - coin["radius"]
        coin["vel"].y *= -0.25
        coin["vel"].x *= 0.75


def updatePlayerAnimation(player, dt):
    # Update the shooting timer if active
    if player["shootTimer"] > 0:
        player["shootTimer"] = max(0, player["shootTimer"] - dt)

    # Determine the desired animation state
    if player["isDead"] and player["animations"].get("death"):
        player["shootTimer"] = 0
        desired_state = "death"
    elif player["isReloading"]:
        player["shootTimer"] = 0
        desired_state = "reload"
    elif player["shootTimer"] > 0 and player["animations"].get("shoot"):
        desired_state = "shoot"
    elif player["isMoving"]:
        desired_state = "run"
    else:
        desired_state = "idle"
        
    # Fallback to idle if the desired state doesn't exist
    if desired_state not in player["animations"] or not player["animations"][desired_state]:
        desired_state = "idle"
    if player["animState"] != desired_state:
        player["animState"] = desired_state
        player["animFrame"] = 0
        player["animTimer"] = 0.0
        if desired_state == "death":
            player["deathPlayed"] = False
    frames = player["animations"].get(player["animState"], [])
    if not frames:
        return
    frame_duration = player["animSpeeds"].get(player["animState"], 0.12)
    player["animTimer"] += dt
    if player["animState"] == "death":
        if player["deathPlayed"]:
            player["animFrame"] = len(frames) - 1
            return
        # advance towards last frame without looping
        while player["animTimer"] >= frame_duration and player["animFrame"] < len(frames) - 1:
            player["animTimer"] -= frame_duration
            player["animFrame"] += 1
        if player["animFrame"] >= len(frames) - 1:
            player["deathPlayed"] = True
        return
    while player["animTimer"] >= frame_duration:
        player["animTimer"] -= frame_duration
        player["animFrame"] = (player["animFrame"] + 1) % len(frames)


def spawnEnemy(state):
    if len(state["enemies"]) >= maxEnemies:
        return
    enemy = createEnemy(state["wave"])
    weather = state.get("weather")
    if weather:
        enemy["speed"] *= weather.get("enemySpeed", 1.0)
    state["enemies"].append(enemy)


def dropCoins(state, position):
    for _ in range(random.randint(1, 3)):
        state["coins"].append(createCoin(position))


def updateWaves(state, dt):
    state["spawnTimer"] -= dt
    if state["spawnTimer"] <= 0:
        spawnEnemy(state)
        weather = state.get("weather")
        spawnFactor = weather.get("spawnFactor", 1.0) if weather else 1.0
        state["spawnTimer"] = max(0.45, (1.4 - state["wave"] * 0.08) / max(0.4, spawnFactor))
    if state["score"] > state["wave"] * 220:
        state["wave"] += 1
        player = state["player"]
        player["health"] = min(player["maxHealth"], player["health"] + 20)
        telemetry = state.get("telemetry", {})
        telemetry["wavesCleared"] = state["wave"] - 1
        logEvent(state, f"wave {state['wave']} intensifies")
    state["shopTimer"] -= dt
    if state["shopTimer"] <= 0 and not state["shopActive"]:
        openShop(state)
    updateWeather(state, dt)


def updateCoins(state, dt):
    player = state["player"]
    for coin in list(state["coins"]):
        updateCoin(coin, dt)
        if coin["pos"].distance_to(player["pos"]) < coin["radius"] + player["radius"]:
            value = coin["value"] * state["coinBonus"]
            grantCoins(state, value)
            state["coins"].remove(coin)
            continue
        if coin["pos"].y >= cityFloor - coin["radius"] and abs(coin["vel"].y) < 5:
            coin["vel"].y = 0


def collectIntelCache(state, cache):
    player = state["player"]
    grantCoins(state, cache.get("coins", 0))
    player["health"] = min(player["maxHealth"], player["health"] + cache.get("heal", 0))
    player["ammo"] = min(player["maxAmmo"], player["ammo"] + 2)
    chargePulse(state, cache.get("pulse", 0))
    logEvent(state, "intel cache cracked — supplies restocked")


def updateIntelCaches(state, dt):
    state["intelTimer"] -= dt
    if state["intelTimer"] <= 0:
        state.setdefault("intelCaches", []).append(createIntelCache())
        state["intelTimer"] = random.uniform(18, 30)
        logEvent(state, "intel cache pinged nearby")
    player = state["player"]
    for cache in list(state.get("intelCaches", [])):
        cache["life"] -= dt
        cache["phase"] += dt * 2.5
        cache["bob"] = math.sin(cache["phase"]) * 8
        if cache["life"] <= 0:
            state["intelCaches"].remove(cache)
            continue
        pos = cache["pos"].copy()
        pos.y += cache.get("bob", 0)
        if pos.distance_to(player["pos"]) < cache["radius"] + player["radius"]:
            state["intelCaches"].remove(cache)
            collectIntelCache(state, cache)
def updateShopNote(state, dt):
    if state["shopNoteTimer"] > 0:
        state["shopNoteTimer"] = max(0, state["shopNoteTimer"] - dt)
        if state["shopNoteTimer"] == 0 and not state["shopActive"]:
            state["shopMessage"] = ""


def updateContracts(state):
    telemetry = state.get("telemetry", {})
    for contract in state.get("contracts", []):
        if contract.get("completed"):
            continue
        ctype = contract.get("type")
        if ctype == "coins":
            contract["progress"] = telemetry.get("coinsCollected", 0)
        elif ctype == "time":
            contract["progress"] = telemetry.get("timeAlive", 0.0)
        elif ctype == "hits":
            contract["progress"] = telemetry.get("shotsHit", 0)
        elif ctype == "distance":
            contract["progress"] = telemetry.get("distanceTraveled", 0.0)
        elif ctype == "waves":
            contract["progress"] = telemetry.get("wavesCleared", 0)
        target = contract.get("target", 1)
        if contract["progress"] >= target:
            contract["completed"] = True
            reward = contract.get("reward", 0)
            state["coinsBank"] += reward
            state["shopMessage"] = f"contract cleared: {contract['name']}"
            state["shopNoteTimer"] = 2.0
            logEvent(state, f"contract complete → {contract['name']} (+{reward}c)")


def handleCollisions(state, dt):
    player = state["player"]
    telemetry = state.get("telemetry", {})
    for enemy in list(state["enemies"]):
        for shot in list(state["shots"]):
            if enemy["pos"].distance_to(shot["pos"]) < enemy["size"] + shot["radius"]:
                enemy["hp"] -= shot["damage"]
                state["shots"].remove(shot)
                state["score"] += 6
                telemetry["shotsHit"] = telemetry.get("shotsHit", 0) + 1
                telemetry["damageDealt"] = telemetry.get("damageDealt", 0.0) + shot["damage"]
        if enemy["hp"] <= 0:
            state["enemies"].remove(enemy)
            comboKillReward(state, 30)
            dropCoins(state, enemy["pos"])
            chargePulse(state, 6)
            continue
        if enemy["pos"].distance_to(player["pos"]) < enemy["size"] + player["radius"]:
            damage = 35 * dt
            player["health"] -= damage
            telemetry["damageTaken"] = telemetry.get("damageTaken", 0.0) + damage
            player["heat"] += 0.1 * dt * fps
            resetCombo(state)
    if player["health"] <= 0 and not state["gameOver"]:
        player["isDead"] = True
        player["shootTimer"] = 0
        state["gameOver"] = True
        state["shopActive"] = False
        logEvent(state, "runner down — systems failing")


def updateGame(state, dt):
    keys = pygame.key.get_pressed()
    player = state["player"]
    telemetry = state.get("telemetry", {})
    telemetry["timeAlive"] = telemetry.get("timeAlive", 0.0) + dt
    if telemetry.get("timeAlive", 0.0) >= telemetry.get("nextTimeMilestone", float("inf")):
        logEvent(state, f"survived {int(telemetry['timeAlive'])}s out here")
        telemetry["nextTimeMilestone"] = telemetry.get("nextTimeMilestone", 0) + 60

    updatePulse(state, dt)
    updateCombo(state, dt)

    # Handle movement
    previousPos = player["pos"].copy()
    movePlayer(player, dt, keys)
    telemetry["distanceTraveled"] = telemetry.get("distanceTraveled", 0.0) + player["pos"].distance_to(previousPos)

    # Handle shooting
    mousePos = pygame.Vector2(pygame.mouse.get_pos())
    if (pygame.mouse.get_pressed()[0] or keys[pygame.K_SPACE]) and not player["isReloading"]:
        shot = createShot(player, mousePos)
        if shot:
            state["shots"].append(shot)
            telemetry["shotsFired"] = telemetry.get("shotsFired", 0) + 1

    # Reload with R key
    if keys[pygame.K_r] and not player["isReloading"] and player["ammo"] < player["maxAmmo"]:
        player["isReloading"] = True
        player["reload"] = 1.5  # 1.5 second reload time

    # Update game objects
    state["shots"] = [s for s in state["shots"] if updateShot(s, dt)]
    for enemy in state["enemies"]:
        updateEnemy(enemy, dt, player["pos"])
    updateCoins(state, dt)
    updateIntelCaches(state, dt)
    updateWaves(state, dt)
    handleCollisions(state, dt)
    updateContracts(state)
    updateShopNote(state, dt)

    # Handle shop interactions
    if state["shopActive"]:
        if keys[pygame.K_1]:
            buyOption(state, 0)
        elif keys[pygame.K_2]:
            buyOption(state, 1)
        elif keys[pygame.K_3]:
            buyOption(state, 2)
        elif keys[pygame.K_4]:
            closeShop(state)


def openShop(state):
    state["shopActive"] = True
    state["shopMessage"] = "shop paused reality"
    state["shopNoteTimer"] = 0.0
    picks = random.sample(state["shopPool"], k=min(5, len(state["shopPool"])) )
    state["shopCards"] = picks
    logEvent(state, "shop manifests between frames")


def closeShop(state):
    state["shopActive"] = False
    state["shopMessage"] = ""
    state["shopTimer"] = random.uniform(18, 28)
    state["shopNoteTimer"] = 0.0
    logEvent(state, "shop blinks out")


def buyOption(state, index):
    if index >= len(state["shopCards"]):
        closeShop(state)
        return
    card = state["shopCards"][index]
    if state["coinsBank"] < card["cost"]:
        state["shopMessage"] = "not enough coin juice"
        state["shopNoteTimer"] = 1.6
        return
    state["coinsBank"] -= card["cost"]
    applyUpgrade(state, card["effect"])
    closeShop(state)
    state["shopMessage"] = f"bought {card['name']}"
    state["shopNoteTimer"] = 2.5
    logEvent(state, f"purchased {card['name']}")


def applyUpgrade(state, effect):
    player = state["player"]
    if effect == "heatSink":
        player["coolRate"] += 0.25
    elif effect == "damage":
        player["damage"] += 1
    elif effect == "heal":
        player["health"] = min(player["maxHealth"], player["health"] + 35)
    elif effect == "maxHealth":
        player["maxHealth"] += 15
        player["health"] = min(player["maxHealth"], player["health"] + 15)
    elif effect == "speed":
        player["speed"] += 45
    elif effect == "fireRate":
        player["fireDelay"] = max(0.08, player["fireDelay"] - 0.02)
    elif effect == "coinBonus":
        state["coinBonus"] += 1


# main

def runGame():
    state = buildGameState()
    while True:
        dt = state["clock"].tick(fps) / 1000
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                if event.key == pygame.K_r:
                    state = buildGameState()
                if event.key == pygame.K_SPACE and state["menu"]:
                    state["menu"] = False
                if event.key == pygame.K_TAB:
                    state["timelineVisible"] = not state["timelineVisible"]
                    if state["timelineVisible"]:
                        logEvent(state, "opened mission log")
                if event.key == pygame.K_e:
                    activatePulse(state)
                if state["shopActive"]:
                    digit = event.unicode if event.unicode else ""
                    if digit.isdigit():
                        choice = int(digit)
                        if 1 <= choice <= len(state["shopCards"]):
                            buyOption(state, choice - 1)
                            continue
                        if choice == len(state["shopCards"]) + 1:
                            closeShop(state)
                            continue
                    if event.key in (pygame.K_RETURN, pygame.K_ESCAPE, pygame.K_KP_ENTER):
                        closeShop(state)
        if not state["menu"] and not state["gameOver"] and not state["shopActive"]:
            updateGame(state, dt)
        updatePlayerAnimation(state["player"], dt)
        drawBackground(state["screen"], state.get("background"), state.get("weather"))
        drawCoins(state["screen"], state["coins"])
        drawIntelCaches(state["screen"], state.get("intelCaches", []))
        drawEnemies(state["screen"], state["enemies"])
        drawShots(state["screen"], state["shots"])
        drawPlayer(state["screen"], state["player"])
        drawHud(state["screen"], state)
        drawPulseFlash(state["screen"], state)
        if state["menu"]:
            drawMenu(state["screen"], state["dialog"])
        if state["shopActive"]:
            drawShop(state["screen"], state)
        if state["gameOver"]:
            drawGameOver(state["screen"], state)
        drawTimeline(state["screen"], state)
        pygame.display.flip()


def main():
    runGame()


if __name__ == "__main__":
    main()
