import unittest
import tinylink


class DummyHandle(object):
    """
    Dummy handler, so the TinyLink class can exchange data with itself.
    """

    def __init__(self):
        self.stream = bytearray()
        self.index = 0
        self.length = 0

    def write(self, data):
        self.stream.extend(data)
        self.length += len(data)

        # Return number of bytes written
        return len(data)

    def read(self, count):
        data = self.stream[self.index:min(self.length, self.index + count)]
        self.index += len(data)

        # Return data
        return bytes(data)


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

        message = b"Hello, this is a test"
        size = link.write(message)

        self.assertEqual(
            size, tinylink.LEN_PREAMBLE + tinylink.LEN_HEADER +
            tinylink.LEN_BODY + len(message))

        # Read `size` bytes to receive the full frame, test it partially.
        link.read(1)
        link.read(1)
        link.read(1)
        frames = link.read(size - 3)

        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0].data, message)

    def test_multiple(self):
        """
        Test multiple messages.
        """

        handle = DummyHandle()
        link = tinylink.TinyLink(handle)

        size = 0

        for i in range(5):
            size += link.write(bytes([97 + i]))

        frames = link.read(size)

        self.assertEqual(len(frames), 5)

        for i in range(5):
            self.assertEqual(frames[i].data, bytes([97 + i]))

    def test_sync(self):
        """
        Test preamble synchronization.
        """

        handle = DummyHandle()
        link = tinylink.TinyLink(handle)

        garbage = b"Garbage here that does not synchronize."
        message = b"Hi!"

        size = handle.write(garbage) + link.write(message)
        frames = link.read(size)

        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0].data, message)

    def test_sync_small(self):
        """
        Test preamble synchronization with smaller buffer.
        """

        handle = DummyHandle()
        link = tinylink.TinyLink(handle, max_length=4)

        garbage = b"Garbage here that does not synchronize."
        message = b"Hi!"

        size = handle.write(garbage) + link.write(message)
        frames = link.read(size)

        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0].data, message)

    def test_size_fit(self):
        """
        Test smaller sized TinyLink that does fit.
        """

        handle = DummyHandle()
        link = tinylink.TinyLink(handle, max_length=4)

        message = b"blub"

        size = link.write(message)
        frames = link.read(size)

        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0].data, message)

    def test_size_no_fit(self):
        """
        Test smaller sized TinyLink that does not fit.
        """

        handle = DummyHandle()
        link = tinylink.TinyLink(handle, max_length=2)

        message = b"blub"

        with self.assertRaises(ValueError):
            link.write(message)

    def test_damaged_a(self):
        """
        Test damaged frame (in total) that will return a Frame with damages is
        True.
        """

        handle = DummyHandle()
        link = tinylink.TinyLink(handle)

        message = b"Hello, this is a test"

        size = link.write(message)
        handle.stream[-tinylink.LEN_CRC:] = [0x00] * tinylink.LEN_CRC
        frames = link.read(size)

        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0].data, message)
        self.assertEqual(frames[0].damaged, True)

    def test_damaged_b(self):
        """
        Test damaged frame (header) that will not return anything.
        """

        handle = DummyHandle()
        link = tinylink.TinyLink(handle)

        message = b"Hello, this is a test"

        size = link.write(message)
        handle.stream[tinylink.LEN_PREAMBLE+tinylink.LEN_HEADER-1] = 0x00
        frames = link.read(size)

        self.assertEqual(len(frames), 0)
