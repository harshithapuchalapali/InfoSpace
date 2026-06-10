import json
from typing import Any, Optional


class ConsolePresenter:
    @staticmethod
    def print_header(text: str) -> None:
        print()
        print(f"== {text} ")
        print(f"=={'-' * (len(text) + 4)}")

    @staticmethod
    def print_page_preview(
        url: str,
        status_code: int,
        elapsed: float,
        size: int,
        title: Optional[str] = None,
    ) -> None:
        status_icon = "[OK]" if 200 <= status_code < 400 else "[ERR]"
        title_str = f" - {title}" if title else ""
        print(
            f"  {status_icon} [{status_code}] {url} "
            f"({size:,} chars in {elapsed:.2f}s){title_str}"
        )

    @staticmethod
    def print_summary(data: dict, title: Optional[str] = None) -> None:
        if title:
            ConsolePresenter.print_header(title)
        for key, value in data.items():
            label = key.replace("_", " ").title()
            print(f"  {label:<25} {value}")
        print()

    @staticmethod
    def print_results(results: list[dict]) -> None:
        if not results:
            print("  (no results)")
            return
        headers = list(results[0].keys())
        col_widths = {h: len(h) for h in headers}
        for row in results:
            for h in headers:
                col_widths[h] = max(col_widths[h], len(str(row.get(h, ""))))
        sep = "-" * (sum(col_widths.values()) + 3 * len(headers) - 1)
        header_line = " | ".join(h.ljust(col_widths[h]) for h in headers)
        print(f"  {header_line}")
        print(f"  {sep}")
        for row in results:
            line = " | ".join(
                str(row.get(h, "")).ljust(col_widths[h]) for h in headers
            )
            print(f"  {line}")
        print(f"  ({len(results)} rows)")


class JsonPresenter:
    @staticmethod
    def serialize(data: Any, indent: int = 2) -> str:
        return json.dumps(data, indent=indent, ensure_ascii=False)
