"""
WSGI Entry Point for Railway
Simple web server for health checks
"""

import os
from flask import Flask, jsonify
from threading import Thread
import time

app = Flask(__name__)

# Startup time for uptime calculation
STARTUP_TIME = time.time()

@app.route('/')
def home():
    """Main page"""
    uptime = time.time() - STARTUP_TIME
    hours = int(uptime // 3600)
    minutes = int((uptime % 3600) // 60)
    seconds = int(uptime % 60)
    
    return {
        "service": "vechnost-autopost-bot",
        "status": "online",
        "uptime": f"{hours}h {minutes}m {seconds}s",
        "version": "2.0",
        "environment": os.getenv("RAILWAY_ENVIRONMENT", "production")
    }

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200

@app.route('/metrics')
def metrics():
    """Metrics endpoint"""
    return jsonify({
        "status": "online",
        "timestamp": time.time(),
        "memory_usage": "N/A",  # Could add psutil for real metrics
        "requests_served": 0
    })

def run_web_server():
    """Run Flask web server"""
    port = int(os.getenv("PORT", 8080))
    print(f"🌐 Starting web server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == "__main__":
    run_web_server()
