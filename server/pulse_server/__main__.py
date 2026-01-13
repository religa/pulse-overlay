"""Entry point for pulse-server."""

import argparse
import asyncio
import logging
import signal

from .ble import PulseMonitor, scan_hr_devices
from .config import Config, load_config
from .log import setup_logging
from .server import PulseServer

logger = logging.getLogger(__name__)

# Shutdown event for graceful termination
_shutdown_event: asyncio.Event | None = None


def _signal_handler() -> None:
    """Handle shutdown signals."""
    if _shutdown_event:
        logger.info("Shutdown requested...")
        _shutdown_event.set()


def _filter_description(name_filter: str | None) -> str:
    """Return description suffix for filter-aware messages."""
    return f" matching '{name_filter}'" if name_filter else ""


def _prompt_device_selection(devices: list[tuple[str, str]]) -> str:
    """Prompt user to select a device from the list."""
    print("Found devices:")
    for i, (addr, name) in enumerate(devices, 1):
        print(f"  {i}. {name} ({addr})")

    while True:
        choice = input("Select device [1]: ").strip() or "1"
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(devices):
                return devices[idx][0]
        except ValueError:
            pass
        print("Invalid selection, try again.")


async def scan_until_found(
    config: Config,
    name_filter: str | None,
    server: "PulseServer",
) -> str | None:
    """Scan repeatedly until a device is found, returning its address."""
    desc = _filter_description(name_filter)

    while not (_shutdown_event and _shutdown_event.is_set()):
        await server.broadcast_status("scanning", None)
        logger.info("Scanning for HR devices%s...", desc)

        devices = await scan_hr_devices(
            timeout=config.ble.scan_timeout,
            name_filter=name_filter,
        )

        if devices:
            # Auto-select if single device or filter was used
            if len(devices) == 1 or name_filter:
                logger.info("Found: %s (%s)", devices[0][1], devices[0][0])
                return devices[0][0]
            return _prompt_device_selection(devices)

        logger.warning("No HR devices%s found, retrying in %.0fs...", desc, config.ble.scan_timeout)
        await asyncio.sleep(config.ble.scan_timeout)

    return None


async def run(config: Config, host: str, port: int, device: str | None, name_filter: str | None) -> None:
    """Run the Pulse server."""
    global _shutdown_event
    _shutdown_event = asyncio.Event()

    # Set up signal handlers for graceful shutdown
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _signal_handler)

    # Start server first so clients can connect during scanning
    server = PulseServer(
        host=host,
        port=port,
        broadcast_timeout=config.server.broadcast_timeout,
    )
    await server.start()
    logger.info("WebSocket server running on ws://%s:%d", host, port)

    monitor = None
    try:
        # Find device (scan repeatedly if needed)
        if device:
            address = device
        else:
            address = await scan_until_found(config, name_filter, server)

        # Check if shutdown was requested during scanning
        if address is None:
            return

        # Start monitor
        monitor = PulseMonitor(
            address=address,
            on_hr=server.broadcast_hr,
            on_status=server.broadcast_status,
            reconnect_min=config.ble.reconnect_min,
            reconnect_max=config.ble.reconnect_max,
        )

        # Run monitor and wait for shutdown signal concurrently
        monitor_task = asyncio.create_task(monitor.run())
        shutdown_task = asyncio.create_task(_shutdown_event.wait())

        # Wait for either shutdown signal or monitor to exit
        done, pending = await asyncio.wait(
            [monitor_task, shutdown_task],
            return_when=asyncio.FIRST_COMPLETED,
        )

        # Cancel pending tasks
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    finally:
        if monitor:
            await monitor.stop()
        await server.stop()
        logger.info("Shutdown complete")


def main() -> None:
    """CLI entry point."""
    config = load_config()

    parser = argparse.ArgumentParser(description="BLE Heart Rate WebSocket Server")
    parser.add_argument("-H", "--host", default=config.server.host, help="Server host")
    parser.add_argument("-p", "--port", type=int, default=config.server.port, help="Server port")
    parser.add_argument("-d", "--device", default=config.device.address or None, help="Device address (skip scanning)")
    parser.add_argument(
        "-n",
        "--name",
        default=config.device.name_filter or None,
        help="Filter by device name (case-insensitive, auto-connects to first match)",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    # Setup logging before anything else
    log_level = "DEBUG" if args.verbose else config.server.log_level
    setup_logging(log_level)

    asyncio.run(run(config, args.host, args.port, args.device, args.name))


if __name__ == "__main__":
    main()
