import sys
import random
import socket
from utils import *
from packet import *


"""  ------------------  """
"""  Script starts here  """
"""  ------------------  """

TIMEOUT_IN_SECONDS = 1
MAX_ATTEMPTS_NUMBER = 4

# parse input
app_request, host, port, filename = parser()


# open file
try:
    if app_request == AppRq.GET:
        file_obj = open(filename, 'w')  # TODO: think of a backup plan? (file is deleted if an error occurs)
    elif app_request == AppRq.PUT:
        file_obj = open(filename, 'r')
except IOError, e:
    if app_request == AppRq.GET:
        sys.stderr.write("Can't create or erase file : ")
    else:
        sys.stderr.write("Can't open file : ")
    sys.stderr.write("%s\n" % str(e))
    close_and_exit(None, None, -1)


# create request packet
if app_request == AppRq.GET:
    request_packet = build_packet_rrq(filename)
else:
    request_packet = build_packet_wrq(filename)


# send request
try:
    attempt_number = 0
    while attempt_number < MAX_ATTEMPTS_NUMBER:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        source_tid = random.randint(10000, 60000)
        sock.bind(('', source_tid))
        sock.sendto(request_packet, (host, port))

        # get an answer or restart loop
        sock.settimeout(TIMEOUT_IN_SECONDS)
        try:
            response_packet, response_address = sock.recvfrom(MAX_PACKET_SIZE)
        except socket.timeout:
            attempt_number += 1
            continue

        # analyse answer
        resp_op_code, resp_blk_num, resp_data = decode_packet(response_packet)
        if app_request == AppRq.GET and resp_op_code == OPCODE.DATA and resp_blk_num == 1:
            break
        elif app_request == AppRq.PUT and resp_op_code == OPCODE.ACK and resp_blk_num == 0:
            break
        elif resp_op_code == OPCODE.ERR:
            break
        else:
            attempt_number += 1
            sock.shutdown()
except socket.error, msg:
    sys.stderr.write('Failed to send request: error Code : ' + str(msg[0]) + ' Message: ' + msg[1]+'\n')
    close_and_exit(file_obj, sock, -2, filename if app_request == AppRq.GET else None)


# if errors, manage request answer errors and exit
if attempt_number == MAX_ATTEMPTS_NUMBER:
    sys.stderr.write('Failed to connect to host %s on port %d.\n   Timeout reached.\n'%(host, port))
    close_and_exit(file_obj, sock, -3, filename if app_request == AppRq.GET else None)
elif resp_op_code == OPCODE.ERR:
    sys.stderr.write('Connexion refused with host %s on port %d.\n   Error code: %s. \n   Message: %s\n'%(host, port, ERROR_CODES[resp_blk_num], resp_data))
    close_and_exit(file_obj, sock, -4, filename if app_request == AppRq.GET else None)


# get or send file
destination_tid = response_address[1]
sock.connect((host, destination_tid))
if app_request == AppRq.GET:
    task_done = receive_file(sock, file_obj, resp_data)
else:
    task_done = send_file(sock, file_obj)

# close and exit
if task_done:
    close_and_exit(file_obj, sock, 0, None)
else:
    if app_request == AppRq.GET:
        close_and_exit(file_obj, sock, 1, filename) # TODO: try to get the error code of ERR paquet from send or receive fonctions from Lerda
    else:
        close_and_exit(file_obj, sock, 1)  # TODO: try to get the error code of ERR paquet from send or receive fonctions from Lerda
