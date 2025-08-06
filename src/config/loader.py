import json
import os
from pathlib import Path
from typing import Optional
import structlog

from .schema import Config

logger = structlog.get_logger()


def load_config(config_path: Optional[str] = None) -> Config:
    """Load configuration from JSON file with environment variable overrides."""
    
    # Determine config file path
    if config_path is None:
        config_path = os.getenv('CONFIG_PATH', '/app/config.json')
    
    config_file = Path(config_path)
    
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    logger.info("Loading configuration", config_path=config_path)
    
    try:
        with open(config_file, 'r') as f:
            config_data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in config file: {e}")
    
    # Apply environment variable overrides
    env_overrides = {
        'LOG_LEVEL': 'log_level',
        'NOTIFICATION_ENDPOINT': 'notification_endpoint',
    }
    
    for env_var, config_key in env_overrides.items():
        env_value = os.getenv(env_var)
        if env_value:
            config_data[config_key] = env_value
            logger.info("Applied environment override", env_var=env_var, config_key=config_key)
    
    try:
        config = Config(**config_data)
        logger.info("Configuration loaded successfully", 
                   target_dates_count=len(config.target_dates),
                   log_level=config.log_level)
        return config
    except Exception as e:
        logger.error("Configuration validation failed", error=str(e))
        raise ValueError(f"Configuration validation failed: {e}")