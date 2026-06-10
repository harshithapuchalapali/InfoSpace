#!/usr/bin/env python3
"""
WebScraper – Clean Architecture CLI entry point.

Usage:
  python main.py https://example.com
  python main.py https://example.com --select "h2" --csv output.csv
  python main.py https://example.com --summary-only
"""

import logging
import sys

from config import ScraperConfig
from application import ScrapeUseCase, ExportUseCase
from infrastructure import RequestsPageFetcher, BeautifulSoupPageParser, CsvExporter, JsonExporter
from interface_adapters import CliController, build_cli_parser


def _setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(levelname)s  %(message)s",
        stream=sys.stderr,
    )


def _wire(config: ScraperConfig):
    fetcher = RequestsPageFetcher(
        timeout=config.timeout,
        delay=config.delay,
        max_retries=config.max_retries,
        respect_robots=config.respect_robots,
        randomize_user_agent=config.randomize_user_agent,
    )
    scrape_uc = ScrapeUseCase(
        fetcher=fetcher,
        parser_factory=lambda html, url: BeautifulSoupPageParser(html, url),
    )
    export_uc = ExportUseCase({
        "csv": CsvExporter(),
        "json": JsonExporter(),
    })
    return scrape_uc, export_uc, fetcher


def main() -> int:
    parser = build_cli_parser()
    args = parser.parse_args()

    _setup_logging(args.verbose)

    config = ScraperConfig(
        timeout=args.timeout,
        delay=args.delay,
        max_retries=args.retries,
        respect_robots=not args.ignore_robots,
        randomize_user_agent=not args.no_random_ua,
        verbose=args.verbose,
    )

    scrape_uc, export_uc, fetcher = _wire(config)
    controller = CliController(scrape_uc, export_uc, lambda html, url: BeautifulSoupPageParser(html, url), args)

    try:
        return controller.run()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
        return 130
    finally:
        fetcher.close()


if __name__ == "__main__":
    sys.exit(main())
