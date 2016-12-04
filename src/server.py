import random

from utils import *
from packet import *
import socket


class Server:

    def __init__(self):
        self.listen_ip = "0.0.0.0"
        self.listen_port = None
        self.directory = None

        # self.app_request = None
        self.sock = None
        self.client_ip = None
        # self.filename = None
        # self.file_obj = None
        # self.request_packet = None
        # self.first_data_packet = None
        self.source_tid = None
        self.state = None

        self.response_address = None
        self.response_packet = None
        # self.last_data_sent = None

    # le parser return arg0 = nom serveur , arg1 = port du serveur, arg2 = fichier destination
    def parser(self):
        parser = argparse.ArgumentParser(description='Tftp python.')

        parser.add_argument(
            '-p', '--port', type=int, help='Port number', required=True)

        parser.add_argument(
            '-d', '--directory', type=str, help='Directory name', required=True)

        parsed_arg = parser.parse_args()

        return int(parsed_arg.port), parsed_arg.directory


    def listen(self):
        """Start a server listening on the supplied interface and port. This
        defaults to INADDR_ANY (all interfaces) and UDP port 69. You can also
        supply a different socket timeout value, if desired."""



        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        print "socket created"



        try:
            # self.sock.bind((self.ip, self.port))
            # self.listen_port = self.sock.getsockname()

            # Bind socket to local host and port
            self.sock.bind((self.listen_ip, self.listen_port))
            # _, self.listen_port = self.sock.getsockname()

        except socket.error as err:
            print 'Bind failed. Error Code : ' + str(err[0]) + ' Message ' + err[1]
            close_and_exit(None, None, -1)

        print 'Socket bind complete'




        # # Start listening on socket
        # self.sock.listen(10)
        # print 'Socket now listening'

        #now keep talking with the client
        while True:
            self.response_packet, self.response_address = self.sock.recvfrom(self.listen_port)

            # analyse answer
            resp_op_code, resp_blk_num, resp_data = decode_packet(self.response_packet)
            # if resp_op_code == OPCODE.ACK and resp_blk_num == 0:
            print resp_op_code
            print resp_blk_num
            print resp_data


            if resp_op_code == OPCODE.WRQ:
                # envoyer ack de confirmation
                self.sock.send(build_packet_ack(1))
                self.state = STATES.WAIT_DATA
                return

            elif resp_op_code == OPCODE.RRQ:
                if len(resp_data) < MAX_PACKET_SIZE:
                    self.state = STATES.WAIT_LAST_ACK
                else:
                    self.state = STATES.WAIT_ACK

                return

            # print data
            # print addr
            # s.sendto("output", addr)

            # wait to accept a connection - blocking call
            # conn, addr = self.sock.accept()
            # print 'Connected with ' + addr[0] + ':' + str(addr[1])

        self.sock.close()


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




# instantiate variables used for the transfer
# TIMEOUT_IN_SECONDS = 1
# MAX_ATTEMPTS_NUMBER = 4
s = Server()

def exec_server_state(state):
    """ function to executes all the states for the client. It uses the variables v instantiate just above
    :param state: The state to execute: STATES(Enum)
    """
    # if state == STATES.WAIT_WRQ_ACK :
    #     return state_wait_wrq_ack(v)
    # if state == STATES.WAIT_FIRST_DATA:
    #     s.listen()
    if state == STATES.WAIT_ACK :
        return state_wait_ack(s)
    elif state == STATES.WAIT_LAST_ACK:
        return state_wait_last_ack(s)
    # elif state == STATES.WAIT_FIRST_DATA:
    #     return state_wait_first_data(v)
    elif state == STATES.WAIT_DATA:
        return state_wait_data(s)
    # elif state == STATES.WAIT_TERMINATION_TIMER_OUT:
    #     return state_wait_termination_timer_out(v)
    # elif state == STATES.DEBUG_RECEIVE_OR_SEND:
    #     return debug_receive_or_send_file(v)


# parse input
s.listen_port, s.directory = s.parser()

# listen
try:
    s.listen()
except:
    print "error listening port"

# send request
# send_request(v)

# start state machine execution
while True:
    exec_server_state(s.state)