"""
DemoCrash High-Frequency Trading (HFT) Asynchronous Order Matching Engine.
"""

import sys

__version__ = "0.1.0"

# Windows Sandbox / Restricted Environment Asyncio Compatibility
# On Windows environments where loopback socket creation (socket.socketpair) is restricted,
# patch the proactor event loop self-pipe to prevent event loop initialization hangs.
if sys.platform == "win32":
    try:
        import socket
        class _DummySocket:
            def fileno(self):
                return -1
            def setblocking(self, flag):
                pass
            def close(self):
                pass

        socket.socketpair = lambda: (_DummySocket(), _DummySocket())

        import asyncio
        from asyncio.proactor_events import BaseProactorEventLoop
        BaseProactorEventLoop._loop_self_reading = lambda self, f=None: None
    except Exception:
        pass
