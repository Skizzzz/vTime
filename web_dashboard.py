"""
vTime - Timelapse Web Dashboard
A simple web interface for monitoring and managing the timelapse system.
"""

from flask import Flask, jsonify, render_template, send_file, request
from datetime import datetime
from ftplib import FTP
import os
import shutil
import subprocess
import json
import sys

app = Flask(__name__, template_folder='templates', static_folder='static')

# === CONFIGURATION ===
CONFIG_FILE = "./dashboard_config.json"
DEFAULT_CONFIG = {
    "project_name": "My Timelapse",
    "rtsp_url": "rtsp://user:pass@camera-ip:554/stream",
    "base_output_dir": "./pics",
    "snapshot_interval": 60,
    "retention_days": 60,
    "ftp": {
        "enabled": True,
        "host": "ftp.example.com",
        "port": 21,
        "user": "ftpuser",
        "password": "ftppass",
        "remote_root": "/timelapse",
        "passive_mode": True,
        "upload_interval_minutes": 60
    }
}

def load_config():
    """Load configuration from file or exit with helpful message if missing"""
    if not os.path.exists(CONFIG_FILE):
        print(f"[ERROR] Config file not found: {CONFIG_FILE}")
        print(f"Please copy dashboard_config.example.json to {CONFIG_FILE} and edit it.")
        sys.exit(1)

    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            # Merge with defaults for any missing keys
            for key in DEFAULT_CONFIG:
                if key not in config:
                    config[key] = DEFAULT_CONFIG[key]
            if 'ftp' in config:
                for key in DEFAULT_CONFIG['ftp']:
                    if key not in config['ftp']:
                        config['ftp'][key] = DEFAULT_CONFIG['ftp'][key]
            return config
    except json.JSONDecodeError as e:
        print(f"[ERROR] Invalid JSON in {CONFIG_FILE}: {e}")
        sys.exit(1)

def save_config(config):
    """Save configuration to file"""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

# Load config at startup
config = load_config()

# Convenience accessors
def get_rtsp_url():
    return config.get('rtsp_url', DEFAULT_CONFIG['rtsp_url'])

def get_base_output_dir():
    return config.get('base_output_dir', DEFAULT_CONFIG['base_output_dir'])

def get_snapshot_interval():
    return config.get('snapshot_interval', DEFAULT_CONFIG['snapshot_interval'])

def get_retention_days():
    return config.get('retention_days', DEFAULT_CONFIG['retention_days'])

def get_ftp_config():
    return config.get('ftp', DEFAULT_CONFIG['ftp'])

def get_project_name():
    return config.get('project_name', DEFAULT_CONFIG['project_name'])

# === HELPER FUNCTIONS ===

def get_folder_stats(folder_path):
    """Get statistics about snapshots in a folder"""
    if not os.path.exists(folder_path):
        return {"count": 0, "size_mb": 0, "latest": None, "oldest": None}

    jpg_files = [f for f in os.listdir(folder_path) if f.lower().endswith(".jpg")]
    total_size = sum(os.path.getsize(os.path.join(folder_path, f)) for f in jpg_files)

    latest_file = None
    oldest_file = None
    if jpg_files:
        files_with_paths = [os.path.join(folder_path, f) for f in jpg_files]
        latest_file = max(files_with_paths, key=os.path.getmtime)
        oldest_file = min(files_with_paths, key=os.path.getmtime)

    return {
        "count": len(jpg_files),
        "size_mb": round(total_size / (1024 * 1024), 2),
        "latest": latest_file,
        "oldest": oldest_file
    }

def get_system_stats():
    """Get system-level statistics"""
    base_dir = get_base_output_dir()
    try:
        disk_usage = shutil.disk_usage(base_dir)
        disk_free_gb = round(disk_usage.free / (1024**3), 2)
        disk_total_gb = round(disk_usage.total / (1024**3), 2)
        disk_used_percent = round((disk_usage.used / disk_usage.total) * 100, 1)
    except:
        disk_free_gb = 0
        disk_total_gb = 0
        disk_used_percent = 0

    # Count total folders/days
    total_days = 0
    total_snapshots = 0
    total_size_mb = 0

    if os.path.exists(base_dir):
        for folder in os.listdir(base_dir):
            folder_path = os.path.join(base_dir, folder)
            if os.path.isdir(folder_path):
                try:
                    datetime.strptime(folder, "%Y-%m-%d")
                    total_days += 1
                    stats = get_folder_stats(folder_path)
                    total_snapshots += stats['count']
                    total_size_mb += stats['size_mb']
                except ValueError:
                    continue

    return {
        "disk_free_gb": disk_free_gb,
        "disk_total_gb": disk_total_gb,
        "disk_used_percent": disk_used_percent,
        "total_days": total_days,
        "total_snapshots": total_snapshots,
        "total_size_mb": round(total_size_mb, 2),
        "retention_days": get_retention_days(),
        "snapshot_interval": get_snapshot_interval()
    }

