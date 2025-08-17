import asyncio
import logging
import os
import signal
import sys
import uvicorn
from pathlib import Path

from .config import ConfigManager
from .email_service import EmailService
from .scheduler import TicketScheduler
from .web_app import WebApp


async def main():
    """Main application entry point"""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    # Load configuration
    config_path = os.environ.get('CONFIG_PATH', 'config.json')
    if not Path(config_path).exists():
        logger.error(f"Configuration file not found: {config_path}")
        logger.info("Please create a configuration file based on config.example.json")
        sys.exit(1)
    
    try:
        config_manager = ConfigManager(config_path)
        config = config_manager.get_config()
        logger.info(f"Loaded configuration from {config_path}")
        logger.info(f"Email recipients configured: {config.email.recipients}")
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)
    
    # Setup email service
    email_service = EmailService(config.email)
    
    # Setup scheduler
    scheduler = TicketScheduler(config, email_service)
    
    # Setup web app
    web_app = WebApp(scheduler, config)
    
    # Setup graceful shutdown
    def signal_handler(signum, frame):
        logger.info("Received shutdown signal")
        asyncio.create_task(shutdown(scheduler))
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start scheduler
    await scheduler.start()
    logger.info("Availability tracker started")
    
    # Start web server
    web_config = uvicorn.Config(
        web_app.app,
        host="0.0.0.0",
        port=config.web_port,
        log_level=config.log_level.lower()
    )
    server = uvicorn.Server(web_config)
    
    logger.info(f"Starting web server on port {config.web_port}")
    
    try:
        # Run server (this will block)
        await server.serve()
    except Exception as e:
        logger.error(f"Web server error: {e}")
    finally:
        await shutdown(scheduler)


async def shutdown(scheduler):
    """Graceful shutdown"""
    logging.info("Shutting down...")
    await scheduler.stop()
    logging.info("Shutdown complete")


def run():
    """Entry point for the application"""
    # Check for single run mode (for testing)
    if os.environ.get('SINGLE_RUN') == 'true':
        asyncio.run(single_run())
    else:
        asyncio.run(main())


async def single_run():
    """Single run mode for testing"""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    config_path = os.environ.get('CONFIG_PATH', 'config.json')
    try:
        config_manager = ConfigManager(config_path)
        config = config_manager.get_config()
        
        email_service = EmailService(config.email)
        scheduler = TicketScheduler(config, email_service)
        
        # Run checks once
        results = await scheduler.run_manual_check()
        
        for result in results:
            print(f"\n=== {result.item_name} ===")
            print(f"Plugin: {result.plugin_name}")
            print(f"Check time: {result.check_time}")
            print(f"Success: {result.success}")
            
            if result.success:
                print("Availabilities:")
                for availability in result.availabilities:
                    print(f"  - {availability.room_type}: {availability.status}")
                    if availability.booking_url:
                        print(f"    Booking URL: {availability.booking_url}")
            else:
                print(f"Error: {result.error_message}")
        
        logger.info("Single run completed")
        
    except Exception as e:
        logger.error(f"Single run failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run()