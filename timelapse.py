import subprocess
import time
from datetime import datetime, date, timedelta
import os
import shutil
from ftplib import FTP
import requests
import json

# === CONFIGURATION ===

CONFIG_FILE = "dashboard_config.json"

def load_config():
    """Load configuration from JSON file"""
    if not os.path.exists(CONFIG_FILE):
        print(f"[ERROR] Config file not found: {CONFIG_FILE}")
        print(f"Please copy dashboard_config.example.json to {CONFIG_FILE} and edit it.")
        exit(1)

    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

config = load_config()

# RTSP Stream
rtsp_url = config.get("rtsp_url", "rtsp://user:pass@camera-ip:554/stream")

# Snapshot settings
snapshot_interval = config.get("snapshot_interval", 60)
base_output_dir = config.get("base_output_dir", "./pics")

# FTP Settings
ftp_config = config.get("ftp", {})
FTP_ENABLED = ftp_config.get("enabled", False)  # Default False - local storage only
FTP_HOST = ftp_config.get("host", "")
FTP_USER = ftp_config.get("user", "")
FTP_PASS = ftp_config.get("password", "")
REMOTE_ROOT = ftp_config.get("remote_root", "/timelapse")

# Retention
retention_days = config.get("retention_days", 60)
upload_interval_minutes = ftp_config.get("upload_interval_minutes", 60)

# Telegram Settings
telegram_config = config.get("telegram", {})
TELEGRAM_BOT_TOKEN = telegram_config.get("bot_token", "")
TELEGRAM_CHAT_ID = telegram_config.get("chat_id", "")
DAILY_REPORT_HOUR = telegram_config.get("daily_report_hour", 8)
TELEGRAM_ENABLED = telegram_config.get("enabled", False)

# Project name for messages
PROJECT_NAME = config.get("project_name", "Timelapse")

# === FUNCTIONS ===

def take_snapshot(current_dir):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(current_dir, f"snapshot_{timestamp}.jpg")
    try:
        subprocess.run([
            "ffmpeg",
            "-rtsp_transport", "tcp",
            "-i", rtsp_url,
            "-t", "1",
            "-frames:v", "1",
            "-loglevel", "error",
            "-y",
            filename
        ], check=True, timeout=10)
        print(f"[{timestamp}] Saved snapshot to {filename}")
    except subprocess.CalledProcessError as e:
        print(f"[{timestamp}] FFmpeg error: {e}")
    except subprocess.TimeoutExpired:
        print(f"[{timestamp}] FFmpeg timed out")

def upload_folder_to_ftp(local_dir, remote_dir):
    print(f"[FTP] Uploading {local_dir} to FTP: /{remote_dir}")
    try:
        ftp = FTP(FTP_HOST)
        ftp.set_pasv(True)
        ftp.login(FTP_USER, FTP_PASS)

        def ensure_remote_path(path):
            for part in path.strip("/").split("/"):
                if part not in ftp.nlst():
                    try:
                        ftp.mkd(part)
                        print(f"[FTP] Created directory: {part}")
                    except Exception as e:
                        print(f"[FTP] Directory may already exist: {e}")
                ftp.cwd(part)

        def upload_dir(local_path, remote_path):
            try:
                ftp.cwd("/")
            except:
                pass
            ensure_remote_path(remote_path)

            for fname in sorted(os.listdir(local_path)):
                if not fname.lower().endswith(".jpg"):
                    continue
                local_file = os.path.join(local_path, fname)
                marker_file = local_file + ".uploaded"

                # Skip if already uploaded
                if os.path.exists(marker_file):
                    continue

                try:
                    with open(local_file, "rb") as f:
                        ftp.storbinary(f"STOR " + fname, f)
                    # Create .uploaded marker
                    with open(marker_file, "w") as marker:
                        marker.write("uploaded\n")
                    print(f"[FTP] Uploaded and marked: {fname}")
                except Exception as e:
                    print(f"[FTP] Failed to upload {fname}: {e}")

        upload_dir(local_dir, remote_dir)
        ftp.quit()
        print("[FTP] Upload complete.")
    except Exception as e:
        print(f"[FTP] Entire FTP upload failed: {e}")

