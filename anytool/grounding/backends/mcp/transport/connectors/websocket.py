"""MCP connector using the WebSocket transports SDK message streams."""
from ..task_managers import WebSocketConnectionManager
from .base import MCPBaseConnector


class WebSocketConnector(MCPBaseConnector):
    def __init__(self, url: str, auth_token: str | None = None, headers: dict[str, str] | None = None):
        self.url = url
        self.auth_token = auth_token
        self.headers = dict(headers or {})
        if auth_token:
            self.headers["Authorization"] = f"Bearer {auth_token}"
        super().__init__(WebSocketConnectionManager(self.url, self.headers))

    @property
    def public_identifier(self) -> dict[str, str]:
        return {"type": "websocket", "url": self.url}
