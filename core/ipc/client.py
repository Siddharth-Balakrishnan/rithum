
"""Unix Domain Socket client for Rithum IPC."""

from __future__ import annotations

import logging
import socket
import threading

from pathlib import Path
from typing import Any

from .framing import (
    FramingError,
    recv_frame,
    send_frame,
)
from .models import (
    Component,
    MessageEnvelope,
    MessageType,
    create_message,
)
from .validator import (
    MessageValidationError,
    validate_message,
)


logger = logging.getLogger(__name__)


class IPCClientError(ConnectionError):
    """Raised when an IPC client operation fails."""


class IPCClient:
    """
    Persistent Unix Domain Socket client.

    A client represents one registered Rithum component and maintains
    a monotonically increasing outgoing sequence number per connection.

    request() sends a message and waits for its correlated response.
    send() transmits a message without waiting for a response.
    """

    def __init__(
        self,
        socket_path: str | Path,
        *,
        component: Component | str,
        server_component: Component | str = Component.SUPERVISOR,
        timeout: float = 5.0,
    ) -> None:

        if timeout <= 0:
            raise ValueError("timeout must be greater than zero.")

        self.socket_path = Path(socket_path)
        self.component = str(component)
        self.server_component = str(server_component)
        self.timeout = timeout

        self._socket: socket.socket | None = None

        self._sequence = 0

        self._lock = threading.RLock()

    # -----------------------------------------------------------------------
    # Properties
    # -----------------------------------------------------------------------

    @property
    def is_connected(self) -> bool:
        """Return whether the client currently has a socket connection."""

        with self._lock:
            return self._socket is not None

    @property
    def sequence(self) -> int:
        """Return the last successfully transmitted sequence number."""

        with self._lock:
            return self._sequence

    # -----------------------------------------------------------------------
    # Connection management
    # -----------------------------------------------------------------------

    def connect(self) -> None:
        """Connect to the supervisor's Unix Domain Socket."""

        with self._lock:

            if self._socket is not None:
                return

            connection = socket.socket(
                socket.AF_UNIX,
                socket.SOCK_STREAM,
            )

            connection.settimeout(self.timeout)

            try:
                connection.connect(str(self.socket_path))

            except OSError as exc:
                connection.close()

                raise IPCClientError(
                    f"Unable to connect to IPC server "
                    f"at {self.socket_path}: {exc}"
                ) from exc

            self._socket = connection

            # The server starts sequence tracking at zero for each
            # new connection.
            self._sequence = 0

            logger.info(
                "IPC client connected: component=%s",
                self.component,
            )

    def close(self) -> None:
        """Close the active connection and reset connection state."""

        with self._lock:

            connection = self._socket
            self._socket = None
            self._sequence = 0

            if connection is not None:

                try:
                    connection.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass

                try:
                    connection.close()
                except OSError:
                    pass

                logger.info(
                    "IPC client disconnected: component=%s",
                    self.component,
                )

    def __enter__(self) -> IPCClient:
        self.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------

    def _require_connection(self) -> socket.socket:
        """Return the active socket or raise an error."""

        if self._socket is None:
            raise IPCClientError(
                "IPC client is not connected. Call connect() first."
            )

        return self._socket

    def _create_message(
        self,
        *,
        target: Component | str,
        message_type: MessageType,
        action: str,
        payload: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        correlation_id: str | None = None,
    ) -> MessageEnvelope:

        return create_message(
            source=self.component,
            target=target,
            message_type=message_type,
            action=action,
            sequence=self._sequence + 1,
            payload=payload,
            metadata=metadata,
            correlation_id=correlation_id,
        )

    def _transmit(
        self,
        message: MessageEnvelope,
    ) -> None:
        """Transmit a message and update sequence after successful send."""

        connection = self._require_connection()

        send_frame(connection, message)

        self._sequence = message.sequence

    def _receive_response(
        self,
        connection: socket.socket,
        *,
        expected_message_id: str,
    ) -> MessageEnvelope:

        data = recv_frame(connection)

        response = validate_message(
            data,
            expected_source=self.server_component,
        )

        if response.target != self.component:
            raise IPCClientError(
                f"Unexpected response target: {response.target!r}."
            )

        if response.message_type not in (
            MessageType.RESPONSE,
            MessageType.ERROR,
        ):
            raise IPCClientError(
                f"Unexpected response message type: "
                f"{response.message_type.value!r}."
            )

        if response.correlation_id != expected_message_id:
            raise IPCClientError(
                "Response correlation ID does not match "
                "the original request."
            )

        return response

    # -----------------------------------------------------------------------
    # One-way message transmission
    # -----------------------------------------------------------------------

    def send(
        self,
        *,
        action: str,
        payload: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        target: Component | str | None = None,
        message_type: MessageType = MessageType.COMMAND,
    ) -> MessageEnvelope:
        """
        Send a message without waiting for a response.

        This is useful for events and notifications.
        """

        with self._lock:

            connection = self._require_connection()

            destination = (
                self.server_component
                if target is None
                else str(target)
            )

            message = self._create_message(
                target=destination,
                message_type=message_type,
                action=action,
                payload=payload,
                metadata=metadata,
            )

            try:
                self._transmit(message)

            except (OSError, FramingError) as exc:
                self.close()

                raise IPCClientError(
                    f"Failed to send IPC message: {exc}"
                ) from exc

            logger.debug(
                "IPC message sent: component=%s action=%s sequence=%s",
                self.component,
                action,
                message.sequence,
            )

            return message

    # -----------------------------------------------------------------------
    # Request-response communication
    # -----------------------------------------------------------------------

    def request(
        self,
        *,
        action: str,
        payload: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        target: Component | str | None = None,
    ) -> MessageEnvelope:
        """
        Send a command and wait for its correlated response.

        The lock remains held while waiting, ensuring that concurrent
        requests cannot mix up their responses on the same connection.
        """

        with self._lock:

            connection = self._require_connection()

            destination = (
                self.server_component
                if target is None
                else str(target)
            )

            message = self._create_message(
                target=destination,
                message_type=MessageType.COMMAND,
                action=action,
                payload=payload,
                metadata=metadata,
            )

            try:
                self._transmit(message)

                response = self._receive_response(
                    connection,
                    expected_message_id=message.message_id,
                )

            except (
                OSError,
                FramingError,
                MessageValidationError,
                IPCClientError,
            ) as exc:

                # A timeout or incomplete response can leave the stream
                # out of sync. Close rather than reusing that connection.
                self.close()

                raise IPCClientError(
                    f"IPC request failed: {exc}"
                ) from exc

            logger.debug(
                "IPC response received: "
                "action=%s correlation_id=%s",
                action,
                message.message_id,
            )

            return response
