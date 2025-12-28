#!/usr/bin/env python3
"""
Simpele LED test - test of de strip werkt
"""

import time
import board
import neopixel
import json
import sys

# Laad configuratie
try:
    with open('config.json', 'r') as f:
        config = json.load(f)

    LED_COUNT = config['led']['count']
    GPIO_PIN = config['led'].get('pin', 18)
    LED_BRIGHTNESS = config['led']['brightness'] / 255.0
except FileNotFoundError:
    print("❌ config.json niet gevonden!")
    sys.exit(1)
except Exception as e:
    print(f"❌ Fout bij lezen config.json: {e}")
    sys.exit(1)

# GPIO pin mapping
gpio_map = {
    12: board.D12,
    13: board.D13,
    18: board.D18,
    21: board.D21
}

if GPIO_PIN not in gpio_map:
    print(f"❌ Ongeldige GPIO pin in config.json: {GPIO_PIN}")
    print(f"   Gebruik: 12, 13, 18 of 21")
    sys.exit(1)

print(f"🔧 Initialiseer LED strip...")
print(f"   LEDs: {LED_COUNT}")
print(f"   GPIO Pin: {GPIO_PIN}")
print(f"   Brightness: {int(LED_BRIGHTNESS * 255)}/255")

try:
    strip = neopixel.NeoPixel(
        gpio_map[GPIO_PIN],
        LED_COUNT,
        brightness=LED_BRIGHTNESS,
        auto_write=False,
        pixel_order=neopixel.GRB
    )
    print(f"✅ LED strip geïnitialiseerd op GPIO {GPIO_PIN}\n")
except Exception as e:
    print(f"❌ Fout bij initialiseren: {e}")
    print(f"   Draai je het script met sudo?")
    sys.exit(1)

try:
    # Test 1: Alle LEDs wit (volle kracht)
    print("Test 1: Alle LEDs WIT (RGB: 255,255,255)")
    strip.fill((255, 255, 255))
    strip.show()
    time.sleep(2)

    # Clear
    strip.fill((0, 0, 0))
    strip.show()
    time.sleep(0.5)

    # Test 2: Rood
    print("Test 2: Alle LEDs ROOD (RGB: 255,0,0)")
    strip.fill((255, 0, 0))
    strip.show()
    time.sleep(2)

    # Clear
    strip.fill((0, 0, 0))
    strip.show()
    time.sleep(0.5)

    # Test 3: Groen
    print("Test 3: Alle LEDs GROEN (RGB: 0,255,0)")
    strip.fill((0, 255, 0))
    strip.show()
    time.sleep(2)

    # Clear
    strip.fill((0, 0, 0))
    strip.show()
    time.sleep(0.5)

    # Test 4: Blauw
    print("Test 4: Alle LEDs BLAUW (RGB: 0,0,255)")
    strip.fill((0, 0, 255))
    strip.show()
    time.sleep(2)

    # Clear
    strip.fill((0, 0, 0))
    strip.show()
    time.sleep(0.5)

    # Test 5: Running light
    print("Test 5: Running light (wit)")
    for i in range(LED_COUNT):
        # Clear previous
        if i > 0:
            strip[i - 1] = (0, 0, 0)

        # Set current
        strip[i] = (255, 255, 255)
        strip.show()
        time.sleep(0.05)

    # Clear
    strip.fill((0, 0, 0))
    strip.show()

    print("\n✅ Test compleet!")

except KeyboardInterrupt:
    print("\n\n⏹️  Test gestopt")

finally:
    # Clear all LEDs
    strip.fill((0, 0, 0))
    strip.show()
    print("LEDs uitgeschakeld")
