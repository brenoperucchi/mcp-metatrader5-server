"""
MetaTrader 5 MCP Server - Tick Persistence Module

Asynchronous tick persistence to PostgreSQL with:
- asyncio.Queue for non-blocking enqueue
- Batch processing (size + timeout triggers)
- Backpressure control
- Graceful shutdown with buffer flush
- Idempotent inserts
- Retry logic with exponential backoff
"""

import asyncio
import asyncpg
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from collections import deque
import logging
from pathlib import Path

logger = logging.getLogger("mt5-mcp-server.tick_persister")


class TickPersisterConfig:
    """Configuration for tick persistence"""

    def __init__(self, config_dict: Dict[str, Any]):
        # Database configuration
        db_config = config_dict.get("database", {})
        self.db_host = db_config.get("host", "localhost")
        self.db_port = db_config.get("port", 5432)
        self.db_name = db_config.get("database", "jumpstart_development")
        self.db_schema = db_config.get("schema", "trading")
        self.db_table = db_config.get("table", "mt5_ticks_1s")
        self.db_user = db_config.get("username", "postgres")
        self.db_password = db_config.get("password", "postgres")

        # Batch configuration
        batch_config = config_dict.get("batch", {})
        self.batch_size = batch_config.get("size", 20)
        self.batch_timeout = batch_config.get("timeout_seconds", 5.0)

        # Backpressure configuration
        backpressure_config = config_dict.get("backpressure", {})
        self.max_queue_size = backpressure_config.get("max_queue_size", 1000)

        # Feature flag
        self.enabled = config_dict.get("enabled", True)

    @property
    def db_dsn(self) -> str:
        """Get PostgreSQL DSN connection string"""
        return (
            f"postgresql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


class TickPersister:
    """
    Asynchronous tick persister using asyncio.Queue and asyncpg.

    Architecture:
    1. enqueue_tick() - Non-blocking (< 0.01ms), puts tick in queue
    2. _worker() - Background task that batches and persists ticks
    3. Batch triggers: size (default 20) OR timeout (default 5s)
    4. Backpressure: Drops oldest ticks if queue full
    5. Graceful shutdown: Flushes remaining ticks on stop
    """

    def __init__(self, config: TickPersisterConfig):
        self.config = config
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=config.max_queue_size)
        self.db_pool: Optional[asyncpg.Pool] = None
        self.worker_task: Optional[asyncio.Task] = None
        self.running = False

        # Statistics
        self.stats = {
            "total_enqueued": 0,
            "total_persisted": 0,
            "total_dropped": 0,
            "batch_count": 0,
            "error_count": 0
        }

    async def start(self):
        """Initialize database connection and start background worker"""
        if not self.config.enabled:
            logger.info("TickPersister is disabled in configuration")
            return

        try:
            # Create database connection pool
            self.db_pool = await asyncpg.create_pool(
                dsn=self.config.db_dsn,
                min_size=1,
                max_size=5,
                command_timeout=60
            )

            # Ensure table exists
            await self._ensure_table_exists()

            # Start background worker
            self.running = True
            self.worker_task = asyncio.create_task(self._worker())

            logger.info(
                f"TickPersister initialized - DB: {self.config.db_host}:"
                f"{self.config.db_port}/{self.config.db_name}, "
                f"Table: {self.config.db_schema}.{self.config.db_table}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize TickPersister: {e}")
            logger.info("Tick persistence will be disabled, but streaming continues normally")
            self.config.enabled = False

    async def _ensure_table_exists(self):
        """Create table if it doesn't exist"""
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {self.config.db_schema}.{self.config.db_table} (
            timestamp TIMESTAMPTZ NOT NULL,
            symbol TEXT NOT NULL,
            open DOUBLE PRECISION,
            high DOUBLE PRECISION,
            low DOUBLE PRECISION,
            close DOUBLE PRECISION,
            volume BIGINT,
            bid DOUBLE PRECISION,
            ask DOUBLE PRECISION,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            PRIMARY KEY (timestamp, symbol)
        );

        CREATE INDEX IF NOT EXISTS idx_mt5_ticks_1s_symbol_time
        ON {self.config.db_schema}.{self.config.db_table} (symbol, timestamp DESC);
        """

        async with self.db_pool.acquire() as conn:
            await conn.execute(create_table_sql)
            logger.info(f"Table {self.config.db_schema}.{self.config.db_table} ready")

    async def enqueue_tick(self, tick: Dict[str, Any]):
        """
        Non-blocking tick enqueue (< 0.01ms).

        Args:
            tick: Tick data with keys: symbol, timestamp, bid, ask, last, volume
        """
        if not self.config.enabled or not self.running:
            return

        try:
            # Non-blocking put
            self.queue.put_nowait(tick)
            self.stats["total_enqueued"] += 1

        except asyncio.QueueFull:
            # Backpressure: Drop oldest tick
            try:
                dropped_tick = self.queue.get_nowait()
                self.stats["total_dropped"] += 1

                # Now add the new tick
                self.queue.put_nowait(tick)
                self.stats["total_enqueued"] += 1

                if self.stats["total_dropped"] % 100 == 1:  # Log every 100 drops
                    logger.warning(
                        f"Queue full ({self.config.max_queue_size} ticks) - "
                        f"Dropped oldest tick | Total dropped: {self.stats['total_dropped']}"
                    )
            except Exception as e:
                logger.error(f"Error handling queue full: {e}")

    async def _worker(self):
        """Background worker that batches and persists ticks"""
        buffer: List[Dict[str, Any]] = []
        last_flush_time = asyncio.get_event_loop().time()

        while self.running:
            try:
                # Calculate remaining timeout
                elapsed = asyncio.get_event_loop().time() - last_flush_time
                remaining_timeout = max(0.1, self.config.batch_timeout - elapsed)

                try:
                    # Wait for tick OR timeout
                    tick = await asyncio.wait_for(
                        self.queue.get(),
                        timeout=remaining_timeout
                    )
                    buffer.append(tick)

                    # Flush if batch size reached
                    if len(buffer) >= self.config.batch_size:
                        await self._flush_batch(buffer)
                        buffer = []
                        last_flush_time = asyncio.get_event_loop().time()

                except asyncio.TimeoutError:
                    # Timeout: Flush partial batch
                    if buffer:
                        await self._flush_batch(buffer)
                        buffer = []
                    last_flush_time = asyncio.get_event_loop().time()

            except asyncio.CancelledError:
                # Graceful shutdown: Flush remaining ticks
                if buffer:
                    logger.info(f"Flushing remaining ticks before shutdown: {len(buffer)} ticks")
                    await self._flush_batch(buffer)
                break

            except Exception as e:
                logger.error(f"Worker error: {e}")
                await asyncio.sleep(1)  # Avoid tight loop on persistent errors

    async def _flush_batch(self, batch: List[Dict[str, Any]], retry_count: int = 0):
        """
        Persist batch to database with retry logic.

        Args:
            batch: List of tick dictionaries
            retry_count: Current retry attempt (for exponential backoff)
        """
        if not batch:
            return

        start_time = asyncio.get_event_loop().time()

        try:
            # Prepare batch insert with idempotent ON CONFLICT
            insert_sql = f"""
            INSERT INTO {self.config.db_schema}.{self.config.db_table}
            (timestamp, symbol, open, high, low, close, volume, bid, ask)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            ON CONFLICT (timestamp, symbol) DO NOTHING
            """

            # Convert ticks to PostgreSQL rows
            rows = []
            for tick in batch:
                # Ensure timestamp is UTC
                timestamp = tick.get("timestamp")
                if isinstance(timestamp, datetime):
                    if timestamp.tzinfo is None:
                        timestamp = timestamp.replace(tzinfo=timezone.utc)
                else:
                    # If timestamp is milliseconds
                    timestamp = datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)

                # Map tick to OHLC (use 'last' for all OHLC since it's a tick)
                last_price = tick.get("last", tick.get("close", 0))

                rows.append((
                    timestamp,
                    tick.get("symbol", "UNKNOWN"),
                    last_price,  # open
                    last_price,  # high
                    last_price,  # low
                    last_price,  # close
                    tick.get("volume", 0),
                    tick.get("bid", 0),
                    tick.get("ask", 0)
                ))

            # Bulk insert
            async with self.db_pool.acquire() as conn:
                await conn.executemany(insert_sql, rows)

            # Update statistics
            elapsed_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            self.stats["total_persisted"] += len(batch)
            self.stats["batch_count"] += 1

            logger.info(
                f"Batch persisted: {len(batch)} ticks in {elapsed_ms:.0f}ms | "
                f"Queue size: {self.queue.qsize()} | "
                f"Total persisted: {self.stats['total_persisted']:,}"
            )

        except Exception as e:
            self.stats["error_count"] += 1
            logger.error(f"Failed to persist batch ({len(batch)} ticks) - Error: {e}")

            # Retry with exponential backoff (max 3 retries)
            if retry_count < 3:
                backoff_delay = min(60, 2 ** retry_count)  # 1s, 2s, 4s, max 60s
                logger.info(f"Retrying in {backoff_delay}s... (attempt {retry_count + 1}/3)")
                await asyncio.sleep(backoff_delay)
                await self._flush_batch(batch, retry_count + 1)
            else:
                logger.warning(
                    f"Discarding batch after 3 failed attempts ({len(batch)} ticks lost)"
                )

    async def stop(self):
        """Graceful shutdown: Stop worker and flush remaining ticks"""
        if not self.running:
            return

        logger.info("Stopping TickPersister...")
        self.running = False

        # Cancel worker task (will trigger flush in worker)
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await asyncio.wait_for(self.worker_task, timeout=30)
            except asyncio.TimeoutError:
                logger.warning("Worker shutdown timeout after 30s")
            except asyncio.CancelledError:
                pass

        # Close database pool
        if self.db_pool:
            await self.db_pool.close()

        # Log final statistics
        logger.info(
            f"TickPersister shutdown complete - "
            f"Total persisted: {self.stats['total_persisted']:,} | "
            f"Total dropped: {self.stats['total_dropped']:,} | "
            f"Batches: {self.stats['batch_count']} | "
            f"Errors: {self.stats['error_count']}"
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get persistence statistics"""
        return {
            **self.stats,
            "queue_size": self.queue.qsize(),
            "running": self.running,
            "enabled": self.config.enabled
        }
