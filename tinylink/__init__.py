from tinylink import utils

import struct

# This can be anything, and is used to synchronize a frame
PREAMBLE = 0xAA55AA55

# Endianness
LITTLE_ENDIAN = "<"
BIG_ENDINAN = ">"

# Protocol states
WAITING_FOR_PREAMBLE = 1
WAITING_FOR_HEADER = 2
WAITING_FOR_BODY = 3

# Message flags
FLAG_NONE = 0x00
FLAG_RESET = 0x01

# Don't change these values!
LEN_PREAMBLE = 4
LEN_FLAGS = 2
LEN_LENGTH = 2
LEN_XOR = 1
LEN_CRC = 4
LEN_HEADER = LEN_FLAGS + LEN_LENGTH + LEN_XOR
LEN_BODY = LEN_CRC

class BaseFrame(object):
    """
    Base frame.
    """

    def __init__(self, data=None, flags=FLAG_NONE):
        self.data = data
        self.flags = flags

    def __repr__(self):
        return "%s(%s, flags=0x%02x)" % (self.__class__.__name__,
            repr(self.data), self.flags)

class Frame(BaseFrame):
    """
    Represent normal frame.
    """
    pass

class DamagedFrame(BaseFrame):
    """
    Represent damaged frame.
    """
    pass

class ResetFrame(BaseFrame):
    """
    Represent reset frame.
    """

    def __init__(self):
        super(ResetFrame, self).__init__(None, FLAG_RESET)

    def __repr__(self):
        return "ResetFrame()"

class TinyLink(object):
    """
    TinyLink state machine for streaming communication with low-speed embedded
    applications that only use RX/TX. Every message is encapsulated in a frame.
    A frame has a header checksum and a frame checksum, to detect errors as fast
    as possible (this can happen when you jump right into a stream of packets).

    A typical frame has 13 bytes overhead, and can have a data payload up to
    65536 bytes.

    It does not provide error correction and the bytes are not aligned.
    """

    def __init__(self, handle, endianness=LITTLE_ENDIAN,
        max_length=2**(LEN_LENGTH * 8)):
        """
        Construct a new TinyLink state machine. A state machine takes a handle,
        which provides a `recv' and `send' method.

        The endianness is either LITTLE_ENDIAN or BIG_ENDIAN. While big endian
        is common for networking, little endian is directly compatible with ARM
        microcontrollers, so the microcontrollers don't have to change the
        endianness.

        Both microcontroller and this instance should agree upon the value of
        `max_length'. In case a message is received that exceeds this value, it
        will be silently ignored.
        """

        self.handle = handle
        self.endianness = endianness
        self.max_length = max_length

        # Set initial state
        self.state = WAITING_FOR_PREAMBLE

        # Pre-allocate buffer that fits header + body. The premable will be
        # cleared when it is detected, so it doesn't need space.
        self.stream = bytearray(max_length + LEN_HEADER + LEN_BODY)
        self.buffer = buffer(self.stream)
        self.index = 0

    def send_frame(self, frame):
        """
        Send a frame via the handle.
        """

        result = bytearray()
        length = len(frame.data or [])

        # Check length of message
        if length > self.max_length:
            raise ValueError("Message length %d exceeds max length %d" %
                (length, self.max_length))

        # Pack header
        checksum_header = utils.checksum_header(frame.flags, length)
        result += struct.pack(self.endianness + "IHHB", PREAMBLE, frame.flags,
            length, checksum_header)

        # Pack data
        if frame.data is not None:
            checksum_frame = utils.checksum_frame(frame.data, checksum_header)
            result += struct.pack(self.endianness + str(length) + "sI",
                frame.data, checksum_frame)

        # Write to file
        return self.handle.send(result)

    def reset(self):
        """
        Shorthand for `send_data(ResetFrame())'.
        """

        return self.send_frame(ResetFrame())

    def write(self, data, flags=FLAG_NONE):
        """
        Shorthand for `send_data(Frame(data, flags=flags))'.
        """

        return self.send_frame(Frame(data, flags=flags))

    def read(self, limit=1, ignore_damaged=False):
        """
        Read at `limit' bytes from the handle and process this byte. Returns a
        list of received frames, if any. A reset frame is indicated by a
        `ResetFrame' instance.

        By default, if a fully received package is damaged, it will be returned
        as a `DamagedFrame' instance, unless `ignored_damaged' is True.
        """

        # Define list for all results
        frames = []

        # Bytes are added one at a time
        for byte in self.handle.recv(limit):
            self.stream[self.index] = byte
            self.index += 1

            # Decide what to do
            if self.state == WAITING_FOR_PREAMBLE:
                if self.index >= LEN_PREAMBLE:
                    start, = struct.unpack_from(self.endianness + "I",
                        self.buffer, self.index - 4)

                    if start == PREAMBLE:
                        # Advance to next state
                        self.index = 0
                        self.state = WAITING_FOR_HEADER
                    elif self.index == self.max_length + LEN_HEADER + LEN_BODY:
                        # Preamble not found and stream is full. Copy last four
                        # bytes, because the next byte may form the preamble
                        # together with the last three bytes.
                        self.stream[0:4] = self.stream[-4:]
                        self.index = 4

            elif self.state == WAITING_FOR_HEADER:
                if self.index == LEN_HEADER:
                    flags, length, checksum = struct.unpack_from(
                        self.endianness + "HHB", self.buffer)

                    # Verify checksum
                    if checksum == utils.checksum_header(flags, length) and \
                        length <= self.max_length:

                        if length > 0:
                            self.state = WAITING_FOR_BODY
                        else:
                            # Empty frame to indicate a reset frame
                            frames.append(ResetFrame())

                            self.index = 0
                            self.state = WAITING_FOR_PREAMBLE
                    else:
                        # Reset to start state
                        self.index = 0
                        self.state = WAITING_FOR_PREAMBLE

            elif self.state == WAITING_FOR_BODY:
                # Unpack header
                flags, length, checksum_a = struct.unpack_from(
                    self.endianness + "HHB", self.buffer)

                if self.index == LEN_HEADER + length + LEN_CRC:
                    # Unpack body
                    result, checksum_b = struct.unpack_from(
                        self.endianness + str(length) + "sI",
                        self.buffer, LEN_HEADER)

                    # Verify checksum
                    if checksum_b == utils.checksum_frame(result, checksum_a):
                        frames.append(Frame(result, flags=flags))
                    elif not ignore_damaged:
                        frames.append(DamagedFrame(result, flags=flags))

                    # Reset to start state
                    self.index = 0
                    self.state = WAITING_FOR_PREAMBLE

        # Done
        return frames