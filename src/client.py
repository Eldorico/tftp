import sys
import random
import socket
from utils import *
from packet import *


class ProtocolVariables:
    """ This class is used to carry variables from one function to another.
        All the "global" variables used during the transfer are in this class.
        This class is send in parameters from one state function to another.
    """
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


def send_request(pv):
    """ Creates a socket in pv and sends the pv.request_paquet to pv.host on pv.port.
    :param pv: a ProtocolVariables object. should contain
            a dest host,
            a dest port,
            a request_paquet that are not None
    """
    try:
        pv.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        pv.source_tid = random.randint(10000, 60000)
        pv.sock.bind(('', pv.source_tid))
        pv.sock.sendto(pv.request_packet, (pv.host, pv.port))
    except socket.error, msg:
        sys.stderr.write('Failed to send request: error Code : ' + str(msg[0]) + ' Message: ' + msg[1] + '\n')
        close_and_exit(pv.file_obj, pv.sock, -2, pv.filename if pv.app_request == AppRq.GET else None)


def state_wait_wrq_ack(pv):
    """ function corresponding to the wait_wrq_ack state.
        Globally, it waits for a wrq ack. If it gets it, we can then pass to the wait_ack state.
    :param pv:
    :return:
    """
    # get an answer or restart loop
    attempt_number = 0
    while attempt_number < MAX_ATTEMPTS_NUMBER:
        pv.sock.settimeout(TIMEOUT_IN_SECONDS)
        try:
            pv.response_packet, pv.response_address = pv.sock.recvfrom(MAX_PACKET_SIZE+4)
            break
        except socket.timeout:
            attempt_number += 1
            pv.sock.close()
            send_request(pv)
            continue
    if attempt_number == MAX_ATTEMPTS_NUMBER:
        sys.stderr.write('Failed to connect to host %s on port %d.\n   Timeout reached.\n' % (pv.host, pv.port))
        close_and_exit(pv.file_obj, pv.sock, -3)

    # analyse answer
    resp_op_code, resp_blk_num, resp_data = decode_packet(pv.response_packet)
    if resp_op_code == OPCODE.ACK and resp_blk_num == 0:
        data_to_send = pv.file_obj.read(MAX_PACKET_SIZE)
        pv.sock.send(build_packet_data(1, data_to_send))
        pv.last_data_sent = data_to_send
        if len(data_to_send) < MAX_PACKET_SIZE:
            pv.state = STATES.WAIT_LAST_ACK
        else:
            pv.state = STATES.WAIT_ACK
        return
    elif resp_op_code == OPCODE.ERR:
        sys.stderr.write('Connexion refused with host %s on port %d.\n   Error code: %s. \n   Message: %s\n'%(pv.host, pv.port, ERROR_CODES[resp_blk_num], resp_data))
        close_and_exit(pv.file_obj, pv.sock, -4)
    else:
        sys.stderr.write('state_wait_wrq_ack() : An error occured\n')
        close_and_exit(pv.file_obj, pv.sock, -5)


def state_wait_first_data(pv):
    """ function corresponding to the wait_wrq_ack state.
        globally, it waits for a the first data packet. If it gets it, we can then pass to the wait_data state.
    :param pv: the variables used for the transfer.
    :return:
    """
    # get an answer or restart loop
    attempt_number = 0
    while attempt_number < MAX_ATTEMPTS_NUMBER:
        pv.sock.settimeout(TIMEOUT_IN_SECONDS)
        try:
            pv.response_packet, pv.response_address = pv.sock.recvfrom(516)
            break
        except socket.timeout:
            attempt_number += 1
            pv.sock.close()
            send_request(pv)
            continue
    if attempt_number == MAX_ATTEMPTS_NUMBER:
        sys.stderr.write('Failed to connect to host %s on port %d.\n   Timeout reached.\n' % (pv.host, pv.port))
        close_and_exit(pv.file_obj, pv.sock, -3, pv.filename)

    # analyse answer
    resp_op_code, resp_blk_num, resp_data = decode_packet(pv.response_packet)
    if resp_op_code == OPCODE.DATA and resp_blk_num == 1:
        pv.file_obj.write(resp_data)
        pv.sock.send(build_packet_ack(1))
        if len(resp_data) < MAX_PACKET_SIZE:
            pv.state = STATES.WAIT_TERMINATION_TIMER_OUT
        else:
            pv.state = STATES.WAIT_DATA
        return
    elif resp_op_code == OPCODE.ERR:
        sys.stderr.write('Connexion refused with host %s on port %d.\n   Error code: %s. \n   Message: %s\n'%(pv.host, pv.port, ERROR_CODES[resp_blk_num], resp_data))
        close_and_exit(pv.file_obj, pv.sock, -4)
    else:
        sys.stderr.write('state_first_data() : An error occured')
        close_and_exit(pv.file_obj, pv.sock, -5, pv.filename)


"""  ------------------------------------  """
"""           Script starts here           """
"""  ------------------------------------  """

# instantiate variables used for the transfer
TIMEOUT_IN_SECONDS = 1
MAX_ATTEMPTS_NUMBER = 4
v = ProtocolVariables()


def exec_client_state(state):
    """ function to executes all the states for the client. It uses the variables v instantiate just above
    :param state: The state to execute: STATES(Enum)
    """
    if state == STATES.WAIT_WRQ_ACK :
        return state_wait_wrq_ack(v)
    elif state == STATES.WAIT_ACK :
        return state_wait_ack(v)
    elif state == STATES.WAIT_LAST_ACK:
        return state_wait_last_ack(v)
    elif state == STATES.WAIT_FIRST_DATA:
        return state_wait_first_data(v)
    elif state == STATES.WAIT_DATA:
        return state_wait_data(v)
    elif state == STATES.WAIT_TERMINATION_TIMER_OUT:
        return state_wait_termination_timer_out(v)


# parse input
v.app_request, v.host, v.port, v.filename = parser()

# open file
try:
    if v.app_request == AppRq.GET:
        v.file_obj = open(v.filename, 'w')  # TODO: think of a backup plan? (file is deleted if an error occurs)
    elif v.app_request == AppRq.PUT:
        v.file_obj = open(v.filename, 'r')
except IOError, e:
    if v.app_request == AppRq.GET:
        sys.stderr.write("Can't create or erase file : ")
    else:
        sys.stderr.write("Can't open file : ")
    sys.stderr.write("%s\n" % str(e))
    close_and_exit(None, None, -1)


# create request packet
if v.app_request == AppRq.GET:
    v.request_packet = build_packet_rrq(v.filename)
    v.state = STATES.WAIT_FIRST_DATA
else:
    v.request_packet = build_packet_wrq(v.filename)
    v.state = STATES.WAIT_WRQ_ACK

# send request
send_request(v)

# start state machine execution
while True:
    exec_client_state(v.state)
