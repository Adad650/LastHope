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


def buildGameState():
    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption("Last Hope")
    state = {
        "screen": screen,
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
    }
    return state


# drawing helpers

def drawBackground(screen):
    screen.fill(darkBackdrop)
    pygame.draw.rect(screen, midGray, pygame.Rect(0, cityFloor, width, height - cityFloor))
    for i in range(7):
        buildingWidth = 90
        gap = 110
        baseX = (i * gap + (i % 2) * 30) % width
        buildingHeight = 120 + (i * 27 % 180)
        pygame.draw.rect(screen, lightGray, pygame.Rect(baseX, cityFloor - buildingHeight, 70, buildingHeight))
        pygame.draw.rect(screen, (90, 90, 120), pygame.Rect(baseX + 15, cityFloor - buildingHeight - 16, 40, 18))


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


def drawMenu(screen, dialog):
    title = bigFont.render("LAST HOPE", True, neonBlue)
    screen.blit(title, (width // 2 - title.get_width() // 2, 160))
    for idx, line in enumerate(dialog):
        txt = uiFont.render(line, True, (230, 230, 230))
        screen.blit(txt, (width // 2 - txt.get_width() // 2, 260 + 40 * idx))


def drawGameOver(screen):
    msg = bigFont.render("system failure", True, heatOrange)
    tip = uiFont.render("press R to reboot the rebellion", True, (255, 255, 255))
    screen.blit(msg, (width // 2 - msg.get_width() // 2, height // 2 - 40))
    screen.blit(tip, (width // 2 - tip.get_width() // 2, height // 2 + 10))


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
    state["enemies"].append(createEnemy(state["wave"]))


def dropCoins(state, position):
    for _ in range(random.randint(1, 3)):
        state["coins"].append(createCoin(position))


def updateWaves(state, dt):
    state["spawnTimer"] -= dt
    if state["spawnTimer"] <= 0:
        spawnEnemy(state)
        state["spawnTimer"] = max(0.45, 1.4 - state["wave"] * 0.08)
    if state["score"] > state["wave"] * 220:
        state["wave"] += 1
        player = state["player"]
        player["health"] = min(player["maxHealth"], player["health"] + 20)
    state["shopTimer"] -= dt
    if state["shopTimer"] <= 0 and not state["shopActive"]:
        openShop(state)


def updateCoins(state, dt):
    player = state["player"]
    for coin in list(state["coins"]):
        updateCoin(coin, dt)
        if coin["pos"].distance_to(player["pos"]) < coin["radius"] + player["radius"]:
            state["coinsBank"] += coin["value"] * state["coinBonus"]
            state["coins"].remove(coin)
            continue
        if coin["pos"].y >= cityFloor - coin["radius"] and abs(coin["vel"].y) < 5:
            coin["vel"].y = 0


def updateShopNote(state, dt):
    if state["shopNoteTimer"] > 0:
        state["shopNoteTimer"] = max(0, state["shopNoteTimer"] - dt)
        if state["shopNoteTimer"] == 0 and not state["shopActive"]:
            state["shopMessage"] = ""


def handleCollisions(state, dt):
    player = state["player"]
    for enemy in list(state["enemies"]):
        for shot in list(state["shots"]):
            if enemy["pos"].distance_to(shot["pos"]) < enemy["size"] + shot["radius"]:
                enemy["hp"] -= shot["damage"]
                state["shots"].remove(shot)
                state["score"] += 6
        if enemy["hp"] <= 0:
            state["enemies"].remove(enemy)
            state["score"] += 30
            dropCoins(state, enemy["pos"])
            continue
        if enemy["pos"].distance_to(player["pos"]) < enemy["size"] + player["radius"]:
            player["health"] -= 35 * dt
            player["heat"] += 0.1 * dt * fps
    if player["health"] <= 0 and not state["gameOver"]:
        player["isDead"] = True
        player["shootTimer"] = 0
        state["gameOver"] = True
        state["shopActive"] = False


def updateGame(state, dt):
    keys = pygame.key.get_pressed()
    player = state["player"]
    
    # Handle movement
    movePlayer(player, dt, keys)
    
    # Handle shooting
    mousePos = pygame.Vector2(pygame.mouse.get_pos())
    if (pygame.mouse.get_pressed()[0] or keys[pygame.K_SPACE]) and not player["isReloading"]:
        shot = createShot(player, mousePos)
        if shot:
            state["shots"].append(shot)
    
    # Reload with R key
    if keys[pygame.K_r] and not player["isReloading"] and player["ammo"] < player["maxAmmo"]:
        player["isReloading"] = True
        player["reload"] = 1.5  # 1.5 second reload time
    
    # Update game objects
    state["shots"] = [s for s in state["shots"] if updateShot(s, dt)]
    for enemy in state["enemies"]:
        updateEnemy(enemy, dt, player["pos"])
    updateCoins(state, dt)
    updateWaves(state, dt)
    handleCollisions(state, dt)
    
    # Handle shop interactions
    if state["shopActive"]:
        updateShopNote(state, dt)
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


def closeShop(state):
    state["shopActive"] = False
    state["shopMessage"] = ""
    state["shopTimer"] = random.uniform(18, 28)
    state["shopNoteTimer"] = 0.0


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
        drawBackground(state["screen"])
        drawCoins(state["screen"], state["coins"])
        drawEnemies(state["screen"], state["enemies"])
        drawShots(state["screen"], state["shots"])
        drawPlayer(state["screen"], state["player"])
        drawHud(state["screen"], state)
        if state["menu"]:
            drawMenu(state["screen"], state["dialog"])
        if state["shopActive"]:
            drawShop(state["screen"], state)
        if state["gameOver"]:
            drawGameOver(state["screen"])
        pygame.display.flip()


def main():
    runGame()


if __name__ == "__main__":
    main()
