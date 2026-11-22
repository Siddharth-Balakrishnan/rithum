
"""Unix Domain Socket server for Rithum IPC."""

from __future__ import annotations

import logging
import os
import socket
import stat
import struct
import threading

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .framing import (
    FramingError,
    recv_frame,
    send_frame,
)
from .models import (
    Component,
    MessageEnvelope,
)
from .validator import (
    MessageValidationError,
    validate_message,
)


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Peer credentials
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class PeerCredentials:
    """Linux process credentials obtained from a connected socket."""

    pid: int
    uid: int
    gid: int


PeerIdentityResolver = Callable[
    [PeerCredentials],
    str | None,
]

MessageHandler = Callable[
    [MessageEnvelope],
    MessageEnvelope | None,
]


# ---------------------------------------------------------------------------
# IPC server
# ---------------------------------------------------------------------------

class IPCServer:
    """
    Multi-client Unix Domain Socket server.

    Each connected client is handled by a separate daemon thread.

    Incoming messages are framed, decoded, validated, and then passed
    to the configured message handler.
    """

    def __init__(
        self,
        socket_path: str | Path,
        on_message: MessageHandler,
        *,
        component: Component | str = Component.SUPERVISOR,
        allowed_uids: set[int] | None = None,
        peer_identity_resolver: PeerIdentityResolver | None = None,
        max_connections: int = 16,
        backlog: int = 16,
    ) -> None:

        if not callable(on_message):
            raise TypeError("on_message must be callable.")

        if max_connections < 1:
            raise ValueError("max_connections must be at least 1.")

        if backlog < 1:
            raise ValueError("backlog must be at least 1.")

        self.socket_path = Path(socket_path)
        self.component = str(component)
        self.on_message = on_message

        # Default: only processes running under the server's UID.
        self.allowed_uids = (
            {os.getuid()}
            if allowed_uids is None
            else set(allowed_uids)
        )

        self.peer_identity_resolver = peer_identity_resolver

        self.max_connections = max_connections
        self.backlog = backlog

        self._server_socket: socket.socket | None = None

        self._running = False

        self._accept_thread: threading.Thread | None = None

        self._connections: set[socket.socket] = set()

        self._connection_threads: set[threading.Thread] = set()

        self._lock = threading.RLock()

        self._connection_slots = threading.BoundedSemaphore(
            max_connections
        )

        self._socket_identity: tuple[int, int] | None = None

    # -----------------------------------------------------------------------
    # Server lifecycle
    # -----------------------------------------------------------------------

    @property
    def is_running(self) -> bool:
        """Return whether the server is running."""

        with self._lock:
            return self._running

    def start(self) -> None:
        """Create the socket and start the background accept thread."""

        with self._lock:

            if self._running:
                raise RuntimeError("IPC server is already running.")

            self._prepare_socket_directory()

            server_socket = socket.socket(
                socket.AF_UNIX,
                socket.SOCK_STREAM,
            )

            try:
                server_socket.bind(str(self.socket_path))

                os.chmod(self.socket_path, 0o600)

                socket_stat = self.socket_path.lstat()

                self._socket_identity = (
                    socket_stat.st_dev,
                    socket_stat.st_ino,
                )

                server_socket.listen(self.backlog)

                # Periodically wake up so stop() can terminate the loop.
                server_socket.settimeout(0.5)

            except Exception:
                server_socket.close()
                self._remove_socket_file()
                raise

            self._server_socket = server_socket
            self._running = True

            self._accept_thread = threading.Thread(
                target=self._accept_loop,
                name="rithum-ipc-accept",
                daemon=True,
            )

            self._accept_thread.start()

        logger.info(
            "IPC server started at %s",
            self.socket_path,
        )

    def stop(self) -> None:
        """Stop accepting connections and close active clients."""

        with self._lock:

            if not self._running:
                return

            self._running = False

            server_socket = self._server_socket
            self._server_socket = None

            connections = list(self._connections)

            accept_thread = self._accept_thread

        if server_socket is not None:
            server_socket.close()

        for connection in connections:
            try:
                connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

            try:
                connection.close()
            except OSError:
                pass

        if (
            accept_thread is not None
            and accept_thread is not threading.current_thread()
        ):
            accept_thread.join(timeout=2.0)

        self._remove_socket_file()

        with self._lock:
            self._connections.clear()
            self._connection_threads.clear()
            self._accept_thread = None

        logger.info("IPC server stopped.")

    def __enter__(self) -> IPCServer:
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.stop()

    # -----------------------------------------------------------------------
    # Socket preparation
    # -----------------------------------------------------------------------

    def _prepare_socket_directory(self) -> None:
        """Create a private socket directory if necessary."""

        parent = self.socket_path.parent

        if parent.is_symlink():
            raise PermissionError(
                "IPC socket directory must not be a symbolic link."
            )

        existed = parent.exists()

        parent.mkdir(
            mode=0o700,
            parents=True,
            exist_ok=True,
        )

        if not parent.is_dir():
            raise NotADirectoryError(
                f"Socket parent is not a directory: {parent}"
            )

        if not existed:
            os.chmod(parent, 0o700)

        directory_stat = parent.stat()

        if directory_stat.st_mode & 0o077:
            raise PermissionError(
                "IPC socket directory must not grant group or "
                "other-user access. Required permissions: 0700."
            )

        if self.socket_path.exists() or self.socket_path.is_symlink():
            raise FileExistsError(
                f"IPC socket path already exists: {self.socket_path}. "
                "Check for another running server or a stale socket."
            )

    def _remove_socket_file(self) -> None:
        """Remove only the socket file created by this server."""

        if self._socket_identity is None:
            return

        try:
            current = self.socket_path.lstat()

            current_identity = (
                current.st_dev,
                current.st_ino,
            )

            if (
                current_identity == self._socket_identity
                and stat.S_ISSOCK(current.st_mode)
            ):
                self.socket_path.unlink()

        except FileNotFoundError:
            pass

        finally:
            self._socket_identity = None

    # -----------------------------------------------------------------------
    # Peer authentication
    # -----------------------------------------------------------------------

    @staticmethod
    def _get_peer_credentials(
        connection: socket.socket,
    ) -> PeerCredentials | None:
        """
        Obtain Linux peer credentials using SO_PEERCRED.

        Returns None when the operating system does not support this
        interface or credentials cannot be obtained.
        """

        if not hasattr(socket, "SO_PEERCRED"):
            return None

        try:
            credentials = connection.getsockopt(
                socket.SOL_SOCKET,
                socket.SO_PEERCRED,
                struct.calcsize("3i"),
            )

            pid, uid, gid = struct.unpack("3i", credentials)

            return PeerCredentials(
                pid=pid,
                uid=uid,
                gid=gid,
            )

        except OSError:
            return None

    def _authenticate_peer(
        self,
        connection: socket.socket,
    ) -> tuple[PeerCredentials, str | None]:

        credentials = self._get_peer_credentials(connection)

        # UID restrictions require independently obtained credentials.
        if credentials is None:
            raise PermissionError(
                "Unable to obtain local peer credentials."
            )

        if credentials.uid not in self.allowed_uids:
            raise PermissionError(
                f"Peer UID {credentials.uid} is not permitted."
            )

        expected_source = None

        if self.peer_identity_resolver is not None:

            expected_source = self.peer_identity_resolver(
                credentials
            )

            if expected_source is None:
                raise PermissionError(
                    "Unable to identify the connected IPC component."
                )

        return credentials, expected_source

    # -----------------------------------------------------------------------
    # Connection management
    # -----------------------------------------------------------------------

    def _accept_loop(self) -> None:
        """Accept connections until the server is stopped."""

        while self.is_running:

            server_socket = self._server_socket

            if server_socket is None:
                break

            try:
                connection, address = server_socket.accept()

            except socket.timeout:
                continue

            except OSError:
                if self.is_running:
                    logger.exception(
                        "IPC accept operation failed."
                    )
                break

            if not self._connection_slots.acquire(blocking=False):

                logger.warning(
                    "IPC connection limit reached. Rejecting connection."
                )

                connection.close()
                continue

            thread = threading.Thread(
                target=self._handle_connection,
                args=(connection,),
                name="rithum-ipc-client",
                daemon=True,
            )

            with self._lock:
                if not self._running:
                    connection.close()
                    self._connection_slots.release()
                    break

                self._connections.add(connection)
                self._connection_threads.add(thread)

            logger.debug(
                "Accepted IPC connection from %s",
                address,
            )

            thread.start()

    def _handle_connection(
        self,
        connection: socket.socket,
    ) -> None:
        """Handle all messages received over one client connection."""

        last_sequence = 0

        try:
            with connection:

                credentials, expected_source = (
                    self._authenticate_peer(connection)
                )

                logger.info(
                    "IPC client connected: PID=%s UID=%s GID=%s",
                    credentials.pid,
                    credentials.uid,
                    credentials.gid,
                )

                while self.is_running:

                    try:
                        data = recv_frame(connection)

                    except ConnectionError:
                        break

                    except FramingError:
                        logger.warning(
                            "Malformed IPC frame received. "
                            "Closing connection."
                        )
                        break

                    try:
                        message = validate_message(
                            data,
                            expected_source=expected_source,
                            last_sequence=last_sequence,
                        )

                    except MessageValidationError as exc:
                        logger.warning(
                            "Rejected IPC message: %s",
                            exc,
                        )
                        break

                    # This server is the entry point for the supervisor.
                    if message.target not in (
                        self.component,
                        "broadcast",
                    ):
                        logger.warning(
                            "Message target mismatch: %s",
                            message.target,
                        )
                        break

                    last_sequence = message.sequence

                    logger.debug(
                        "IPC message accepted: "
                        "source=%s action=%s sequence=%s",
                        message.source,
                        message.action,
                        message.sequence,
                    )

                    try:
                        response = self.on_message(message)

                    except Exception:
                        logger.exception(
                            "IPC message handler failed."
                        )
                        break

                    if response is not None:

                        try:
                            send_frame(
                                connection,
                                response,
                            )

                        except (OSError, FramingError):
                            logger.exception(
                                "Failed to send IPC response."
                            )
                            break

        except PermissionError as exc:
            logger.warning(
                "IPC peer authentication failed: %s",
                exc,
            )

        except OSError:
            if self.is_running:
                logger.exception(
                    "IPC connection error."
                )

        finally:

            try:
                connection.close()
            except OSError:
                pass

            with self._lock:
                self._connections.discard(connection)

                current_thread = threading.current_thread()

                self._connection_threads.discard(current_thread)

            self._connection_slots.release()

            logger.debug("IPC client disconnected.")