# === FTP FUNCTIONS ===

def get_ftp_upload_stats():
    """Get FTP upload statistics by counting .uploaded marker files"""
    base_dir = get_base_output_dir()
    stats = {
        "total_uploaded": 0,
        "total_pending": 0,
        "by_date": []
    }

    if not os.path.exists(base_dir):
        return stats

    for folder in sorted(os.listdir(base_dir), reverse=True)[:7]:  # Last 7 days
        folder_path = os.path.join(base_dir, folder)
        if os.path.isdir(folder_path):
            try:
                datetime.strptime(folder, "%Y-%m-%d")
                jpg_files = [f for f in os.listdir(folder_path) if f.lower().endswith(".jpg")]
                uploaded_markers = [f for f in os.listdir(folder_path) if f.endswith(".uploaded")]

                uploaded = len(uploaded_markers)
                pending = len(jpg_files) - uploaded

                stats["total_uploaded"] += uploaded
                stats["total_pending"] += pending
                stats["by_date"].append({
                    "date": folder,
                    "uploaded": uploaded,
                    "pending": max(0, pending),
                    "total": len(jpg_files)
                })
            except ValueError:
                continue

    return stats

def test_ftp_connection():
    """Test FTP connection with current settings"""
    ftp_conf = get_ftp_config()
    result = {
        "success": False,
        "message": "",
        "server_info": None,
        "remote_dirs": []
    }

    try:
        ftp = FTP()
        ftp.connect(ftp_conf['host'], ftp_conf.get('port', 21), timeout=10)
        ftp.login(ftp_conf['user'], ftp_conf['password'])

        if ftp_conf.get('passive_mode', True):
            ftp.set_pasv(True)

        result["server_info"] = ftp.getwelcome()

        # Try to list remote root directory
        try:
            ftp.cwd(ftp_conf['remote_root'])
            result["remote_dirs"] = ftp.nlst()[:20]  # Limit to 20 items
        except:
            result["remote_dirs"] = ["(could not list directory)"]

        ftp.quit()
        result["success"] = True
        result["message"] = "Connection successful"

    except Exception as e:
        result["message"] = str(e)

    return result

def get_ftp_remote_status():
    """Get status of files on FTP server"""
    ftp_conf = get_ftp_config()
    result = {
        "connected": False,
        "error": None,
        "folders": [],
        "total_files": 0
    }

    try:
        ftp = FTP()
        ftp.connect(ftp_conf['host'], ftp_conf.get('port', 21), timeout=10)
        ftp.login(ftp_conf['user'], ftp_conf['password'])

        if ftp_conf.get('passive_mode', True):
            ftp.set_pasv(True)

        # Navigate to remote root
        try:
            ftp.cwd(ftp_conf['remote_root'])
        except:
            ftp.mkd(ftp_conf['remote_root'])
            ftp.cwd(ftp_conf['remote_root'])

        # List date folders
        folders = []
        for item in sorted(ftp.nlst(), reverse=True)[:10]:  # Last 10 folders
            try:
                datetime.strptime(item, "%Y-%m-%d")
                ftp.cwd(item)
                files = [f for f in ftp.nlst() if f.lower().endswith('.jpg')]
                file_count = len(files)
                result["total_files"] += file_count
                folders.append({
                    "name": item,
                    "file_count": file_count
                })
                ftp.cwd("..")
            except:
                continue

        result["folders"] = folders
        result["connected"] = True
        ftp.quit()

    except Exception as e:
        result["error"] = str(e)

    return result

def trigger_ftp_upload(date_str=None):
    """Manually trigger FTP upload for a specific date or today"""
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    base_dir = get_base_output_dir()
    local_dir = os.path.join(base_dir, date_str)
    ftp_conf = get_ftp_config()

    if not os.path.exists(local_dir):
        return {"success": False, "error": f"Local directory not found: {date_str}"}

    result = {
        "success": False,
        "uploaded": 0,
        "skipped": 0,
        "failed": 0,
        "errors": []
    }

    try:
        ftp = FTP()
        ftp.connect(ftp_conf['host'], ftp_conf.get('port', 21), timeout=30)
        ftp.login(ftp_conf['user'], ftp_conf['password'])

        if ftp_conf.get('passive_mode', True):
            ftp.set_pasv(True)

        # Navigate to/create remote path
        remote_path = f"{ftp_conf['remote_root']}/{date_str}"
        for part in remote_path.strip("/").split("/"):
            try:
                ftp.cwd(part)
            except:
                try:
                    ftp.mkd(part)
                    ftp.cwd(part)
                except Exception as e:
                    result["errors"].append(f"Could not create directory {part}: {e}")

        # Upload files
        for fname in sorted(os.listdir(local_dir)):
            if not fname.lower().endswith(".jpg"):
                continue

            local_file = os.path.join(local_dir, fname)
            marker_file = local_file + ".uploaded"

            if os.path.exists(marker_file):
                result["skipped"] += 1
                continue

            try:
                with open(local_file, "rb") as f:
                    ftp.storbinary(f"STOR {fname}", f)
                # Create marker
                with open(marker_file, "w") as marker:
                    marker.write("uploaded\n")
                result["uploaded"] += 1
            except Exception as e:
                result["failed"] += 1
                result["errors"].append(f"{fname}: {str(e)}")

        ftp.quit()
        result["success"] = True

    except Exception as e:
        result["errors"].append(str(e))

    return result

