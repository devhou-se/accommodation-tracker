import asyncio
import signal
import sys
import os
from typing import Optional
import structlog

from config import load_config, Config
from scrapers import ShirakawaScraper
from notifications import NotificationClient


class AccommodationChecker:
    """Main application class for checking accommodation availability."""
    
    def __init__(self, config: Config):
        self.config = config
        self.running = True
        self.scraper = None
        self.notification_client = None
        self.logger = structlog.get_logger()
        
        # Configure structured logging
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
        
        # Set log level
        import logging
        logging.basicConfig(level=getattr(logging, config.log_level))
        
        self.logger.info(
            "Accommodation checker initialized",
            target_dates=config.target_dates,
            log_level=config.log_level
        )
    
    async def start(self, single_run=False):
        """Start the accommodation checking service."""
        self.logger.info("Starting accommodation checker service", single_run=single_run)
        
        # Initialize components
        self.scraper = ShirakawaScraper(timeout_seconds=self.config.timeout_seconds)
        self.notification_client = NotificationClient(
            endpoint_url=str(self.config.notification_endpoint),
            timeout_seconds=self.config.timeout_seconds,
            retry_attempts=self.config.retry_attempts
        )
        
        # Test notification endpoint
        self.logger.info("Testing notification endpoint")
        endpoint_works = await self.notification_client.test_endpoint()
        if not endpoint_works:
            self.logger.warning("Notification endpoint test failed, but continuing...")
        
        # Set up signal handlers
        self._setup_signal_handlers()
        
        if single_run:
            # Run once and exit
            try:
                await self._check_availability()
                self.logger.info("Single run completed successfully")
            except Exception as e:
                self.logger.error("Error during single run", error=str(e))
                raise
        else:
            # Main checking loop
            while self.running:
                try:
                    await self._check_availability()
                    
                    if self.running:
                        self.logger.info(
                            "Sleeping until next check",
                            interval_seconds=self.config.check_interval_seconds
                        )
                        await asyncio.sleep(self.config.check_interval_seconds)
                        
                except KeyboardInterrupt:
                    self.logger.info("Received keyboard interrupt")
                    break
                except Exception as e:
                    self.logger.error("Unexpected error in main loop", error=str(e))
                    if self.running:
                        await asyncio.sleep(60)  # Wait before retrying
        
        await self.cleanup()
    
    async def _check_availability(self):
        """Perform a single availability check cycle."""
        self.logger.info("Starting availability check", target_dates=self.config.target_dates)
        
        try:
            # Check availability
            results = await self.scraper.check_availability(self.config.target_dates)
            
            if results:
                self.logger.info("Availability found", count=len(results))
                
                # Send notifications
                success_count = await self.notification_client.send_notifications(results)
                
                self.logger.info(
                    "Availability check completed",
                    total_results=len(results),
                    notifications_sent=success_count
                )
            else:
                self.logger.info("No availability found")
                
        except Exception as e:
            self.logger.error("Error during availability check", error=str(e))
            raise
    
    async def cleanup(self):
        """Clean up resources."""
        self.logger.info("Cleaning up resources")
        
        if self.scraper:
            await self.scraper.cleanup()
        
        self.logger.info("Cleanup completed")
    
    def _setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            self.logger.info("Received shutdown signal", signal=signum)
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def health_check(self) -> dict:
        """Perform health check and return status."""
        return {
            "status": "healthy" if self.running else "shutting_down",
            "target_dates": self.config.target_dates,
            "check_interval": self.config.check_interval_seconds,
            "notification_endpoint": str(self.config.notification_endpoint)
        }


async def main():
    """Main entry point."""
    try:
        # Check for single run mode
        single_run = os.getenv('SINGLE_RUN', 'false').lower() == 'true'
        
        # Load configuration
        config_path = os.getenv('CONFIG_PATH')
        config = load_config(config_path)
        
        # Create and start the checker
        checker = AccommodationChecker(config)
        await checker.start(single_run=single_run)
        
    except FileNotFoundError as e:
        print(f"Configuration file not found: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())