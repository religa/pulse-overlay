"""WebSocket server for broadcasting heart rate data."""

import asyncio
import json
import logging

from websockets.asyncio.server import ServerConnection, serve
from websockets.exceptions import ConnectionClosedError

logger = logging.getLogger(__name__)


class PulseServer:
    """WebSocket server that broadcasts HR data to all connected clients."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8765,
        broadcast_timeout: float = 0.5,
    ):
        self.host = host
        self.port = port
        self._broadcast_timeout = broadcast_timeout
        self._clients: set[ServerConnection] = set()
        self._server = None

    def _client_info(self, websocket: ServerConnection) -> str:
        """Get client info string for logging."""
        addr = websocket.remote_address
        if addr:
            return f"{addr[0]}:{addr[1]}"
        return "unknown"

    async def _handler(self, websocket: ServerConnection) -> None:
        """Handle a WebSocket connection."""
        self._clients.add(websocket)
        logger.info("Client connected: %s (%d total)", self._client_info(websocket), len(self._clients))
        try:
            async for _ in websocket:
                pass  # We don't expect messages from clients
        except ConnectionClosedError:
            pass  # Client disconnected abruptly, this is normal
        finally:
            self._clients.discard(websocket)
            logger.info("Client disconnected: %s (%d total)", self._client_info(websocket), len(self._clients))

    async def broadcast(self, message: dict) -> None:
        """Broadcast a message to all connected clients."""
        if not self._clients:
            return
        # Snapshot clients to avoid RuntimeError if set changes during iteration
        clients = list(self._clients)
        data = json.dumps(message)
        try:
            results = await asyncio.wait_for(
                asyncio.gather(
                    *[client.send(data) for client in clients],
                    return_exceptions=True,
                ),
                timeout=self._broadcast_timeout,
            )
            # Remove clients that failed to receive
            self._remove_failed_clients(clients, results)
        except TimeoutError:
            logger.warning("Broadcast timeout, slow client(s) skipped")

    def _remove_failed_clients(self, clients: list[ServerConnection], results: list) -> None:
        """Remove clients that failed to receive a message."""
        for client, result in zip(clients, results, strict=True):
            if isinstance(result, Exception):
                self._clients.discard(client)
                logger.debug("Removed failed client: %s", result)

    async def broadcast_hr(self, bpm: int, rr_ms: list[float], timestamp_ms: int) -> None:
        """Broadcast heart rate data."""
        msg: dict[str, int | list[float]] = {"bpm": bpm, "timestamp": timestamp_ms}
        if rr_ms:
            msg["rr_ms"] = [round(rr, 2) for rr in rr_ms]
        await self.broadcast(msg)

    async def broadcast_status(self, status: str, device: str | None = None) -> None:
        """Broadcast status message."""
        msg = {"status": status}
        if device:
            msg["device"] = device
        await self.broadcast(msg)

    async def start(self) -> None:
        """Start the WebSocket server."""
        self._server = await serve(self._handler, self.host, self.port)
        logger.debug("Server started on %s:%d", self.host, self.port)

    async def stop(self) -> None:
        """Stop the WebSocket server."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            logger.debug("Server stopped")

    @property
    def client_count(self) -> int:
        """Number of connected clients."""
        return len(self._clients)
