"""Locate the FT232R FTDI regardless of which ttyUSB* it lands on."""
import sys

from serial.tools import list_ports

FTDI_VID_PID = (0x0403, 0x6001)


def find_ftdi() -> str:
    for p in list_ports.comports():
        if (p.vid, p.pid) == FTDI_VID_PID:
            return p.device
    sys.exit('FT232R not found on any tty port')
