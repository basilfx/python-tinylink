from typing import Protocol


class AsyncHandle(Protocol):
    """Protocol for an asynchronous handle."""

    async def read(self, size: int) -> bytes:
        """Read up to `size` bytes from the handle.

        Args:
            size: Maximum number of bytes to read.

        Returns:
            The bytes read from the handle. May be less than `size` if fewer
            bytes are available.
        """

    async def write(self, data: bytes) -> None:
        """Write data to the handle.

        Args:
            data: The bytes to write to the handle.
        """


class Handle(Protocol):
    """Protocol for a synchronous handle."""

    def read(self, size: int) -> bytes:
        """Read up to `size` bytes from the handle.

        Args:
            size: Maximum number of bytes to read.

        Returns:
            The bytes read from the handle. May be less than `size` if fewer
            bytes are available.
        """

    def write(self, data: bytes) -> None:
        """Write data to the handle.

        Args:
            data: The bytes to write to the handle.
        """
