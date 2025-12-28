#!/bin/bash

echo "🔍 LED Strip Diagnose"
echo "===================="
echo ""

# Check Pi model
echo "📟 Raspberry Pi model:"
if [ -f /proc/device-tree/model ]; then
    cat /proc/device-tree/model
    echo ""
else
    echo "   ⚠️  Niet op een Raspberry Pi!"
fi
echo ""

# Lees GPIO pin uit config.json
GPIO_PIN=18
if [ -f config.json ]; then
    GPIO_PIN=$(python3 -c "import json; print(json.load(open('config.json'))['led']['pin'])" 2>/dev/null || echo "18")
fi

# Check of audio is uitgeschakeld (alleen belangrijk voor GPIO 18)
echo "🔊 Audio status:"
if [ "$GPIO_PIN" -eq 18 ]; then
    echo "   ℹ️  GPIO 18 gedetecteerd - audio moet UIT zijn!"
    if grep -q "^dtparam=audio=off" /boot/config.txt 2>/dev/null || grep -q "^dtparam=audio=off" /boot/firmware/config.txt 2>/dev/null; then
        echo "   ✅ Audio is uitgeschakeld in config.txt"
    elif grep -q "^#dtparam=audio=on" /boot/config.txt 2>/dev/null || grep -q "^#dtparam=audio=on" /boot/firmware/config.txt 2>/dev/null; then
        echo "   ✅ Audio is uitgeschakeld (commented out)"
    else
        echo "   ❌ Audio is AAN - dit conflicteert met GPIO 18!"
        echo "   💡 Los op: Voeg 'dtparam=audio=off' toe aan /boot/config.txt (of /boot/firmware/config.txt)"
        echo "   💡 Of gebruik GPIO 12, 13 of 21 in config.json"
    fi
else
    echo "   ℹ️  GPIO $GPIO_PIN gebruikt - geen audio conflict"
    echo "   ✅ Audio hoeft niet uitgeschakeld te worden"
fi
echo ""

# Check SPI
echo "🔌 SPI status:"
if lsmod | grep -q spi_bcm2835; then
    echo "   ℹ️  SPI module geladen"
else
    echo "   ℹ️  SPI module niet geladen (niet nodig voor WS281x)"
fi
echo ""

# Check als script als root draait
echo "👤 Gebruiker:"
if [ "$EUID" -eq 0 ]; then
    echo "   ✅ Script draait als root (vereist voor GPIO)"
else
    echo "   ❌ Script draait NIET als root! Gebruik 'sudo'"
fi
echo ""

# Check Python versie
echo "🐍 Python versie:"
python3 --version
echo ""

# Check of neopixel libraries zijn geïnstalleerd
echo "📚 Python libraries:"

# Check neopixel (huidige library)
if venv/bin/python -c "import neopixel" 2>/dev/null; then
    echo "   ✅ neopixel is geïnstalleerd"
else
    echo "   ❌ neopixel is NIET geïnstalleerd!"
    echo "   💡 Los op: source venv/bin/activate && pip install adafruit-circuitpython-neopixel"
fi

# Check pygame
if venv/bin/python -c "import pygame" 2>/dev/null; then
    echo "   ✅ pygame is geïnstalleerd"
else
    echo "   ❌ pygame is NIET geïnstalleerd!"
    echo "   💡 Los op: source venv/bin/activate && pip install pygame"
fi

# Check board (deel van neopixel/blinka)
if venv/bin/python -c "import board" 2>/dev/null; then
    echo "   ✅ board (Adafruit Blinka) is geïnstalleerd"
else
    echo "   ❌ board library is NIET geïnstalleerd!"
    echo "   💡 Los op: source venv/bin/activate && pip install adafruit-circuitpython-neopixel"
fi

echo ""

# Check voeding
echo "⚡ Voeding:"
echo "   ℹ️  30 LEDs @ max helderheid = ~1.8A @ 5V"
echo "   ℹ️  Zorg voor goede 5V voeding (minimaal 2A)"
echo ""

# GPIO pin informatie
echo "📍 GPIO Pin Configuratie:"
echo "   Huidige pin: GPIO $GPIO_PIN"
echo ""
echo "   Beschikbare PWM pins:"
echo "   • GPIO 12 (PWM0) - geen audio conflict"
echo "   • GPIO 13 (PWM1) - geen audio conflict"
echo "   • GPIO 18 (PWM0) - vereist audio=off op Pi 4/5"
echo "   • GPIO 21 (PWM1) - geen audio conflict"
echo ""
echo "   💡 Wijzig pin in config.json: \"pin\": 12"
echo ""

# Als Pi 4/5 en GPIO 18, geef waarschuwing
if [ -f /proc/device-tree/model ]; then
    MODEL=$(cat /proc/device-tree/model 2>/dev/null | tr -d '\0')
    if [[ "$MODEL" == *"Pi 4"* ]] || [[ "$MODEL" == *"Pi 5"* ]]; then
        if [ "$GPIO_PIN" -eq 18 ]; then
            echo "⚠️  Pi 4/5 + GPIO 18 Combinatie:"
            echo "   Audio MOET uitgeschakeld zijn in boot config!"
            echo "   Alternatief: Gebruik GPIO 12 of 13 (geen herstart nodig)"
            echo ""
        fi
    fi
fi

# Geef checklist
echo "📋 Checklist:"
echo "   1. ✓ Draai scripts altijd met sudo"
echo "   2. ✓ Juiste libraries geïnstalleerd (zie boven)"
echo "   3. ✓ Config.json correct ingesteld"
if [ "$GPIO_PIN" -eq 18 ]; then
    echo "   4. ✓ Audio uitgeschakeld (voor GPIO 18)"
fi
echo ""

echo "✅ Diagnose compleet!"
