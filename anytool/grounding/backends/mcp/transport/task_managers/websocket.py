"""
WebSocket connection management for MCP implementations.

This module provides a connection manager for WebSocket-based MCP connections.
"""

from contextlib import asynccontextmanager
from typing import Any, Tuple
import anyio
from mcp import types
from mcp.shared.message import SessionMessage
from pydantic import ValidationError
from websockets.asyncio.client import connect
from anytool.utils.logging import Logger
from anytool.grounding.core.transport.task_managers import (
    AsyncContextConnectionManager,
)

logger = Logger.get_logger(__name__)


@asynccontextmanager
async def _websocket_streams(url: str, headers: dict[str, str]):
    read_sender, read_stream = anyio.create_memory_object_stream(0)
    write_stream, write_receiver = anyio.create_memory_object_stream(0)
    async with connect(url, additional_headers=headers, subprotocols=["mcp"]) as socket:
        async def receive():
            async with read_sender:
                async for raw in socket:
                    try:
                        message = SessionMessage(types.JSONRPCMessage.model_validate_json(raw))
                    except ValidationError as error:
                        message = error
                    await read_sender.send(message)

        async def send():
            async with write_receiver:
                async for message in write_receiver:
                    await socket.send(message.message.model_dump_json(by_alias=True, exclude_none=True))

        async with anyio.create_task_group() as group:
            group.start_soon(receive)
            group.start_soon(send)
            try:
                yield read_stream, write_stream
            finally:
                group.cancel_scope.cancel()

class WebSocketConnectionManager(
    AsyncContextConnectionManager[Tuple[Any, Any], ...]
):

    def __init__(self, url: str, headers: dict[str, str] | None = None):
        self.url = url
        self.headers = dict(headers or {})
        super().__init__(_websocket_streams, url, self.headers)
        logger.debug("WebSocketConnectionManager init url=%s", url)
