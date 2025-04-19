import argparse
import asyncio
import csv
import struct
import sys
from io import StringIO
from typing import Optional

import serial_asyncio
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import FileHistory
from prompt_toolkit.patch_stdout import patch_stdout

import tinylink
from tinylink.utils import create_async_handle


def parse_arguments(argv: list[str]) -> argparse.Namespace:
    """
    Create and parse command line arguments.
    """

    parser = argparse.ArgumentParser(prog=argv[0])

    # Add options.
    parser.add_argument("port", type=str, help="serial port")
    parser.add_argument(
        "baudrate", type=int, nargs="?", default=9600, help="serial baudrate"
    )
    parser.add_argument(
        "--length", type=int, default=2**16, help="maximum length of payload"
    )
    parser.add_argument(
        "--endianness",
        type=str,
        default="little",
        choices=["big", "little"],
        help="endianness of link",
    )

    # Parse command line.
    return parser.parse_args(argv[1:])


def dump(prefix: str, data: bytes) -> str:
    """
    Dump data as two hex columns.
    """

    result = []
    length = len(data)

    for i in range(0, length, 16):
        hexstr = ""
        bytestr = b""

        for j in range(0, 16):
            if i + j < length:
                b = data[i + j]
                hexstr += "%02x " % b
                bytestr += bytes((b,)) if 0x20 <= b < 0x7F else b"."
            else:
                hexstr += "   "

            if (j % 4) == 3:
                hexstr += " "

        result.append(prefix + " " + hexstr + bytestr.decode("ascii"))

    # Return concatenated string.
    return "\n".join(result)


async def handle_link(link: tinylink.AsyncTinyLink) -> None:
    """
    Process incoming frames.
    """

    while True:
        frame = await link.read_frame()

        if frame:
            sys.stdout.write(">>> # Flags = 0x%04x\n" % frame.flags)

            if frame.payload:
                sys.stdout.write(">>> # Length = %d\n" % len(frame.payload))
                sys.stdout.write(dump(">>>", frame.payload) + "\n\n")


async def handle_console(link: tinylink.AsyncTinyLink) -> Optional[bool]:
    """
    Process console inputs.
    """

    completer = WordCompleter(["\\flags=", "\\pack=", "\\wait=", "\\repeat="])

    session = PromptSession(history=FileHistory(".history"))

    while True:
        with patch_stdout():
            try:
                line = await session.prompt_async("--> ", completer=completer)
            except KeyboardInterrupt:
                continue

            if not line:
                continue

            await parse_line(link, line)


async def parse_line(link: tinylink.AsyncTinyLink, line: str) -> None:
    # Abuse the CSV module as a command parser, because CSV-like arguments are
    # possible.
    items = list(csv.reader(StringIO(line.strip()), delimiter=" "))

    if not items:
        return

    frame = tinylink.Frame()
    repeat = 1
    pack = "B"

    for item in items[0]:
        if item == "":
            continue
        elif item[0] == "\\":
            try:
                k, v = item[1:].split("=")

                if k == "flags":
                    frame.flags = int(v) & 0xFFFF
                elif k == "pack":
                    pack = v
                elif k == "wait":
                    await asyncio.sleep(float(v))
                elif k == "repeat":
                    repeat = int(v)
                else:
                    raise ValueError(f"Unknown modifier: {k}")
            except Exception as e:  # noqa
                sys.stdout.write(f"Unable to parse modifier: {e}\n")
                return
        else:
            try:
                # Assume it is a float.
                value = struct.pack(link.endianness + pack, float(item))
            except:  # noqa
                try:
                    # Assume it is an int.
                    value = struct.pack(link.endianness + pack, int(item, 0))
                except:  # noqa
                    try:
                        # Assume it is a byte string.
                        item_bytes = item.encode("ascii")
                        value = struct.pack(
                            link.endianness + str(len(item_bytes)) + "s", item_bytes
                        )
                    except Exception as e:  # noqa
                        sys.stdout.write(
                            "Unable to parse input as float, integer or byte\n"
                        )
                        return

            # Concat to frame.
            frame.payload = (frame.payload or bytes()) + value

    # Output the frame.
    for _ in range(repeat):
        sys.stdout.write("<<< # Flags = 0x%04x\n" % frame.flags)

        if frame.payload:
            sys.stdout.write("<<< # Length = %d\n" % len(frame.payload))
            sys.stdout.write(dump("<<<", frame.payload) + "\n\n")

        # Write the frame.
        try:
            await link.write_frame(frame)
        except ValueError as e:
            sys.stdout.write(f"Could not write frame: {e}\n")
            return


def run() -> None:
    """
    Entry point for console script.
    """

    sys.exit(asyncio.run(main(sys.argv)))


async def main(argv: list[str]) -> int:
    """
    Main entry point.
    """

    # Parse arguments.
    arguments = parse_arguments(argv)

    if arguments.endianness == "little":
        endianness = tinylink.LITTLE_ENDIAN
    else:
        endianness = tinylink.BIG_ENDIAN

    # Open serial port and create link.
    reader, writer = await serial_asyncio.open_serial_connection(
        url=arguments.port, baudrate=arguments.baudrate
    )

    link = tinylink.AsyncTinyLink(
        create_async_handle(reader, writer),
        max_payload_length=arguments.length,
        endianness=endianness,
    )

    # Start co-routines and wait until finished.
    await asyncio.gather(handle_console(link), handle_link(link))

    # Done.
    return 0


# E.g. `python cli.py /dev/tty.usbmodem1337 --baudrate 9600`.
if __name__ == "__main__":
    run()
