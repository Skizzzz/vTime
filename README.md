# vTime - Timelapse Capture System

A timelapse capture system with web dashboard for monitoring and managing IP camera snapshots. Designed for Raspberry Pi deployment.

## Features

- **RTSP Camera Capture** - Automated snapshots from IP cameras via FFmpeg
- **Web Dashboard** - Dark theme UI for monitoring, gallery browsing, and configuration
- **FTP Upload** - Automatic backup to remote FTP server with upload tracking
- **Telegram Integration** - Bot commands for remote status checks, photos, and full config management
- **Microsoft Teams Integration** - Scheduled webhook notifications with customizable messages
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

This installs dependencies and configures systemd services to run from the cloned directory.

### 3. Configure

```bash
cp dashboard_config.example.json dashboard_config.json
nano dashboard_config.json
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
    "enabled": false,
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
  },
  "teams": {
    "enabled": false,
    "webhook_url": "https://outlook.office.com/webhook/YOUR_WEBHOOK_URL",
    "message_template": "📸 {project_name} status: {count} snapshots today ({size_mb} MB). Disk: {disk_free_gb} GB free.",
    "schedule_hours": [8, 12, 18],
    "interval_minutes": 0
  }
}
```

FTP is disabled by default - images are stored locally. Enable when ready to sync to a remote server.

### Telegram Setup (Optional)

**Get your Bot Token:**
1. Open Telegram and search for [@BotFather](https://t.me/BotFather)
2. Send `/newbot` and follow the prompts to name your bot
3. BotFather will reply with your bot token (looks like `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)
4. Copy this token to `telegram.bot_token` in your config

**Get your Chat ID:**
1. Search for [@userinfobot](https://t.me/userinfobot) on Telegram
2. Send any message to it
3. It will reply with your user ID (a number like `123456789`)
4. Copy this to `telegram.chat_id` in your config

**Enable notifications:**
1. Set `telegram.enabled` to `true` in your config
2. Restart the timelapse service
3. Send `/help` to your bot to verify it's working

**Available bot commands:**

| Command | Description |
|---------|-------------|
| `/status` | Get current system status with latest photo |
| `/photo` | Take and send a snapshot immediately |
| `/config` | View all current configuration settings |
| `/set <key> <value>` | Modify any configuration setting |
| `/reload` | Reload configuration from file |
| `/teams` | View Teams webhook status |
| `/teams test` | Send a test message to Teams |
| `/help` | Show all available commands |

**Configuration via Telegram:**

You can modify all settings directly from Telegram using `/set`:

```
/set name My Project          # Change project name
/set interval 30              # Snapshot every 30 seconds
/set retention 90             # Keep 90 days of images
/set ftp.enabled true         # Enable FTP uploads
/set ftp.host ftp.example.com # Set FTP hostname
/set telegram.daily_hour 9    # Daily report at 9 AM
/set teams.enabled true       # Enable Teams notifications
/set teams.hours 8,12,18      # Teams messages at 8am, 12pm, 6pm
```

Changes are applied immediately without requiring a service restart.

### Microsoft Teams Setup (Optional)

**Create a Teams Webhook:**
1. In Microsoft Teams, go to the channel where you want notifications
2. Click the `...` menu next to the channel name
3. Select **Connectors** (or **Workflows** in newer Teams)
4. Search for **Incoming Webhook** and click **Configure**
5. Give your webhook a name (e.g., "Timelapse Bot") and optionally upload an icon
6. Click **Create** and copy the webhook URL
7. Paste the URL into `teams.webhook_url` in your config

**Configure scheduling:**

- `schedule_hours`: Array of hours (24h format) to send messages. Default: `[8, 12, 18]` (8am, 12pm, 6pm)
- `interval_minutes`: Set to a number > 0 to send every N minutes instead of at specific hours. Default: `0` (disabled)

**Message template variables:**

Customize `message_template` using these placeholders:
- `{project_name}` - Your project name
- `{count}` - Number of snapshots today
- `{size_mb}` - Total size in MB
- `{disk_free_gb}` - Free disk space in GB
- `{disk_used_percent}` - Disk usage percentage
- `{date}` - Current date (YYYY-MM-DD)
- `{time}` - Current time (HH:MM:SS)
- `{datetime}` - Full timestamp

Example template:
```
"message_template": "📸 {project_name}: {count} snapshots captured. {disk_free_gb} GB free."
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
vTime/
├── pics/                    # Snapshots organized by date
│   └── YYYY-MM-DD/
│       └── snapshot_*.jpg
├── templates/
│   └── dashboard.html
├── timelapse.py             # Main capture script
├── web_dashboard.py         # Flask dashboard
├── dashboard_config.json    # Your configuration (gitignored)
├── setup.sh                 # Raspberry Pi setup script
└── manage.sh                # Service management script
```

## License

MIT