def delete_old_folders(base_dir, keep_days=21):
    today = date.today()
    for folder in os.listdir(base_dir):
        folder_path = os.path.join(base_dir, folder)
        if os.path.isdir(folder_path):
            try:
                folder_date = datetime.strptime(folder, "%Y-%m-%d").date()
                age = (today - folder_date).days
                if age > keep_days:
                    print(f"Deleting old folder: {folder_path}")
                    shutil.rmtree(folder_path)
            except ValueError:
                continue

def send_telegram_message(message):
    """Send a text message via Telegram bot"""
    if not TELEGRAM_ENABLED:
        return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
        response = requests.post(url, data=data, timeout=10)
        if response.status_code == 200:
            print("[Telegram] Message sent successfully")
            return True
        else:
            print(f"[Telegram] Failed to send message: {response.text}")
            return False
    except Exception as e:
        print(f"[Telegram] Error sending message: {e}")
        return False

def send_telegram_photo(photo_path, caption=""):
    """Send a photo via Telegram bot"""
    if not TELEGRAM_ENABLED:
        return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        with open(photo_path, 'rb') as photo:
            files = {'photo': photo}
            data = {'chat_id': TELEGRAM_CHAT_ID, 'caption': caption, 'parse_mode': 'HTML'}
            response = requests.post(url, data=data, files=files, timeout=30)
        if response.status_code == 200:
            print(f"[Telegram] Photo sent: {photo_path}")
            return True
        else:
            print(f"[Telegram] Failed to send photo: {response.text}")
            return False
    except Exception as e:
        print(f"[Telegram] Error sending photo: {e}")
        return False

def get_folder_stats(folder_path):
    """Get statistics about snapshots in a folder"""
    if not os.path.exists(folder_path):
        return {"count": 0, "size_mb": 0, "latest": None}

    jpg_files = [f for f in os.listdir(folder_path) if f.lower().endswith(".jpg")]
    total_size = sum(os.path.getsize(os.path.join(folder_path, f)) for f in jpg_files)

    latest_file = None
    if jpg_files:
        latest_file = max([os.path.join(folder_path, f) for f in jpg_files], key=os.path.getmtime)

    return {
        "count": len(jpg_files),
        "size_mb": total_size / (1024 * 1024),
        "latest": latest_file
    }

