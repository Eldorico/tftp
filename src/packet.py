# -*- coding: utf-8 -*-

__title__ = "packet.py"
__description__ = "This module implements the packet types of TFTP itself, and the corresponding encode and decode methods for them."
__author__ = "Federico Lerda, Kevin Estalella, and Federico Pfeiffer"
__version__ = "1.0.0"


from aenum import enum
import struct


class OPCODE(enum):
    RRQ = 1
    WRQ = 2
    DATA = 3
    ACK = 4
    ERR = 5

ERROR_CODES = ["Undef",
               "File not found",
               "Access violation",
               "Disk full or allocation exceeded",
               "Illegal TFTP operation",
               "Unknown transfer ID",
               "File already exists",
               "No such user"]

DEFAULT_MODE = "octet"


def build_packet_rrq(filename, mode = DEFAULT_MODE):
    return struct.pack("!H", OPCODE.RRQ) + filename + "\0" + mode + "\0"


def build_packet_wrq(filename, mode = DEFAULT_MODE):
    return struct.pack("!H", OPCODE.WRQ) + filename + "\0" + mode + "\0"


def build_packet_data(blocknr, data):
    return struct.pack("!HH", OPCODE.DATA, blocknr) + data


def build_packet_ack(blocknr):
    return struct.pack("!HH", OPCODE.ACK, blocknr)


def build_packet_err(errcode):
    return struct.pack("!HH", OPCODE.ERR, errcode) + ERROR_CODES[errcode] + "\0"


def decode_packet(msg):
    """
    This function is used to decode a received packet where the first parameter
    is the OPCODE in the integer format and the values are the data of the others Packet parameters.
    """
    opcode = struct.unpack("!H", msg[:2])[0]
    if opcode == OPCODE.RRQ:
        l = msg[2:].split('\0')
        if len(l) != 3:
            return None
        return opcode, l[1], l[0]
    elif opcode == OPCODE.WRQ:
        l = msg[2:].split('\0')
        if len(l) != 3:
            return None
        return opcode, l[1], l[0]
    elif opcode == OPCODE.ACK:
        block_num = struct.unpack("!H", msg[2:])[0]
        return opcode, block_num, None
    elif opcode == OPCODE.DATA:
        block_num = struct.unpack("!H", msg[2:4])[0]
        data = msg[4:]
        return opcode, block_num, data
    elif opcode == OPCODE.ERR:
        block_num = struct.unpack("!H", msg[2:4])[0]
        errmsg = msg[4:]
        return opcode, block_num, errmsg
    return None