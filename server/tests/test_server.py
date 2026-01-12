"""Tests for pulse_server.server module."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pulse_server.server import PulseServer


class TestPulseServerInit:
    """Tests for PulseServer initialization."""

    def test_default_values(self):
        """PulseServer uses correct defaults."""
        server = PulseServer()
        assert server.host == "127.0.0.1"
        assert server.port == 8765
        assert server._broadcast_timeout == 0.5
        assert server._clients == set()
        assert server._server is None

    def test_custom_values(self):
        """PulseServer accepts custom values."""
        server = PulseServer(
            host="0.0.0.0",
            port=9000,
            broadcast_timeout=2.0,
        )
        assert server.host == "0.0.0.0"
        assert server.port == 9000
        assert server._broadcast_timeout == 2.0


class TestClientCount:
    """Tests for client_count property."""

    def test_client_count_empty(self):
        """client_count is 0 when no clients connected."""
        server = PulseServer()
        assert server.client_count == 0

    def test_client_count_with_clients(self, mock_websocket):
        """client_count reflects connected clients."""
        server = PulseServer()
        server._clients.add(mock_websocket)
        assert server.client_count == 1

        mock_ws2 = AsyncMock()
        server._clients.add(mock_ws2)
        assert server.client_count == 2

    def test_client_count_after_removal(self, mock_websocket):
        """client_count updates after client removal."""
        server = PulseServer()
        server._clients.add(mock_websocket)
        assert server.client_count == 1

        server._clients.discard(mock_websocket)
        assert server.client_count == 0


class TestBroadcast:
    """Tests for broadcast method."""

    @pytest.mark.asyncio
    async def test_broadcast_no_clients(self):
        """Broadcast with no clients does nothing."""
        server = PulseServer()
        await server.broadcast({"test": "message"})
        # Should not raise

    @pytest.mark.asyncio
    async def test_broadcast_single_client(self, mock_websocket):
        """Broadcast sends to single client."""
        server = PulseServer()
        server._clients.add(mock_websocket)

        await server.broadcast({"bpm": 72})

        mock_websocket.send.assert_called_once()
        sent_data = mock_websocket.send.call_args[0][0]
        assert json.loads(sent_data) == {"bpm": 72}

    @pytest.mark.asyncio
    async def test_broadcast_multiple_clients(self):
        """Broadcast sends to all clients."""
        server = PulseServer()
        clients = [AsyncMock() for _ in range(3)]
        for client in clients:
            server._clients.add(client)

        await server.broadcast({"status": "connected"})

        for client in clients:
            client.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_json_format(self, mock_websocket):
        """Broadcast sends valid JSON."""
        server = PulseServer()
        server._clients.add(mock_websocket)

        message = {"bpm": 85, "timestamp": 1234567890, "rr_ms": [820.5]}
        await server.broadcast(message)

        sent_data = mock_websocket.send.call_args[0][0]
        parsed = json.loads(sent_data)
        assert parsed == message

    @pytest.mark.asyncio
    async def test_broadcast_timeout_handling(self, mock_websocket):
        """Broadcast handles slow client timeout."""
        server = PulseServer(broadcast_timeout=0.01)
        server._clients.add(mock_websocket)

        # Make send take too long
        async def slow_send(_):
            await asyncio.sleep(1)

        mock_websocket.send = slow_send

        # Should not raise, just log warning
        await server.broadcast({"bpm": 72})

    @pytest.mark.asyncio
    async def test_broadcast_exception_handling(self):
        """Broadcast handles client send exceptions."""
        server = PulseServer()

        good_client = AsyncMock()
        bad_client = AsyncMock()
        bad_client.send.side_effect = Exception("Connection closed")

        server._clients.add(good_client)
        server._clients.add(bad_client)

        # Should not raise, gather returns exceptions
        await server.broadcast({"bpm": 72})

        # Good client still receives message
        good_client.send.assert_called_once()


class TestBroadcastHR:
    """Tests for broadcast_hr method."""

    @pytest.mark.asyncio
    async def test_broadcast_hr_basic(self, mock_websocket):
        """broadcast_hr sends bpm and timestamp."""
        server = PulseServer()
        server._clients.add(mock_websocket)

        await server.broadcast_hr(72, [], 1704910800000)

        sent_data = json.loads(mock_websocket.send.call_args[0][0])
        assert sent_data["bpm"] == 72
        assert sent_data["timestamp"] == 1704910800000
        assert "rr_ms" not in sent_data

    @pytest.mark.asyncio
    async def test_broadcast_hr_with_rr(self, mock_websocket):
        """broadcast_hr includes RR intervals when present."""
        server = PulseServer()
        server._clients.add(mock_websocket)

        await server.broadcast_hr(75, [820.3125, 839.84375], 1704910800000)

        sent_data = json.loads(mock_websocket.send.call_args[0][0])
        assert sent_data["bpm"] == 75
        assert "rr_ms" in sent_data
        assert len(sent_data["rr_ms"]) == 2

    @pytest.mark.asyncio
    async def test_broadcast_hr_rr_rounding(self, mock_websocket):
        """broadcast_hr rounds RR intervals to 2 decimals."""
        server = PulseServer()
        server._clients.add(mock_websocket)

        await server.broadcast_hr(75, [820.3456789], 1704910800000)

        sent_data = json.loads(mock_websocket.send.call_args[0][0])
        assert sent_data["rr_ms"] == [820.35]

    @pytest.mark.asyncio
    async def test_broadcast_hr_empty_rr_omitted(self, mock_websocket):
        """broadcast_hr omits rr_ms when list is empty."""
        server = PulseServer()
        server._clients.add(mock_websocket)

        await server.broadcast_hr(80, [], 1704910800000)

        sent_data = json.loads(mock_websocket.send.call_args[0][0])
        assert "rr_ms" not in sent_data


class TestBroadcastStatus:
    """Tests for broadcast_status method."""

    @pytest.mark.asyncio
    async def test_broadcast_status_connecting(self, mock_websocket):
        """broadcast_status sends connecting status."""
        server = PulseServer()
        server._clients.add(mock_websocket)

        await server.broadcast_status("connecting")

        sent_data = json.loads(mock_websocket.send.call_args[0][0])
        assert sent_data == {"status": "connecting"}

    @pytest.mark.asyncio
    async def test_broadcast_status_connected_with_device(self, mock_websocket):
        """broadcast_status includes device when provided."""
        server = PulseServer()
        server._clients.add(mock_websocket)

        await server.broadcast_status("connected", "Polar H10")

        sent_data = json.loads(mock_websocket.send.call_args[0][0])
        assert sent_data == {"status": "connected", "device": "Polar H10"}

    @pytest.mark.asyncio
    async def test_broadcast_status_disconnected(self, mock_websocket):
        """broadcast_status sends disconnected status."""
        server = PulseServer()
        server._clients.add(mock_websocket)

        await server.broadcast_status("disconnected")

        sent_data = json.loads(mock_websocket.send.call_args[0][0])
        assert sent_data == {"status": "disconnected"}

    @pytest.mark.asyncio
    async def test_broadcast_status_device_none(self, mock_websocket):
        """broadcast_status omits device when None."""
        server = PulseServer()
        server._clients.add(mock_websocket)

        await server.broadcast_status("connecting", None)

        sent_data = json.loads(mock_websocket.send.call_args[0][0])
        assert "device" not in sent_data


class TestServerLifecycle:
    """Tests for start/stop methods."""

    @pytest.mark.asyncio
    async def test_start_creates_server(self):
        """start() creates WebSocket server."""
        with patch("pulse_server.server.serve") as mock_serve:
            mock_server = MagicMock()

            # serve() returns an awaitable that yields the server
            async def serve_coro(*args, **kwargs):
                return mock_server

            mock_serve.side_effect = serve_coro

            server = PulseServer(host="localhost", port=8080)
            await server.start()

            mock_serve.assert_called_once()
            call_args = mock_serve.call_args
            assert call_args[0][1] == "localhost"
            assert call_args[0][2] == 8080
            assert server._server == mock_server

    @pytest.mark.asyncio
    async def test_stop_closes_server(self):
        """stop() closes WebSocket server."""
        mock_server = MagicMock()
        mock_server.close = MagicMock()
        mock_server.wait_closed = AsyncMock()

        server = PulseServer()
        server._server = mock_server

        await server.stop()

        mock_server.close.assert_called_once()
        mock_server.wait_closed.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_without_server(self):
        """stop() does nothing when server not started."""
        server = PulseServer()
        await server.stop()
        # Should not raise


class TestHandler:
    """Tests for _handler method."""

    @pytest.mark.asyncio
    async def test_handler_adds_client(self, mock_websocket):
        """_handler adds client to set on connect."""
        server = PulseServer()

        # Simulate empty message iteration
        mock_websocket.__aiter__ = lambda self: self
        mock_websocket.__anext__ = AsyncMock(side_effect=StopAsyncIteration)

        await server._handler(mock_websocket)

        # Client should be removed after handler completes
        assert mock_websocket not in server._clients

    @pytest.mark.asyncio
    async def test_handler_removes_client_on_disconnect(self, mock_websocket):
        """_handler removes client when connection closes."""
        server = PulseServer()

        mock_websocket.__aiter__ = lambda self: self
        mock_websocket.__anext__ = AsyncMock(side_effect=StopAsyncIteration)

        # Add client manually then run handler
        server._clients.add(mock_websocket)
        assert server.client_count == 1

        await server._handler(mock_websocket)

        # Handler should have removed client via finally block
        # (Note: handler adds then removes in same call, so empty after)
        assert server.client_count == 0

    @pytest.mark.asyncio
    async def test_handler_removes_client_on_exception(self, mock_websocket):
        """_handler removes client when exception occurs."""
        server = PulseServer()

        mock_websocket.__aiter__ = lambda self: self
        mock_websocket.__anext__ = AsyncMock(side_effect=Exception("Connection lost"))

        with pytest.raises(Exception, match="Connection lost"):
            await server._handler(mock_websocket)

        assert mock_websocket not in server._clients
