import asyncio
import pytest

from anytool.grounding.core.search_tools import SearchCoordinator
from anytool.grounding.core.tool.base import BaseTool
from anytool.grounding.core.types import BackendType, ToolSchema


class SampleTool(BaseTool):
    async def _arun(self):
        return "unused"


@pytest.mark.parametrize("mutate_result", [False, True])
def test_search_cache_tracks_candidate_contents_and_does_not_share_result_lists(mutate_result):
    coordinator = SearchCoordinator(enable_llm_filter=False, enable_cache_persistence=False)
    first, second = SampleTool(), SampleTool()
    candidates = [first]

    async def run():
        result = await coordinator._arun("same task", candidates)
        assert result == [first]
        if mutate_result:
            result.clear()
        assert await coordinator._arun("same task", candidates) == [first]
        candidates[:] = [second]
        assert await coordinator._arun("same task", candidates) == [second]

    asyncio.run(run())


def test_search_cache_recomputes_ranking_after_description_changes():
    coordinator = SearchCoordinator(enable_llm_filter=False, enable_cache_persistence=False)
    first, second = [SampleTool(schema=ToolSchema(name=name, description=description, backend_type=BackendType.MCP))
                     for name, description in [("first", "weather"), ("second", "calendar")]]
    for tool in (first, second):
        tool.bind_runtime_info(BackendType.MCP, "session", server_name="server")
    candidates = [first, second]

    async def run():
        assert await coordinator._arun("weather", candidates, mode="keyword", max_tools=1) == [first]
        first.schema.description = "calendar"
        second.schema.description = "weather"
        assert await coordinator._arun("weather", candidates, mode="keyword", max_tools=1) == [second]

    asyncio.run(run())
