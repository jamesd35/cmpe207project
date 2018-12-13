import socket, sys
from thread import *
import threading, hashlib
import struct
import pdb
import os
import time
import logging

NROFBYTES_INT = 4
NROFBYTES_DOUBLE = 8
RETRYLIMIT = 3
TIMEOUT = 3.0
ACK = "ACK"
ACKSIZE = 3
REGTYPE = 0
ACKTYPE = 2
ACKSUCCESS = "ack successful"

logging.basicConfig(filename='client.log',level=logging.DEBUG,
        format='%(asctime)s %(message)s', datefmt='[%m/%d/%Y %I:%M:%S %p]')

def listener(sd):
    while (True):
        response = recvmsg(sd)
        if response == None:
            sd.close()
            logging.debug('Received EOF')
            os._exit(0)

        if response == ACKSUCCESS:
            logging.info("notification received")
            continue
        if response == 'exit':
            sd.close()
            logging.info('exiting')
            os._exit(0)

        logging.info("response received")
        print('\nReceived from server:\n%s' % response)
    return

#helper function to receive response from server
def recvmsg(sd):
    rawMsgAttr = recvn(sd, NROFBYTES_INT*2)
    if not rawMsgAttr:
        return None
    # msgTypes: 0 regular, 1 notification
    msgLen, msgType = struct.unpack('>II', rawMsgAttr)
    if msgType == 1:
        rawPostId = recvn(sd, NROFBYTES_INT)
        notification = recvn(sd, msgLen)
        ackSize = struct.pack('>I', ACKSIZE)
        ackType = struct.pack('>I', ACKTYPE)
        sd.send( ackSize + ackType + rawPostId + ACK )
        print "[Notification]:\n%s" % notification
        return ACKSUCCESS
    elif msgType == REGTYPE:
        timestamp = time.time()
        rawTimestamp = recvn(sd, NROFBYTES_DOUBLE)
        if not rawTimestamp:
            return None
        reqTime = struct.unpack('>d', rawTimestamp)[0]
        srvResponse = (timestamp - reqTime) * 10**3
        logging.info( "%s ms response time from server" % srvResponse)
        return recvn(sd, msgLen)

#helper function to receive n bytes or return None if EOF
def recvn(sd, n):
    data = b''
    while len(data) < n:
        tmp = sd.recv(n - len(data))
        if not tmp:
            return None
        data += tmp
    return data

def Main():
    try:
        HOST = socket.gethostname()
    except socket.error, e:
        logging.debug('gethostname error: %s', e)
        sys.exit(1)

    PORT = 9091
    try:
        sd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except socket.error, e:
        logging.debug('Error creating socket: %s', e)
        sys.exit(1)

    try:
        sd.connect((HOST, PORT))
    except socket.error, e:
        logging.debug('Socket connection failed: %s', e)
        sys.exit( 1 )
    logging.debug('socket connection established')

    # send login info so that the server knows who this is
    loggedIn = False
    while not loggedIn:
        usrName = raw_input("Username: ")
        timestamp = time.time()
        msg = struct.pack('>IId', len(usrName), REGTYPE, timestamp) + usrName
        try:
            sd.sendall(msg)
        except socket.error, e:
            logging.debug('Could not send username: %s', e)
            sys.exit(1)
        password = raw_input("Password: ")
        hashPsw = hashlib.sha1( password )
        timestamp = time.time()
        msg = struct.pack('>IId', len(hashPsw.hexdigest()), REGTYPE, timestamp) + \
                            hashPsw.hexdigest()
        try:
            sd.sendall(msg)
        except socket.error, e:
            logging.debug('Could not send password: %s', e)
            sys.exit(1)

        loggedIn = recvmsg(sd)
        if loggedIn != "0":
            print "Logged In!"
        else:
            print "Invalid login credentials, try again."
            loggedIn = False
    print "Type help for a list of commands"
    start_new_thread(listener, (sd,))
    while (True):
        cmd = raw_input('Enter a command: \n')
        if cmd == "help":
            print "\nValid Commands:\nlistUsers\npost <username>: msg"
            print "Example - post nick: hello nick"
            print "getWall <username>\nexit\n"
            continue 
        timestamp = time.time()
        msg = struct.pack('>IId', len(cmd), REGTYPE, timestamp) + cmd
        try:
            sd.sendall(msg)
        except socket.error, e:
            logging.debug('Could not send request: %s', e)
            os._exit(0)

        logging.info('request sent to server')
        time.sleep(1)

if __name__ == '__main__':
    Main()