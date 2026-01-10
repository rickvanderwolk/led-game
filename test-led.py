#!/usr/bin/env python3
"""
Simple LED test - test if the strip works
"""

import time
import board
import neopixel
import json
import sys

# Load configuration
try:
    with open('config.json', 'r') as f:
        config = json.load(f)

    LED_COUNT = config['led']['count']
    GPIO_PIN = config['led'].get('pin', 18)
    LED_BRIGHTNESS = config['led']['brightness'] / 255.0
except FileNotFoundError:
    print("❌ config.json not found!")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error reading config.json: {e}")
    sys.exit(1)

# GPIO pin mapping
gpio_map = {
    12: board.D12,
    13: board.D13,
    18: board.D18,
    21: board.D21
}

if GPIO_PIN not in gpio_map:
    print(f"❌ Invalid GPIO pin in config.json: {GPIO_PIN}")
    print(f"   Use: 12, 13, 18 or 21")
    sys.exit(1)

print(f"🔧 Initializing LED strip...")
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
    print(f"✅ LED strip initialized on GPIO {GPIO_PIN}\n")
except Exception as e:
    print(f"❌ Error initializing: {e}")
    print(f"   Are you running the script with sudo?")
    sys.exit(1)

try:
    # Test 1: All LEDs white (full power)
    print("Test 1: All LEDs WHITE (RGB: 255,255,255)")
    strip.fill((255, 255, 255))
    strip.show()
    time.sleep(2)

    # Clear
    strip.fill((0, 0, 0))
    strip.show()
    time.sleep(0.5)

    # Test 2: Red
    print("Test 2: All LEDs RED (RGB: 255,0,0)")
    strip.fill((255, 0, 0))
    strip.show()
    time.sleep(2)

    # Clear
    strip.fill((0, 0, 0))
    strip.show()
    time.sleep(0.5)

    # Test 3: Green
    print("Test 3: All LEDs GREEN (RGB: 0,255,0)")
    strip.fill((0, 255, 0))
    strip.show()
    time.sleep(2)

    # Clear
    strip.fill((0, 0, 0))
    strip.show()
    time.sleep(0.5)

    # Test 4: Blue
    print("Test 4: All LEDs BLUE (RGB: 0,0,255)")
    strip.fill((0, 0, 255))
    strip.show()
    time.sleep(2)

    # Clear
    strip.fill((0, 0, 0))
    strip.show()
    time.sleep(0.5)

    # Test 5: Running light
    print("Test 5: Running light (white)")
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

    print("\n✅ Test complete!")

except KeyboardInterrupt:
    print("\n\n⏹️  Test stopped")

finally:
    # Clear all LEDs
    strip.fill((0, 0, 0))
    strip.show()
    print("LEDs turned off")
