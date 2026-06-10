"""
InfoSnap – Flask web app with Clean Architecture.

Provides a REST API and serves a frontend for scraping web pages.
"""

import logging
import sys

from flask import Flask, render_template

from config import ScraperConfig
from application import ScrapeUseCase, ExportUseCase
from infrastructure import RequestsPageFetcher, BeautifulSoupPageParser, CsvExporter, JsonExporter
from interface_adapters import web_bp
from interface_adapters.web_controller import init_controllers

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s  %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


def create_app(config: ScraperConfig | None = None) -> Flask:
    if config is None:
        config = ScraperConfig()

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

    app = Flask(__name__)
    app.register_blueprint(web_bp)
    init_controllers(scrape_uc, export_uc)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/logo-preview")
    def logo_preview():
        return render_template("logo-preview.html")

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=3001)
