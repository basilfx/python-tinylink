import sys
import csv
import signal
import serial
import select
import struct
import tinylink
import argparse
import cStringIO
import time

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
    parser.add_argument("baudrate", type=int, default=9600,
        help="serial baudrate")
    parser.add_argument("--length", type=int, default=2**16,
        help="maximum length of frame")
    parser.add_argument("--endianness", type=str, default="little",
        choices=["big", "little"], help="maximum length of frame")

    # Parse command line
    return parser.parse_args(), parser

def dump(prefix, data):
    """
    Dump data as two hex columns
    """

    result = []
    length = len(data)

    for i in xrange(0, length, 16):
        hexstr = bytestr = ""

        for j in xrange(0, 16):
            if i + j < length:
                b = ord(data[i + j])
                hexstr  += "%02x " % b
                bytestr += data[i + j] if 0x20 <= b < 0x7F else "."
            else:
                hexstr  += "   "

            if (j % 4) == 3:
                hexstr += " "

        result.append(prefix + " " + hexstr + bytestr)

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

        if type(frame) != tinylink.ResetFrame:
            sys.stdout.write("### Lenght = %d\n" % len(frame.data))
            sys.stdout.write(dump("<<<", frame.data) + "\n\n")
        else:
            sys.stdout.write("\n")

def process_stdin(link):
    """
    Process stdin commands.
    """

    command = sys.stdin.readline()

    # End of file
    if len(command) == 0:
        return False

    # Very simple command parser
    items = list(csv.reader(cStringIO.StringIO(command.strip()), delimiter=" "))

    if not items:
        return

    # Initialize state and start parsing
    frame = tinylink.BaseFrame()
    repeat = 1
    pack = "B"

    try:
        for item in items[0]:
            if item[0] == "/":
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
                    raise ValueError("Unkown option: %s" % key)
            else:
                try:
                    # Assume it's a float
                    value = struct.pack(link.endianness + pack, float(item))
                except:
                    try:
                        # Assume it's an int
                        value = struct.pack(link.endianness + pack,
                            int(item, 0))
                    except ValueError:
                        # Assume as string
                        value = ""

                        for b in item:
                            value += struct.pack(link.endianness + "B",
                                ord(b))

                # Concat to frame
                frame.data = (frame.data or "") + value
    except Exception as e:
        sys.stdout.write("Parse exception: %s\n" % e)
        return

    # Output the data
    for i in xrange(repeat):
        sys.stdout.write("### Flags = 0x%04x\n" % frame.flags)

        if frame.data:
            sys.stdout.write("### Lenght = %d\n" % len(frame.data))
            sys.stdout.write(dump(">>>", frame.data) + "\n\n")

        # Send frame
        try:
            link.write_frame(frame)
        except ValueError as e:
            sys.stdout.write("Could not send frame: %s\n" % e)
            return

def main():
    """
    Main entry point.
    """

    arguments, parser = parse_arguments()

    # Open  serial port and create link
    if arguments.endianness == "little":
        endianness = tinylink.LITTLE_ENDIAN
    else:
        endianness = tinylink.BIG_ENDIAN

    handle = serial.Serial(arguments.port, baudrate=arguments.baudrate)
    link = tinylink.TinyLink(handle, max_length=arguments.length,
        endianness=endianness)

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