from anytool.grounding.core.session import BaseSession
from anytool.grounding.core.types import BackendType, SessionStatus


class Session(BaseSession):
    async def initialize(self):
        return {}


def test_session_info_uses_the_configured_session_name():
    session = Session(None, session_id="shell:example", backend_type=BackendType.SHELL)
    session.session_info = {"version": "test"}
    info = session.info
    assert info.session_name == "shell:example"
    assert info.backend_type == BackendType.SHELL
    assert info.status == SessionStatus.DISCONNECTED
    assert info.created_at == session._created_at
    assert info.metadata == {"version": "test"}
