from six.moves import xrange
from six import StringIO

import csv
import six
import sys
import time
import select
import struct
import tinylink
import argparse

try:
    import serial
except ImportError:
    serial = None


def run():
    """
    Entry point for console script.
    """

    sys.exit(main())


def parse_arguments():
    """
    Create and parse command line arguments.
    """

    parser = argparse.ArgumentParser()

    # Add option
    parser.add_argument("port", type=str, help="serial port")
    parser.add_argument(
        "baudrate", type=int, default=9600, help="serial baudrate")
    parser.add_argument(
        "--length", type=int, default=2**16, help="maximum length of frame")
    parser.add_argument(
        "--endianness", type=str, default="little", choices=["big", "little"],
        help="maximum length of frame")

    # Parse command line
    return parser.parse_args(), parser


def dump(prefix, data):
    """
    Dump data as two hex columns.
    """

    result = []
    length = len(data)

    for i in xrange(0, length, 16):
        hexstr = ""
        bytestr = b""

        for j in xrange(0, 16):
            if i + j < length:
                b = six.indexbytes(data, i + j)
                hexstr += "%02x " % b
                bytestr += six.int2byte(b) if 0x20 <= b < 0x7F else b"."
            else:
                hexstr += "   "

            if (j % 4) == 3:
                hexstr += " "

        result.append(prefix + " " + hexstr + bytestr.decode("ascii"))

    # Return concatenated string
    return "\n".join(result)


def process_link(link):
    """
    Process incoming link data.
    """

    frames = link.read()

    # Print received frames
    for frame in frames:
        sys.stdout.write("### Type = %s\n" % frame.__class__.__name__)
        sys.stdout.write("### Flags = 0x%04x\n" % frame.flags)

        sys.stdout.write("### Length = %d\n" % len(frame.data))
        sys.stdout.write(dump("<<<", frame.data) + "\n\n")


def process_stdin(link):
    """
    Process stdin commands.
    """

    command = sys.stdin.readline()

    # End of file.
    if len(command) == 0:
        return False

    # Abuse the CSV module as a command parser, because CSV-like arguments are
    # possible.
    items = list(csv.reader(StringIO(command.strip()), delimiter=" "))

    if not items:
        return

    # Initialize state and start parsing.
    frame = tinylink.Frame()
    repeat = 1
    pack = "B"

    try:
        for item in items[0]:
            if item[0] == "\\":
                k, v = item[1:].split("=")

                if k == "flags":
                    frame.flags = int(v, 0)
                elif k == "pack":
                    pack = v
                elif k == "wait":
                    time.sleep(float(v))
                elif k == "repeat":
                    repeat = int(v)
                else:
                    raise ValueError("Unkown option: %s" % k)
            else:
                try:
                    # Assume it is a float.
                    value = struct.pack(link.endianness + pack, float(item))
                except:
                    try:
                        # Assume it is an int.
                        value = struct.pack(
                            link.endianness + pack, int(item, 0))
                    except ValueError:
                        # Assume it is a byte string.
                        item = item.encode("ascii")
                        value = struct.pack(
                            link.endianness + str(len(item)) + "s", item)

                # Concat to frame.
                frame.data = (frame.data or bytes()) + value
    except Exception as e:
        sys.stdout.write("Parse exception: %s\n" % e)

    # Output the data.
    for i in xrange(repeat):
        sys.stdout.write("### Flags = 0x%04x\n" % frame.flags)

        if frame.data:
            sys.stdout.write("### Length = %d\n" % len(frame.data))
            sys.stdout.write(dump(">>>", frame.data) + "\n\n")

        # Send the frame.
        try:
            link.write_frame(frame)
        except ValueError as e:
            sys.stdout.write("Could not send frame: %s\n" % e)
            return


def main():
    """
    Main entry point.
    """

    if serial is None:
        sys.stdout.write(
            "TinyLink CLI uses PySerial, but it is not installed. Please "
            "install this first.\n")
        return 1

    # Parse arguments
    arguments, parser = parse_arguments()

    if arguments.endianness == "little":
        endianness = tinylink.LITTLE_ENDIAN
    else:
        endianness = tinylink.BIG_ENDIAN

    # Open  serial port and create link
    handle = serial.Serial(arguments.port, baudrate=arguments.baudrate)
    link = tinylink.TinyLink(
        handle, max_length=arguments.length, endianness=endianness)

    # Loop until finished
    try:
        # Input indicator
        sys.stdout.write("--> ")
        sys.stdout.flush()

        while True:
            readables, _, _ = select.select([handle, sys.stdin], [], [])

            # Read from serial port
            if handle in readables:
                process_link(link)

            # Read from stdin
            if sys.stdin in readables:
                if process_stdin(link) is False:
                    break

                # Input indicator
                sys.stdout.write("--> ")
                sys.stdout.flush()
    except KeyboardInterrupt:
        handle.close()

    # Done
    return 0

# E.g. `python tinylink_cli.py /dev/tty.usbmodem1337 --baudrate 9600'
if __name__ == "__main__":
    run()
