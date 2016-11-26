#! /usr/bin/python
# -*- coding: utf-8 -*-

import struct, enum

OPCODE = enum(RRQ=1, WRQ=2, DATA=3, ACK=4, ERR=5)
# OPCODE_RRQ = 1
# OPCODE_WRQ = 2
# OPCODE_DATA = 3
# OPCODE_ACK = 4
# OPCODE_ERR = 5

ERROR_CODES = enum('Undefined',
                   'File not found',
                   'Access violation',
                   'Disk full or allocation exceeded',
                   'Illegal TFTP operation',
                   'Unknown transfer ID',
                   'File already exists',
                   'No such user'
                   )
# ERROR_CODES = ["Undef",
#                "File not found",
#                "Access violation",
#                "Disk full or allocation exceeded",
#                "Illegal TFTP operation",
#                "Unknown transfer ID",
#                "File already exists",
#                "No such user"]

DEFAULT_MODE = "binary"


def build_packet_rrq(filename, mode = DEFAULT_MODE):
    return struct.pack("!H", OPCODE.RRQ) + filename + "\0" + mode + "\0"


def build_packet_wrq(filename, mode = DEFAULT_MODE):
    return struct.pack("!H", OPCODE.WRQ) + filename + "\0" + mode + "\0"


def build_packet_data(blocknr, data):
    return struct.pack("!HH", OPCODE.DATA, blocknr) + data


def build_packet_ack(blocknr):
    return struct.pack("!HH", OPCODE.ACK, blocknr)


def build_packet_err(errcode, errmsg):
    return struct.pack("!HH", OPCODE.ERR, errcode) + ERROR_CODES[errcode] + "\0"
    # return struct.pack("!HH", OPCODE.ERR, errcode) + errmsg + "\0" #initial


def decode_packet(msg):
    """
    Cette fonction  permet de recevoir un packet ou la premiere valeure
    est le OPCODE au format entier et les valeur suivantes sont les donnees des autres
    parametres du paquets.
    """
    opcode = struct.unpack("!H", msg[:2])[0]
    if opcode == OPCODE.RRQ:
        l = msg[2:].split('\0')
        if len(l) != 3:
            return None
        return opcode, l[1], l[2]
    elif opcode == OPCODE.WRQ:
        l = msg[2:].split('\0')
        if len(l) != 3:
            return None
        return opcode, l[1], l[2]
    elif opcode == OPCODE.ACK:
        block_num = struct.unpack("!H", msg[2:])[0]
        return opcode, block_num
    elif opcode == OPCODE.DATA:
        block_num = struct.unpack("!H", msg[2:4])[0]
        data = msg[4:]
        return opcode, block_num, data
    elif opcode == OPCODE.ERR:
        block_num = struct.unpack("!H", msg[2:4])[0]
        errmsg = msg[4:]
        return opcode, block_num, errmsg
    return None