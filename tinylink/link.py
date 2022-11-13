import struct
from typing import Protocol

from . import consts, utils


class Handle(Protocol):
    """
    Protocol for a handler.
    """

    def read(self, size: int) -> bytes:
        """ "
        Read up to  `size` bytes.
        """

    def write(self, data: bytes) -> int:
        """
        Write data and return the number of bytes written.
        """


class Frame:
    """
    Represents a frame.
    """

    data: bytes
    flags: int
    damaged: int

    def __init__(
        self, data: bytes = None, flags: int = consts.FLAG_NONE, damaged: bool = False
    ) -> None:
        if data is not None:
            if type(data) is not bytes:
                raise ValueError("Provided data must be encoded as bytes.")
        else:
            data = bytes()

        self.data = data
        self.flags = flags
        self.damaged = damaged

    def __repr__(self) -> str:
        return "%s(%s, flags=%d, damaged=%s)" % (
            self.__class__.__name__,
            repr(self.data),
            self.flags,
            self.damaged,
        )


class TinyLink:
    """
    TinyLink state machine for streaming communication with low-speed embedded
    applications that only use RX/TX. Every message is encapsulated in a frame.
    A frame has a header checksum and a frame checksum, to detect errors as
    fast as possible (this can happen when you jump right into a stream of
    packets, without being synchronized).

    A typical frame has 13 bytes overhead, and can have a data payload up to
    65536 bytes.

    It does not provide error correction and the bytes are not aligned.
    """

    handle: Handle
    endianness: str
    max_length: int
    ignore_damaged: bool

    def __init__(
        self,
        handle: Handle,
        endianness: str = consts.LITTLE_ENDIAN,
        max_length: int = 2 ** (consts.LEN_LENGTH * 8),
        ignore_damaged: bool = False,
    ) -> None:
        """
        Construct a new TinyLink state machine. A state machine takes a handle,
        which provides a `read` and `write` method.

        The endianness is either `consts.LITTLE_ENDIAN` or `consts.BIG_ENDIAN`.
        While big endian is common for networking, little endian is directly
        compatible with ARM microcontrollers, so the microcontrollers do not
        have to perform conversion of endianness.

        Both microcontroller and this instance should agree upon the value of
        `max_lengthz. In case a message is received that exceeds this value, it
        will be silently ignored.

        By default, if a fully received frame is damaged, it will be returned
        as an instance of `DamagedFrame` instance, unless `ignored_damaged` is
        set to `True`.
        """

        self.handle = handle
        self.endianness = endianness
        self.max_length = max_length
        self.ignore_damaged = ignore_damaged

        # Set initial state
        self.state = consts.WAITING_FOR_PREAMBLE

        # Pre-allocate buffer that fits header + body. The premable will be
        # cleared when it is detected, so it does not need space.
        self.stream = bytearray(max_length + consts.LEN_HEADER + consts.LEN_BODY)
        self.index = 0

        # Python 2 does not allow unpack from bytearray, but Python 3.
        self.buffer = self.stream

    def write_frame(self, frame: Frame) -> int:
        """
        Write a frame via the handle.
        """

        result = bytearray()
        length = len(frame.data or [])

        # Check length of message.
        if length > self.max_length:
            raise ValueError(
                "Message length %d exceeds max length %d" % (length, self.max_length)
            )

        # Pack header.
        checksum_header = utils.checksum_header(frame.flags, length)
        result += struct.pack(
            self.endianness + "IHHB",
            consts.PREAMBLE,
            frame.flags,
            length,
            checksum_header,
        )

        # Pack data.
        if frame.data is not None:
            checksum_frame = utils.checksum_frame(frame.data, checksum_header)
            result += struct.pack(
                self.endianness + str(length) + "sI", frame.data, checksum_frame
            )

        # Write to file.
        return self.handle.write(result)

    def write(self, data: bytes, flags: int = consts.FLAG_NONE) -> int:
        """
        Shorthand for `write_frame(Frame(data, flags=flags))`.
        """

        return self.write_frame(Frame(data, flags=flags))

    def read(self, limit: int = 1) -> list[Frame]:
        """
        Read up to `limit` bytes from the handle and process it. Returns a list
        of received frames, if any.
        """

        # List of frames received.
        frames = []

        # Bytes are added one at a time.
        while limit:
            char = self.handle.read(1)

            if not char:
                return []

            # Append to stream.
            self.stream[self.index] = ord(char)
            self.index += 1

            # Decide what to do.
            if self.state == consts.WAITING_FOR_PREAMBLE:
                if self.index >= consts.LEN_PREAMBLE:
                    (start,) = struct.unpack_from(
                        self.endianness + "I", self.buffer, self.index - 4
                    )

                    if start == consts.PREAMBLE:
                        # Advance to next state.
                        self.index = 0
                        self.state = consts.WAITING_FOR_HEADER
                    elif (
                        self.index
                        == self.max_length + consts.LEN_HEADER + consts.LEN_BODY
                    ):
                        # Preamble not found and stream is full. Copy last four
                        # bytes, because the next byte may form the preamble
                        # together with the last three bytes.
                        self.stream[0:4] = self.stream[-4:]
                        self.index = 4

            elif self.state == consts.WAITING_FOR_HEADER:
                if self.index == consts.LEN_HEADER:
                    flags, length, checksum = struct.unpack_from(
                        self.endianness + "HHB", self.buffer
                    )

                    # Verify checksum.
                    if (
                        checksum == utils.checksum_header(flags, length)
                        and length <= self.max_length
                    ):

                        if length > 0:
                            self.state = consts.WAITING_FOR_BODY
                        else:
                            # Frame without body.
                            frames.append(Frame(flags=flags))

                            self.index = 0
                            self.state = consts.WAITING_FOR_PREAMBLE
                    else:
                        # Reset to start state.
                        self.index = 0
                        self.state = consts.WAITING_FOR_PREAMBLE

            elif self.state == consts.WAITING_FOR_BODY:
                # Unpack header.
                flags, length, checksum_a = struct.unpack_from(
                    self.endianness + "HHB", self.buffer
                )

                if self.index == consts.LEN_HEADER + length + consts.LEN_CRC:
                    # Unpack body.
                    result, checksum_b = struct.unpack_from(
                        self.endianness + str(length) + "sI",
                        self.buffer,
                        consts.LEN_HEADER,
                    )

                    # Verify checksum.
                    if checksum_b == utils.checksum_frame(result, checksum_a):
                        frames.append(Frame(result, flags=flags))
                    elif not self.ignore_damaged:
                        frames.append(Frame(result, flags=flags, damaged=True))

                    # Reset to start state.
                    self.index = 0
                    self.state = consts.WAITING_FOR_PREAMBLE

            # Decrement number of bytes to read.
            limit -= 1

        # Done.
        return frames
