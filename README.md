# python-tinylink
Frame-based streaming protocol for embedded applications.

## Introduction
This is a Python module to provide a bi-directional frame-based streaming protocol for low-speed embedded applications, such as serial connected devices. It allowes the receiver to 'jump into' a stream of data frames. Every frame starts with a preamble, so the receiver can synchronize. Any mismatch in checksum will the receiver.

A payload is optional. The reserved `RESET` flag can be used to indicate that the link should reset, for instance when the receiver just started and the sender should restart.

The format of a frame is as follows:

```
| 0xAA 0x55 0xAA 0x55 | AA AA BB BB CC | XX XX .. .. .. .. XX XX YY YY YY YY |
| Preamble            | Header         | Body (optional)                     |

Fields:
A = Length
B = Flags
C = XOR checksum over header
X = Body payload (max. 65536 bytes)
Y = CRC32 checksum over header + body
```

Error correction is not implemented and the bytes are not aligned. The endianness is customizable.

## Statechart diagram
Below is a simplified statechart diagram of the receiver.
![Alt text](docs/statechart.png)

## Installation
The latest development version can be installed via `pip install git+https://github.com/basilfx/python-tinylink`.

## Tests
Tests can be executed with `nose`. Check the `tests/` folder for more information.

## License
See the `LICENSE` file (MIT license).