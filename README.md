
# NEON LUNCH DUTY ++

An arcade survival prototype built with `pygame`. Pilot a neon courier as endless enemy waves crash through the lunch plaza, trade coins for pop-up upgrades, and push your luck with a heat-based blaster system. The project lives in this repo as a focused prototype (`main.py`) plus a couple of helper scripts.

## Requirements
- Python 3.10+ (any modern CPython works)
- `pygame` 2.5+
- (optional) `pyautogui` and `keyboard` if you want to experiment with `typing_effect.py`

## Getting Started
1. Create a virtual environment (recommended):
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install pygame pyautogui keyboard
   ```
   Only `pygame` is required to play; the other two packages are for the auto-typing helper script.
3. Launch the prototype:
   ```bash
   python main.py
   ```

## Controls
- `WASD` *or* arrow keys – movement
- `Mouse` to aim, `Left Mouse` or `Space` to fire / start the run
- `Shift` – dash burst (costs heat)
- Number keys (`1-n`) – buy the highlighted shop card, `n+1` skips the shop
- `ENTER` or `ESC` – close the shop without purchasing
- `R` – reboot after destruction
- `ESC` – quit the game at any time

## Gameplay Loop
- **Heat management**: every shot adds heat; max heat locks the weapon until it cools. Dashes also spike the gauge.
- **Wave scaling**: enemy stats ramp automatically as your score climbs. Cleared thresholds heal the pilot slightly.
- **Coins & shop**: fallen enemies drop coins. Temporary shops pause time and let you buy upgrades listed below.
- **Endless push**: there is no level break—survive as long as possible for a bigger score.

### Shop Cards
| Upgrade | Effect |
| --- | --- |
| heat sink | Faster passive cooling |
| side hustle | +1 shot damage |
| restock | Instant +35 HP |
| armor plating | +15 max HP and heal |
| espresso skates | +45 movement speed |
| trigger tweak | Faster fire rate |
| coin printer | Doubled coin value |

## Repository Layout
- `main.py` – the primary NEON LUNCH DUTY ++ gameplay loop.
- `typing_effect.py` – a PyAutoGUI/keyboard helper that can auto-type scripts or flavor text for demos. Requires desktop control permissions; use with caution.
- `test.py` – an experimental scratchpad mirroring earlier gameplay logic.
- `index.html` – placeholder for a future web landing page.

## Typing Effect Helper
`typing_effect.py` loads a script, types it into any focused window with a synthetic “hacker” cadence, and supports keyboard interrupts. Start it with:
```bash
python typing_effect.py
```
Make sure PyAutoGUI and keyboard have the necessary OS permissions before running, and keep your cursor in a safe text editor when the script is active.

## Roadmap Ideas
- Add SFX/music hooks and polished HUD art.
- Expand the shop pool with defensive or area-control cards.
- Persist high scores to a local file.
- Port the prototype loop to a web build if `pygame-ce` or a WASM wrapper becomes viable.

Have fun defending the plaza, and feel free to fork the prototype for your own neon experiments.
