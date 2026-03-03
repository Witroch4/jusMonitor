"""Browser pool for reusing Chromium instances across scraping requests.

Instead of launching and killing Chromium for every single request (~3s overhead),
we keep a small pool of warm browser instances that are acquired/released.

Browsers are recycled after N uses to prevent memory leaks.
"""

import asyncio
import logging
import random
import string
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from playwright.async_api import (
    async_playwright,
    Browser,
    BrowserContext,
    Page,
    Playwright,
)
from playwright_stealth import Stealth

from app.config import settings

logger = logging.getLogger(__name__)

_stealth = Stealth()

BROWSER_ARGS = [
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--disable-blink-features=AutomationControlled",
    "--window-size=1920,1080",
    "--ignore-certificate-errors",
    "--disable-http2",
]

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


@dataclass
class BrowserInstance:
    """A pooled browser instance with usage tracking."""
    playwright: Playwright
    browser: Browser
    use_count: int = 0
    max_uses: int = 20
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    @property
    def should_recycle(self) -> bool:
        return self.use_count >= self.max_uses


@dataclass
class ScrapeSession:
    """A browser context + page checked out from the pool."""
    context: BrowserContext
    page: Page
    _instance: BrowserInstance


class BrowserPool:
    """Pool of reusable Chromium browser instances.

    Usage:
        pool = BrowserPool(size=2)
        await pool.initialize()

        async with pool.acquire() as session:
            await session.page.goto("https://example.com")
            # ...

        await pool.shutdown()
    """

    def __init__(self, size: int = 2, max_uses_per_browser: int = 20):
        self._size = size
        self._max_uses = max_uses_per_browser
        self._instances: list[BrowserInstance] = []
        self._available: asyncio.Queue[BrowserInstance] = asyncio.Queue()
        self._initialized = False
        self._lock = asyncio.Lock()
        self._total_requests = 0

    async def initialize(self) -> None:
        """Start the pool with N browser instances."""
        if self._initialized:
            return

        async with self._lock:
            if self._initialized:
                return

            logger.info("browser_pool_starting", extra={"size": self._size})
            for i in range(self._size):
                instance = await self._create_instance()
                self._instances.append(instance)
                await self._available.put(instance)

            self._initialized = True
            logger.info("browser_pool_ready", extra={"size": self._size})

    async def _create_instance(self) -> BrowserInstance:
        """Launch a fresh Chromium instance."""
        pw = await async_playwright().start()
        browser = await pw.chromium.launch(
            headless=True,
            args=BROWSER_ARGS,
        )
        logger.info("browser_launched", extra={"pid": browser.contexts})
        return BrowserInstance(
            playwright=pw,
            browser=browser,
            max_uses=self._max_uses,
        )

    async def _recycle_instance(self, old: BrowserInstance) -> BrowserInstance:
        """Kill old browser and create a fresh one."""
        logger.info("browser_recycling", extra={"uses": old.use_count})
        try:
            await old.browser.close()
            await old.playwright.stop()
        except Exception as e:
            logger.warning(f"browser_recycle_cleanup_error: {e}")

        new = await self._create_instance()
        # Replace in instances list
        try:
            idx = self._instances.index(old)
            self._instances[idx] = new
        except ValueError:
            self._instances.append(new)
        return new

    @asynccontextmanager
    async def acquire(self):
        """Check out a browser session from the pool.

        Yields a ScrapeSession with a fresh BrowserContext and Page.
        The context is destroyed on release, keeping the browser clean.
        """
        if not self._initialized:
            await self.initialize()

        instance = await self._available.get()
        self._total_requests += 1

        # Recycle if needed
        if instance.should_recycle:
            instance = await self._recycle_instance(instance)

        instance.use_count += 1

        # Create an isolated context (each request gets its own cookies etc.)
        context = await instance.browser.new_context(
            user_agent=USER_AGENT,
            locale="pt-BR",
            timezone_id="America/Sao_Paulo",
            viewport={"width": 1920, "height": 1080},
            ignore_https_errors=True,
            accept_downloads=True,
        )
        await _stealth.apply_stealth_async(context)
        page = await context.new_page()

        session = ScrapeSession(context=context, page=page, _instance=instance)

        try:
            yield session
        finally:
            # Cleanup context but keep browser alive
            try:
                await page.close()
            except Exception:
                pass
            try:
                await context.close()
            except Exception:
                pass
            # Return instance to pool
            await self._available.put(instance)

    async def shutdown(self) -> None:
        """Gracefully close all browser instances."""
        logger.info("browser_pool_shutting_down")
        for instance in self._instances:
            try:
                await instance.browser.close()
                await instance.playwright.stop()
            except Exception as e:
                logger.warning(f"browser_shutdown_error: {e}")
        self._instances.clear()
        self._initialized = False
        logger.info("browser_pool_shutdown_complete")

    def health(self) -> dict:
        """Health check info for /health endpoint."""
        return {
            "initialized": self._initialized,
            "pool_size": self._size,
            "available": self._available.qsize() if self._initialized else 0,
            "total_requests": self._total_requests,
            "instances": [
                {
                    "use_count": i.use_count,
                    "max_uses": i.max_uses,
                    "contexts": len(i.browser.contexts) if self._initialized else 0,
                }
                for i in self._instances
            ],
        }


# ── Module-level singleton ──
browser_pool = BrowserPool(size=2, max_uses_per_browser=20)


# ── Human delay helper ──
async def human_delay(min_s: float = 0.5, max_s: float = 1.5) -> None:
    """Sleep for a random duration to mimic human behavior."""
    jitter = random.uniform(-0.3, 0.3)  # ±30% jitter
    delay = random.uniform(min_s, max_s) * (1 + jitter)
    delay = max(0.1, delay)  # Never sleep less than 100ms
    await asyncio.sleep(delay)