def get_available_dates():
    """Get list of available date folders"""
    base_dir = get_base_output_dir()
    dates = []
    if os.path.exists(base_dir):
        for folder in sorted(os.listdir(base_dir), reverse=True):
            folder_path = os.path.join(base_dir, folder)
            if os.path.isdir(folder_path):
                try:
                    datetime.strptime(folder, "%Y-%m-%d")
                    stats = get_folder_stats(folder_path)
                    dates.append({
                        "date": folder,
                        "count": stats['count'],
                        "size_mb": stats['size_mb']
                    })
                except ValueError:
                    continue
    return dates

def get_snapshots_for_date(date_str, page=1, per_page=50):
    """Get paginated list of snapshots for a specific date"""
    folder_path = os.path.join(get_base_output_dir(), date_str)
    if not os.path.exists(folder_path):
        return {"snapshots": [], "total": 0, "page": page, "per_page": per_page}

    jpg_files = sorted(
        [f for f in os.listdir(folder_path) if f.lower().endswith(".jpg")],
        reverse=True
    )

    total = len(jpg_files)
    start = (page - 1) * per_page
    end = start + per_page

    snapshots = []
    for f in jpg_files[start:end]:
        file_path = os.path.join(folder_path, f)
        mtime = os.path.getmtime(file_path)
        snapshots.append({
            "filename": f,
            "timestamp": datetime.fromtimestamp(mtime).strftime("%H:%M:%S"),
            "size_kb": round(os.path.getsize(file_path) / 1024, 1)
        })

    return {
        "snapshots": snapshots,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page
    }

def take_manual_snapshot():
    """Take a snapshot on demand"""
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    output_dir = os.path.join(get_base_output_dir(), today_str)
    os.makedirs(output_dir, exist_ok=True)

    timestamp = now.strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(output_dir, f"snapshot_{timestamp}.jpg")

    try:
        subprocess.run([
            "ffmpeg",
            "-rtsp_transport", "tcp",
            "-i", get_rtsp_url(),
            "-t", "1",
            "-frames:v", "1",
            "-loglevel", "error",
            "-y",
            filename
        ], check=True, timeout=15, capture_output=True)

        if os.path.exists(filename):
            return {"success": True, "filename": os.path.basename(filename), "date": today_str}
        else:
            return {"success": False, "error": "Snapshot file not created"}
    except subprocess.CalledProcessError as e:
        return {"success": False, "error": f"FFmpeg error: {e.stderr.decode() if e.stderr else str(e)}"}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Capture timed out"}
    except Exception as e:
        return {"success": False, "error": str(e)}

# === API ROUTES ===

@app.route('/')
def index():
    """Serve the main dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/status')
def api_status():
    """Get current system status"""
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    today_dir = os.path.join(get_base_output_dir(), today_str)

    today_stats = get_folder_stats(today_dir)
    system_stats = get_system_stats()

    # Calculate expected snapshots for today so far
    seconds_today = now.hour * 3600 + now.minute * 60 + now.second
    expected_today = seconds_today // get_snapshot_interval()

    return jsonify({
        "project_name": get_project_name(),
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
        "today": {
            "date": today_str,
            "snapshots": today_stats['count'],
            "expected": expected_today,
            "size_mb": today_stats['size_mb'],
            "capture_rate": round((today_stats['count'] / max(expected_today, 1)) * 100, 1)
        },
        "system": system_stats,
        "latest_snapshot": os.path.basename(today_stats['latest']) if today_stats['latest'] else None
    })

@app.route('/api/dates')
def api_dates():
    """Get list of available dates"""
    return jsonify(get_available_dates())

@app.route('/api/snapshots/<date_str>')
def api_snapshots(date_str):
    """Get snapshots for a specific date"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    return jsonify(get_snapshots_for_date(date_str, page, per_page))

