#!/bin/bash

# =============================================================================
# Time Lapse System - Raspberry Pi Setup Script
# =============================================================================
# This script installs and configures:
# - Python dependencies
# - FFmpeg for camera capture
# - Main timelapse capture service (timelapse.py)
# - Web dashboard service (web_dashboard.py)
# - Auto-start on boot via systemd
# =============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="/home/$(whoami)/timelapse"
SERVICE_USER=$(whoami)
DASHBOARD_PORT=5050

echo -e "${BLUE}"
echo "============================================="
echo "   Time Lapse System - Setup Script"
echo "============================================="
echo -e "${NC}"

# Check if running on Raspberry Pi
if [[ ! -f /proc/device-tree/model ]] || ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
    echo -e "${YELLOW}Warning: This doesn't appear to be a Raspberry Pi.${NC}"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${GREEN}[1/7]${NC} Updating system packages..."
sudo apt-get update -qq

echo -e "${GREEN}[2/7]${NC} Installing dependencies..."
sudo apt-get install -y -qq python3 python3-pip python3-venv ffmpeg

echo -e "${GREEN}[3/7]${NC} Creating installation directory..."
mkdir -p "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR/pics"
mkdir -p "$INSTALL_DIR/templates"
mkdir -p "$INSTALL_DIR/static"

echo -e "${GREEN}[4/7]${NC} Copying application files..."
cp "$SCRIPT_DIR/timelapse.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/web_dashboard.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/templates/dashboard.html" "$INSTALL_DIR/templates/"

# Copy config template
if [[ -f "$SCRIPT_DIR/dashboard_config.example.json" ]]; then
    cp "$SCRIPT_DIR/dashboard_config.example.json" "$INSTALL_DIR/"
fi

# Copy user config if it exists (for upgrades)
if [[ -f "$SCRIPT_DIR/dashboard_config.json" ]]; then
    cp "$SCRIPT_DIR/dashboard_config.json" "$INSTALL_DIR/"
fi

echo -e "${GREEN}[5/7]${NC} Setting up Python virtual environment..."
cd "$INSTALL_DIR"
python3 -m venv venv
source venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet flask requests

echo -e "${GREEN}[6/7]${NC} Creating systemd services..."

# Create timelapse capture service
sudo tee /etc/systemd/system/timelapse-capture.service > /dev/null << EOF
[Unit]
Description=Time Lapse Capture Service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python3 $INSTALL_DIR/timelapse.py
Restart=always
RestartSec=30
StandardOutput=journal
StandardError=journal

# Restart limits
StartLimitIntervalSec=300
StartLimitBurst=5

[Install]
WantedBy=multi-user.target
EOF

# Create web dashboard service
sudo tee /etc/systemd/system/timelapse-dashboard.service > /dev/null << EOF
[Unit]
Description=Time Lapse Web Dashboard
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python3 $INSTALL_DIR/web_dashboard.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Restart limits
StartLimitIntervalSec=300
StartLimitBurst=5

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}[7/7]${NC} Enabling services..."
sudo systemctl daemon-reload
sudo systemctl enable timelapse-capture.service
sudo systemctl enable timelapse-dashboard.service

echo ""
echo -e "${BLUE}=============================================${NC}"
echo -e "${GREEN}Setup complete!${NC}"
echo -e "${BLUE}=============================================${NC}"
echo ""
echo -e "Installation directory: ${YELLOW}$INSTALL_DIR${NC}"
echo ""
echo -e "${BLUE}Services created:${NC}"
echo "  - timelapse-capture   (camera snapshot capture)"
echo "  - timelapse-dashboard (web interface on port $DASHBOARD_PORT)"
echo ""
echo -e "${BLUE}Useful commands:${NC}"
echo "  Start services:    sudo systemctl start timelapse-capture timelapse-dashboard"
echo "  Stop services:     sudo systemctl stop timelapse-capture timelapse-dashboard"
echo "  View status:       sudo systemctl status timelapse-capture timelapse-dashboard"
echo "  View logs:         journalctl -u timelapse-capture -f"
echo "                     journalctl -u timelapse-dashboard -f"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Edit the config file to set your camera URL and project name:"
echo "     nano $INSTALL_DIR/dashboard_config.json"
echo ""
echo "  2. Start the services:"
echo "     sudo systemctl start timelapse-capture timelapse-dashboard"
echo ""
echo "  3. Access the dashboard at:"
echo "     http://$(hostname -I | awk '{print $1}'):$DASHBOARD_PORT"
echo ""
