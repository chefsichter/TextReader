"""Small local command bridge for desktop-managed hotkeys and single-instance UX."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket


CommandCallback = Callable[[str], None]


class LocalCommandServer(QObject):
    """Receive lightweight commands from secondary launcher invocations."""

    command_received = Signal(str)

    def __init__(self, server_name: str) -> None:
        super().__init__()
        self._server_name = server_name
        self._server = QLocalServer(self)
        self._server.newConnection.connect(self._consume_pending_connections)

    @property
    def server_name(self) -> str:
        return self._server_name

    def start(self) -> bool:
        """Start listening and remove stale sockets when required."""

        if self._server.listen(self._server_name):
            return True
        QLocalServer.removeServer(self._server_name)
        return self._server.listen(self._server_name)

    def stop(self) -> None:
        """Stop listening for local commands."""

        self._server.close()

    def _consume_pending_connections(self) -> None:
        while self._server.hasPendingConnections():
            socket = self._server.nextPendingConnection()
            socket.readyRead.connect(
                lambda current_socket=socket: self._read_command(current_socket),
            )
            socket.disconnected.connect(socket.deleteLater)

    def _read_command(self, socket: QLocalSocket) -> None:
        payload = bytes(socket.readAll()).decode("utf-8", errors="ignore").strip()
        if payload:
            self.command_received.emit(payload)
        socket.disconnectFromServer()


def send_local_command(server_name: str, command: str, timeout_ms: int = 1000) -> bool:
    """Send one command to a running app instance if it exists."""

    socket = QLocalSocket()
    socket.connectToServer(server_name)
    if not socket.waitForConnected(timeout_ms):
        return False
    socket.write(command.encode("utf-8"))
    socket.flush()
    socket.waitForBytesWritten(timeout_ms)
    socket.disconnectFromServer()
    return True
