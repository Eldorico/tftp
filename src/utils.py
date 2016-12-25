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
    LISTEN = 8


class AppRq(Enum):
    GET = 1
    PUT = 2

MAX_PACKET_SIZE = 512
MAX_ATTEMPTS_NUMBER = 4


def state_wait_ack(pv):
    """
    :param pv: protocolVariable. A Client or Server Object
    :return:
    """

    pv.last_block_num = 1
    """
        Je recois les paquets et je send le ACK;
        Si le ACK recu est mauvaise je re-send la data precedente ou timeout,
    """
    while True:
        data_next = pv.file_obj.read(MAX_PACKET_SIZE)

        attempt_number = 0
        # reception des paquets ACK 1 --> penultimate ACK
        while attempt_number < MAX_ATTEMPTS_NUMBER:
            try:
                ack = pv.sock.recv(MAX_PACKET_SIZE)
                op_code, resp_blk_num, resp_data = decode_packet(ack)
                if op_code == OPCODE.ERR:
                    sys.stderr.write('Error code: %s. \n   Message: %s\n' % (ERROR_CODES[resp_blk_num], resp_data))
                    close_and_exit(pv.file_obj, pv.sock, -4)
                elif resp_blk_num == pv.last_block_num:
                    pv.last_block_num +=1
                    break
                else:
                    continue
            except socket.timeout:
                pv.sock.send(build_packet_data(pv.last_block_num, pv.last_data_sent))
                attempt_number += 1
                pv.nb_paquets_lost += 1
                continue
        if attempt_number == MAX_ATTEMPTS_NUMBER:
            sys.stderr.write('Failed to connect to host %s on port %d.\n   Timeout reached.\n' % (pv.host, pv.port))
            close_and_exit(pv.file_obj, pv.sock, -3)

        pv.sock.send(build_packet_data(pv.last_block_num, data_next))

        if len(data_next) < MAX_PACKET_SIZE:
            # go the the STATE = LAST_ACK
            pv.last_data_sent = data_next
            pv.state = STATES.WAIT_LAST_ACK
            return

def state_wait_data(pv):
    """
    :param pv: protocolVariable. A Client or Server Object
    :return:
    """

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
                pv.nb_paquets_lost += 1
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
            block_num_ack += 1

        if len(resp_data) < MAX_PACKET_SIZE:
            pv.sock.send(build_packet_ack(resp_blk_num))
            pv.last_block_num = resp_blk_num
            pv.state = STATES.WAIT_TERMINATION_TIMER_OUT
            return


def state_wait_last_ack(pv, is_server = False):
    """
    :param pv: protocolVariable. A Client or Server Object
    :return:
    """
    attempt_number = 0
    # reception du last paquet
    while attempt_number < MAX_ATTEMPTS_NUMBER:
        try:
            ack = pv.sock.recv(MAX_PACKET_SIZE)
            op_code, resp_blk_num, resp_data = decode_packet(ack)
            if op_code == OPCODE.ERR:
                sys.stderr.write('Error code: %s. \n   Message: %s\n' % (ERROR_CODES[resp_blk_num], resp_data))
                print("Nb packets lost: %d. Efficienty: %f"%( pv.nb_paquets_lost, float(pv.last_block_num) / float(pv.last_block_num+pv.nb_paquets_lost)))
                close_and_exit(pv.file_obj, pv.sock, -4, None, is_server)
            break
        except socket.timeout:
            #print(pv.last_block_num, pv.last_data_sent)
            pv.sock.send(build_packet_data(pv.last_block_num, pv.last_data_sent))
            attempt_number += 1
            pv.nb_paquets_lost += 1
            continue
    if attempt_number == MAX_ATTEMPTS_NUMBER:
        sys.stderr.write('Failed to connect to host %s on port %d.\n   Timeout reached.\n' % (pv.host, pv.port))
        print("Nb packets lost: %d. Efficienty: %f"%( pv.nb_paquets_lost, float(pv.last_block_num) / float(pv.last_block_num+pv.nb_paquets_lost)))
        close_and_exit(pv.file_obj, pv.sock, -3, None, is_server)
    else :
        print("Nb packets lost: %d. Efficienty: %f"%( pv.nb_paquets_lost, float(pv.last_block_num) / float(pv.last_block_num+pv.nb_paquets_lost)))
        close_and_exit(pv.file_obj, pv.sock, 0, None, is_server)

    if is_server:
        pv.sock.shutdown(socket.SHUT_RDWR)
        pv.sock.close()
        pv.state = STATES.LISTEN
        return

def state_wait_termination_timer_out(pv, is_server = False):
    """
    :param pv: protocolVariable. A Client or Server Object
    :return:
    """
    while True:
        attempt_number = 0
        # reception des paquets msg
        # receive avec timeout socket sinon resend ACK blk_num
        while attempt_number < MAX_ATTEMPTS_NUMBER:
            try:
                paquet = pv.sock.recv(516)
                break
            except socket.timeout:
                try:
                    pv.sock.send(build_packet_ack(pv.last_block_num))
                except:
                    if is_server:
                        pv.state = STATES.LISTEN
                        return

                attempt_number += 1
                pv.nb_paquets_lost += 1
                continue
            except socket.error:
                print("Nb packets lost: %d. Efficienty: %f"%( pv.nb_paquets_lost, float(pv.last_block_num) / float(pv.last_block_num+pv.nb_paquets_lost)))
                close_and_exit(pv.file_obj, pv.sock, 0, None, is_server)
        if attempt_number == MAX_ATTEMPTS_NUMBER:
            #exit correctly
            print("Nb packets lost: %d. Efficienty: %f"%( pv.nb_paquets_lost, float(pv.last_block_num) / float(pv.last_block_num+pv.nb_paquets_lost)))
            close_and_exit(pv.file_obj, pv.sock, 0, None, is_server)
        #Decode du msg avec paquet.py
        op_code, resp_blk_num, resp_data = decode_packet(paquet)
        if op_code == OPCODE.ERR:
            sys.stderr.write('Error code: %s. \n   Message: %s\n' % (ERROR_CODES[resp_blk_num], resp_data))
            print("Nb packets lost: %d. Efficienty: %f"%( pv.nb_paquets_lost, float(pv.last_block_num) / float(pv.last_block_num+pv.nb_paquets_lost)))
            close_and_exit(pv.file_obj, pv.sock, -4, None, is_server)

        if is_server:
            pv.sock.shutdown(socket.SHUT_RDWR)
            pv.sock.close()
            pv.state = STATES.LISTEN
            return


def close_and_exit(file_object, socket_obj, exit_code, filepath_to_delete = None, is_server = False):
    """ closes a file, a socket and exits the program with a given exit code (unless is_server is True)
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

    if not is_server:
        # exit program
        sys.exit(exit_code)
