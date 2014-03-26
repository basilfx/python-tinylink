import utils
import struct

# This can be anything, and is used to synchronize a frame
PREAMBLE = 0xAA55AA55

# Either '<' (little endian) or '>' (big endian). While big endian is common for
# networking, little endian is directly compatible with MCUs like Cortex M3
ENDIANNESS = "<"

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

class TinyLink(object):
    """
    """

    def __init__(self, handle):
        self.handle = handle
        self.stream = bytearray()
        self.state = WAITING_FOR_PREAMBLE

    def send_reset(self, data):
        return self.send_frame(flags=FLAG_RESET)

    def send_data(self, data):
        return self.send_frame(flags=FLAG_NONE, data=data)

    def send_frame(self, flags, data=None):
        result = bytearray()
        length = len(data or [])

        # Pack header
        checksum_header = utils.checksum_header(flags, length)
        result += struct.pack(ENDIANNESS + "IHHB", PREAMBLE, flags, length, checksum_header)

        # Pack data
        if data is not None:
            checksum_frame = utils.checksum_frame(data, checksum_header)
            result += struct.pack(ENDIANNESS + str(length) + "sI", data, checksum_frame)

        # Write to file
        self.handle.send(result)

    def write(self, data):
        return self.send_data(data)

    def read(self, limit=-1):
        """
        Read at least one byte from the file and process this byte. Return a
        list of received packets, if any.
        """

        # Define list for all results
        frames = []

        # Bytes are added one at a time
        for byte in self.handle.recv(1):
            self.stream += byte

            # Decide what to do
            if self.state == WAITING_FOR_PREAMBLE:
                if len(self.stream) >= LEN_PREAMBLE:
                    start, = struct.unpack_from(ENDIANNESS + "I", buffer(self.stream), len(self.stream) - 4)

                    if start == PREAMBLE:
                        self.stream = bytearray()
                        self.state = WAITING_FOR_HEADER
                    else:
                        self.stream = bytearray()
                        self.state = WAITING_FOR_PREAMBLE

            elif self.state == WAITING_FOR_HEADER:
                if len(self.stream) == LEN_HEADER:
                    flags, length, checksum = struct.unpack_from(ENDIANNESS + "HHB", buffer(self.stream))

                    # Verify checksum
                    if checksum == utils.checksum_header(flags, length):
                        if length > 0:
                            self.state = WAITING_FOR_BODY
                        else:
                            frames.append(None)

                            self.stream = bytearray()
                            self.state = WAITING_FOR_PREAMBLE
                    else:
                        self.stream = bytearray()
                        self.state = WAITING_FOR_PREAMBLE

            elif self.state == WAITING_FOR_BODY:
                # Unpack header
                flags, length, checksum_a = struct.unpack_from(ENDIANNESS + "HHB", buffer(self.stream))

                if len(self.stream) == LEN_HEADER + length + LEN_CRC:
                    # Unpack body
                    result, checksum_b = struct.unpack_from(ENDIANNESS + str(length) + "sI", buffer(self.stream), LEN_HEADER)

                    # Verify checksum
                    if checksum_b == utils.checksum_frame(result, checksum_a):
                        frames.append(result)

                    # Reset to start state
                    self.stream = bytearray()
                    self.state = WAITING_FOR_PREAMBLE

        # Done
        return frames