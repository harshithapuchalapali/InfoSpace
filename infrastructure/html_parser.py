import logging
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from domain import PageParserPort

logger = logging.getLogger(__name__)


class BeautifulSoupPageParser(PageParserPort):
    def __init__(self, html: str, base_url: Optional[str] = None) -> None:
        self.soup = BeautifulSoup(html, "lxml")
        self.base_url = base_url

    def title(self) -> Optional[str]:
        tag = self.soup.find("title")
        return tag.get_text(strip=True) if tag else None

    def body_text(self) -> str:
        body = self.soup.find("body")
        if body is None:
            return ""
        return body.get_text(separator=" ", strip=True)

    def meta_description(self) -> Optional[str]:
        tag = self.soup.find("meta", attrs={"name": "description"})
        if tag and tag.get("content"):
            return tag["content"].strip()
        return None

    def all_links(self) -> list[dict]:
        links: list[dict] = []
        for a in self.soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href or href.startswith("#"):
                continue
            absolute = urljoin(self.base_url, href) if self.base_url else href
            links.append({
                "href": href,
                "url": absolute,
                "text": a.get_text(strip=True),
            })
        return links

    def internal_links(self) -> list[dict]:
        if not self.base_url:
            return []
        domain = urlparse(self.base_url).netloc
        return [lnk for lnk in self.all_links() if urlparse(lnk["url"]).netloc == domain]

    def external_links(self) -> list[dict]:
        if not self.base_url:
            return self.all_links()
        domain = urlparse(self.base_url).netloc
        return [lnk for lnk in self.all_links() if urlparse(lnk["url"]).netloc != domain]

    def images(self) -> list[dict]:
        imgs: list[dict] = []
        for img in self.soup.find_all("img", src=True):
            src = img["src"].strip()
            absolute = urljoin(self.base_url, src) if self.base_url else src
            imgs.append({
                "src": src,
                "url": absolute,
                "alt": img.get("alt", "").strip(),
            })
        return imgs

    def select(self, css_selector: str) -> list[Tag]:
        return self.soup.select(css_selector)

    def select_one(self, css_selector: str) -> Optional[Tag]:
        return self.soup.select_one(css_selector)

    def extract(self, css_selector: str, attribute: Optional[str] = None) -> list[Any]:
        results: list[Any] = []
        for el in self.soup.select(css_selector):
            if attribute:
                val = el.get(attribute)
                if val is not None:
                    results.append(val.strip() if isinstance(val, str) else val)
            else:
                results.append(el.get_text(strip=True))
        return results

    def table_to_dicts(self, table_selector: str = "table") -> list[dict]:
        table = self.soup.select_one(table_selector)
        if not table:
            return []
        rows = table.find_all("tr")
        if not rows:
            return []
        header_cells = rows[0].find_all(["th", "td"])
        headers = [h.get_text(strip=True) for h in header_cells]
        data: list[dict] = []
        for row in rows[1:]:
            cells = row.find_all("td")
            if not cells:
                continue
            row_data: dict[str, str] = {}
            for i, cell in enumerate(cells):
                key = headers[i] if i < len(headers) else f"col_{i}"
                row_data[key] = cell.get_text(strip=True)
            data.append(row_data)
        return data

    def meta_tags(self) -> dict[str, str]:
        tags: dict[str, str] = {}
        for tag in self.soup.find_all("meta"):
            name = tag.get("name") or tag.get("property")
            content = tag.get("content")
            if name and content:
                tags[name.strip()] = content.strip()
        return tags

    def summary(self) -> dict:
        return {
            "title": self.title(),
            "meta_description": self.meta_description(),
            "word_count": len(self.body_text().split()),
            "link_count": len(self.all_links()),
            "internal_links": len(self.internal_links()),
            "external_links": len(self.external_links()),
            "image_count": len(self.images()),
        }
