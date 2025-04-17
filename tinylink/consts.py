# This can be anything, but must be an alternating pattern.
PREAMBLE = 0xAA55AA55

# The escape character is used for byte-stuffing of the header and body.
FLAG = 0xAA
ESCAPE = 0x1B

# Endianness.
LITTLE_ENDIAN = "<"
BIG_ENDIAN = ">"

# Protocol states.
WAITING_FOR_PREAMBLE = 1
WAITING_FOR_HEADER = 2
WAITING_FOR_BODY = 3

# Do not change these values!
LEN_PREAMBLE = 4

LEN_FLAGS = 2
LEN_LENGTH = 2
LEN_XOR = 1
LEN_HEADER = LEN_FLAGS + LEN_LENGTH + LEN_XOR

LEN_CRC = 4
LEN_BODY = LEN_CRC
