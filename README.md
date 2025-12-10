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
# Install dependencies
pip install flask requests

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
nano ~/timelapse/dashboard_config.json
```

Edit RTSP URL, FTP credentials, and other settings.

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

On first run, `dashboard_config.json` is created with defaults:

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
    "upload_interval": 3600
  }
}
```

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
