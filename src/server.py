__title__ = "server.py"
__description__ = "Instantiate an instance of the server, and then run the listen() method to listen for client requests."
__author__ = "Federico Lerda, Kevin Estalella, and Federico Pfeiffer"
__version__ = "1.0.0"

import random

from utils import *
from packet import *
import socket


class Server:

    def __init__(self):
        self.listen_ip = "0.0.0.0"
        self.listen_port = None
        self.directory = None
        self.sock = None
        self.client_ip = None
        self.file_obj = None
        self.filename = None
        self.source_tid = None
        self.destination_tid = None
        self.state = None
        self.response_address = None
        self.response_packet = None
        self.nb_paquets_lost = 0


    def parser(self):
        """ parse the user input of the command line
        :return: the parser return arg0 = port and arg1 = directory
        """
        parser = argparse.ArgumentParser(description='Tftp python.')

        parser.add_argument(
            '-p', '--port', type=int, help='Port number', required=True)

        parser.add_argument(
            '-d', '--directory', type=str, help='Directory name', required=True)

        parsed_arg = parser.parse_args()

        return int(parsed_arg.port), parsed_arg.directory


    def state_wait_first_data(self):
        """ function corresponding to the wait_first_data state.
            globally, it waits for the first data packet. If it gets it, we can then pass to the wait_data state.
        :param self: the variables used for the transfer.
        :return:
        """

        TIMEOUT_IN_SECONDS = 1

        attempt_number = 0
        while attempt_number < MAX_ATTEMPTS_NUMBER:
            self.sock.settimeout(TIMEOUT_IN_SECONDS)
            try:
                self.response_packet, self.response_address = self.sock.recvfrom(516)
                break
            except socket.timeout:
                attempt_number += 1
                self.sock.sendto(build_packet_ack(0), self.response_address)
                self.nb_paquets_lost += 1
                continue
        if attempt_number == MAX_ATTEMPTS_NUMBER:
            sys.stderr.write('Failed to connect to host %s on port %d.\n   Timeout reached.\n' % (self.host, self.port))
            close_and_exit(self.file_obj, self.sock, -3, self.filename)

        # analyse answer
        resp_op_code, resp_blk_num, resp_data = decode_packet(self.response_packet)
        if resp_op_code == OPCODE.DATA and resp_blk_num == 1:
            destination_tid = self.response_address[1]
            self.sock.connect((self.listen_ip, destination_tid))
            self.file_obj.write(resp_data)
            self.sock.send(build_packet_ack(1))
            if len(resp_data) < MAX_PACKET_SIZE:
                self.last_block_num = resp_blk_num
                self.state = STATES.WAIT_TERMINATION_TIMER_OUT
            else:
                self.state = STATES.WAIT_DATA
            return
        elif resp_op_code == OPCODE.ERR:
            sys.stderr.write('Connexion refused with host %s on port %d.\n   Error code: %s. \n   Message: %s\n' % (
            self.host, self.port, ERROR_CODES[resp_blk_num], resp_data))
            close_and_exit(self.file_obj, self.sock, -4)
        else:
            sys.stderr.write('state_first_data() : An error occured')
            close_and_exit(self.file_obj, self.sock, -5, self.filename)


    def listen(self):
        """Start a server listening on the supplied interface and port. This
        defaults to 0.0.0.0 and port passed in command line parameter."""

        # Create UDP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        try:
            # Bind socket to local host and port
            self.sock.bind((self.listen_ip, self.listen_port))

        except socket.error as err:
            print 'Bind failed. Error Code : ' + str(err[0]) + ' Message ' + err[1]
            close_and_exit(None, None, -1)

        self.response_packet, self.response_address = self.sock.recvfrom(self.listen_port)
        self.destination_tid = self.response_address[1]

        # analyse answer
        resp_op_code, resp_blk_num, resp_filename = decode_packet(self.response_packet)

        self.filename = resp_filename #Comment je get filename

        self.sock.connect((self.listen_ip, self.destination_tid))
        self.nb_paquets_lost = 0

        # WRQ REQUEST - Client ask to write a file
        if resp_op_code == OPCODE.WRQ:
            try:
                # open file
                self.file_obj = open(self.directory+'/'+self.filename, 'w')   #CHANGER FICHIER
            except IOError, e:
                sys.stderr.write("Can't create or erase file : ")
                sys.stderr.write("%s\n" % str(e))
                close_and_exit(None, None, -1)

            block_num = 0

            self.source_tid = random.randint(10000, 60000)

            self.sock.close()

            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.bind((self.listen_ip, self.source_tid))
            self.sock.connect((self.listen_ip, self.destination_tid))

            # create and send ack packet
            self.sock.sendto(build_packet_ack(block_num), self.response_address)

            self.state = STATES.WAIT_FIRST_DATA
            return

        # READ REQUEST - Client ask to read a file
        elif resp_op_code == OPCODE.RRQ:
            try:
                self.file_obj = open(self.directory+'/'+self.filename, 'r')
            except IOError, e:
                sys.stderr.write("Can't open file : ")
                sys.stderr.write("%s\n" % str(e))
                close_and_exit(None, None, -1)

            self.source_tid = random.randint(10000, 60000)
            self.sock.close()

            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.bind((self.listen_ip, self.source_tid))
            self.sock.connect((self.listen_ip, self.destination_tid))

            block_num = 1
            data_to_send = self.file_obj.read(MAX_PACKET_SIZE)

            if len(data_to_send) < MAX_PACKET_SIZE:
                self.state = STATES.WAIT_LAST_ACK
            else:
                self.state = STATES.WAIT_ACK
            self.sock.sendto(build_packet_data(block_num, data_to_send), self.response_address)
            return


    def exec_server_state(self, state):
        """ function to executes all the states for the server
        :param state: The state to execute: STATES(Enum)
        """
        if state == STATES.WAIT_FIRST_DATA:
            return self.state_wait_first_data()
        if state == STATES.WAIT_ACK :
            return state_wait_ack(self)
        elif state == STATES.WAIT_LAST_ACK:
            return state_wait_last_ack(self, True)
        elif state == STATES.WAIT_DATA:
            return state_wait_data(self)
        elif state == STATES.WAIT_TERMINATION_TIMER_OUT:
            return state_wait_termination_timer_out(self, True)
        elif state == STATES.LISTEN:
            return self.listen()


"""  ------------------------------------  """
"""           Script starts here           """
"""  ------------------------------------  """

s = Server()

# parse input
s.listen_port, s.directory = s.parser()

# listen is the initial state for server
s.state = STATES.LISTEN

# start state machine execution
while True:
    s.exec_server_state(s.state)
