"""
http_client.py
--------------
Shared httpx.AsyncClient with connection pooling, explicit timeouts,
and retry-with-backoff for transient failures.

Usage:
    from app.http_client import HttpClient

    # In lifespan startup:
    HttpClient.start()

    # In lifespan shutdown:
    await HttpClient.stop()

    # In services:
    client = HttpClient.get()
    response = await client.post(url, json=payload)

    # With retry:
    response = await HttpClient.request_with_retry("POST", url, json=payload)
"""

import asyncio
import httpx
from typing import Optional
from app.utils.logger import get_dobo_logger

logger = get_dobo_logger(__name__)


# Connection pool limits
_POOL_LIMITS = httpx.Limits(
    max_connections=50,
    max_keepalive_connections=20,
    keepalive_expiry=30,
)

# Default timeouts
_TIMEOUT = httpx.Timeout(
    connect=5.0,     # 5s to establish connection
    read=15.0,       # 15s to read response
    write=10.0,      # 10s to send request
    pool=10.0,       # 10s waiting for a connection from pool
)

# Retry config
MAX_RETRIES = 3
RETRY_BACKOFF = [0.5, 1.0, 2.0]  # seconds between retries
RETRYABLE_STATUS_CODES = {502, 503, 504, 429}


class HttpClient:
    """
    Singleton async HTTP client with connection pooling.
    Start once at app lifespan, reuse across all services.
    """

    _client: Optional[httpx.AsyncClient] = None

    @classmethod
    def start(cls):
        """Create the shared client. Call once at app startup."""
        if cls._client is not None:
            return
        cls._client = httpx.AsyncClient(
            limits=_POOL_LIMITS,
            timeout=_TIMEOUT,
            follow_redirects=True,
        )
        logger.info("Shared async client started (pool: 50 max, 20 keepalive)")

    @classmethod
    async def stop(cls):
        """Close the shared client. Call at app shutdown."""
        if cls._client is not None:
            await cls._client.aclose()
            cls._client = None
            logger.info("Shared async client closed")

    @classmethod
    def get(cls) -> httpx.AsyncClient:
        """Get the shared client instance."""
        if cls._client is None:
            raise RuntimeError("HttpClient not started. Call HttpClient.start() in lifespan.")
        return cls._client

    @classmethod
    async def request_with_retry(
        cls,
        method: str,
        url: str,
        max_retries: int = MAX_RETRIES,
        **kwargs,
    ) -> httpx.Response:
        """
        Make an HTTP request with retry + exponential backoff for transient failures.

        Retries on:
          - Connection errors (httpx.ConnectError, httpx.ConnectTimeout)
          - 502, 503, 504, 429 status codes

        Does NOT retry on:
          - 4xx client errors (except 429)
          - Timeouts on read (the request reached the server)

        Returns the response or raises the last exception.
        """
        client = cls.get()
        last_error: Optional[Exception] = None

        for attempt in range(max_retries + 1):
            try:
                response = await client.request(method, url, **kwargs)

                # Success or non-retryable error
                if response.status_code not in RETRYABLE_STATUS_CODES:
                    return response

                # Retryable status code
                if attempt < max_retries:
                    wait = RETRY_BACKOFF[min(attempt, len(RETRY_BACKOFF) - 1)]
                    await asyncio.sleep(wait)
                    continue

                return response  # Final attempt, return whatever we got

            except (httpx.ConnectError, httpx.ConnectTimeout) as e:
                last_error = e
                if attempt < max_retries:
                    wait = RETRY_BACKOFF[min(attempt, len(RETRY_BACKOFF) - 1)]
                    await asyncio.sleep(wait)
                    continue
                raise

            except httpx.TimeoutException:
                # Read/write timeout — request reached server, don't retry
                raise

        # Should not reach here, but safety net
        if last_error:
            raise last_error
        raise RuntimeError("Unexpected retry loop exit")
