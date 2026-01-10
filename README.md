# LED Runner

An endless runner game on a WS2812B LED strip, controlled with game controllers on a Raspberry Pi.

## How it works

Colored obstacles move across the LED strip towards the player (white LED in the center). Press the matching color button on your controller to dodge each obstacle. Miss one and it's game over.

## Features

- 1-4 player co-op (auto-detected based on connected controllers)
- Progressive difficulty (speed increases, more colors unlock)
- START button to pause, resume, and restart
- Score display on LED strip after game over

## Controls

| Players | Distribution |
|---------|--------------|
| 1 | All colors |
| 2 | P1: Yellow + Green, P2: Red + Blue |
| 3 | P1: Yellow, P2: Red, P3: Green + Blue |
| 4 | P1: Yellow, P2: Red, P3: Green, P4: Blue |

## Hardware

- Raspberry Pi
- WS2812B LED strip (default: 60 LEDs)
- 1-4 USB game controllers
- 5V power supply (2A+ recommended)

## Setup

```bash
./setup.sh
```

This installs dependencies, creates a virtual environment, and sets up a systemd service.

## Configuration

Edit `config.json` to change LED count, GPIO pin, brightness, and button mapping.

## Usage

```bash
# Start manually
./start.sh

# Or use the service
sudo systemctl start led-runner
sudo systemctl stop led-runner
```