def send_daily_telegram_report():
    """Send comprehensive daily report via Telegram"""
    if not TELEGRAM_ENABLED:
        return

    yesterday = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    yesterday_dir = os.path.join(base_output_dir, yesterday)

    # Get statistics
    stats = get_folder_stats(yesterday_dir)

    # Get system info
    try:
        disk_usage = shutil.disk_usage(base_output_dir)
        disk_free_gb = disk_usage.free / (1024**3)
        disk_used_percent = (disk_usage.used / disk_usage.total) * 100
    except:
        disk_free_gb = 0
        disk_used_percent = 0

    # Count total folders
    try:
        total_folders = len([d for d in os.listdir(base_output_dir)
                           if os.path.isdir(os.path.join(base_output_dir, d))])
    except:
        total_folders = 0

    # Build message
    message = f"<b>📸 {PROJECT_NAME} - Daily Report</b>\n\n"
    message += f"<b>Date:</b> {yesterday}\n\n"
    message += f"<b>📊 Yesterday's Stats:</b>\n"
    message += f"• Snapshots captured: {stats['count']}\n"
    message += f"• Total size: {stats['size_mb']:.1f} MB\n"
    message += f"• Expected: {(24*60*60) // snapshot_interval} snapshots\n\n"

    message += f"<b>💾 System Health:</b>\n"
    message += f"• Disk free: {disk_free_gb:.1f} GB\n"
    message += f"• Disk usage: {disk_used_percent:.1f}%\n"
    message += f"• Total archived days: {total_folders}\n"
    message += f"• Retention: {retention_days} days\n\n"

    # Check for issues
    expected_snapshots = (24*60*60) // snapshot_interval
    if stats['count'] < expected_snapshots * 0.9:  # Less than 90% of expected
        message += f"⚠️ <b>Warning:</b> Only {stats['count']}/{expected_snapshots} snapshots captured\n"

    if disk_free_gb < 1.0:  # Less than 1GB free
        message += f"⚠️ <b>Warning:</b> Low disk space ({disk_free_gb:.1f} GB free)\n"

    if stats['count'] == 0:
        message += "❌ <b>Error:</b> No snapshots captured yesterday!\n"

    # Send message
    send_telegram_message(message)

    # Send latest snapshot if available
    if stats['latest'] and os.path.exists(stats['latest']):
        # Get the file's timestamp
        file_time = datetime.fromtimestamp(os.path.getmtime(stats['latest']))
        caption = f"📸 Latest snapshot from {yesterday}\n{file_time.strftime('%Y-%m-%d %H:%M:%S')}"
        send_telegram_photo(stats['latest'], caption)

def send_telegram_alert(alert_type, details):
    """Send real-time alert for errors"""
    if not TELEGRAM_ENABLED:
        return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if alert_type == "snapshot_error":
        message = f"⚠️ <b>Snapshot Error</b>\n\n"
        message += f"Time: {timestamp}\n"
        message += f"Details: {details}"
    elif alert_type == "upload_error":
        message = f"⚠️ <b>FTP Upload Error</b>\n\n"
        message += f"Time: {timestamp}\n"
        message += f"Details: {details}"
    else:
        message = f"⚠️ <b>Alert: {alert_type}</b>\n\n{details}"

    send_telegram_message(message)

def get_telegram_updates(offset=None):
    """Get new messages from Telegram bot"""
    if not TELEGRAM_ENABLED:
        return []
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
        params = {"timeout": 0, "offset": offset} if offset else {"timeout": 0}
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            return response.json().get("result", [])
        return []
    except Exception as e:
        print(f"[Telegram] Error getting updates: {e}")
        return []

