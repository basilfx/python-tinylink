CRC32_POLYNOMIAL = 0xEDB88320L
CRC32_INITIAL = 0x00000000L

def crc32(buf):
    """
    Calculate CRC32 of given input
    """

    result = CRC32_INITIAL

    def crc32_value(c):
        ulTemp1 = (result >> 8) & 0x00FFFFFFl
        ulCRC = (result ^ c) & 0xff

        for i in range(8):
            if ulCRC & 0x01:
                ulCRC = (ulCRC >> 1) ^ CRC32_POLYNOMIAL
            else:
                ulCRC = ulCRC >> 1

        return ulTemp1 ^ ulCRC

    # Execute above function for each byte
    for b in buf:
        result = crc32_value(b)

    # Done
    return result

def checksum_header(flags, length):
    """
    Calculate checksum over the header.
    """

    a = (flags & 0x00FF) >> 0
    b = (flags & 0xFF00) >> 8
    c = (length & 0x00FF) >> 0
    d = (length & 0xFF00) >> 8

    return a ^ b ^ c ^ d

def checksum_frame(data, checksum_header):
    """
    Calculate checksum of both the checksum header and the data.
    """

    return crc32(data + bytearray([checksum_header])) & 0xffffffff