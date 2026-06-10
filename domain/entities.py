from dataclasses import dataclass, field
from typing import Optional


class RobotsBlockedError(Exception):
    """Raised when a request is blocked by robots.txt."""


@dataclass
class PageData:
    url: str
    status_code: int
    html: str
    headers: dict
    elapsed: float


@dataclass
class ScrapeRequest:
    urls: list[str]
    selectors: Optional[list[str]] = None
    attr: Optional[str] = None
    extract_links: bool = False
    extract_images: bool = False
    summary_only: bool = False
    table_selector: Optional[str] = None


@dataclass
class ScrapeResult:
    page: PageData
    extracted_data: list[dict] = field(default_factory=list)
    summary: Optional[dict] = None


@dataclass
class PageSummary:
    url: str
    status_code: int
    elapsed: float
    size: int
    title: Optional[str] = None
    meta_description: Optional[str] = None
    word_count: int = 0
    link_count: int = 0
    internal_links: int = 0
    external_links: int = 0
    image_count: int = 0


@dataclass
class ExportRequest:
    data: list[dict]
    filepath: str
    format: str
