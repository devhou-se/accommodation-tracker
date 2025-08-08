#!/usr/bin/env python3
"""
Status tracking system for the accommodation checker
Maintains run history, availability data, and system metrics
"""
import asyncio
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import structlog
import aiofiles
import aiosqlite
import pytz

from config.schema import Config
from scrapers.base import AccommodationResult
from notifications.client import NotificationClient

# Japan timezone for consistent timestamps
JST = pytz.timezone('Asia/Tokyo')

logger = structlog.get_logger(__name__)

class StatusTracker:
    """Tracks system status, availability history, and performance metrics"""
    
    def __init__(self, config: Config, db_path: str = "/app/data/status.db"):
        self.config = config
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.current_status = {
            "last_check": None,
            "status": "starting",
            "message": "System initializing...",
            "checks_today": 0,
            "errors_today": 0,
            "availabilities_found": 0,
            "accommodations_checked": 0,
            "uptime_start": datetime.now(JST).isoformat()
        }
        
        self.metrics = {
            "total_checks": 0,
            "successful_checks": 0,
            "failed_checks": 0,
            "notifications_sent": 0,
            "average_check_duration": 0.0,
            "last_availability_found": None
        }
    
    async def initialize(self):
        """Initialize the database and load existing data"""
        try:
            await self._setup_database()
            await self._load_metrics()
            logger.info("Status tracker initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize status tracker", error=str(e))
            raise
    
    async def _setup_database(self):
        """Setup SQLite database for storing status and history"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS check_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    status TEXT NOT NULL,
                    accommodations_checked INTEGER DEFAULT 0,
                    availabilities_found INTEGER DEFAULT 0,
                    duration_seconds REAL DEFAULT 0,
                    error_message TEXT,
                    target_dates TEXT
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS availability_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    accommodation_name TEXT NOT NULL,
                    available_dates TEXT NOT NULL,
                    link TEXT NOT NULL,
                    location TEXT NOT NULL,
                    price_info TEXT,
                    notification_sent BOOLEAN DEFAULT 0
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS system_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    metadata TEXT
                )
            """)
            
            await db.commit()
    
    async def _load_metrics(self):
        """Load existing metrics from database"""
        async with aiosqlite.connect(self.db_path) as db:
            # Load basic metrics
            cursor = await db.execute("SELECT COUNT(*) FROM check_runs")
            self.metrics["total_checks"] = (await cursor.fetchone())[0]
            
            cursor = await db.execute("SELECT COUNT(*) FROM check_runs WHERE status = 'success'")
            self.metrics["successful_checks"] = (await cursor.fetchone())[0]
            
            cursor = await db.execute("SELECT COUNT(*) FROM availability_history")
            total_availabilities = (await cursor.fetchone())[0]
            
            # Update current status
            cursor = await db.execute("""
                SELECT timestamp, accommodations_checked, availabilities_found 
                FROM check_runs 
                ORDER BY timestamp DESC 
                LIMIT 1
            """)
            last_run = await cursor.fetchone()
            if last_run:
                self.current_status["last_check"] = last_run[0]
                self.current_status["accommodations_checked"] = last_run[1] or 0
                
            # Get today's stats
            today = datetime.now(JST).strftime("%Y-%m-%d")
            cursor = await db.execute("""
                SELECT COUNT(*) FROM check_runs 
                WHERE date(timestamp) = ?
            """, (today,))
            self.current_status["checks_today"] = (await cursor.fetchone())[0]
            
            cursor = await db.execute("""
                SELECT COUNT(*) FROM availability_history 
                WHERE date(timestamp) = ?
            """, (today,))
            self.current_status["availabilities_found"] = (await cursor.fetchone())[0]
    
    async def record_check_start(self) -> str:
        """Record the start of a new check cycle"""
        check_id = datetime.now(JST).isoformat()
        
        self.current_status.update({
            "status": "running",
            "message": "🔄 Checking accommodations...",
            "last_check": check_id
        })
        
        logger.info("Check cycle started", check_id=check_id)
        return check_id
    
    async def record_check_complete(self, check_id: str, results: List[AccommodationResult], 
                                  duration: float, error: Optional[str] = None):
        """Record completion of a check cycle"""
        status = "success" if not error else "error"
        accommodations_checked = len(results) if not error else 0
        availabilities_found = sum(len(r.available_dates) for r in results) if results else 0
        
        # Update current status
        self.current_status.update({
            "status": "idle" if not error else "error",
            "message": f"✅ Last check: {accommodations_checked} accommodations, {availabilities_found} availabilities found" if not error 
                      else f"❌ Error: {error}",
            "accommodations_checked": accommodations_checked,
            "checks_today": self.current_status.get("checks_today", 0) + 1,
            "errors_today": self.current_status.get("errors_today", 0) + (1 if error else 0)
        })
        
        # Update metrics
        self.metrics["total_checks"] += 1
        if not error:
            self.metrics["successful_checks"] += 1
        else:
            self.metrics["failed_checks"] += 1
        
        # Store in database
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO check_runs 
                (timestamp, status, accommodations_checked, availabilities_found, duration_seconds, error_message, target_dates)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                check_id, status, accommodations_checked, availabilities_found, 
                duration, error, json.dumps(self.config.target_dates)
            ))
            
            # Store availability results
            for result in results:
                if result.available_dates:  # Only store if there are available dates
                    await db.execute("""
                        INSERT INTO availability_history
                        (timestamp, accommodation_name, available_dates, link, location, price_info)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        check_id, result.accommodation_name, json.dumps(result.available_dates),
                        result.link, result.location, result.price_info
                    ))
                    
                    self.metrics["last_availability_found"] = check_id
            
            await db.commit()
        
        logger.info("Check cycle completed", 
                   check_id=check_id, 
                   status=status,
                   accommodations=accommodations_checked,
                   availabilities=availabilities_found,
                   duration=duration)
    
    async def record_notification_sent(self, accommodation_name: str, success: bool):
        """Record that a notification was sent"""
        if success:
            self.metrics["notifications_sent"] += 1
            
        # Update database to mark notification as sent
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE availability_history 
                SET notification_sent = ? 
                WHERE accommodation_name = ? AND notification_sent = 0
                ORDER BY timestamp DESC 
                LIMIT 1
            """, (1 if success else 0, accommodation_name))
            await db.commit()
    
    async def get_current_status(self) -> Dict[str, Any]:
        """Get current system status"""
        uptime_start = datetime.fromisoformat(self.current_status["uptime_start"])
        # Handle timezone-aware comparison
        current_time = datetime.now(JST)
        if uptime_start.tzinfo is None:
            uptime_start = JST.localize(uptime_start)
        uptime_seconds = (current_time - uptime_start).total_seconds()
        
        return {
            **self.current_status,
            "uptime_seconds": uptime_seconds,
            "uptime_human": self._format_duration(uptime_seconds),
            "target_dates": self.config.target_dates,
            "check_interval": self.config.check_interval_seconds,
            "notification_endpoint": str(self.config.notification_endpoint),
            "metrics": self.metrics
        }
    
    async def get_history(self, hours: int = 24) -> Dict[str, Any]:
        """Get availability history for the specified time period"""
        since = datetime.now(JST) - timedelta(hours=hours)
        since_str = since.isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            # Get check runs
            cursor = await db.execute("""
                SELECT timestamp, status, accommodations_checked, availabilities_found, duration_seconds, error_message
                FROM check_runs 
                WHERE timestamp > ?
                ORDER BY timestamp DESC
            """, (since_str,))
            
            check_runs = []
            async for row in cursor:
                check_runs.append({
                    "timestamp": row[0],
                    "status": row[1],
                    "accommodations_checked": row[2] or 0,
                    "availabilities_found": row[3] or 0,
                    "duration_seconds": row[4] or 0,
                    "error_message": row[5]
                })
            
            # Get availability discoveries
            cursor = await db.execute("""
                SELECT timestamp, accommodation_name, available_dates, link, location, price_info, notification_sent
                FROM availability_history 
                WHERE timestamp > ?
                ORDER BY timestamp DESC
            """, (since_str,))
            
            discoveries = []
            async for row in cursor:
                discoveries.append({
                    "timestamp": row[0],
                    "accommodation_name": row[1],
                    "available_dates": json.loads(row[2]) if row[2] else [],
                    "link": row[3],
                    "location": row[4],
                    "price_info": row[5],
                    "notification_sent": bool(row[6])
                })
        
        return {
            "period_hours": hours,
            "check_runs": check_runs,
            "discoveries": discoveries,
            "summary": {
                "total_runs": len(check_runs),
                "successful_runs": len([r for r in check_runs if r["status"] == "success"]),
                "total_discoveries": len(discoveries),
                "accommodations_with_availability": len(set(d["accommodation_name"] for d in discoveries))
            }
        }
    
    async def get_accommodations_status(self) -> Dict[str, Any]:
        """Get current status of all tracked accommodations"""
        # This would typically come from the last scraper run
        # For now, we'll return a summary based on recent history
        
        async with aiosqlite.connect(self.db_path) as db:
            # Get recent availability for each accommodation
            cursor = await db.execute("""
                SELECT accommodation_name, 
                       MAX(timestamp) as last_seen,
                       available_dates,
                       link,
                       location
                FROM availability_history 
                WHERE timestamp > ?
                GROUP BY accommodation_name
                ORDER BY accommodation_name
            """, ((datetime.now(JST) - timedelta(days=7)).isoformat(),))
            
            accommodations = []
            async for row in cursor:
                accommodations.append({
                    "name": row[0],
                    "last_availability": row[1],
                    "recent_dates": json.loads(row[2]) if row[2] else [],
                    "link": row[3],
                    "location": row[4],
                    "status": "available" if row[2] else "no_availability"
                })
        
        return {
            "accommodations": accommodations,
            "total_tracked": len(accommodations),
            "with_recent_availability": len([a for a in accommodations if a["recent_dates"]])
        }
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get detailed system metrics"""
        async with aiosqlite.connect(self.db_path) as db:
            # Calculate average check duration
            cursor = await db.execute("""
                SELECT AVG(duration_seconds) 
                FROM check_runs 
                WHERE status = 'success' AND duration_seconds > 0
            """)
            avg_duration = await cursor.fetchone()
            if avg_duration and avg_duration[0]:
                self.metrics["average_check_duration"] = float(avg_duration[0])
            
            # Get hourly success rate for last 24 hours
            cursor = await db.execute("""
                SELECT 
                    strftime('%H', timestamp) as hour,
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful
                FROM check_runs 
                WHERE timestamp > ?
                GROUP BY strftime('%H', timestamp)
                ORDER BY hour
            """, ((datetime.now(JST) - timedelta(hours=24)).isoformat(),))
            
            hourly_stats = []
            async for row in cursor:
                success_rate = (row[2] / row[1] * 100) if row[1] > 0 else 0
                hourly_stats.append({
                    "hour": int(row[0]),
                    "total_checks": row[1],
                    "successful_checks": row[2],
                    "success_rate": round(success_rate, 1)
                })
        
        return {
            **self.metrics,
            "hourly_stats": hourly_stats,
            "success_rate": round((self.metrics["successful_checks"] / max(self.metrics["total_checks"], 1)) * 100, 1)
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now(JST).isoformat(),
            "checks": {}
        }
        
        # Check database connectivity
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("SELECT 1")
            health_status["checks"]["database"] = "ok"
        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["checks"]["database"] = f"error: {str(e)}"
        
        # Check if we've had recent successful checks
        if self.current_status["last_check"]:
            last_check = datetime.fromisoformat(self.current_status["last_check"])
            # Handle timezone-aware comparison
            if last_check.tzinfo is None:
                last_check = JST.localize(last_check)
            time_since_check = datetime.now(JST) - last_check
            
            if time_since_check > timedelta(minutes=self.config.check_interval_seconds / 60 * 2):
                health_status["status"] = "warning"
                health_status["checks"]["recent_activity"] = f"warning: last check {self._format_duration(time_since_check.total_seconds())} ago"
            else:
                health_status["checks"]["recent_activity"] = "ok"
        else:
            health_status["checks"]["recent_activity"] = "warning: no checks recorded"
        
        # Check error rate
        error_rate = (self.current_status.get("errors_today", 0) / max(self.current_status.get("checks_today", 1), 1)) * 100
        if error_rate > 50:
            health_status["status"] = "unhealthy"
            health_status["checks"]["error_rate"] = f"high: {error_rate:.1f}%"
        elif error_rate > 25:
            health_status["status"] = "warning"  
            health_status["checks"]["error_rate"] = f"elevated: {error_rate:.1f}%"
        else:
            health_status["checks"]["error_rate"] = f"ok: {error_rate:.1f}%"
        
        return health_status
    
    async def test_notification(self) -> Dict[str, Any]:
        """Send a test notification"""
        try:
            from scrapers.base import AccommodationResult
            
            test_result = AccommodationResult(
                accommodation_name="🏯 Test Ryokan",
                available_dates=["2025-12-25"],
                link="https://example.com/test",
                location="Test Location, Shirakawa-go",
                discovered_at=datetime.now(JST).isoformat()
            )
            
            client = NotificationClient(str(self.config.notification_endpoint))
            success = await client.send_notification(test_result)
            
            await self.record_notification_sent("Test Ryokan", success)
            
            return {
                "success": success,
                "message": "Test notification sent successfully!" if success else "Test notification failed",
                "timestamp": datetime.now(JST).isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Test notification failed: {str(e)}",
                "timestamp": datetime.now(JST).isoformat()
            }
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in human readable format"""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds // 60)}m {int(seconds % 60)}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"