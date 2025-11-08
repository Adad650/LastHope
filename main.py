import random
import sys

import pygame

width, height = 1100, 720
fps = 60
cityFloor = height - 120
maxEnemies = 50

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


def createPlayer():
    return {
        "pos": pygame.Vector2(width / 2, height / 2),
        "radius": 24,
        "speed": 360,
        "maxHealth": 130,
        "health": 130,
        "cool": 0.0,
        "heat": 0.0,
        "dash": 0.0,
        "damage": 1,
        "coolRate": 0.8,
        "fireDelay": 0.18,
    }


def createShot(player, target):
    if player["cool"] > 0 or player["heat"] >= 3:
        return None
    direction = target - player["pos"]
    if direction.length_squared() == 0:
        direction = pygame.Vector2(1, 0)
    direction = direction.normalize()
    speed = 650 + player["heat"] * 40
    shot = {
        "pos": player["pos"].copy(),
        "vel": direction * speed,
        "damage": player["damage"],
        "life": 1.3,
        "radius": 6,
    }
    player["cool"] = player["fireDelay"]
    player["heat"] += 0.32
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
    pygame.display.set_caption("NEON LUNCH DUTY ++")
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


# --------------------------- drawing helpers ------------------------------

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
    color = neonBlue if player["dash"] <= 0 else (180, 255, 255)
    pygame.draw.circle(screen, color, (int(player["pos"].x), int(player["pos"].y)), player["radius"])
    pygame.draw.circle(
        screen,
        neonPink,
        (int(player["pos"].x), int(player["pos"].y - player["radius"] + 4)),
        6,
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
    pygame.draw.rect(screen, (55, 35, 45), pygame.Rect(30, 30, 340, 26), border_radius=8)
    ratio = player["health"] / player["maxHealth"]
    pygame.draw.rect(screen, neonPink, pygame.Rect(30, 30, 340 * ratio, 26), border_radius=8)
    screen.blit(uiFont.render(f"HP {int(player['health'])}/{player['maxHealth']}", True, (255, 255, 255)), (40, 32))
    screen.blit(uiFont.render(f"score {state['score']}", True, (215, 255, 200)), (width - 230, 34))
    screen.blit(uiFont.render(f"coins {state['coinsBank']}", True, coinGold), (width - 230, 66))
    screen.blit(uiFont.render(f"wave {state['wave']}", True, (200, 220, 255)), (width - 230, 98))
    screen.blit(smallFont.render(f"heat {player['heat']:.1f}/3", True, heatOrange), (40, 60))
    if state["shopMessage"]:
        note = smallFont.render(state["shopMessage"], True, (255, 255, 255))
        screen.blit(note, (width // 2 - note.get_width() // 2, 20))


def drawMenu(screen, dialog):
    title = bigFont.render("NEON LUNCH DUTY", True, neonBlue)
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


# --------------------------- gameplay logic -------------------------------

def movePlayer(player, dt, keys):
    direction = pygame.Vector2(0, 0)
    if keys[pygame.K_w]:
        direction.y -= 1
    if keys[pygame.K_s]:
        direction.y += 1
    if keys[pygame.K_a]:
        direction.x -= 1
    if keys[pygame.K_d]:
        direction.x += 1
    if keys[pygame.K_UP]:
        direction.y -= 1
    if keys[pygame.K_DOWN]:
        direction.y += 1
    if keys[pygame.K_LEFT]:
        direction.x -= 1
    if keys[pygame.K_RIGHT]:
        direction.x += 1
    if direction.length_squared() > 0:
        direction = direction.normalize()
    dashSpeed = 1.65 if player["dash"] > 0 else 1
    player["pos"] += direction * player["speed"] * dashSpeed * dt
    player["pos"].x = max(player["radius"], min(width - player["radius"], player["pos"].x))
    player["pos"].y = max(player["radius"], min(cityFloor - player["radius"], player["pos"].y))
    player["cool"] = max(0, player["cool"] - dt)
    player["heat"] = max(0, player["heat"] - dt * player["coolRate"])
    player["dash"] = max(0, player["dash"] - dt)


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
        state["gameOver"] = True
        state["shopActive"] = False


def updateGame(state, dt):
    keys = pygame.key.get_pressed()
    movePlayer(state["player"], dt, keys)
    if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]:
        dashPlayer(state["player"])
    mousePos = pygame.Vector2(pygame.mouse.get_pos())
    if pygame.mouse.get_pressed()[0] or keys[pygame.K_SPACE]:
        shot = createShot(state["player"], mousePos)
        if shot:
            state["shots"].append(shot)
    state["shots"] = [shot for shot in state["shots"] if updateShot(shot, dt)]
    for enemy in state["enemies"]:
        updateEnemy(enemy, dt, state["player"]["pos"])
    handleCollisions(state, dt)
    updateCoins(state, dt)
    updateWaves(state, dt)
    updateShopNote(state, dt)


# --------------------------- shop & upgrades ------------------------------

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


# --------------------------- main loop ------------------------------------

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
