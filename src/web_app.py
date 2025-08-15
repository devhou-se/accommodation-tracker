from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from datetime import datetime
from typing import Optional
from .scheduler import TicketScheduler
from .config import AppConfig


class WebApp:
    """Web dashboard for the ticket availability service"""
    
    def __init__(self, scheduler: TicketScheduler, config: AppConfig):
        self.scheduler = scheduler
        self.config = config
        self.app = FastAPI(title="Ticket Availability Tracker")
        self.templates = Jinja2Templates(directory="src/templates")
        
        # Setup routes
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup web routes"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def dashboard(request: Request):
            """Main dashboard page"""
            plugin_status = self.scheduler.get_plugin_status()
            recent_results = self.scheduler.get_recent_results(limit=20)
            
            return self.templates.TemplateResponse("dashboard.html", {
                "request": request,
                "plugin_status": plugin_status,
                "recent_results": recent_results,
                "current_time": datetime.now()
            })
        
        @self.app.get("/api/status")
        async def api_status():
            """API endpoint for status"""
            return {
                "scheduler_running": self.scheduler.running,
                "plugins": self.scheduler.get_plugin_status(),
                "recent_checks": len(self.scheduler.check_history),
                "current_time": datetime.now().isoformat()
            }
        
        @self.app.get("/api/results")
        async def api_results(limit: int = 50):
            """API endpoint for recent results"""
            results = self.scheduler.get_recent_results(limit=limit)
            return [self._serialize_result(result) for result in results]
        
        @self.app.post("/api/check/{plugin_name}")
        async def api_manual_check(plugin_name: str):
            """API endpoint for manual check"""
            results = await self.scheduler.run_manual_check(plugin_name)
            if not results:
                raise HTTPException(status_code=404, detail="Plugin not found")
            return [self._serialize_result(result) for result in results]
        
        @self.app.post("/api/check-all")
        async def api_check_all():
            """API endpoint to check all plugins"""
            results = await self.scheduler.run_manual_check()
            return [self._serialize_result(result) for result in results]
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {"status": "healthy", "timestamp": datetime.now().isoformat()}
    
    def _serialize_result(self, result):
        """Serialize CheckResult for JSON response"""
        return {
            "plugin_name": result.plugin_name,
            "event_name": result.event_name,
            "check_time": result.check_time.isoformat(),
            "success": result.success,
            "error_message": result.error_message,
            "availabilities": [
                {
                    "date": a.date,
                    "seat_type": a.seat_type,
                    "status": a.status,
                    "price": a.price,
                    "booking_url": a.booking_url,
                    "venue": a.venue
                }
                for a in result.availabilities
            ]
        }