import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List
from .config import AppConfig
from .plugins import create_plugin
from .email_service import EmailService
from .plugins.base import CheckResult


class TicketScheduler:
    """Manages scheduled ticket availability checks"""
    
    def __init__(self, config: AppConfig, email_service: EmailService):
        self.config = config
        self.email_service = email_service
        self.plugins = []
        self.check_history: List[CheckResult] = []
        self.running = False
        self.tasks = []
        
        # Initialize plugins
        for plugin_config in config.plugins:
            if plugin_config.enabled:
                try:
                    plugin = create_plugin(plugin_config.type, plugin_config.config)
                    self.plugins.append((plugin, plugin_config))
                    logging.info(f"Loaded plugin: {plugin_config.name}")
                except Exception as e:
                    logging.error(f"Failed to load plugin {plugin_config.name}: {e}")
    
    async def start(self):
        """Start the scheduler"""
        if self.running:
            return
        
        self.running = True
        logging.info("Starting ticket availability scheduler")
        
        # Start scheduled checks for each plugin
        for plugin, plugin_config in self.plugins:
            task = asyncio.create_task(
                self._schedule_plugin_checks(plugin, plugin_config)
            )
            self.tasks.append(task)
    
    async def stop(self):
        """Stop the scheduler"""
        if not self.running:
            return
        
        self.running = False
        logging.info("Stopping ticket availability scheduler")
        
        # Cancel all running tasks
        for task in self.tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.tasks.clear()
    
    async def _schedule_plugin_checks(self, plugin, plugin_config):
        """Schedule regular checks for a plugin"""
        interval = timedelta(minutes=plugin_config.check_interval_minutes)
        
        while self.running:
            try:
                # Perform check
                result = await plugin.check_availability()
                
                # Store result
                self.check_history.append(result)
                
                # Keep only last 100 results per plugin
                self.check_history = [
                    r for r in self.check_history[-1000:]  # Keep last 1000 total
                ]
                
                # Log result
                if result.success:
                    available_count = len([a for a in result.availabilities if a.status == "available"])
                    logging.info(f"Plugin {plugin.name} check completed: {available_count} available tickets")
                    
                    # Send notification if tickets are available
                    if available_count > 0:
                        await self._send_notification(result)
                else:
                    logging.error(f"Plugin {plugin.name} check failed: {result.error_message}")
                    # Could also send error notifications here
                
            except Exception as e:
                logging.error(f"Error in plugin {plugin.name}: {e}")
            
            # Wait for next check
            try:
                await asyncio.sleep(interval.total_seconds())
            except asyncio.CancelledError:
                break
    
    async def _send_notification(self, result: CheckResult):
        """Send email notification for availability"""
        try:
            # Check if we should send notification (avoid spam)
            if self._should_send_notification(result):
                success = await self.email_service.send_availability_notification(result)
                if success:
                    logging.info(f"Notification sent for {result.item_name}")
                else:
                    logging.error(f"Failed to send notification for {result.item_name}")
        except Exception as e:
            logging.error(f"Error sending notification: {e}")
    
    def _should_send_notification(self, result: CheckResult) -> bool:
        """Determine if we should send a notification"""
        # For now, send notification if any tickets are available
        # Could add more sophisticated logic like:
        # - Only send once per day for same availability
        # - Only send if availability changed from previous check
        available_count = len([a for a in result.availabilities if a.status == "available"])
        return available_count > 0
    
    async def run_manual_check(self, plugin_name: str = None) -> List[CheckResult]:
        """Run manual check for one or all plugins"""
        results = []
        
        if plugin_name:
            # Check specific plugin
            for plugin, plugin_config in self.plugins:
                if plugin_config.name == plugin_name:
                    result = await plugin.check_availability()
                    results.append(result)
                    break
        else:
            # Check all plugins
            for plugin, plugin_config in self.plugins:
                result = await plugin.check_availability()
                results.append(result)
        
        # Store results
        self.check_history.extend(results)
        
        return results
    
    def get_recent_results(self, limit: int = 50) -> List[CheckResult]:
        """Get recent check results"""
        return sorted(self.check_history, key=lambda x: x.check_time, reverse=True)[:limit]
    
    def get_plugin_status(self) -> List[Dict]:
        """Get status of all plugins"""
        status = []
        for plugin, plugin_config in self.plugins:
            # Get latest result for this plugin
            plugin_results = [r for r in self.check_history if r.plugin_name == plugin.name]
            latest_result = max(plugin_results, key=lambda x: x.check_time) if plugin_results else None
            
            status.append({
                "name": plugin_config.name,
                "type": plugin_config.type,
                "enabled": plugin_config.enabled,
                "check_interval_minutes": plugin_config.check_interval_minutes,
                "last_check": latest_result.check_time if latest_result else None,
                "last_success": latest_result.success if latest_result else None,
                "event_info": plugin.get_item_info()
            })
        
        return status