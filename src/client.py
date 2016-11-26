import sys
import socket
from utils import *
from packet import build_packet_wrq


# parse input
app_rq, host, port, filename = parser()

# open file
try:
    if app_rq == AppRq.GET:
        file_obj = open(filename, 'w+')
    elif app_rq == AppRq.PUT:
        file_obj = open(filename, 'r')
except IOError, e:
    sys.stderr.write("%s\n" % str(e))


file_obj.close()


# send request
"""
nb_attemp = 0
if app_rq == AppRq.GET:
    rq_packet = build_packet_rrq

sock_request = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock_request.sendto(, (host, port))
"""