import struct
from typing import Optional

from . import consts, types, utils


class Frame:
    """Represents a frame. A frame contains flags and an optional payload."""

    flags: int
    payload: Optional[bytes]

    def __init__(self, flags: int = 0x0000, payload: Optional[bytes] = None) -> None:
        """Initialize a new frame with optional flags and payload.

        Args:
            flags: The frame flags (default: 0x0000).
            payload: Optional payload data (default: None).
        """
        if flags & 0xFFFF != flags:
            raise ValueError("Flags must be in range 0 - 65535.")

        self.flags = flags
        self.payload = payload

    def __repr__(self) -> str:
        """Return a string representation of the frame.

        Returns:
            A string containing the frame's flags and payload if present.
        """
        class_name = self.__class__.__name__

        if self.payload is None:
            return f"{class_name}(flags={self.flags:04x})"
        else:
            return f"{class_name}({self.payload}, flags={self.flags:04x})"


class BaseTinyLink:
    """TinyLink state machine for streaming communication with low-speed
    embedded applications that only use RX/TX.

    A link exchanges frames. Frames exist out of a preamble, a header and a
    body. The header contain flags and length information. The body contains
    the optional payload. Checksums are included to detect errors as fast as
    possible (this can happen when you jump right into a stream of bytes,
    without being synchronized). The header and body are escaped.

    The payload can be up to 65536 bytes. A minimal frame (without payload and
    escaping) is 13 bytes.

    The protocol favors reliability and simplicity over speed and complexity.
    """

    endianness: str
    max_payload_length: int

    state: int
    buffer: bytearray
    index: int
    unescaping: bool

    def __init__(
        self,
        endianness: str = consts.LITTLE_ENDIAN,
        max_payload_length: int = 2 ** (consts.LEN_LENGTH * 8) - 1,
    ) -> None:
        """Construct a new TinyLink state machine.

        The endianness is either `consts.LITTLE_ENDIAN` or `consts.BIG_ENDIAN`.
        While big endian is common for networking, little endian is directly
        compatible with ARM microcontrollers, so the microcontrollers do not
        have to perform conversion of endianness.

        Both microcontroller and this instance should agree upon the value of
        `max_payload_length`. In case a frame is received that exceeds this
        value, it will be silently ignored.
        """

        self.endianness = endianness
        self.max_payload_length = max_payload_length

        # Set initial state.
        self.state = consts.WAITING_FOR_PREAMBLE

        # Pre-allocate byte buffer that fits header + body. The premable will
        # be cleared when it is detected, so it does not need space.
        self.buffer = bytearray(
            max_payload_length + consts.LEN_HEADER + consts.LEN_BODY
        )
        self.index = 0
        self.unescaping = False

    def _write_frame(self, frame: Frame) -> bytes:
        """Construct the bytes of a frame to write to a handle.

        Args:
            frame: The frame to write.

        Raises:
            ValueError: If the payload length exceeds the maximum length.

        Returns:
            The bytes to write to a handle.
        """

        flags = frame.flags
        payload = frame.payload or bytes()
        length = len(payload)

        # Check length of payload.
        if length > self.max_payload_length:
            raise ValueError(
                "Message length of %d bytes exceeds maximum payload length of %d bytes"
                % (length, self.max_payload_length)
            )

        # pack preamble.
        preamble = struct.pack(self.endianness + "I", consts.PREAMBLE)

        # Pack header.
        checksum_header = self._checksum_header(flags, length)
        header = struct.pack(
            self.endianness + "HHB",
            flags,
            length,
            checksum_header,
        )

        # Pack body.
        checksum_frame = self._checksum_frame(header, payload)
        body = struct.pack(
            self.endianness + str(length) + "sI", payload, checksum_frame
        )

        # Done.
        return preamble + self._escape(header + body)

    def _read_byte(self, byte: bytes) -> Optional[Frame]:
        """Process a byte that was read.

        Args:
            byte: The byte read from a source.

        Returns:
            A `Frame`, if the frame is complete (i.e. all bytes received), or
                `None` if not yet complete.
        """

        result = None

        # Unescape and append to buffer.
        if self.state in {consts.WAITING_FOR_HEADER, consts.WAITING_FOR_BODY}:
            if self.unescaping:
                self.index = self.index - 1
                self.unescaping = False
            else:
                if byte[0] == consts.ESCAPE:
                    self.unescaping = True

        self.buffer[self.index] = byte[0]
        self.index += 1

        if self.unescaping:
            return

        # Decide what to do.
        if self.state == consts.WAITING_FOR_PREAMBLE:
            if self.index >= consts.LEN_PREAMBLE:
                (preamble,) = struct.unpack_from(
                    self.endianness + "I", self.buffer[self.index - 4 : self.index]
                )

                if preamble == consts.PREAMBLE:
                    # Preamble found. Start reading the header.
                    self.index = 0
                    self.state = consts.WAITING_FOR_HEADER
                elif (
                    self.index
                    == self.max_payload_length + consts.LEN_HEADER + consts.LEN_BODY
                ):
                    # Preamble not found and buffer is full. Copy last four
                    # bytes, because the next byte may form the preamble
                    # together with the last three bytes.
                    self.buffer[0:4] = self.buffer[-4:]
                    self.index = 4

        elif self.state == consts.WAITING_FOR_HEADER:
            if self.index == consts.LEN_HEADER:
                flags, length, checksum_header = struct.unpack_from(
                    self.endianness + "HHB", self.buffer
                )

                # Verify checksum.
                if (
                    checksum_header == self._checksum_header(flags, length)
                    and length <= self.max_payload_length
                ):
                    self.state = consts.WAITING_FOR_BODY
                else:
                    # Reset to start state.
                    self.index = 0
                    self.state = consts.WAITING_FOR_PREAMBLE

        elif self.state == consts.WAITING_FOR_BODY:
            flags, length, _ = struct.unpack_from(self.endianness + "HHB", self.buffer)

            if self.index == length + consts.LEN_HEADER + consts.LEN_CRC:
                payload, checksum_frame = struct.unpack_from(
                    self.endianness + str(length) + "sI",
                    self.buffer,
                    consts.LEN_HEADER,
                )

                # Verify checksum.
                if checksum_frame == self._checksum_frame(
                    self.buffer[: consts.LEN_HEADER], payload
                ):
                    result = Frame(flags=flags, payload=payload)

                # Reset to start state.
                self.index = 0
                self.state = consts.WAITING_FOR_PREAMBLE

        # Done.
        return result

    def _checksum_header(self, flags, length) -> int:
        """Calculate the header checksum.

        Args:
            flags: The flags field to checksum.
            length: The length field to checksum.

        Returns:
            A single-byte checksum of the header fields.
        """

        a = (flags & 0x00FF) >> 0
        b = (flags & 0xFF00) >> 8
        c = (length & 0x00FF) >> 0
        d = (length & 0xFF00) >> 8

        return a ^ b ^ c ^ d

    def _checksum_frame(self, header: bytes, payload: bytes) -> int:
        """Calculate the frame checksum (header and payload).

        Args:
            header: The frame header.
            payload: The frame payload.

        Returns:
            A four-byte CRC32 checksum of the header and body.
        """

        return utils.crc32(header + payload) & 0xFFFFFFFF

    def _escape(self, data: bytes) -> bytes:
        """Escape the data using byte-stuffing, so that the data can safely
        contain the preamble.

        Args:
            data: The data to escape.

        Returns:
            The escaped data.
        """

        buffer = bytearray(len(data) * 2)
        index = 0

        for byte in data:
            if byte == consts.FLAG:
                buffer[index] = consts.ESCAPE
                buffer[index + 1] = consts.FLAG
                index += 2
            elif byte == consts.ESCAPE:
                buffer[index] = consts.ESCAPE
                buffer[index + 1] = consts.ESCAPE
                index += 2
            else:
                buffer[index] = byte
                index += 1

        return bytes(buffer[:index])


