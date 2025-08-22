from flask import Flask, request, jsonify
import json
import time
import os
import threading
from datetime import datetime

app = Flask(__name__)

# Global storage for ESP data
espa_storage = []
permanent_history = []
TIME_LIMIT = 120  # 2 minutes

def cleanup_old_data():
    """Remove devices that haven't sent data for more than 120 seconds"""
    current_time = time.time()
    global espa_storage
    espa_storage = [entry for entry in espa_storage if current_time - entry.get('timestamp', 0) < TIME_LIMIT]

def format_timestamp(timestamp):
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

@app.route('/', methods=['GET'])
def root():
    return jsonify({
        "status": "ESP BLE Server is running",
        "endpoints": {
            "POST /data/espa": "Send BLE data",
            "GET /data/espa": "Get current BLE data",
            "GET /data/history/espa": "Get all history"
        },
        "active_devices": len(espa_storage)
    })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_devices": len(espa_storage)
    })

@app.route('/data/espa', methods=['GET'])
def get_espa_data():
    cleanup_old_data()
    return jsonify({
        "esp_type": "ESPA",
        "active_devices": len(espa_storage),
        "devices": espa_storage,
        "timestamp": datetime.now().isoformat()
    }), 200

@app.route('/data/espa', methods=['POST'])
def post_espa_data():
    try:
        # Try to parse JSON
        incoming_data = request.get_json(silent=True)
        if incoming_data is None:
            # Fallback for non-JSON data
            incoming_data = {"raw_body": request.data.decode('utf-8')}

        log_entry = {
            "esp_type": "ESPA",
            "timestamp": time.time(),
            "formatted_timestamp": format_timestamp(time.time()),
            "data": incoming_data
        }

        # Store in both active and permanent storage
        espa_storage.append(log_entry)
        permanent_history.append(log_entry)
        
        # Clean up old data
        cleanup_old_data()

        print(f"✅ Received ESPA data: {incoming_data}")

        return jsonify({
            "status": "success",
            "message": "ESPA data received",
            "received": incoming_data,
            "timestamp": log_entry["formatted_timestamp"]
        }), 200

    except Exception as e:
        print(f"❌ Error processing ESPA data: {str(e)}")
        return jsonify({
            "status": "error", 
            "message": str(e)
        }), 400

@app.route('/data/history/espa', methods=['GET'])
def get_espa_history():
    history_sorted = sorted(permanent_history, key=lambda x: x['timestamp'], reverse=True)
    return jsonify({
        "esp_type": "ESPA",
        "total_logs": len(history_sorted),
        "logs": history_sorted
    }), 200

# Background cleanup thread
def background_cleanup():
    while True:
        time.sleep(30)  # Run every 30 seconds
        cleanup_old_data()

cleanup_thread = threading.Thread(target=background_cleanup, daemon=True)
cleanup_thread.start()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
