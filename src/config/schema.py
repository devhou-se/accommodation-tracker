from typing import List, Optional
from pydantic import BaseModel, field_validator, HttpUrl, EmailStr
from datetime import datetime
import re


class Config(BaseModel):
    target_dates: List[str]
    notification_endpoint: HttpUrl
    mailgun_api_key: Optional[str] = None
    mailgun_domain: Optional[str] = None
    notification_emails: Optional[List[str]] = []
    email_from: Optional[str] = "noreply@gassho-zukuri-checker.com"
    log_level: str = "INFO"
    check_interval_seconds: int = 300
    retry_attempts: int = 3
    timeout_seconds: int = 30
    
    @field_validator('target_dates')
    @classmethod
    def validate_dates(cls, v):
        date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
        for date_str in v:
            if not date_pattern.match(date_str):
                raise ValueError(f"Invalid date format: {date_str}. Expected YYYY-MM-DD")
            try:
                datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                raise ValueError(f"Invalid date: {date_str}")
        return v
    
    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR']
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v.upper()
    
    @field_validator('check_interval_seconds')
    @classmethod
    def validate_check_interval(cls, v):
        if v < 60:
            raise ValueError("check_interval_seconds must be at least 60 seconds")
        return v
    
    @field_validator('retry_attempts')
    @classmethod
    def validate_retry_attempts(cls, v):
        if v < 1 or v > 10:
            raise ValueError("retry_attempts must be between 1 and 10")
        return v
    
    @field_validator('timeout_seconds')
    @classmethod
    def validate_timeout(cls, v):
        if v < 5 or v > 300:
            raise ValueError("timeout_seconds must be between 5 and 300")
        return v