#!/usr/bin/env python3
"""
Status page web server for the Japanese Accommodation Availability Checker
Provides real-time monitoring and historical data visualization
"""
import asyncio
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from pathlib import Path
import pytz

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_config
from status_tracker import StatusTracker

# Japan timezone
JST = pytz.timezone('Asia/Tokyo')

app = FastAPI(title="Ryokan Status Dashboard", description="📊 Real-time accommodation tracking status")

# Setup static files and templates
static_dir = Path(__file__).parent / "static"
templates_dir = Path(__file__).parent / "templates" 
static_dir.mkdir(exist_ok=True)
templates_dir.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
templates = Jinja2Templates(directory=str(templates_dir))

# Global status tracker
status_tracker = None

@app.on_event("startup")
async def startup_event():
    global status_tracker
    try:
        config = load_config()
        status_tracker = StatusTracker(config)
        await status_tracker.initialize()
        print("🌸 Status tracker initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize status tracker: {e}")
        status_tracker = None

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main status dashboard page"""
    if not status_tracker:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Status tracker not initialized"
        })
    
    # Get current JST time
    current_jst = datetime.now(JST)
    
    context = {
        "request": request,
        "page_title": "🏯 Ryokan Tracker Dashboard",
        "current_time": current_jst.strftime("%Y-%m-%d %H:%M:%S JST"),
    }
    
    return templates.TemplateResponse("dashboard.html", context)

@app.get("/api/status")
async def get_status():
    """Get current system status"""
    if not status_tracker:
        return JSONResponse({"error": "Status tracker not available"}, status_code=503)
    
    return await status_tracker.get_current_status()

@app.get("/api/history")
async def get_history(hours: int = 24):
    """Get availability history for the specified number of hours"""
    if not status_tracker:
        return JSONResponse({"error": "Status tracker not available"}, status_code=503)
    
    return await status_tracker.get_history(hours)

@app.get("/api/accommodations")
async def get_accommodations():
    """Get list of tracked accommodations with their current status"""
    if not status_tracker:
        return JSONResponse({"error": "Status tracker not available"}, status_code=503)
    
    return await status_tracker.get_accommodations_status()

@app.get("/api/metrics")
async def get_metrics():
    """Get system metrics and performance data"""
    if not status_tracker:
        return JSONResponse({"error": "Status tracker not available"}, status_code=503)
    
    return await status_tracker.get_metrics()

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    if not status_tracker:
        return JSONResponse({
            "status": "unhealthy",
            "message": "Status tracker not initialized",
            "timestamp": datetime.now().isoformat()
        }, status_code=503)
    
    health_status = await status_tracker.health_check()
    status_code = 200 if health_status["status"] == "healthy" else 503
    
    return JSONResponse(health_status, status_code=status_code)

@app.post("/api/test-notification")
async def test_notification():
    """Trigger a test notification"""
    if not status_tracker:
        return JSONResponse({"error": "Status tracker not available"}, status_code=503)
    
    result = await status_tracker.test_notification()
    return JSONResponse(result)

@app.post("/api/check-now")
async def check_now():
    """Manually trigger an availability check"""
    if not status_tracker:
        return JSONResponse({"error": "Status tracker not available"}, status_code=503)
    
    try:
        # Import here to avoid circular imports
        from scrapers import ShirakawaScraper
        from notifications import NotificationClient
        import time
        
        # Initialize scraper and notification client
        config = load_config()
        scraper = ShirakawaScraper(timeout_seconds=config.timeout_seconds)
        notification_client = NotificationClient(
            endpoint_url=str(config.notification_endpoint),
            timeout_seconds=config.timeout_seconds,
            retry_attempts=config.retry_attempts
        )
        
        # Record check start
        check_id = await status_tracker.record_check_start()
        start_time = time.time()
        error = None
        results = []
        
        try:
            # Perform the check
            results = await scraper.check_availability(config.target_dates)
            
            if results:
                # Send notifications
                success_count = await notification_client.send_notifications(results)
                
                # Record notification success
                for result in results:
                    await status_tracker.record_notification_sent(
                        result.accommodation_name, 
                        success_count > 0
                    )
        
        except Exception as e:
            error = str(e)
        
        finally:
            # Record check completion
            duration = time.time() - start_time
            await status_tracker.record_check_complete(
                check_id, results, duration, error
            )
            
            # Cleanup scraper
            await scraper.cleanup()
        
        if error:
            return JSONResponse({
                "success": False,
                "message": f"Check failed: {error}",
                "timestamp": datetime.now(JST).isoformat(),
                "check_id": check_id
            }, status_code=500)
        else:
            return JSONResponse({
                "success": True,
                "message": f"Manual check completed! Found {len(results)} accommodations with availability",
                "timestamp": datetime.now(JST).isoformat(),
                "check_id": check_id,
                "results_count": len(results),
                "availabilities_count": sum(len(r.available_dates) for r in results)
            })
            
    except Exception as e:
        return JSONResponse({
            "success": False,
            "message": f"Failed to trigger check: {str(e)}",
            "timestamp": datetime.now(JST).isoformat()
        }, status_code=500)

@app.get("/api/config")
async def get_config():
    """Get current configuration (sanitized)"""
    try:
        config = load_config()
        return JSONResponse({
            "target_dates": config.target_dates,
            "notification_endpoint": str(config.notification_endpoint),
            "log_level": config.log_level,
            "check_interval_seconds": config.check_interval_seconds,
            "retry_attempts": config.retry_attempts,
            "timeout_seconds": config.timeout_seconds,
            "timestamp": datetime.now(JST).isoformat()
        })
    except Exception as e:
        return JSONResponse({
            "error": f"Failed to load configuration: {str(e)}",
            "timestamp": datetime.now(JST).isoformat()
        }, status_code=500)

def main():
    """Run the status server"""
    print("🌸 Starting Ryokan Status Dashboard...")
    print("📊 Dashboard will be available at: http://localhost:8000")
    
    uvicorn.run(
        "status_server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )

if __name__ == "__main__":
    main()