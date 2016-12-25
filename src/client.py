import sys
import random
import socket
from utils import *
from packet import *


class Client:

    def __init__(self):
        self.app_request = None
        self.sock = None
        self.host = None
        self.port = None
        self.filename = None
        self.file_obj = None
        self.request_packet = None
        self.source_tid = None
        self.state = None
        self.response_address = None
        self.response_packet = None
        self.last_data_sent = None
        self.last_block_num = None
        self.nb_paquets_lost = 0

    def send_request(self):
        """ Creates a socket in self and sends the self.request_paquet to self.host on self.port.
        :param self: a ProtocolVariables object. should contain
                a dest host,
                a dest port,
                a request_paquet that are not None
        """
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.source_tid = random.randint(10000, 60000)
            self.sock.bind(('', self.source_tid))
            self.sock.sendto(self.request_packet, (self.host, self.port))
        except socket.error, msg:
            sys.stderr.write('Failed to send request: error Code : ' + str(msg[0]) + ' Message: ' + msg[1] + '\n')
            close_and_exit(self.file_obj, self.sock, -2, self.filename if self.app_request == AppRq.GET else None)

    def state_wait_wrq_ack(self):
        """ function corresponding to the wait_wrq_ack state.
            Globally, it waits for a wrq ack. If it gets it, we can then pass to the wait_ack state.
        :param self:
        :return:
        """
        # get an answer or restart loop
        attempt_number = 0
        while attempt_number < MAX_ATTEMPTS_NUMBER:
            self.sock.settimeout(TIMEOUT_IN_SECONDS)
            try:
                self.response_packet, self.response_address = self.sock.recvfrom(MAX_PACKET_SIZE+4)
                break
            except socket.timeout:
                attempt_number += 1
                self.nb_paquets_lost += 1
                self.sock.close()
                self.send_request()
                continue
        if attempt_number == MAX_ATTEMPTS_NUMBER:
            sys.stderr.write('Failed to connect to host %s on port %d.\n   Timeout reached.\n' % (self.host, self.port))
            close_and_exit(self.file_obj, self.sock, -3)

        # analyse answer
        resp_op_code, resp_blk_num, resp_data = decode_packet(self.response_packet)
        if resp_op_code == OPCODE.ACK and resp_blk_num == 0:
            destination_tid = self.response_address[1]
            self.sock.connect((self.host, destination_tid))
            data_to_send = self.file_obj.read(MAX_PACKET_SIZE)
            self.sock.send(build_packet_data(1, data_to_send))
            self.last_data_sent = data_to_send
            self.last_block_num = 1
            if len(data_to_send) < MAX_PACKET_SIZE:
                self.state = STATES.WAIT_LAST_ACK
            else:
                self.state = STATES.WAIT_ACK
            return
        elif resp_op_code == OPCODE.ERR:
            sys.stderr.write('Connexion refused with host %s on port %d.\n   Error code: %s. \n   Message: %s\n'%(self.host, self.port, ERROR_CODES[resp_blk_num], resp_data))
            close_and_exit(self.file_obj, self.sock, -4)
        else:
            sys.stderr.write('state_wait_wrq_ack() : An error occured\n')
            close_and_exit(self.file_obj, self.sock, -5)

    def state_wait_first_data(self):
        """ function corresponding to the wait_wrq_ack state.
            globally, it waits for a the first data packet. If it gets it, we can then pass to the wait_data state.
        :param self: the variables used for the transfer.
        :return:
        """
        # get an answer or restart loop
        attempt_number = 0
        while attempt_number < MAX_ATTEMPTS_NUMBER:
            self.sock.settimeout(TIMEOUT_IN_SECONDS)
            try:
                self.response_packet, self.response_address = self.sock.recvfrom(516)
                break
            except socket.timeout:
                attempt_number += 1
                self.sock.close()
                self.send_request()
                continue
        if attempt_number == MAX_ATTEMPTS_NUMBER:
            sys.stderr.write('Failed to connect to host %s on port %d.\n   Timeout reached.\n' % (self.host, self.port))
            close_and_exit(self.file_obj, self.sock, -3, self.filename)

        # analyse answer
        resp_op_code, resp_blk_num, resp_data = decode_packet(self.response_packet)
        if resp_op_code == OPCODE.DATA and resp_blk_num == 1:
            destination_tid = self.response_address[1]
            self.sock.connect((self.host, destination_tid))
            self.file_obj.write(resp_data)
            self.sock.send(build_packet_ack(1))
            if len(resp_data) < MAX_PACKET_SIZE:
                self.last_block_num = resp_blk_num
                self.state = STATES.WAIT_TERMINATION_TIMER_OUT
            else:
                self.state = STATES.WAIT_DATA
            return
        elif resp_op_code == OPCODE.ERR:
            sys.stderr.write('Connexion refused with host %s on port %d.\n   Error code: %s. \n   Message: %s\n'%(self.host, self.port, ERROR_CODES[resp_blk_num], resp_data))
            close_and_exit(self.file_obj, self.sock, -4)
        else:
            sys.stderr.write('state_first_data() : An error occured')
            close_and_exit(self.file_obj, self.sock, -5, self.filename)

    def exec_client_state(self, state):
        """ function to executes all the states for the client.
        :param state: The state to execute: STATES(Enum)
        """
        if state == STATES.WAIT_WRQ_ACK :
            return self.state_wait_wrq_ack()
        elif state == STATES.WAIT_ACK :
            return state_wait_ack(self)
        elif state == STATES.WAIT_LAST_ACK:
            return state_wait_last_ack(self)
        elif state == STATES.WAIT_FIRST_DATA:
            return self.state_wait_first_data()
        elif state == STATES.WAIT_DATA:
            return state_wait_data(self)
        elif state == STATES.WAIT_TERMINATION_TIMER_OUT:
            return state_wait_termination_timer_out(self)
        else:
            sys.stderr.write('exec_client_state() : State not recognized')

    def parser(self):
        """ parse the user input of the command line
        :return: le parser return arg0 = nom serveur , arg1 = port du serveur, arg2 = fichier destination
        """
        parser = argparse.ArgumentParser(description='Tftp python.')
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('-get', help='get a file from server', nargs=3, metavar=('server', 'port', 'filename'))
        group.add_argument('-put', help='send a file to server', nargs=3, metavar=('server', 'port', 'filename'))
        parsed_arg = parser.parse_args()
        if parsed_arg.get:
            return AppRq.GET, parsed_arg.get[0], int(parsed_arg.get[1]), parsed_arg.get[2]
        elif parsed_arg.put:
            return AppRq.PUT, parsed_arg.put[0], int(parsed_arg.put[1]), parsed_arg.put[2]


"""  ------------------------------------  """
"""           Script starts here           """
"""  ------------------------------------  """

# instantiate variables used for the transfer
TIMEOUT_IN_SECONDS = 1
MAX_ATTEMPTS_NUMBER = 4

c = Client()

# parse input
c.app_request, c.host, c.port, c.filename = c.parser()

# open file
try:
    if c.app_request == AppRq.GET:
        c.file_obj = open(c.filename, 'w')  # TODO: think of a backup plan? (file is deleted if an error occurs)
    elif c.app_request == AppRq.PUT:
        c.file_obj = open(c.filename, 'r')
except IOError, e:
    if c.app_request == AppRq.GET:
        sys.stderr.write("Can't create or erase file : ")
    else:
        sys.stderr.write("Can't open file : ")
    sys.stderr.write("%s\n" % str(e))
    close_and_exit(None, None, -1)


# create request packet
if c.app_request == AppRq.GET:
    c.request_packet = build_packet_rrq(c.filename)
    c.state = STATES.WAIT_FIRST_DATA
else:
    c.request_packet = build_packet_wrq(c.filename)
    c.state = STATES.WAIT_WRQ_ACK

# send request
c.send_request()

# start state machine execution
while True:
    c.exec_client_state(c.state)
