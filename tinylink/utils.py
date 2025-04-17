import asyncio

from . import types

CRC32_POLYNOMIAL = 0xEDB88320
CRC32_INITIAL = 0x00000000


def crc32(buf) -> int:
    """Calculate CRC32 of given input.

    Args:
        buf: the buffer to calculate CRC32 over.

    Returns:
        A four-byte CRC32 checksum.
    """

    result = CRC32_INITIAL

    def crc32_value(c):
        temp = (result >> 8) & 0x00FFFFFF
        crc = (result ^ c) & 0xFF

        for _ in range(8):
            if crc & 0x01:
                crc = (crc >> 1) ^ CRC32_POLYNOMIAL
            else:
                crc = crc >> 1

        return temp ^ crc

    # Execute function for each byte.
    for b in buf:
        result = crc32_value(b)

    return result


def create_async_handle(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter
) -> types.AsyncHandle:
    """Create a handle from a `asyncio.StreamReader` and asyncio.StreamWriter`
    pair.

    Args:
        reader: The reader instance.
        writer: The writer instance.

    Returns:
        A handle that can be used with `link.AsyncTinyLink`.
    """

    class Handle:
        async def read(self, size: int) -> bytes:
            return await reader.read(size)

        async def write(self, data: bytes) -> None:
            writer.write(data)
            await writer.drain()

    return Handle()
