import logging
from typing import Callable, Optional

from domain import (
    PageFetcherPort, PageParserPort, DataExporterPort,
    ScrapeRequest, ScrapeResult, ExportRequest, RobotsBlockedError,
)

logger = logging.getLogger(__name__)


class ScrapeUseCase:
    def __init__(
        self,
        fetcher: PageFetcherPort,
        parser_factory: Callable[[str, Optional[str]], PageParserPort],
    ):
        self._fetcher = fetcher
        self._parser_factory = parser_factory

    def execute(self, request: ScrapeRequest) -> list[ScrapeResult]:
        results: list[ScrapeResult] = []

        for url in request.urls:
            try:
                page = self._fetcher.fetch(url, ignore_robots=request.ignore_robots)
            except RobotsBlockedError:
                logger.warning("Robots.txt blocked: %s", url)
                raise
            if page is None:
                logger.error("Failed to fetch: %s", url)
                continue

            parser = self._parser_factory(page.html, page.url)
            result = ScrapeResult(page=page)

            if request.summary_only:
                result.summary = parser.summary()
            else:
                extracted = []
                if request.selectors:
                    for selector in request.selectors:
                        values = parser.extract(selector, attribute=request.attr)
                        for val in values:
                            extracted.append({
                                "url": page.url,
                                "selector": selector,
                                "value": val,
                            })
                if request.table_selector:
                    rows = parser.table_to_dicts(request.table_selector)
                    for row in rows:
                        row["url"] = page.url
                        extracted.append(row)
                if request.extract_links:
                    links = parser.all_links()
                    for lnk in links:
                        lnk["url_source"] = page.url
                        lnk["type"] = "link"
                    extracted.extend(links)
                if request.extract_images:
                    imgs = parser.images()
                    for img in imgs:
                        img["url_source"] = page.url
                        img["type"] = "image"
                    extracted.extend(imgs)
                result.extracted_data = extracted

            results.append(result)

        return results

    def close(self) -> None:
        self._fetcher.close()


class ExportUseCase:
    def __init__(self, exporters: dict[str, DataExporterPort]):
        self._exporters = exporters

    def execute(self, request: ExportRequest) -> str:
        exporter = self._exporters.get(request.format)
        if not exporter:
            raise ValueError(f"Unsupported export format: {request.format}")
        return exporter.export(request.data, request.filepath)
