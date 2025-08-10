#!/usr/bin/env python3
"""
Quick start script for the Gassho-zukuri Checker with Status Dashboard
"""
import asyncio
import subprocess
import sys
import time
import json
import webbrowser
from pathlib import Path

def print_banner():
    print("""
🏯  ====================================  🏯
    GASSHO-ZUKURI ACCOMMODATION TRACKER
         WITH STATUS DASHBOARD
🏯  ====================================  🏯

Starting services:
• Main accommodation checker
• Web status dashboard 
• Mock notification endpoint

Dashboard will be available at: http://localhost:8000
""")

def check_config():
    """Check if configuration file exists"""
    config_file = Path("config.json")
    if not config_file.exists():
        print("⚠️  Configuration file not found!")
        print("Creating config.json from example...")
        
        example_config = Path("config.example.json")
        if example_config.exists():
            # Copy example config
            config_content = example_config.read_text()
            config_file.write_text(config_content)
            print("✅ Created config.json from example")
            print("🔧 Please edit config.json with your notification endpoint")
        else:
            print("❌ No config.example.json found!")
            return False
    
    # Validate config
    try:
        with open(config_file) as f:
            config = json.load(f)
        
        required_fields = ["target_dates", "notification_endpoint"]
        for field in required_fields:
            if field not in config:
                print(f"❌ Missing required field '{field}' in config.json")
                return False
        
        print(f"✅ Configuration valid")
        print(f"   Target dates: {', '.join(config['target_dates'])}")
        print(f"   Notification endpoint: {config['notification_endpoint']}")
        return True
        
    except Exception as e:
        print(f"❌ Error reading config.json: {e}")
        return False

def start_docker_services():
    """Start Docker services with dashboard"""
    print("\n🐳 Starting Docker services...")
    
    try:
        # Build and start services
        subprocess.run([
            "docker", "compose", "-f", "docker-compose.with-dashboard.yml", 
            "up", "--build", "-d"
        ], check=True)
        
        print("✅ Services started successfully!")
        
        # Wait a moment for services to initialize
        print("\n⏳ Waiting for services to initialize...")
        time.sleep(10)
        
        # Check service health
        check_service_health()
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start services: {e}")
        return False

def check_service_health():
    """Check if services are healthy"""
    services = [
        ("Dashboard", "http://localhost:8000/api/health"),
        ("Mock Notification", "http://localhost:8082/health")
    ]
    
    print("\n🏥 Checking service health...")
    
    for service_name, health_url in services:
        try:
            import urllib.request
            with urllib.request.urlopen(health_url, timeout=5) as response:
                if response.status == 200:
                    print(f"✅ {service_name}: Healthy")
                else:
                    print(f"⚠️  {service_name}: Unhealthy (HTTP {response.status})")
        except Exception as e:
            print(f"❌ {service_name}: Failed to check health - {e}")

def show_service_info():
    """Show information about running services"""
    print("""
🎌 =====================================
           SERVICES RUNNING
🎌 =====================================

📊 Status Dashboard:
   URL: http://localhost:8000
   Features:
   • Real-time system status
   • Availability history 
   • Performance metrics
   • Interactive charts
   • Test notifications

🔔 Mock Notification Server:
   URL: http://localhost:8082
   Endpoints:
   • POST /notify - Receive notifications
   • GET /notifications - View all notifications
   • GET /health - Health check

🏯 Main Accommodation Checker:
   Running in background
   Checking Shirakawa-go accommodations
   Sending notifications when available

🎌 =====================================

Commands:
• View logs: docker compose -f docker-compose.with-dashboard.yml logs -f
• Stop services: docker compose -f docker-compose.with-dashboard.yml down
• Restart: docker compose -f docker-compose.with-dashboard.yml restart

Opening dashboard in browser...
""")

def open_dashboard():
    """Open the dashboard in the default browser"""
    try:
        webbrowser.open("http://localhost:8000")
    except Exception as e:
        print(f"⚠️  Could not open browser automatically: {e}")
        print("   Please visit http://localhost:8000 manually")

def main():
    """Main function"""
    print_banner()
    
    # Check configuration
    if not check_config():
        print("\n❌ Configuration check failed!")
        print("   Please fix the configuration and try again")
        sys.exit(1)
    
    # Start services
    if not start_docker_services():
        print("\n❌ Failed to start services!")
        sys.exit(1)
    
    # Show service info
    show_service_info()
    
    # Open dashboard
    time.sleep(2)
    open_dashboard()
    
    print("\n🎉 All services are running!")
    print("   Press Ctrl+C to stop when you're done testing")
    
    try:
        # Keep script running so user can see status
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping services...")
        subprocess.run([
            "docker", "compose", "-f", "docker-compose.with-dashboard.yml", "down"
        ])
        print("✅ Services stopped successfully!")

if __name__ == "__main__":
    main()