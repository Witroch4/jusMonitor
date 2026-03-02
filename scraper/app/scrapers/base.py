"""Base scraper with Bright Data proxy and playwright-stealth integration."""

import logging
import random
import string
from contextlib import asynccontextmanager
from dataclasses import dataclass

from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright
from playwright_stealth import stealth_async

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class BrowserSession:
    """Holds all Playwright objects for proper cleanup."""

    playwright: Playwright
    browser: Browser
    context: BrowserContext
    page: Page


class BaseScraper:
    """Base class providing Playwright browser with Bright Data proxy and stealth."""

    BROWSER_ARGS = [
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--disable-blink-features=AutomationControlled",
        "--window-size=1920,1080",
        "--ignore-certificate-errors",
    ]

    @asynccontextmanager
    async def create_session(self):
        """Create a browser session with proxy and stealth. Use as async context manager.

        Yields:
            BrowserSession with playwright, browser, context, and page.
        """
        pw = await async_playwright().start()
        proxy_config = self._build_proxy_config()
        logger.info("launching_browser", extra={"proxy": bool(proxy_config)})

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

        page = await context.new_page()
        await stealth_async(page)

        session = BrowserSession(
            playwright=pw, browser=browser, context=context, page=page
        )

        try:
            yield session
        finally:
            await browser.close()
            await pw.stop()

    async def apply_stealth(self, page: Page) -> None:
        """Apply stealth to a new page/popup (must be called on every new tab)."""
        await stealth_async(page)

    def _build_proxy_config(self) -> dict | None:
        """Build Bright Data proxy config with sticky session."""
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
