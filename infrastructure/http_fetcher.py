import logging
import time
from functools import wraps
from typing import Any, Callable, Optional, TypeVar
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests

from domain import PageData, PageFetcherPort, RobotsBlockedError
from .rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 "
    "Firefox/120.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.1 Safari/605.1.15",
]


def _retry(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (requests.RequestException,),
):
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exc: Optional[Exception] = None
            wait = delay
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    logger.warning(
                        "Attempt %d/%d failed for %s: %s",
                        attempt, max_retries, func.__name__, e,
                    )
                    if attempt < max_retries:
                        time.sleep(wait)
                        wait *= backoff
            raise last_exc
        return wrapper
    return decorator


class _RobotsCache:
    def __init__(self) -> None:
        self._parsers: dict[str, RobotFileParser] = {}

    def can_fetch(self, url: str, user_agent: str = "*") -> bool:
        domain = urlparse(url).netloc
        if domain not in self._parsers:
            parser = RobotFileParser()
            parser.set_url(f"https://{domain}/robots.txt")
            try:
                parser.read()
            except Exception:
                logger.debug("Could not read robots.txt for %s - allowing", domain)
                self._parsers[domain] = RobotFileParser()
            else:
                self._parsers[domain] = parser
        return self._parsers[domain].can_fetch(user_agent, url)


class RequestsPageFetcher(PageFetcherPort):
    def __init__(
        self,
        timeout: int = 30,
        delay: float = 1.0,
        max_retries: int = 3,
        respect_robots: bool = True,
        randomize_user_agent: bool = True,
    ):
        self._timeout = timeout
        self._max_retries = max_retries
        self._respect_robots = respect_robots
        self._randomize_ua = randomize_user_agent
        self._rate_limiter = RateLimiter(delay)
        self._ua_index = 0
        self._robots = _RobotsCache() if respect_robots else None
        self.session = requests.Session()
        self.session.headers.update(self._get_headers())

    def _get_ua(self) -> str:
        if not self._randomize_ua:
            return USER_AGENTS[0]
        ua = USER_AGENTS[self._ua_index % len(USER_AGENTS)]
        self._ua_index += 1
        return ua

    def _get_headers(self) -> dict:
        return {
            "User-Agent": self._get_ua(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    def fetch(self, url: str) -> Optional[PageData]:
        url = url.strip()
        if self._robots and not self._robots.can_fetch(url):
            raise RobotsBlockedError(f"Blocked by robots.txt: {url}")
        self._rate_limiter.wait()
        try:
            resp = self._do_request(url)
        except requests.RequestException as exc:
            logger.error("Failed to fetch %s: %s", url, exc)
            return None
        if resp is None:
            return None
        return PageData(
            url=resp.url,
            status_code=resp.status_code,
            html=resp.text,
            headers=dict(resp.headers),
            elapsed=resp.elapsed.total_seconds(),
        )

    @_retry(max_retries=3, delay=1.0)
    def _do_request(self, url: str) -> Optional[requests.Response]:
        if self._randomize_ua:
            self.session.headers.update({"User-Agent": self._get_ua()})
        resp = self.session.get(
            url,
            timeout=self._timeout,
            allow_redirects=True,
            stream=False,
        )
        resp.raise_for_status()
        return resp

    def close(self) -> None:
        self.session.close()
