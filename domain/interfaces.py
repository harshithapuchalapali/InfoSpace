from abc import ABC, abstractmethod
from typing import Optional

from .entities import PageData


class PageFetcherPort(ABC):
    @abstractmethod
    def fetch(self, url: str, ignore_robots: bool = False) -> Optional[PageData]:
        ...

    @abstractmethod
    def close(self) -> None:
        ...


class PageParserPort(ABC):
    @abstractmethod
    def title(self) -> Optional[str]:
        ...

    @abstractmethod
    def body_text(self) -> str:
        ...

    @abstractmethod
    def meta_description(self) -> Optional[str]:
        ...

    @abstractmethod
    def all_links(self) -> list[dict]:
        ...

    @abstractmethod
    def internal_links(self) -> list[dict]:
        ...

    @abstractmethod
    def external_links(self) -> list[dict]:
        ...

    @abstractmethod
    def images(self) -> list[dict]:
        ...

    @abstractmethod
    def extract(self, css_selector: str, attribute: Optional[str] = None) -> list:
        ...

    @abstractmethod
    def table_to_dicts(self, table_selector: str) -> list[dict]:
        ...

    @abstractmethod
    def summary(self) -> dict:
        ...

    @abstractmethod
    def meta_tags(self) -> dict[str, str]:
        ...


class DataExporterPort(ABC):
    @abstractmethod
    def export(self, data: list[dict], filepath: str) -> str:
        ...
