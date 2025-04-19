# python-tinylink
Frame-based streaming protocol for embedded applications.

[![Linting](https://github.com/basilfx/python-tinylink/actions/workflows/lint.yml/badge.svg)](https://github.com/basilfx/python-tinylink/actions/workflows/lint.yml)
[![Testing](https://github.com/basilfx/python-tinylink/actions/workflows/test.yml/badge.svg)](https://github.com/basilfx/python-tinylink/actions/workflows/test.yml)

## Introduction
This is a general purpose Python module to provide a bi-directional frame-based
streaming protocol for low-speed embedded applications, such as serial
connected devices. It allowes the receiver to 'jump into' a stream of data
frames. Every frame starts with a preamble, so the receiver can synchronize.

The format of a frame is as follows:

```
| Preamble            | Header         | Body                                |
| 0xAA 0x55 0xAA 0x55 | AA AA BB BB CC | XX XX .. .. .. .. XX XX YY YY YY YY |

Fields:
A = Flags
B = Length
C = XOR checksum over header
X = Payload (max. 65536 bytes)
Y = CRC32 checksum over header + payload
```

The flags field can be used for arbitrary purposes. The payload is optional.

Escaping of the header and body are performed using byte-stuffing, to ensure
that the header and body can contain bytes of the preamble.

Error correction is not implemented and the bytes are not strictly aligned. The
endianness is customizable.

## State chart diagram
Below is a simplified statechart diagram of the receiver.
![Alt text](docs/statechart.png)

## Installation
The latest development version can be installed via
`pip install git+https://github.com/basilfx/python-tinylink`.

## CLI
A CLI is included to experiment with TinyLink. When installed, run
`tinylink /dev/tty.PORT_HERE` to start it. You can use it to send raw bytes via
the link and display what comes back.

The CLI supports so-called modifiers to modify the outgoing data. For example,
the input `\flags=16 hello world` would send a frame with the flags equal to 16
and the payload 'hello world'

The CLI requires additional dependencies, that are installed using the `cli`
dependency specification (`poetry install --extras cli`).

## Tests
To run the tests, please clone this repository and run `poetry run pytest`.

## Contributing
See the [`CONTRIBUTING.md`](CONTRIBUTING.md) file.

## License
See the [`LICENSE.md`](LICENSE.md) file (MIT license).
