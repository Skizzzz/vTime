# vTime - Timelapse Capture System

A timelapse capture system with web dashboard for monitoring and managing IP camera snapshots. Designed for Raspberry Pi deployment.

## Features

- **RTSP Camera Capture** - Automated snapshots from IP cameras via FFmpeg
- **Web Dashboard** - Dark theme UI for monitoring, gallery browsing, and configuration
- **FTP Upload** - Automatic backup to remote FTP server with upload tracking
- **Telegram Integration** - Bot commands for remote status checks and photos
- **Raspberry Pi Ready** - Systemd services with auto-start on boot

## Quick Start (Local)

```bash
# Clone the repository
git clone <repo-url>
cd vTime

# Install dependencies
pip install -r requirements.txt

# Copy and configure settings
cp dashboard_config.example.json dashboard_config.json
# Edit dashboard_config.json with your camera URL, FTP settings, etc.

# Run the dashboard
python web_dashboard.py
```

Access at `http://localhost:5050`

## Raspberry Pi Deployment

### 1. Copy files to Pi

```bash
scp -r vTime/ pi@<pi-ip>:~/
```

### 2. Run setup script

```bash
cd ~/vTime
./setup.sh
```

This installs dependencies, creates `/home/<user>/timelapse`, and configures systemd services.

### 3. Configure

```bash
cp ~/timelapse/dashboard_config.example.json ~/timelapse/dashboard_config.json
nano ~/timelapse/dashboard_config.json
```

Edit RTSP URL, FTP credentials, Telegram settings, and other options.

### 4. Start services

```bash
./manage.sh start
```

Access dashboard at `http://<pi-ip>:5050`

## Service Management

```bash
./manage.sh start      # Start capture + dashboard
./manage.sh stop       # Stop both services
./manage.sh restart    # Restart both services
./manage.sh status     # Check service status
./manage.sh logs       # View capture logs (live)
./manage.sh logs-all   # View all logs (live)
./manage.sh enable     # Enable auto-start on boot
./manage.sh disable    # Disable auto-start
./manage.sh uninstall  # Remove services (keeps data)
```

## Configuration

Copy `dashboard_config.example.json` to `dashboard_config.json` and edit:

```json
{
  "project_name": "My Timelapse",
  "rtsp_url": "rtsp://user:pass@camera-ip:554/stream",
  "base_output_dir": "./pics",
  "snapshot_interval": 60,
  "retention_days": 60,
  "ftp": {
    "host": "ftp.example.com",
    "port": 21,
    "user": "ftpuser",
    "password": "ftppass",
    "remote_root": "/timelapse",
    "passive_mode": true,
    "upload_interval_minutes": 60
  },
  "telegram": {
    "enabled": false,
    "bot_token": "YOUR_BOT_TOKEN",
    "chat_id": "YOUR_CHAT_ID",
    "daily_report_hour": 8
  }
}
```

### Telegram Setup (Optional)

1. Create a bot via [@BotFather](https://t.me/BotFather) on Telegram
2. Get your chat ID from [@userinfobot](https://t.me/userinfobot)
3. Set `telegram.enabled` to `true` and fill in your credentials

## Dashboard Features

- **Overview Tab** - Live stats, latest snapshot, storage usage, quick FTP status
- **FTP Uploads Tab** - Upload statistics, connection testing, remote server browser
- **Gallery Tab** - Browse snapshots by date with pagination
- **Editable Title** - Click the title to rename your project

## Requirements

- Python 3.7+
- FFmpeg
- Flask, Requests

## File Structure

```
~/timelapse/
├── pics/                    # Snapshots organized by date
│   └── YYYY-MM-DD/
│       └── snapshot_*.jpg
├── templates/
│   └── dashboard.html
├── timelapse.py             # Main capture script
├── web_dashboard.py         # Flask dashboard
└── dashboard_config.json    # Configuration
```

## License

MIT
