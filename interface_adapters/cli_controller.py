import argparse
from typing import Callable, Optional

from application import ScrapeUseCase, ExportUseCase
from domain import PageData, PageParserPort, ScrapeRequest, ExportRequest, RobotsBlockedError
from .presenters import ConsolePresenter as ui


def build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="webscraper",
        description="Scrape web pages and extract structured data.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("urls", nargs="+", help="One or more URLs to scrape")
    extract = parser.add_argument_group("Extraction")
    extract.add_argument("--select", type=str, action="append", metavar="SELECTOR", help="CSS selector to extract data (repeatable)")
    extract.add_argument("--attr", type=str, metavar="ATTR", help="Attribute to extract from selected elements")
    extract.add_argument("--table", type=str, metavar="SELECTOR", help="Parse an HTML <table> at the given CSS selector")
    extract.add_argument("--links", action="store_true", help="Extract all links")
    extract.add_argument("--images", action="store_true", help="Extract all images")
    extract.add_argument("--summary-only", action="store_true", help="Only show page-level summary")
    output = parser.add_argument_group("Output")
    output.add_argument("--json", type=str, metavar="FILE", help="JSON output file")
    output.add_argument("--csv", type=str, metavar="FILE", help="CSV output file")
    behaviour = parser.add_argument_group("Behaviour")
    behaviour.add_argument("--delay", type=float, default=1.0, help="Delay between requests (default: 1.0)")
    behaviour.add_argument("--timeout", type=int, default=30, help="Request timeout (default: 30)")
    behaviour.add_argument("--retries", type=int, default=3, help="Max retries (default: 3)")
    behaviour.add_argument("--ignore-robots", action="store_true", help="Ignore robots.txt")
    behaviour.add_argument("--no-random-ua", action="store_true", help="Disable random user-agent")
    parser.add_argument("-v", "--verbose", action="store_true", help="Debug logging")
    return parser


class CliController:
    def __init__(
        self,
        scrape_uc: ScrapeUseCase,
        export_uc: ExportUseCase,
        parser_factory: Callable[[str, Optional[str]], PageParserPort],
        args: argparse.Namespace,
    ):
        self._scrape_uc = scrape_uc
        self._export_uc = export_uc
        self._parser_factory = parser_factory
        self.args = args

    def run(self) -> int:
        pages: list[PageData] = []

        for url in self.args.urls:
            print(f"\n>> Fetching: {url}")
            fetch_req = ScrapeRequest(urls=[url])
            try:
                results = self._scrape_uc.execute(fetch_req)
            except RobotsBlockedError:
                print(f"  [ROBOTS BLOCKED] {url}")
                print("  Tip: Use --ignore-robots to bypass this restriction")
                continue
            if not results:
                print(f"  [FAILED] {url}")
                continue

            pr = results[0]
            ui.print_page_preview(
                pr.page.url, pr.page.status_code,
                pr.page.elapsed, len(pr.page.html),
            )
            pages.append(pr.page)

        if not pages:
            return 1

        all_extracted: list[dict] = []
        for page in pages:
            parser = self._parser_factory(page.html, page.url)

            if self.args.summary_only:
                ui.print_summary(parser.summary(), title=page.url)
                continue

            extracted = self._extract_page(parser, page.url)
            if extracted:
                all_extracted.extend(extracted)
                print(f"  Results for {page.url}:")
                ui.print_results(extracted)

            if self.args.links:
                links = parser.all_links()
                print(f"\n  Links ({len(links)} total):")
                for lnk in links[:20]:
                    text = lnk["text"][:60] if lnk["text"] else "(no text)"
                    print(f"    * {lnk['url']}  - {text}")
                if len(links) > 20:
                    print(f"    ... and {len(links) - 20} more")
                for lnk in links:
                    lnk["url_source"] = page.url
                    lnk["type"] = "link"
                    all_extracted.append(lnk)

            if self.args.images:
                imgs = parser.images()
                print(f"\n  Images ({len(imgs)} total):")
                for img in imgs[:10]:
                    alt = img["alt"][:40] if img["alt"] else "(no alt)"
                    print(f"    [IMG] {img['url']}  - {alt}")
                if len(imgs) > 10:
                    print(f"    ... and {len(imgs) - 10} more")
                for img in imgs:
                    img["url_source"] = page.url
                    img["type"] = "image"
                    all_extracted.append(img)

        if all_extracted:
            if self.args.csv:
                self._export_uc.execute(ExportRequest(data=all_extracted, filepath=self.args.csv, format="csv"))
            if self.args.json:
                self._export_uc.execute(ExportRequest(data=all_extracted, filepath=self.args.json, format="json"))

        if self.args.json and not all_extracted and not self.args.summary_only:
            raw = [{"url": p.url, "status": p.status_code, "html": p.html, "elapsed": p.elapsed} for p in pages]
            self._export_uc.execute(ExportRequest(data=raw, filepath=self.args.json, format="json"))

        return 0

    def _extract_page(self, parser: PageParserPort, url: str) -> list[dict]:
        extracted: list[dict] = []
        if self.args.select:
            for selector in self.args.select:
                values = parser.extract(selector, attribute=self.args.attr)
                for val in values:
                    extracted.append({"url": url, "selector": selector, "value": val})
        if self.args.table:
            rows = parser.table_to_dicts(self.args.table)
            for row in rows:
                row["url"] = url
                extracted.append(row)
        return extracted