@app.route('/api/snapshot/take', methods=['POST'])
def api_take_snapshot():
    """Take a manual snapshot"""
    result = take_manual_snapshot()
    return jsonify(result)

@app.route('/api/image/<date_str>/<filename>')
def api_image(date_str, filename):
    """Serve an image file"""
    file_path = os.path.join(get_base_output_dir(), date_str, filename)
    if os.path.exists(file_path) and filename.lower().endswith('.jpg'):
        return send_file(file_path, mimetype='image/jpeg')
    return jsonify({"error": "Image not found"}), 404

@app.route('/api/latest')
def api_latest():
    """Get the most recent snapshot"""
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    today_dir = os.path.join(get_base_output_dir(), today_str)

    stats = get_folder_stats(today_dir)
    if stats['latest']:
        return send_file(stats['latest'], mimetype='image/jpeg')

    return jsonify({"error": "No snapshots available"}), 404

# === FTP API ROUTES ===

@app.route('/api/ftp/status')
def api_ftp_status():
    """Get FTP upload status and statistics"""
    ftp_conf = get_ftp_config()
    upload_stats = get_ftp_upload_stats()

    return jsonify({
        "enabled": ftp_conf.get('enabled', True),
        "config": {
            "host": ftp_conf['host'],
            "port": ftp_conf.get('port', 21),
            "user": ftp_conf['user'],
            "remote_root": ftp_conf['remote_root'],
            "passive_mode": ftp_conf.get('passive_mode', True),
            "upload_interval": ftp_conf.get('upload_interval_minutes', 60)
        },
        "uploads": upload_stats
    })

@app.route('/api/ftp/test', methods=['POST'])
def api_ftp_test():
    """Test FTP connection"""
    return jsonify(test_ftp_connection())

@app.route('/api/ftp/remote')
def api_ftp_remote():
    """Get FTP remote server status"""
    return jsonify(get_ftp_remote_status())

@app.route('/api/ftp/upload', methods=['POST'])
def api_ftp_upload():
    """Trigger manual FTP upload"""
    data = request.get_json() or {}
    date_str = data.get('date')
    return jsonify(trigger_ftp_upload(date_str))

@app.route('/api/ftp/config', methods=['GET'])
def api_ftp_config_get():
    """Get FTP configuration"""
    ftp_conf = get_ftp_config()
    # Return config without password for security
    return jsonify({
        "enabled": ftp_conf.get('enabled', True),
        "host": ftp_conf['host'],
        "port": ftp_conf.get('port', 21),
        "user": ftp_conf['user'],
        "password": "********",  # Masked
        "remote_root": ftp_conf['remote_root'],
        "passive_mode": ftp_conf.get('passive_mode', True),
        "upload_interval_minutes": ftp_conf.get('upload_interval_minutes', 60)
    })

@app.route('/api/ftp/config', methods=['POST'])
def api_ftp_config_save():
    """Save FTP configuration"""
    global config
    data = request.get_json()

    if not data:
        return jsonify({"success": False, "error": "No data provided"}), 400

    # Update FTP config
    ftp_conf = config.get('ftp', {})
    if 'enabled' in data:
        ftp_conf['enabled'] = bool(data['enabled'])
    if 'host' in data:
        ftp_conf['host'] = data['host']
    if 'port' in data:
        ftp_conf['port'] = int(data['port'])
    if 'user' in data:
        ftp_conf['user'] = data['user']
    if 'password' in data and data['password'] != '********':
        ftp_conf['password'] = data['password']
    if 'remote_root' in data:
        ftp_conf['remote_root'] = data['remote_root']
    if 'passive_mode' in data:
        ftp_conf['passive_mode'] = bool(data['passive_mode'])
    if 'upload_interval_minutes' in data:
        ftp_conf['upload_interval_minutes'] = int(data['upload_interval_minutes'])

    config['ftp'] = ftp_conf
    save_config(config)

    return jsonify({"success": True, "message": "Configuration saved"})

@app.route('/api/project-name', methods=['POST'])
def api_project_name_save():
    """Save project name"""
    global config
    data = request.get_json()

    if not data or 'name' not in data:
        return jsonify({"success": False, "error": "No name provided"}), 400

    config['project_name'] = data['name'].strip()
    save_config(config)

    return jsonify({"success": True, "name": config['project_name']})

# === MAIN ===

if __name__ == '__main__':
    # Create templates and static directories if they don't exist
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)

    print("=" * 50)
    print(f"{get_project_name()} - Web Dashboard")
    print("=" * 50)
    print(f"Starting server at http://localhost:5050")
    print("=" * 50)

    app.run(host='0.0.0.0', port=5050, debug=True)
