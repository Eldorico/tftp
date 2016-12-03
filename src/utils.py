#!/bin/env python
"Tftp common utility module"
## Federico*2 + Kevin ##
## receive_file + send_file##

import os
import sys
import socket
import struct
import binascii
import argparse
from packet import *
from aenum import Enum


class STATES(Enum):
    WAIT_WRQ_ACK = 1
    WAIT_ACK = 2
    WAIT_LAST_ACK = 3
    WAIT_FIRST_DATA = 4
    WAIT_DATA = 5
    WAIT_TERMINATION_TIMER_OUT = 6
    DEBUG_RECEIVE_OR_SEND = 7


class AppRq(Enum):
    GET = 1
    PUT = 2

MAX_PACKET_SIZE = 512
MAX_ATTEMPTS_NUMBER = 4


def state_wait_ack(pv):

    block_num = 1
    """
        Je recois les paquets et je send le ACK;
        Si le ACK recu est mauvaise je re-send la data precedente ou timeout,
    """
    while True:
        block_num +=1
        data_next = pv.fileobj.read(MAX_PACKET_SIZE)

        attempt_number = 0
        # reception des paquets ACK 1 --> penultimate ACK
        while attempt_number < MAX_ATTEMPTS_NUMBER:
            try:
                ack = pv.sock.recv(MAX_PACKET_SIZE)
                op_code, resp_blk_num, resp_data = decode_packet(ack)
                if op_code == OPCODE.ERR:
                    sys.stderr.write('Error code: %s. \n   Message: %s\n' % (ERROR_CODES[resp_blk_num], resp_data))
                    close_and_exit(pv.file_obj, pv.sock, -4)
                break
            except socket.timeout:
                pv.socksend(build_packet_data(pv.block_num, pv.data))
                attempt_number += 1
                continue
        if attempt_number == MAX_ATTEMPTS_NUMBER:
            sys.stderr.write('Failed to connect to host %s on port %d.\n   Timeout reached.\n' % (pv.host, pv.port))
            close_and_exit(pv.file_obj, pv.sock, -3)

        pv.sock.send(build_packet_data(block_num, data_next))

        if len(data_next) < MAX_PACKET_SIZE:
            # go the the STATE = LAST_ACK
            pv.last_data_sent = data_next
            pv.last_block_num = block_num
            pv.state = STATES.WAIT_LAST_ACK
            return

def state_wait_data(pv):

    block_num_ack = 1
    while True:
        attempt_number = 0
        # reception des paquets msg
        # receive avec timeout socket sinon resend ACK blk_num
        while attempt_number < MAX_ATTEMPTS_NUMBER:
            try:
                paquet = pv.sock.recv(516)
                break
            except socket.timeout:
                pv.sock.send(build_packet_ack(block_num_ack))
                attempt_number += 1
                continue
        if attempt_number == MAX_ATTEMPTS_NUMBER:
            sys.stderr.write('Failed to connect to host %s on port %d.\n   Timeout reached.\n' % (pv.host, pv.port))
            close_and_exit(pv.file_obj, pv.sock, -3, pv.filename)
        #Decode du msg avec paquet.py
        op_code, resp_blk_num, resp_data = decode_packet(paquet)
        if op_code == OPCODE.ERR:
            sys.stderr.write('Error code: %s. \n   Message: %s\n' % (ERROR_CODES[resp_blk_num], resp_data))
            close_and_exit(pv.file_obj, pv.sock, -4, pv.filename)

        elif op_code == OPCODE.DATA:
            # il s'agit bien d'un paquet DATA.
            if resp_blk_num != block_num_ack+1:
                # skip unexpected #block data packet
                print 'unexpected block num', resp_blk_num
                continue
            pv.file_obj.write(resp_data)
            pv.sock.send(build_packet_ack(resp_blk_num))

        if len(resp_data) < MAX_PACKET_SIZE:
            pv.sock.send(build_packet_ack(resp_blk_num))
            pv.last_block_num = resp_blk_num
            pv.state = STATES.WAIT_TERMINATION_TIMER_OUT
            return

    block_num_ack += 1


def state_wait_last_ack(pv):
    attempt_number = 0
    # reception du last paquet
    while attempt_number < MAX_ATTEMPTS_NUMBER:
        try:
            ack = pv.sock.recv(MAX_PACKET_SIZE)
            op_code, resp_blk_num, resp_data = decode_packet(ack)
            if op_code == OPCODE.ERR:
                sys.stderr.write('Error code: %s. \n   Message: %s\n' % (ERROR_CODES[resp_blk_num], resp_data))
                close_and_exit(pv.file_obj, pv.sock, -4)
            break
        except socket.timeout:
            pv.socksend(build_packet_data(pv.block_num, pv.data))
            attempt_number += 1
            continue
    if attempt_number == MAX_ATTEMPTS_NUMBER:
        sys.stderr.write('Failed to connect to host %s on port %d.\n   Timeout reached.\n' % (pv.host, pv.port))
        close_and_exit(pv.file_obj, pv.sock, -3)
    else :
        close_and_exit(pv.file_obj, pv.sock, 0)


def state_wait_termination_timer_out(pv):

    while True:
        attempt_number = 0
        # reception des paquets msg
        # receive avec timeout socket sinon resend ACK blk_num
        while attempt_number < MAX_ATTEMPTS_NUMBER:
            try:
                paquet = pv.sock.recv(516)
                break
            except socket.timeout:
                pv.sock.send(build_packet_ack(pv.last_block_num))
                attempt_number += 1
                continue
        if attempt_number == MAX_ATTEMPTS_NUMBER:
            #exit correctly
            close_and_exit(pv.file_obj, pv.sock, 0)
        #Decode du msg avec paquet.py
        op_code, resp_blk_num, resp_data = decode_packet(paquet)
        if op_code == OPCODE.ERR:
            sys.stderr.write('Error code: %s. \n   Message: %s\n' % (ERROR_CODES[resp_blk_num], resp_data))
            close_and_exit(pv.file_obj, pv.sock, -4)

# le parser return arg0 = nom serveur , arg1 = port du serveur, arg2 = fichier destination
def parser():
    parser = argparse.ArgumentParser(description='Tftp python.')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-get', help='get a file from server', nargs=3, metavar=('server', 'port', 'filename'))
    group.add_argument('-put', help='send a file to server', nargs=3, metavar=('server', 'port', 'filename'))
    parsed_arg = parser.parse_args()
    if parsed_arg.get:
        return AppRq.GET, parsed_arg.get[0], int(parsed_arg.get[1]), parsed_arg.get[2]
    elif parsed_arg.put:
        return AppRq.PUT, parsed_arg.put[0], int(parsed_arg.put[1]), parsed_arg.put[2]

def close_and_exit(file_object, socket_obj, exit_code, filepath_to_delete = None):
    """ closes a file, a socket and exits the program with a given exit code
    :param file_object:  the file object to close
    :param socket_obj: the socket object to close
    :param exit_code:
    :param filepath_to_delete: if not None, the file represented by filepath will be deleted
    """
    # close file and delete if needed
    try:
        if file_object is not None:
            file_object.close()
            if filepath_to_delete is not None:
                os.remove(filepath_to_delete)

        # close socket
        if socket_obj is not None:
            socket_obj.shutdown(socket.SHUT_RDWR)
    except Exception:
        pass

    # exit program
    sys.exit(exit_code)






