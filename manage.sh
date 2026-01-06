#!/bin/bash

# =============================================================================
# Time Lapse System - Management Script
# =============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SERVICES="timelapse-capture timelapse-dashboard"

case "$1" in
    start)
        echo -e "${GREEN}Starting services...${NC}"
        sudo systemctl start $SERVICES
        sleep 2
        sudo systemctl status $SERVICES --no-pager
        ;;
    stop)
        echo -e "${YELLOW}Stopping services...${NC}"
        sudo systemctl stop $SERVICES
        echo -e "${GREEN}Services stopped.${NC}"
        ;;
    restart)
        echo -e "${YELLOW}Restarting services...${NC}"
        sudo systemctl restart $SERVICES
        sleep 2
        sudo systemctl status $SERVICES --no-pager
        ;;
    status)
        sudo systemctl status $SERVICES --no-pager
        ;;
    logs)
        SERVICE="${2:-timelapse-capture}"
        echo -e "${BLUE}Showing logs for $SERVICE (Ctrl+C to exit)${NC}"
        journalctl -u "$SERVICE" -f
        ;;
    logs-all)
        echo -e "${BLUE}Showing all timelapse logs (Ctrl+C to exit)${NC}"
        journalctl -u timelapse-capture -u timelapse-dashboard -f
        ;;
    enable)
        echo -e "${GREEN}Enabling auto-start on boot...${NC}"
        sudo systemctl enable $SERVICES
        echo -e "${GREEN}Services will start automatically on boot.${NC}"
        ;;
    disable)
        echo -e "${YELLOW}Disabling auto-start on boot...${NC}"
        sudo systemctl disable $SERVICES
        echo -e "${YELLOW}Services will NOT start automatically on boot.${NC}"
        ;;
    uninstall)
        echo -e "${RED}This will remove the timelapse services.${NC}"
        read -p "Are you sure? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "Stopping services..."
            sudo systemctl stop $SERVICES 2>/dev/null || true
            echo "Disabling services..."
            sudo systemctl disable $SERVICES 2>/dev/null || true
            echo "Removing service files..."
            sudo rm -f /etc/systemd/system/timelapse-capture.service
            sudo rm -f /etc/systemd/system/timelapse-dashboard.service
            sudo systemctl daemon-reload
            echo -e "${GREEN}Services removed. Your data (pics/) is preserved.${NC}"
        fi
        ;;
    *)
        echo "Time Lapse System - Management Script"
        echo ""
        echo "Usage: $0 {command}"
        echo ""
        echo "Commands:"
        echo "  start      Start all services"
        echo "  stop       Stop all services"
        echo "  restart    Restart all services"
        echo "  status     Show service status"
        echo "  logs       Show capture service logs (live)"
        echo "  logs-all   Show all logs (live)"
        echo "  enable     Enable auto-start on boot"
        echo "  disable    Disable auto-start on boot"
        echo "  uninstall  Remove services (keeps data)"
        echo ""
        exit 1
        ;;
esac
