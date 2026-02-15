"""
Pydantic models for the Twitter/X Scraper sidecar service.
Defines data structures for tweets, commands, responses, and configurations.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


# ─── Enums ───────────────────────────────────────────────

class ScrapeType(str, Enum):
    PROFILE = "profile"
    BOOKMARKS = "bookmarks"


class ScrapeMode(str, Enum):
    COUNT = "count"
    DAYS = "days"
    DATE_RANGE = "date_range"
    ALL = "all"


class LoginMethod(str, Enum):
    MANUAL = "manual"
    AUTOMATIC = "automatic"


class ScrapeStatus(str, Enum):
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ERROR = "error"


class ExportFormat(str, Enum):
    JSON = "json"
    MARKDOWN = "md"
    DOCX = "docx"


# ─── Tweet Model ────────────────────────────────────────

class TweetData(BaseModel):
    """Tweet data structure with engagement metrics"""
    id: str
    text: str = ""
    date: Optional[str] = None  # ISO format string
    date_str: str = ""
    media_urls: List[str] = Field(default_factory=list)
    tweet_url: str = ""
    has_article: bool = False
    needs_full_text: bool = False
    # Engagement metrics
    likes: int = 0
    retweets: int = 0
    replies: int = 0
    views: int = 0


# ─── Command Models (stdin) ─────────────────────────────

class LoginCommand(BaseModel):
    command: str = "login"
    method: LoginMethod = LoginMethod.MANUAL
    username: Optional[str] = None
    password: Optional[str] = None


class ScrapeCommand(BaseModel):
    command: str = "scrape"
    type: ScrapeType = ScrapeType.PROFILE
    target: str = ""
    mode: ScrapeMode = ScrapeMode.COUNT
    count: Optional[int] = None
    days: Optional[int] = None
    start_date: Optional[str] = None  # ISO format
    end_date: Optional[str] = None    # ISO format


class ExportCommand(BaseModel):
    command: str = "export"
    format: ExportFormat = ExportFormat.JSON
    scrape_id: Optional[str] = None
    output_dir: Optional[str] = None
    filename: Optional[str] = None


class AnalyzeCommand(BaseModel):
    command: str = "analyze"
    scrape_id: Optional[str] = None
    api_key: str = ""
    tweets: Optional[List[Dict[str, Any]]] = None


class ControlCommand(BaseModel):
    command: str  # "pause", "resume", "cancel", "status", "stop"


class SettingsCommand(BaseModel):
    command: str = "settings"
    action: str = "get"  # "get" or "set"
    settings: Optional[Dict[str, Any]] = None


class LoginConfirmCommand(BaseModel):
    command: str = "login_confirm"


# ─── Response Models (stdout) ───────────────────────────

class MessageType(str, Enum):
    PROGRESS = "progress"
    TWEET = "tweet"
    LOGIN_STATUS = "login_status"
    LOGIN_WAITING = "login_waiting"
    COMPLETE = "complete"
    ERROR = "error"
    STATUS = "status"
    EXPORT_COMPLETE = "export_complete"
    ANALYSIS_RESULT = "analysis_result"
    LOG = "log"
    READY = "ready"
    SETTINGS = "settings"


class ProgressMessage(BaseModel):
    type: str = MessageType.PROGRESS
    collected: int = 0
    target: Optional[int] = None
    tweet: Optional[TweetData] = None
    message: str = ""


class LoginStatusMessage(BaseModel):
    type: str = MessageType.LOGIN_STATUS
    success: bool = False
    message: str = ""


class LoginWaitingMessage(BaseModel):
    type: str = MessageType.LOGIN_WAITING
    message: str = "Waiting for manual login..."


class CompleteMessage(BaseModel):
    type: str = MessageType.COMPLETE
    total: int = 0
    scrape_id: Optional[str] = None
    tweets: List[TweetData] = Field(default_factory=list)


class ErrorMessage(BaseModel):
    type: str = MessageType.ERROR
    message: str = ""
    code: Optional[str] = None


class StatusMessage(BaseModel):
    type: str = MessageType.STATUS
    status: ScrapeStatus = ScrapeStatus.RUNNING
    collected: int = 0
    target: Optional[int] = None


class ExportCompleteMessage(BaseModel):
    type: str = MessageType.EXPORT_COMPLETE
    format: str = ""
    path: str = ""
    message: str = ""


class AnalysisResultMessage(BaseModel):
    type: str = MessageType.ANALYSIS_RESULT
    sentiment: Optional[Dict[str, Any]] = None
    topics: Optional[List[str]] = None
    style: Optional[str] = None
    recommendations: Optional[List[str]] = None
    summary: Optional[str] = None


class LogMessage(BaseModel):
    type: str = MessageType.LOG
    level: str = "info"  # "info", "warning", "error", "debug"
    message: str = ""


class ReadyMessage(BaseModel):
    type: str = MessageType.READY
    version: str = "1.0.0"


class SettingsMessage(BaseModel):
    type: str = MessageType.SETTINGS
    settings: Dict[str, Any] = Field(default_factory=dict)
