import asyncio
import json
import pytest

from websockets.asyncio.server import serve

from anytool.grounding.backends.mcp.transport.connectors.websocket import WebSocketConnector


@pytest.mark.parametrize("auth_token", [None, "test-token"])
def test_websocket_initializes_and_calls_tools_through_sdk_streams(auth_token):
    async def run():
        methods = []

        async def handle(socket):
            assert socket.request.headers.get("Authorization") == (f"Bearer {auth_token}" if auth_token else None)
            async for raw in socket:
                request = json.loads(raw)
                methods.append(request["method"])
                if "id" not in request:
                    continue
                if request["method"] == "initialize":
                    result = {
                        "protocolVersion": request["params"]["protocolVersion"],
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "test", "version": "1"},
                    }
                elif request["method"] == "tools/list":
                    result = {"tools": [{"name": "echo", "inputSchema": {"type": "object"}}]}
                elif request["method"] == "tools/call":
                    result = {"content": [{"type": "text", "text": "echoed"}], "isError": False}
                else:
                    raise AssertionError(request)
                await socket.send(json.dumps({"jsonrpc": "2.0", "id": request["id"], "result": result}))

        async with serve(handle, "127.0.0.1", 0, subprotocols=["mcp"]) as server:
            port = server.sockets[0].getsockname()[1]
            connector = WebSocketConnector(f"ws://127.0.0.1:{port}", auth_token=auth_token)
            try:
                await connector.connect()
                assert connector.is_connected
                await connector.initialize()
                assert [tool.name for tool in connector.tools] == ["echo"]
                result = await connector.call_tool("echo", {})
                assert result.content[0].text == "echoed"
            finally:
                await connector.disconnect()
            assert not connector.is_connected
            assert connector._connection_manager._task.done()
            assert connector._connection_manager.get_streams() is None
            assert "notifications/initialized" in methods

    asyncio.run(asyncio.wait_for(run(), timeout=10))