class AsyncTinyLink(BaseTinyLink):

    handle: types.AsyncHandle

    def __init__(self, handle: types.AsyncHandle, *args, **kwargs) -> None:
        """Construct a new asynchronous TinyLink instance.

        See `TinyLink.__init__` for more information.

        Args:
            handle: A handle that provides a `read` and `write` method. Note
                that the handle is just a wrapper and does not 'own' it.
        """
        super().__init__(*args, **kwargs)

        self.handle = handle

    async def read_frame(self) -> Optional[Frame]:
        while True:
            byte = await self.handle.read(1)

            # Handle end-of-file.
            if not byte:
                return None

            result = self._read_byte(byte)

            if result:
                return result

    async def read(self) -> bytes:
        frame = await self.read_frame()

        # Handle end-of-file.
        if not frame:
            return bytes()

        return frame.payload or bytes()

    async def write_frame(self, frame: Frame) -> None:
        await self.handle.write(self._write_frame(frame))

    async def write(self, payload: bytearray, flags: int = 0x0000) -> None:
        await self.write_frame(Frame(payload=payload, flags=flags))


class TinyLink(BaseTinyLink):

    handle: types.Handle

    def __init__(self, handle: types.Handle, *args, **kwargs) -> None:
        """Construct a new synchronous TinyLink instance.

        See `TinyLink.__init__` for more information.

        Args:
            handle: A handle that provides a `read` and `write` method. Note
                that the handle is just a wrapper and does not 'own' it.
        """
        super().__init__(*args, **kwargs)

        self.handle = handle

    def read_frame(self) -> Optional[Frame]:
        while True:
            byte = self.handle.read(1)

            # Handle end-of-file.
            if not byte:
                return None

            result = self._read_byte(byte)

            if result:
                return result

    def read(self) -> bytes:
        frame = self.read_frame()

        # Handle end-of-file.
        if not frame:
            return bytes()

        return frame.payload or bytes()

    def write_frame(self, frame: Frame) -> None:
        self.handle.write(self._write_frame(frame))

    def write(self, payload: bytes, flags: int = 0x0000) -> None:
        self.write_frame(Frame(payload=payload, flags=flags))
