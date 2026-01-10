#!/bin/bash

echo "🔍 LED Runner Diagnostics"
echo "========================="
echo ""

# Check Pi model
echo "📟 Raspberry Pi model:"
if [ -f /proc/device-tree/model ]; then
    cat /proc/device-tree/model
    echo ""
else
    echo "   ⚠️  Not running on a Raspberry Pi!"
fi
echo ""

# Read GPIO pin from config.json
GPIO_PIN=18
if [ -f config.json ]; then
    GPIO_PIN=$(python3 -c "import json; print(json.load(open('config.json'))['led']['pin'])" 2>/dev/null || echo "18")
fi

# Check if audio is disabled (only important for GPIO 18)
echo "🔊 Audio status:"
if [ "$GPIO_PIN" -eq 18 ]; then
    echo "   ℹ️  GPIO 18 detected - audio must be OFF!"
    if grep -q "^dtparam=audio=off" /boot/config.txt 2>/dev/null || grep -q "^dtparam=audio=off" /boot/firmware/config.txt 2>/dev/null; then
        echo "   ✅ Audio is disabled in config.txt"
    elif grep -q "^#dtparam=audio=on" /boot/config.txt 2>/dev/null || grep -q "^#dtparam=audio=on" /boot/firmware/config.txt 2>/dev/null; then
        echo "   ✅ Audio is disabled (commented out)"
    else
        echo "   ❌ Audio is ON - this conflicts with GPIO 18!"
        echo "   💡 Fix: Add 'dtparam=audio=off' to /boot/config.txt (or /boot/firmware/config.txt)"
        echo "   💡 Or use GPIO 12, 13 or 21 in config.json"
    fi
else
    echo "   ℹ️  GPIO $GPIO_PIN in use - no audio conflict"
    echo "   ✅ Audio does not need to be disabled"
fi
echo ""

# Check SPI
echo "🔌 SPI status:"
if lsmod | grep -q spi_bcm2835; then
    echo "   ℹ️  SPI module loaded"
else
    echo "   ℹ️  SPI module not loaded (not needed for WS281x)"
fi
echo ""

# Check if script is running as root
echo "👤 User:"
if [ "$EUID" -eq 0 ]; then
    echo "   ✅ Script is running as root (required for GPIO)"
else
    echo "   ❌ Script is NOT running as root! Use 'sudo'"
fi
echo ""

# Check Python version
echo "🐍 Python version:"
python3 --version
echo ""

# Check if neopixel libraries are installed
echo "📚 Python libraries:"

# Check neopixel (current library)
if venv/bin/python -c "import neopixel" 2>/dev/null; then
    echo "   ✅ neopixel is installed"
else
    echo "   ❌ neopixel is NOT installed!"
    echo "   💡 Fix: source venv/bin/activate && pip install adafruit-circuitpython-neopixel"
fi

# Check pygame
if venv/bin/python -c "import pygame" 2>/dev/null; then
    echo "   ✅ pygame is installed"
else
    echo "   ❌ pygame is NOT installed!"
    echo "   💡 Fix: source venv/bin/activate && pip install pygame"
fi

# Check board (part of neopixel/blinka)
if venv/bin/python -c "import board" 2>/dev/null; then
    echo "   ✅ board (Adafruit Blinka) is installed"
else
    echo "   ❌ board library is NOT installed!"
    echo "   💡 Fix: source venv/bin/activate && pip install adafruit-circuitpython-neopixel"
fi

echo ""

# Check power supply
echo "⚡ Power supply:"
echo "   ℹ️  30 LEDs @ max brightness = ~1.8A @ 5V"
echo "   ℹ️  Ensure you have a good 5V power supply (minimum 2A)"
echo ""

# GPIO pin information
echo "📍 GPIO Pin Configuration:"
echo "   Current pin: GPIO $GPIO_PIN"
echo ""
echo "   Available PWM pins:"
echo "   • GPIO 12 (PWM0) - no audio conflict"
echo "   • GPIO 13 (PWM1) - no audio conflict"
echo "   • GPIO 18 (PWM0) - requires audio=off on Pi 4/5"
echo "   • GPIO 21 (PWM1) - no audio conflict"
echo ""
echo "   💡 Change pin in config.json: \"pin\": 12"
echo ""

# If Pi 4/5 and GPIO 18, give warning
if [ -f /proc/device-tree/model ]; then
    MODEL=$(cat /proc/device-tree/model 2>/dev/null | tr -d '\0')
    if [[ "$MODEL" == *"Pi 4"* ]] || [[ "$MODEL" == *"Pi 5"* ]]; then
        if [ "$GPIO_PIN" -eq 18 ]; then
            echo "⚠️  Pi 4/5 + GPIO 18 Combination:"
            echo "   Audio MUST be disabled in boot config!"
            echo "   Alternative: Use GPIO 12 or 13 (no restart needed)"
            echo ""
        fi
    fi
fi

# Give checklist
echo "📋 Checklist:"
echo "   1. ✓ Always run scripts with sudo"
echo "   2. ✓ Correct libraries installed (see above)"
echo "   3. ✓ config.json correctly configured"
if [ "$GPIO_PIN" -eq 18 ]; then
    echo "   4. ✓ Audio disabled (for GPIO 18)"
fi
echo ""

echo "✅ Diagnostics complete!"
