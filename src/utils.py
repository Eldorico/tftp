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


def state_wait_ack(protocol_variables):
    """
    :param protocol_variables:
    :return:
    """
    pass


def state_wait_data(protocol_variables):
    """
    :param protocol_variables:
    :return:
    """
    pass


def state_wait_last_ack(protocol_variables):
    """
    :param protocol_variables:
    :return:
    """
    pass


def state_wait_termination_timer_out(protocol_variables):
    """
    :param protocol_variables:
    :return:
    """
    pass


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

# -- receive file --.
def receive_file(sock, fd, first_data_blk):
    #on traite le premiere paquet et ACK
    if first_data_blk:
        fd.write(first_data_blk)
        sock.send(build_packet_ack(1))
    block_num_ack = 1

    if len(first_data_blk) < MAX_PACKET_SIZE:
        fd.close()
        file_len = len(first_data_blk)
        print '%d bytes recu.' % file_len
        return True

    else:

        #loop du tftp reception donees.
        done = 0

        attempt_number = 0
        """
            Si packet data OK send ACK au serveur;
            Si erreur dans le packet ou timeout, exit et return erreur;
        """

        while done == 0:
            attempt_number = 0
            # reception des paquets msg
            # receive avec timeout socket sinon resend ACK blk_num
            while attempt_number < MAX_ATTEMPTS_NUMBER:
                try:
                    paquet = sock.recv(516)
                    break
                except socket.timeout:
                    sock.send(build_packet_ack(block_num_ack))
                    attempt_number += 1
                    continue

            #print "test", paquet
            #Decode du msg avec paquet.py
            opcode,blck_num, data = decode_packet(paquet)
            #test OPCODE
            if opcode == OPCODE.ERR:
                print "Error", data
                return False
            elif opcode == OPCODE.DATA:
                # il s'agit bien d'un paquet DATA.
                if blck_num != block_num_ack+1:
                    # skip unexpected #block data packet
                    print 'unexpected block num', blck_num
                    continue
                fd.write(data)

                sock.send(build_packet_ack(blck_num))
                done = 0

                if len(data) < MAX_PACKET_SIZE:
                    #done = True
                    fd.close()
                    file_len = MAX_PACKET_SIZE * (block_num_ack) + len(data)
                    print '%d bytes recu.' % file_len
                    done = 1
                    # dernier paquet set de DONE = 1

            block_num_ack += 1

    return True


def send_file(socket_obj, file_obj):
    """
    :param socket_obj:
    :param file_obj:
    :return:
    """
    pass


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






