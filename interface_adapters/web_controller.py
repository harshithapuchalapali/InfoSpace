import csv
import io
import json
import logging
import re

from flask import Blueprint, jsonify, request, Response

from application import ScrapeUseCase, ExportUseCase, ScrapeRequestDTO, ScrapeResponseDTO
from domain import ScrapeRequest, RobotsBlockedError

logger = logging.getLogger(__name__)

web_bp = Blueprint("web", __name__)

_latest_data: list[dict] = []
_latest_format: str = "json"

_scrape_uc: ScrapeUseCase = None
_export_uc: ExportUseCase = None


def init_controllers(scrape_uc: ScrapeUseCase, export_uc: ExportUseCase) -> None:
    global _scrape_uc, _export_uc
    _scrape_uc = scrape_uc
    _export_uc = export_uc


@web_bp.route("/api/scrape", methods=["POST"])
def api_scrape():
    global _latest_data, _latest_format

    body = request.get_json(silent=True) or {}
    url = (body.get("url") or "").strip()
    mode = body.get("mode", "summary")
    selectors = body.get("selectors") or []
    attr = body.get("attr") or None
    delay = float(body.get("delay", 0.0))
    timeout = int(body.get("timeout", 30))
    ignore_robots = bool(body.get("ignore_robots", False))

    if not url:
        return jsonify({"success": False, "error": "URL is required"}), 400
    if not re.match(r"^https?://", url, re.IGNORECASE):
        return jsonify({"success": False, "error": "URL must start with http:// or https://"}), 400

    sel_list = selectors if mode == "selectors" else None
    domain_req = ScrapeRequest(
        urls=[url],
        selectors=sel_list,
        attr=attr,
        extract_links=(mode == "links"),
        extract_images=(mode == "images"),
        summary_only=(mode == "summary"),
    )

    try:
        results = _scrape_uc.execute(domain_req)
    except RobotsBlockedError:
        logger.warning("Robots.txt blocked: %s", url)
        return jsonify({
            "success": False,
            "error": "The website's robots.txt prevents scraping. "
                     "Tick the 'Ignore robots.txt' checkbox and try again.",
            "error_type": "robots_blocked",
        }), 400
    except Exception as exc:
        logger.exception("Fetch error")
        return jsonify({"success": False, "error": f"Fetch failed: {exc}"}), 500

    if not results:
        return jsonify({
            "success": False,
            "error": "Failed to fetch page - server returned an error or the URL is unreachable.",
        }), 400

    pr = results[0]
    page_info = {
        "url": pr.page.url,
        "status": pr.page.status_code,
        "elapsed": pr.page.elapsed,
        "size": len(pr.page.html),
    }

    if mode == "summary" and pr.summary:
        result = {
            "success": True,
            "page": page_info,
            "data": pr.summary,
            "display": "summary",
        }
        _latest_data = [{"key": k, "value": v} for k, v in pr.summary.items()]
    elif mode in ("selectors", "links", "images"):
        result = {
            "success": True,
            "page": page_info,
            "data": pr.extracted_data,
            "display": "table",
        }
        _latest_data = pr.extracted_data
    else:
        return jsonify({"success": False, "error": f"Unknown mode: {mode}"}), 400

    _latest_format = mode
    return jsonify(result)


@web_bp.route("/api/download/<fmt>")
def api_download(fmt: str):
    global _latest_data
    if not _latest_data:
        return jsonify({"success": False, "error": "No data to download. Scrape something first!"}), 400

    if fmt == "json":
        return Response(
            json.dumps(_latest_data, indent=2, ensure_ascii=False),
            mimetype="application/json",
            headers={"Content-Disposition": "attachment; filename=scraped_data.json"},
        )
    elif fmt == "csv":
        output = io.StringIO()
        fieldnames = list(_latest_data[0].keys())
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(_latest_data)
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=scraped_data.csv"},
        )
    else:
        return jsonify({"success": False, "error": f"Unsupported format: {fmt}"}), 400
