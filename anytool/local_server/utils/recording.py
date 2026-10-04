"""Drain recording diagnostics without blocking the recording process."""

import threading


class RecordingStderr:
    def __init__(self, stream):
        self.stream = stream
        self._tail = ""
        self._lock = threading.Lock()
        self.thread = threading.Thread(target=self._read, daemon=True)
        self.thread.start()

    def _read(self):
        try:
            while chunk := self.stream.read(4096):
                with self._lock:
                    self._tail = (self._tail + chunk)[-8192:]
        except (OSError, ValueError):
            pass

    def text(self):
        self.thread.join(timeout=2)
        with self._lock:
            return self._tail


def start_recording_stderr(process):
    if process.stderr is not None:
        process._anytool_stderr_capture = RecordingStderr(process.stderr)


def read_recording_stderr(process):
    capture = getattr(process, "_anytool_stderr_capture", None)
    try:
        return capture.text() if capture is not None else "Unknown error"
    finally:
        finish_recording_stderr(process)


def finish_recording_stderr(process):
    if process is None or process.poll() is None:
        return
    capture = getattr(process, "_anytool_stderr_capture", None)
    if capture is not None:
        capture.thread.join(timeout=2)
    for stream in (process.stderr, process.stdin):
        if stream is not None:
            stream.close()
