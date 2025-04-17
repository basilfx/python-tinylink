import unittest

import tinylink


class DummyHandle(object):
    """
    Dummy handle, so the TinyLink class can exchange data with itself.
    """

    buffer: bytes
    index: int
    length: int

    def __init__(self) -> None:
        self.buffer = bytearray()
        self.index = 0
        self.length = 0

    def read(self, size: int) -> bytes:
        data = self.buffer[self.index : min(self.length, self.index + size)]
        self.index += len(data)

        # Return data.
        return bytes(data)

    def write(self, data: bytes) -> int:
        self.buffer.extend(data)
        self.length += len(data)

        # Return number of bytes written.
        return len(data)


class TinyLinkTest(unittest.TestCase):
    """
    Test TinyLink
    """

    def test_basic(self):
        """
        Test read/write by using a dummy handle.
        """

        handle = DummyHandle()
        link = tinylink.TinyLink(handle)

        flags = 123
        payload = b"Hello, this is a test"
        link.write_frame(tinylink.Frame(flags=flags, payload=payload))

        self.assertEqual(
            len(handle.buffer),
            tinylink.LEN_PREAMBLE
            + tinylink.LEN_HEADER
            + tinylink.LEN_BODY
            + len(payload),
        )

        frame = link.read_frame()

        self.assertEqual(frame.flags, flags)
        self.assertEqual(frame.payload, payload)

    def test_flags_only(self):
        """
        Test frame with only a flags and no payload.
        """

        handle = DummyHandle()
        link = tinylink.TinyLink(handle)

        flags = 123
        link.write_frame(tinylink.Frame(flags=flags))

        self.assertEqual(
            len(handle.buffer),
            tinylink.LEN_PREAMBLE + tinylink.LEN_HEADER + tinylink.LEN_BODY,
        )

        frame = link.read_frame()

        self.assertEqual(frame.flags, flags)

    def test_escaping(self):
        """
        Test escaping of flag (first byte of preamble) inside the header and
        body.
        """

        handle = DummyHandle()
        link = tinylink.TinyLink(handle)

        flags = tinylink.consts.FLAG
        payload = bytes([tinylink.consts.ESCAPE])
        link.write_frame(tinylink.Frame(flags=flags, payload=payload))

        # The frame will contain the flag five times: once in the header and
        # once in the body.
        overhead = 2

        self.assertEqual(
            len(handle.buffer),
            tinylink.LEN_PREAMBLE
            + tinylink.LEN_HEADER
            + tinylink.LEN_BODY
            + len(payload)
            + overhead,
        )

        frame = link.read_frame()

        self.assertEqual(frame.flags, flags)
        self.assertEqual(frame.payload, payload)

    def test_escaping_last_byte(self):
        """
        Test frame where the very last byte requires escaping (and the logic
        could assume the frame is complete. This happens to be the case for
        flag value 10.
        """

        handle = DummyHandle()
        link = tinylink.TinyLink(handle)

        flags = 10
        link.write_frame(tinylink.Frame(flags=flags))

        # The frame with flag value 10 and no payload requires the last frame
        # checksum byte to be escaped. The overhead will be 1.
        overhead = 1

        self.assertEqual(
            len(handle.buffer),
            tinylink.LEN_PREAMBLE + tinylink.LEN_HEADER + tinylink.LEN_BODY + overhead,
        )

        frame = link.read_frame()

        self.assertEqual(frame.flags, flags)

    def test_escaping_max_payload_length(self):
        """
        Test escaping with maximum payload length (which means that the
        internal buffer should not overflow).
        """

        handle = DummyHandle()
        link = tinylink.TinyLink(handle)

        flags = 123
        payload = bytes([tinylink.consts.FLAG] * link.max_payload_length)
        link.write_frame(tinylink.Frame(flags=flags, payload=payload))

        # Every payload byte will be esacped, so the overhead will be twice the
        # number of payload bytes.
        overhead = len(payload)

        self.assertEqual(
            len(handle.buffer),
            tinylink.LEN_PREAMBLE
            + tinylink.LEN_HEADER
            + tinylink.LEN_BODY
            + len(payload)
            + overhead,
        )

        frame = link.read_frame()

        self.assertEqual(frame.flags, flags)
        self.assertEqual(frame.payload, payload)

    def test_multiple(self):
        """
        Test multiple payloads.
        """

        handle = DummyHandle()
        link = tinylink.TinyLink(handle)

        for i in range(5):
            link.write(bytes([97 + i]))

        for i in range(5):
            frame = link.read_frame()
            self.assertEqual(frame.payload, bytes([97 + i]))

    def test_sync(self):
        """
        Test preamble synchronization.
        """

        handle = DummyHandle()
        link = tinylink.TinyLink(handle)

        garbage = b"Garbage here that does not synchronize."
        payload = b"Hi!"

        handle.write(garbage)
        link.write_frame(tinylink.Frame(payload=payload))
        frame = link.read_frame()

        self.assertEqual(frame.payload, payload)

    def test_sync_small(self):
        """
        Test preamble synchronization with smaller buffer.
        """

        handle = DummyHandle()
        link = tinylink.TinyLink(handle, max_payload_length=4)

        garbage = b"Garbage here that does not synchronize."
        payload = b"Hi!"

        handle.write(garbage)
        link.write_frame(tinylink.Frame(payload=payload))
        frame = link.read_frame()

        self.assertEqual(frame.payload, payload)

    def test_size_fit(self):
        """
        Test smaller sized TinyLink that does fit.
        """

        handle = DummyHandle()
        link = tinylink.TinyLink(handle, max_payload_length=4)

        payload = b"blub"

        link.write_frame(tinylink.Frame(payload=payload))
        frame = link.read_frame()

        self.assertEqual(frame.payload, payload)

    def test_size_no_fit(self):
        """
        Test smaller sized TinyLink that does not fit.
        """

        handle = DummyHandle()
        link = tinylink.TinyLink(handle, max_payload_length=2)

        payload = b"blub"

        with self.assertRaises(ValueError):
            link.write_frame(tinylink.Frame(payload=payload))

    def test_damaged(self):
        """
        Test damaged frame (header) that will not return anything.
        """

        handle = DummyHandle()
        link = tinylink.TinyLink(handle)

        payload = b"Hello, this is a test"

        link.write_frame(tinylink.Frame(payload=payload))
        handle.buffer[tinylink.LEN_PREAMBLE + tinylink.LEN_HEADER - 1] = 0x00
        frame = link.read_frame()

        self.assertEqual(frame, None)
