"""Base scraper with proxy rotation (Decodo/Smartproxy or Bright Data) and playwright-stealth v2.

Proxy selection:
- SMARTPROXY_DECODO=true  → Decodo/Smartproxy via gate.decodo.com:7000 (rotating BR IPs)
- SMARTPROXY_DECODO=false → Bright Data (legacy) or no proxy if credentials are empty

NOTE: Decodo proxy blocks .jus.br domains (403). Tribunal scraping uses
direct access (residential IP) by default. Proxy is available for future
non-tribunal scraping needs.

Uses playwright-stealth v2 (mattwmaster58 fork) which is compatible with
RichFaces A4J.
"""

import logging
import random
import string
from contextlib import asynccontextmanager
from dataclasses import dataclass

from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright
from playwright_stealth import Stealth

from app.config import settings

logger = logging.getLogger(__name__)

# Single Stealth instance — all evasions enabled (safe with v2)
_stealth = Stealth()


@dataclass
class BrowserSession:
    """Holds all Playwright objects for proper cleanup."""

    playwright: Playwright
    browser: Browser
    context: BrowserContext
    page: Page


class BaseScraper:
    """Base class providing Playwright browser with proxy rotation and stealth."""

    BROWSER_ARGS = [
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--disable-blink-features=AutomationControlled",
        "--window-size=1920,1080",
        "--ignore-certificate-errors",
        "--disable-http2",  # TRF3 Akamai returns ERR_HTTP2_PROTOCOL_ERROR
    ]

    @asynccontextmanager
    async def create_session(self, use_proxy: bool = False):
        """Create a browser session with stealth. Proxy is opt-in.

        Args:
            use_proxy: If True and proxy is configured, route through proxy.
                       Default False — .jus.br domains block proxy IPs.

        Yields:
            BrowserSession with playwright, browser, context, and page.
        """
        pw = await async_playwright().start()
        proxy_config = self._build_proxy_config() if use_proxy else None
        logger.info("launching_browser", extra={
            "proxy": bool(proxy_config),
            "use_proxy": use_proxy,
        })

        launch_kwargs = {
            "headless": True,
            "args": self.BROWSER_ARGS,
        }
        if proxy_config:
            launch_kwargs["proxy"] = proxy_config

        browser = await pw.chromium.launch(**launch_kwargs)

        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            locale="pt-BR",
            timezone_id="America/Sao_Paulo",
            viewport={"width": 1920, "height": 1080},
            ignore_https_errors=True,
            accept_downloads=True,
        )

        # Apply stealth to the entire context (covers all pages/popups)
        await _stealth.apply_stealth_async(context)

        page = await context.new_page()

        session = BrowserSession(
            playwright=pw, browser=browser, context=context, page=page
        )

        try:
            yield session
        finally:
            await browser.close()
            await pw.stop()

    async def apply_stealth(self, page: Page) -> None:
        """No-op. Stealth v2 is applied at context level, covers all pages."""
        pass

    def _build_proxy_config(self) -> dict | None:
        """Build proxy config based on SMARTPROXY_DECODO env var."""
        if settings.smartproxy_decodo:
            return self._build_decodo_proxy()
        return self._build_brightdata_proxy()

    def _build_decodo_proxy(self) -> dict | None:
        """Build Decodo/Smartproxy proxy config with rotating BR sessions."""
        if not settings.proxy_user or not settings.proxy_pass:
            logger.warning("Decodo proxy enabled but credentials missing")
            return None

        session_id = random.randint(10000, 9999999)
        final_username = f"user-{settings.proxy_user}-country-br-session-{session_id}"

        logger.info("proxy_decodo_session", extra={"session_id": session_id})

        return {
            "server": f"http://{settings.proxy_host}:{settings.proxy_port}",
            "username": final_username,
            "password": settings.proxy_pass,
        }

    def _build_brightdata_proxy(self) -> dict | None:
        """Build Bright Data proxy config (legacy)."""
        if not settings.bd_username or not settings.bd_password:
            logger.warning("Bright Data proxy not configured, running without proxy")
            return None

        session_id = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
        proxy_user = f"{settings.bd_username}-country-br-session-{session_id}"

        return {
            "server": f"http://{settings.bd_host}",
            "username": proxy_user,
            "password": settings.bd_password,
        }

    @staticmethod
    async def human_delay(min_s: float = 0.5, max_s: float = 1.5) -> None:
        """Random delay to mimic human behavior."""
        import asyncio

        await asyncio.sleep(random.uniform(min_s, max_s))