def handle_telegram_command(command, current_output_dir):
    """Handle commands sent to the Telegram bot"""
    command = command.lower().strip()
    now = datetime.now()

    if command in ["status", "/status"]:
        # Get current status
        today_str = now.strftime("%Y-%m-%d")
        stats = get_folder_stats(current_output_dir)

        # Get disk info
        try:
            disk_usage = shutil.disk_usage(base_output_dir)
            disk_free_gb = disk_usage.free / (1024**3)
            disk_used_percent = (disk_usage.used / disk_usage.total) * 100
        except:
            disk_free_gb = 0
            disk_used_percent = 0

        # Build status message
        message = f"<b>📊 Current Status</b>\n\n"
        message += f"<b>Time:</b> {now.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        message += f"<b>Today's Stats:</b>\n"
        message += f"• Snapshots today: {stats['count']}\n"
        message += f"• Total size: {stats['size_mb']:.1f} MB\n\n"
        message += f"<b>System Health:</b>\n"
        message += f"• Disk free: {disk_free_gb:.1f} GB\n"
        message += f"• Disk usage: {disk_used_percent:.1f}%\n"
        message += f"• Service: Running ✅"

        send_telegram_message(message)

        # Send latest snapshot if available
        if stats['latest'] and os.path.exists(stats['latest']):
            file_time = datetime.fromtimestamp(os.path.getmtime(stats['latest']))
            caption = f"📸 Latest snapshot\n{file_time.strftime('%Y-%m-%d %H:%M:%S')}"
            send_telegram_photo(stats['latest'], caption)

    elif command in ["photo", "/photo", "snapshot", "/snapshot"]:
        # Take a new snapshot on demand
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        on_demand_snapshot = os.path.join(current_output_dir, f"snapshot_{timestamp}.jpg")

        try:
            subprocess.run([
                "ffmpeg",
                "-rtsp_transport", "tcp",
                "-i", rtsp_url,
                "-t", "1",
                "-frames:v", "1",
                "-loglevel", "error",
                "-y",
                on_demand_snapshot
            ], check=True, timeout=10)

            if os.path.exists(on_demand_snapshot):
                caption = f"📸 On-demand snapshot\n{now.strftime('%Y-%m-%d %H:%M:%S')}"
                send_telegram_photo(on_demand_snapshot, caption)
            else:
                send_telegram_message("❌ Failed to capture snapshot")
        except Exception as e:
            send_telegram_message(f"❌ Error capturing snapshot: {str(e)}")

    elif command in ["help", "/help", "/start"]:
        help_msg = f"<b>🤖 {PROJECT_NAME} Bot - Commands</b>\n\n"
        help_msg += "<b>Available commands:</b>\n"
        help_msg += "• <code>status</code> - Get current system status with latest photo\n"
        help_msg += "• <code>photo</code> - Take and send a new snapshot immediately\n"
        help_msg += "• <code>help</code> - Show this help message\n\n"
        help_msg += f"<b>Automatic notifications:</b>\n"
        help_msg += f"• Daily report at {DAILY_REPORT_HOUR}:00 AM\n"
        help_msg += "• Real-time error alerts\n"
        help_msg += "• Startup notifications"
        send_telegram_message(help_msg)

    else:
        # Unknown command
        send_telegram_message(f"❓ Unknown command: '{command}'\n\nSend <code>help</code> to see available commands.")

def test_telegram():
    """Test Telegram bot configuration"""
    print("Testing Telegram bot...")
    print(f"Bot Token: {TELEGRAM_BOT_TOKEN[:20]}...")
    print(f"Chat ID: {TELEGRAM_CHAT_ID}")
    print()

    # Test 1: Simple message
    print("Test 1: Sending test message...")
    test_msg = f"<b>🤖 {PROJECT_NAME} Bot Test</b>\n\n"
    test_msg += "✅ Bot configuration successful!\n"
    test_msg += f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    test_msg += "\nYour Telegram notifications are working correctly."

    if send_telegram_message(test_msg):
        print("✅ Test message sent successfully!")
    else:
        print("❌ Failed to send test message")
        return False

    print()
    return True

# === MAIN LOOP ===

# Send startup notification
startup_msg = f"<b>🚀 {PROJECT_NAME} Started</b>\n\n"
startup_msg += "✅ Service started successfully\n"
startup_msg += f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
startup_msg += f"📸 Snapshot interval: {snapshot_interval} seconds\n"
if FTP_ENABLED:
    startup_msg += f"☁️ FTP upload: Every {upload_interval_minutes} minutes\n"
else:
    startup_msg += "☁️ FTP upload: Disabled (local storage only)\n"
startup_msg += f"📊 Daily report: {DAILY_REPORT_HOUR}:00 AM\n"
startup_msg += f"🗑️ Retention: {retention_days} days"
send_telegram_message(startup_msg)
print("[Startup] Telegram notification sent")

# Take and send initial startup snapshot
print("[Startup] Taking initial snapshot...")
now = datetime.now()
today_str = now.strftime("%Y-%m-%d")
startup_dir = os.path.join(base_output_dir, today_str)
os.makedirs(startup_dir, exist_ok=True)

timestamp = now.strftime("%Y%m%d_%H%M%S")
startup_snapshot = os.path.join(startup_dir, f"snapshot_{timestamp}.jpg")

