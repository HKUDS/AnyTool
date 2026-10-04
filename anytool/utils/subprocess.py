"""Lifecycle helpers for locally executed asynchronous subprocesses."""

import asyncio
import os
import signal


def process_group_options():
    return {"start_new_session": True} if os.name != "nt" else {}


async def communicate_with_timeout(process, timeout):
    try:
        return await asyncio.wait_for(process.communicate(), timeout=timeout)
    except (asyncio.TimeoutError, asyncio.CancelledError):
        if os.name == "nt":
            if process.returncode is None:
                # Terminate the owned command's descendants as well as its shell.
                killer = await asyncio.create_subprocess_exec(
                    os.path.join(os.environ["SystemRoot"], "System32", "taskkill.exe"),
                    "/PID", str(process.pid), "/T", "/F",
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await killer.wait()
                if process.returncode is None:
                    try:
                        process.kill()
                    except ProcessLookupError:
                        pass
        else:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        await process.communicate()
        raise
