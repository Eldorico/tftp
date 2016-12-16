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
        self.file_obj = None
        self.filename = None
        # self.request_packet = None
        # self.first_data_packet = None
        self.source_tid = None
        self.destination_tid = None
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


    def state_wait_first_data(self):
        """ function corresponding to the wait_wrq_ack state.
            globally, it waits for a the first data packet. If it gets it, we can then pass to the wait_data state.
        :param self: the variables used for the transfer.
        :return:
        """
        # get an answer or restart loop

        TIMEOUT_IN_SECONDS = 1

        attempt_number = 0
        while attempt_number < MAX_ATTEMPTS_NUMBER:
            self.sock.settimeout(TIMEOUT_IN_SECONDS)
            try:
                self.response_packet, self.response_address = self.sock.recvfrom(516)
                break
            except socket.timeout:
                attempt_number += 1
                # self.sock.close()

                self.sock.sendto(build_packet_ack(0), self.response_address)
                # self.send_request()
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
        # while True:
        self.response_packet, self.response_address = self.sock.recvfrom(self.listen_port)
        self.destination_tid = self.response_address[1]

        print "" + str(self.response_address)

        # analyse answer
        resp_op_code, resp_blk_num, resp_filename = decode_packet(self.response_packet)

        print "resp_op_code: "+ str(resp_op_code)
        print "resp_blk_num: "+ str(resp_blk_num)
        print "resp_filename: "+ str(resp_filename)

        self.filename = resp_filename #Comment je get filename

        self.sock.connect((self.listen_ip, self.destination_tid))

        # WRQ REQUEST
        if resp_op_code == OPCODE.WRQ:
            try:
                self.file_obj = open(self.directory+'/'+self.filename, 'w')   #CHANGER FICHIER
            except IOError, e:
                sys.stderr.write("Can't create or erase file : ")
                sys.stderr.write("%s\n" % str(e))
                close_and_exit(None, None, -1)


            # random_port = random.randint(10000, 60000)
            block_num = 0

            self.source_tid = random.randint(10000, 60000)


            #  si arrive ouvrir fichier ecriture faire dessous

            self.sock.sendto(build_packet_ack(block_num), self.response_address)

            self.state = STATES.WAIT_FIRST_DATA
            return

        # READ REQUEST ->  DEMANDE DU CLIENT POUR LIRE
        elif resp_op_code == OPCODE.RRQ:
            try:
                self.file_obj = open(self.directory+'/'+self.filename, 'r')
            except IOError, e:
                sys.stderr.write("Can't open file : ")
                sys.stderr.write("%s\n" % str(e))
                close_and_exit(None, None, -1)

            self.source_tid = random.randint(10000, 60000) #CHOOSE TID?
            block_num = 1
            data_to_send = self.file_obj.read(MAX_PACKET_SIZE)

            if len(data_to_send) < MAX_PACKET_SIZE:
                # random_port = random.randint(10000, 60000)  # RANDOM PORT?
                self.sock.sendto(build_packet_data(block_num, data_to_send), self.response_address)
                self.state = STATES.WAIT_LAST_ACK
            else:
                random_port = random.randint(10000, 60000)
                self.sock.sendto(build_packet_data(block_num, data_to_send), self.response_address)
                self.state = STATES.WAIT_ACK
            return

        # self.sock.close()

                #
                # if len(resp_data) > MAX_PACKET_SIZE:
                #
                #     #OUVRIR FICHIER EN LECTURE
                #
                #     #resp_data == filename + mode ?
                #     print "resp_data when RRQ data > 512 (if)"
                #     print resp_data
                #
                #     self.file_obj = open(resp_data, 'r')
                #
                #     self.sock.send(build_packet_data(resp_data))
                #     self.source_tid = random.randint(10000, 60000)
                #     self.state = STATES.WAIT_LAST_ACK
                #     #start timer?
                # else:
                #     print "resp_data when RRQ data <= 512 (else)"
                #     print resp_data
                #
                #     self.file_obj = open(resp_data, 'r')
                #
                #     self.sock.send(build_packet_data(resp_data))
                #     self.source_tid = random.randint(10000, 60000)
                #     self.state = STATES.WAIT_ACK
                #     #start timer?
                # return

        # print data
        # print addr
        # s.sendto("output", addr)

        # wait to accept a connection - blocking call
        # conn, addr = self.sock.accept()
        # print 'Connected with ' + addr[0] + ':' + str(addr[1])


    #
    # def send_request(self):
    #     """ Creates a socket in self and sends the self.request_paquet to self.host on self.port.
    #     :param self: a ProtocolVariables object. should contain
    #             a dest host,
    #             a dest port,
    #             a request_paquet that are not None
    #     """
    #     try:
    #         self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    #         self.source_tid = random.randint(10000, 60000)
    #         self.sock.bind(('', self.source_tid))
    #         self.sock.sendto(self.request_packet, (self.host, self.port))
    #     except socket.error, msg:
    #         sys.stderr.write('Failed to send request: error Code : ' + str(msg[0]) + ' Message: ' + msg[1] + '\n')
    #         close_and_exit(self.file_obj, self.sock, -2, self.filename if self.app_request == AppRq.GET else None)




    # instantiate variables used for the transfer
    # TIMEOUT_IN_SECONDS = 1
    # MAX_ATTEMPTS_NUMBER = 4

    def exec_server_state(self, state):
        """ function to executes all the states for the client. It uses the variables v instantiate just above
        :param state: The state to execute: STATES(Enum)
        """
        # if state == STATES.WAIT_WRQ_ACK :
        #     return state_wait_wrq_ack(v)
        if state == STATES.WAIT_FIRST_DATA:
            return self.state_wait_first_data()
        if state == STATES.WAIT_ACK :
            return state_wait_ack(self)
        elif state == STATES.WAIT_LAST_ACK:
            return state_wait_last_ack(self)
        # elif state == STATES.WAIT_FIRST_DATA:
        #     return state_wait_first_data(v)
        elif state == STATES.WAIT_DATA:
            return state_wait_data(self)
        # elif state == STATES.WAIT_TERMINATION_TIMER_OUT:
        #     return state_wait_termination_timer_out(v)
        # elif state == STATES.DEBUG_RECEIVE_OR_SEND:
        #     return debug_receive_or_send_file(v)



s = Server()
# parse input
s.listen_port, s.directory = s.parser()

# listen
# try:
s.listen()
# except:
#     print "error listening port"
#     close_and_exit(s.file_obj, s.sock, -5)

# send request
# send_request(v)

# start state machine execution
while True:
    s.exec_server_state(s.state)