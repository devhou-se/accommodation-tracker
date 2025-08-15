import json
import yaml
from typing import Dict, List
from pathlib import Path
from dataclasses import dataclass


@dataclass
class EmailConfig:
    """Email notification configuration"""
    api_key: str
    domain: str
    from_email: str
    recipients: List[str]


@dataclass
class PluginConfig:
    """Individual plugin configuration"""
    type: str
    name: str
    config: Dict
    check_interval_minutes: int = 60
    enabled: bool = True


@dataclass
class AppConfig:
    """Main application configuration"""
    email: EmailConfig
    plugins: List[PluginConfig]
    web_port: int = 8080
    log_level: str = "INFO"


class ConfigManager:
    """Manages application configuration from JSON/YAML files"""
    
    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self.config = self._load_config()
    
    def _load_config(self) -> AppConfig:
        """Load configuration from file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            if self.config_path.suffix.lower() in ['.yaml', '.yml']:
                data = yaml.safe_load(f)
            else:
                data = json.load(f)
        
        return self._parse_config(data)
    
    def _parse_config(self, data: Dict) -> AppConfig:
        """Parse configuration data into structured format"""
        # Email configuration
        email_data = data.get('email', {})
        email_config = EmailConfig(
            api_key=email_data.get('api_key', ''),
            domain=email_data.get('domain', ''),
            from_email=email_data.get('from_email', 'noreply@' + email_data.get('domain', 'localhost')),
            recipients=email_data.get('recipients', [])
        )
        
        # Plugin configurations
        plugins_data = data.get('plugins', [])
        plugin_configs = []
        for plugin_data in plugins_data:
            plugin_config = PluginConfig(
                type=plugin_data.get('type'),
                name=plugin_data.get('name'),
                config=plugin_data.get('config', {}),
                check_interval_minutes=plugin_data.get('check_interval_minutes', 60),
                enabled=plugin_data.get('enabled', True)
            )
            plugin_configs.append(plugin_config)
        
        return AppConfig(
            email=email_config,
            plugins=plugin_configs,
            web_port=data.get('web_port', 8080),
            log_level=data.get('log_level', 'INFO')
        )
    
    def reload(self):
        """Reload configuration from file"""
        self.config = self._load_config()
    
    def get_config(self) -> AppConfig:
        """Get current configuration"""
        return self.config