try:
    subprocess.run([
        "ffmpeg",
        "-rtsp_transport", "tcp",
        "-i", rtsp_url,
        "-t", "1",
        "-frames:v", "1",
        "-loglevel", "error",
        "-y",
        startup_snapshot
    ], check=True, timeout=10)

    if os.path.exists(startup_snapshot):
        print(f"[Startup] Snapshot captured: {startup_snapshot}")
        startup_caption = f"📸 First snapshot on startup\n{now.strftime('%Y-%m-%d %H:%M:%S')}"
        send_telegram_photo(startup_snapshot, startup_caption)
        print("[Startup] Initial snapshot sent to Telegram")
    else:
        print("[Startup] Snapshot file not created")
except Exception as e:
    print(f"[Startup] Failed to capture initial snapshot: {e}")

last_upload_time = datetime.now()
last_cleanup_date = date.today()
last_snapshot_time = datetime.now()
daily_report_sent = False
snapshot_error_count = 0
upload_error_count = 0
last_update_id = None  # Track last processed Telegram message

# Command check interval (seconds) - check for commands more frequently
command_check_interval = 5

while True:
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    current_output_dir = os.path.join(base_output_dir, today_str)
    os.makedirs(current_output_dir, exist_ok=True)

    # Check for Telegram commands (every loop iteration)
    try:
        updates = get_telegram_updates(last_update_id)
        for update in updates:
            last_update_id = update['update_id'] + 1
            if 'message' in update and 'text' in update['message']:
                # Only respond to messages from the configured chat
                if str(update['message']['chat']['id']) == str(TELEGRAM_CHAT_ID):
                    command_text = update['message']['text']
                    print(f"[Telegram] Received command: {command_text}")
                    handle_telegram_command(command_text, current_output_dir)
    except Exception as e:
        print(f"[Telegram] Error processing commands: {e}")

    # Send daily report at specified hour
    if now.hour == DAILY_REPORT_HOUR and not daily_report_sent:
        send_daily_telegram_report()
        daily_report_sent = True
    elif now.hour != DAILY_REPORT_HOUR:
        daily_report_sent = False  # Reset flag for next day

    # Take snapshot (only if enough time has passed)
    if (now - last_snapshot_time).total_seconds() >= snapshot_interval:
        try:
            snapshot_before_count = len([f for f in os.listdir(current_output_dir) if f.endswith('.jpg')])
            take_snapshot(current_output_dir)
            snapshot_after_count = len([f for f in os.listdir(current_output_dir) if f.endswith('.jpg')])

            # Check if snapshot was actually created
            if snapshot_after_count > snapshot_before_count:
                snapshot_error_count = 0  # Reset error count on success
            else:
                snapshot_error_count += 1
                if snapshot_error_count == 5:  # Alert after 5 consecutive failures
                    send_telegram_alert("snapshot_error", f"5 consecutive snapshot failures detected")

        except Exception as e:
            snapshot_error_count += 1
            if snapshot_error_count == 5:
                send_telegram_alert("snapshot_error", f"Exception: {str(e)}")

        last_snapshot_time = now

    # Upload every N minutes (60 for hourly) - only if FTP is enabled
    if FTP_ENABLED and (now - last_upload_time) >= timedelta(minutes=upload_interval_minutes):
        remote_path = f"{REMOTE_ROOT}/{today_str}"
        try:
            upload_folder_to_ftp(current_output_dir, remote_path)
            upload_error_count = 0  # Reset on success
        except Exception as e:
            upload_error_count += 1
            if upload_error_count == 3:  # Alert after 3 consecutive upload failures
                send_telegram_alert("upload_error", f"3 consecutive FTP upload failures: {str(e)}")
        last_upload_time = now

    # Daily cleanup
    if now.date() != last_cleanup_date:
        delete_old_folders(base_output_dir, keep_days=retention_days)
        last_cleanup_date = now.date()

    # Sleep for a short time to check commands frequently
    time.sleep(command_check_interval)