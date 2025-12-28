#!/bin/bash

set -e

echo "🎮 LED Strip Game - Installatie"
echo "================================"

# Installeer systeem dependencies
echo ""
echo "📦 Installeer systeem dependencies..."
sudo apt update
sudo apt install -y python3-dev python3-venv python3-pip build-essential

# Maak virtual environment
echo ""
echo "🐍 Maak virtual environment..."
python3 -m venv venv

# Activeer virtual environment
source venv/bin/activate

# Upgrade pip
echo ""
echo "⬆️  Upgrade pip..."
pip install --upgrade pip

# Installeer Python packages
echo ""
echo "📚 Installeer Python packages..."
pip install -r requirements.txt

echo ""
echo "🔧 Installeer systemd service..."

# Bepaal huidige user en directory
CURRENT_USER=$(whoami)
INSTALL_DIR=$(pwd)
HOME_DIR=$(eval echo ~$CURRENT_USER)

echo "   Installeer voor gebruiker: $CURRENT_USER"
echo "   Installatie directory: $INSTALL_DIR"

# Genereer service file uit template
sed -e "s|{{USER}}|$CURRENT_USER|g" \
    -e "s|{{INSTALL_DIR}}|$INSTALL_DIR|g" \
    -e "s|{{HOME_DIR}}|$HOME_DIR|g" \
    led-strip-game.service.template > led-strip-game.service

# Kopieer service file naar systemd directory
sudo cp led-strip-game.service /etc/systemd/system/

# Herlaad systemd
sudo systemctl daemon-reload

# Enable service (start bij boot)
sudo systemctl enable led-strip-game.service

echo ""
echo "🚀 Service starten..."
sudo systemctl start led-strip-game.service

# Wacht even en check status
sleep 2
echo ""
if sudo systemctl is-active --quiet led-strip-game.service; then
    echo "✅ Service draait!"
    echo ""
    echo "Bekijk live logs met:"
    echo "  journalctl -u led-strip-game -f"
else
    echo "⚠️  Service kon niet starten. Check de status:"
    echo "  sudo systemctl status led-strip-game"
    echo "  journalctl -u led-strip-game -n 50"
fi

echo ""
echo "✅ Installatie compleet!"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Service commando's:"
echo "  sudo systemctl start led-strip-game    # Start de service"
echo "  sudo systemctl stop led-strip-game     # Stop de service"
echo "  sudo systemctl restart led-strip-game  # Herstart de service"
echo "  sudo systemctl status led-strip-game   # Status bekijken"
echo "  journalctl -u led-strip-game -f        # Logs bekijken (live)"
echo ""
echo "De service start automatisch op bij reboot."
echo ""
echo "Of start handmatig met: ./start.sh"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
