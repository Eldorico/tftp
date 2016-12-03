import random

from utils import *
from packet import *
import socket

class ProtocolVariables:
    """ This class is used to carry variables from one function to another.
        All the "global" variables used during the transfer are in this class.
        This class is send in parameters from one state function to another.
    """
    def __init__(self):
        self.listen_ip = "0.0.0.0"
        self.listen_port = None
        self.directory = None

        # self.app_request = None
        self.sock = None
        # self.host = None
        # self.filename = None
        # self.file_obj = None
        # self.request_packet = None
        # self.first_data_packet = None
        self.source_tid = None
        self.state = None
        # self.response_address = None
        # self.response_packet = None
        # self.last_data_sent = None

# le parser return arg0 = nom serveur , arg1 = port du serveur, arg2 = fichier destination
def parserServer():
    parser = argparse.ArgumentParser(description='Tftp python.')

    parser.add_argument(
        '-p', '--port', type=int, help='Port number', required=True)

    parser.add_argument(
        '-d', '--directory', type=str, help='Directory name', required=True)

    parsed_arg = parser.parse_args()

    return int(parsed_arg.port), parsed_arg.directory


def listen(pv):
    """Start a server listening on the supplied interface and port. This
    defaults to INADDR_ANY (all interfaces) and UDP port 69. You can also
    supply a different socket timeout value, if desired."""

    pv.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print "socket created"

    try:
        # pv.sock.bind((pv.ip, pv.port))
        # pv.listen_port = pv.sock.getsockname()

        # Bind socket to local host and port
        pv.sock.bind((pv.listen_ip, pv.listen_port))
        # _, pv.listen_port = pv.sock.getsockname()

    except socket.error as err:
        print 'Bind failed. Error Code : ' + str(err[0]) + ' Message ' + err[1]
        close_and_exit(None, None, -1)

    print 'Socket bind complete'

    # Start listening on socket
    pv.sock.listen(10)
    print 'Socket now listening'

    #now keep talking with the client
    while 1:
        #wait to accept a connection - blocking call
        conn, addr = pv.sock.accept()
        print 'Connected with ' + addr[0] + ':' + str(addr[1])

    pv.sock.close()


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




# instantiate variables used for the transfer
# TIMEOUT_IN_SECONDS = 1
# MAX_ATTEMPTS_NUMBER = 4
v = ProtocolVariables()

def exec_server_state(state):
    """ function to executes all the states for the client. It uses the variables v instantiate just above
    :param state: The state to execute: STATES(Enum)
    """
    # if state == STATES.WAIT_WRQ_ACK :
    #     return state_wait_wrq_ack(v)
    if state == STATES.WAIT_FIRST_DATA:
        listen(v)
    elif state == STATES.WAIT_ACK :
        return state_wait_ack(v)
    elif state == STATES.WAIT_LAST_ACK:
        return state_wait_last_ack(v)
    # elif state == STATES.WAIT_FIRST_DATA:
    #     return state_wait_first_data(v)
    elif state == STATES.WAIT_DATA:
        return state_wait_data(v)
    # elif state == STATES.WAIT_TERMINATION_TIMER_OUT:
    #     return state_wait_termination_timer_out(v)
    # elif state == STATES.DEBUG_RECEIVE_OR_SEND:
    #     return debug_receive_or_send_file(v)


# parse input
v.listen_port, v.directory = parserServer()

# listen
try:
    listen(v)
except:
    print "error listening port"

    v.state = STATES.WAIT_FIRST_DATA

# send request
# send_request(v)

# start state machine execution
while True:
    exec_server_state(v.state)