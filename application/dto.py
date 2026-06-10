from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ScrapeRequestDTO:
    url: str
    mode: str = "summary"
    selectors: Optional[list[str]] = None
    attr: Optional[str] = None
    delay: float = 0.0
    timeout: int = 30
    ignore_robots: bool = False


@dataclass
class ScrapeResponseDTO:
    success: bool
    page: Optional[dict] = None
    data: Any = None
    display: str = "summary"
    error: Optional[str] = None
    error_type: Optional[str] = None


@dataclass
class ExportResponseDTO:
    success: bool
    content: Optional[str] = None
    mimetype: str = "application/json"
    filename: str = "data.json"
    error: Optional[str] = None
