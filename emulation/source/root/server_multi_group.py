import socket
import struct
import sys
import netifaces
import traceback
import signal

is_running = True
sock = None

def exit(signal, frame):
    is_running = False
    sock.close()
    sys.exit(0)


def chooseInterface():
    interfaces = netifaces.interfaces()
    def printInterfaces():
        print('Indique a interface de captura:')
        for i in range(len(interfaces)):
            print (i+1, '-', interfaces[i])

    if len(interfaces) == 1: #user has just 1 interface and any
        return interfaces[0]
    else:
        printInterfaces()
        inputValue = input('Numero da interface: ')

        if int(inputValue)-1 not in range(len(interfaces)):
            raise Exception('numero de interface invalida')
        inputValue = interfaces[int(inputValue)-1]
        return inputValue


signal.signal(signal.SIGINT, exit)
signal.signal(signal.SIGTERM, exit)

multicast_group = [('ff05::12:12:12', 10000),
                   ('ff05::12:12:13', 10000),
                   ('ff05::12:12:14', 10000),
                   ('ff05::12:12:15', 10000),
                   ('ff05::12:12:16', 10000),
                   ('ff05::12:12:17', 10000),
                   ('ff05::12:12:18', 10000),
                   ('ff05::12:12:19', 10000),
                   ('ff05::12:12:20', 10000),
                   ('ff05::12:12:21', 10000),
                   ('ff05::12:12:22', 10000),
                   ('ff05::12:12:23', 10000),
                   ('ff05::12:12:24', 10000),
                   ('ff05::12:12:25', 10000),
                   ('ff05::12:12:26', 10000),
                   ('ff05::12:12:27', 10000),
                   ('ff05::12:12:28', 10000),
                   ('ff05::12:12:29', 10000),
                   ('ff05::12:12:30', 10000),
                   ('ff05::12:12:31', 10000),
                   ('ff05::12:12:32', 10000),
                   ('ff05::12:12:33', 10000),
                   ('ff05::12:12:34', 10000),
                   ('ff05::12:12:35', 10000),
                   ('ff05::12:12:36', 10000),
                   ('ff05::12:12:37', 10000),
                   ('ff05::12:12:38', 10000),
                   ('ff05::12:12:39', 10000),
                   ('ff05::12:12:40', 10000),
                   ('ff05::12:12:41', 10000),
                   ('ff05::12:12:42', 10000),
                   ('ff05::12:12:43', 10000),
                   ('ff05::12:12:44', 10000),
                   ('ff05::12:12:45', 10000),
                   ('ff05::12:12:46', 10000),
                   ('ff05::12:12:47', 10000),
                   ('ff05::12:12:48', 10000),
                   ('ff05::12:12:49', 10000),
                   ('ff05::12:12:50', 10000),
                   ('ff05::12:12:51', 10000),
                   ('ff05::12:12:52', 10000),
                   ]

# Create the datagram socket
sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)

# Set the time-to-live for messages to 1 so they do not go past the
# local network segment.
ttl = 12
sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_HOPS, ttl)


interface_name = chooseInterface()
ip_interface = netifaces.ifaddresses(interface_name)[netifaces.AF_INET6][0]['addr']

sock.bind((ip_interface, 10000))
try:
    # Look for responses from all recipients
    while is_running:
        input_msg = input('msg --> ')
        try:
            for g in multicast_group:
                sock.sendto(input_msg.encode("utf-8"), g)
        except:
            traceback.print_exc()
            continue
            #print >>sys.stderr, 'received "%s" from %s' % (data, server)

finally:
    #print >>sys.stderr, 'closing socket'
    sock.close()
