#!/bin/env python
"Tftp common utility module"
## Federico*2 + Kevin ##
## receive_file + send_file##

import sys
import struct
import binascii
import argparse


MAX_PACKET_SIZE = 512


# le parser return arg0 = nom serveur , arg1 = port du serveur, arg2 = fichier destination
def parser():
    parser = argparse.ArgumentParser(description='Tftp python.')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-get', help='Get + nom du fichier', nargs = 3)
    group.add_argument('-put', help='Put + nom du fichier', nargs = 3)
    return parser.parse_args().get[1]


# -- receive file --.
def receive_file(sock, fd, first_data_blk, option):
    #on traite le premiere paquet et ACK
    if first_data_blk:
        fd.write(first_data_blk)
        sock.send(build_ack_paquet(1))
    block_num_ack = 1
    #loop du tftp reception donees.
    done = 0

    """
        Si packet data OK send ACK au serveur;
        Si erreur dans le packet ou timeout, exit et return erreur;
    """

    while not done:
        # reception des paquets msg
        paquet = sock.recvfrom(MAX_PACKET_SIZE)
        #Decode du msg avec paquet.py
        opcode,blck_num, data = decodepaquet(paquet)
        #test OPCODE
        if opcode == ERROR:
            print "Error", data
            return False
        elif opcode == DATA:
            # il s'agit bien d'un paquet DATA.
            if block_num != block_num_ack+1:
                # skip unexpected #block data packet
                print 'unexpected block num %d' % block_num
                continue
            fd.write(data)
            sock.send(build_ack_paquet(1))

            if len(data) < MAX_PACKET_SIZE:
                done = True
                fd.close()
                file_len = MAX_PACKET_SIZE * (block_num_ack -1) + len(data)
                print '%d bytes recu.' % file_len
                # dernier paquet set de DONE = 1
                done = 1

            block_num_ack += 1

    return True

if __name__ == "__main__":

    parser()






