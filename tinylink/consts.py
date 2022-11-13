# This can be anything, and is used to synchronize a frame.
PREAMBLE = 0xAA55AA55

# Endianness.
LITTLE_ENDIAN = "<"
BIG_ENDIAN = ">"

# Protocol states.
WAITING_FOR_PREAMBLE = 1
WAITING_FOR_HEADER = 2
WAITING_FOR_BODY = 3

# Message flags (reserved).
FLAG_NONE = 0x00
FLAG_RESET = 0x01
FLAG_ERROR = 0x02
FLAG_PRIORITY = 0x04

# Do not change these values!
LEN_PREAMBLE = 4
LEN_FLAGS = 2
LEN_LENGTH = 2
LEN_XOR = 1
LEN_CRC = 4
LEN_HEADER = LEN_FLAGS + LEN_LENGTH + LEN_XOR
LEN_BODY = LEN_CRC
