import socket
import sys
from thread import *
import threading
import AppDbInterface, AppUtil
import struct
import logging
import select

NROFBYTES_INT = 4
NROFBYTE_DOUBLE = 8
REGTYPE = 0
NOTIFYTYPE = 1
ACKTYPE = 2
AQUIRED_ACK = 3
TIMEOUT = 3.0
CMD_EXIT = 0

sdlist = []
logging.basicConfig(filename='server.log',level=logging.DEBUG,
        format='%(asctime)s %(message)s', datefmt='[%m/%d/%Y %I:%M:%S %p]')
lock = threading.Lock()

def missedNotifications( sd, session ):
    maxPostId = session.appDb.maxNotification()
    lastPostId = session.appDb.usersGetLastNotify( session.uid )
    if lastPostId < maxPostId:
        msgs = session.appDb.messageGetSubset( lastPostId )
        missedList = ""
        for notification in msgs:
            missedList += notification[ "posterName" ] + " posted to "
            missedList += notification[ "wallOwnerName" ] + ": "
            missedList += notification[ "msg" ] + "\n"
        updateLen = len( missedList ) 
        update = struct.pack( '>III', updateLen, NOTIFYTYPE, maxPostId ) + missedList
        try:
            sd.send( update )
        except socket.error, e:
            logging.debug('Could not send missed notifications: %s', e)
            lock.acquire()
            sdlist.remove(sd)
            lock.release()
            sys.exit(1)
        readCheck = select.select( [sd], [], [], TIMEOUT )
        if not len( readCheck[0] ):
            logging.debug( "[WARNING]: Failed ack response on login" )
            return False
        else:
            recvmsg(sd, session)
            return True
    else:
        return True

def processLogin( sd, session ):
    # modular function to try verifying login information once only
    utime, usrName = recvmsg(sd)
    passtime, hashPass = recvmsg(sd)
    try:
        response = session.appDb.usersGetId( usrName )
        pswCheck = session.appDb.usersCheckPsw( usrName, hashPass )
        if not pswCheck:
            response = 0
    except AppDbInterface.NoRecordError, e: 
        m = ": Non-registered user tried to sign in or incorrect credentials"
        logging.debug( str( e ) + m )
        response = 0 # response 0 implies error / none found
    msg = struct.pack('>II', len( str(response)), REGTYPE) + utime + \
                        str(response)
    try:
        sd.send( msg )
    except socket.error, e:
        logging.debug('Could not send login response: %s', e)
        lock.acquire()
        sdlist.remove(sd)
        lock.release()
        sys.exit(1)
    return response

#thread function to handle each client
def requesthandler(sd):
    session = AppUtil.Session( sd )
    # check login until valid / connection lost
    login = 0
    while not login:
        login = processLogin( sd, session )
    #client has successfully logged in, add sd to global list
    lock.acquire()
    sdlist.append(sd)
    lock.release()
    # store the user id state from successful login info
    session.uid = login
    # initialize the current wall to the user's own wall
    session.wallView = login
    logging.debug('%s logged in', session.uid) 
    #notify client for all messages when they log in
    loop = missedNotifications( sd, session )
    usrName = session.appDb.usersGetName( session.uid )
    logging.info('missed notifications sent to %s', usrName)
    while (True):
        timestamp, data = recvmsg(sd, session)
        if not data:
            break
        if data == AQUIRED_ACK:
            continue
        logging.info('request received from %s', usrName)
        response = processrequest(data, session, sd)
        if response == CMD_EXIT: 
            msg = struct.pack('>II', 4, REGTYPE) + timestamp + "exit"
            try:
                sd.send( msg )
            except socket.error, e:
                logging.debug('Could not send response: %s', e)
                break
        else: 
            msg = struct.pack('>II', len(response), REGTYPE) + timestamp + \
                    response
            try:
                sd.send(msg)
            except socket.error, e:
                logging.debug('Could not send response: %s', e)
                break

        logging.info('response sent to %s', usrName)
    lock.acquire()
    sdlist.remove(sd)
    lock.release()
    sd.close()

#takes client request and processes accordingly
#returns response string to send back to client
#or 0 on exit
def processrequest(req, session, sd):
    #split at most twice (post uid: msg) where msg can have spaces
    splitstr = req.split(' ', 2)
    cmd = splitstr[0]
    errormsg = "invalid command"
    if (cmd == "listUsers"):
        if len(splitstr) != 1:
            return errormsg
        else:
            #dbquery to get user list
            t = AppUtil.makeTable( session.appDb.usersList(), [ 'Users' ] )
            return str( t )
    elif (cmd == "post"):
        if len(splitstr) != 3:
            return errormsg
        else:
            msg = splitstr[2]
            try:
                wallOwnerName = (splitstr[1])[:-1] #remove last (:) and get wall
                wallOwnerId = session.appDb.usersGetId( wallOwnerName )
                usrName = session.appDb.usersGetName( session.uid )
                postId = session.appDb.messagePost( session.uid, usrName, 
                                            wallOwnerId, wallOwnerName, msg )
            except AppDbInterface.DatabaseError, e:
                response = 'Bad command or user does not exist'
                logging.debug( str( e ) )
                return response
            #notify all other online users
            lock.acquire()
            for i in sdlist:
                if i != sd:
                    response = "%s posted to" % (usrName)
                    response += " %s: %s" % (wallOwnerName, msg)
                    notification = struct.pack('>III', len(response), NOTIFYTYPE, 
                                        postId) + response
                    try:
                        i.send(notification)
                    except socket.error, e:
                        logging.debug('Could not send notification: %s', e)
                        continue
            lock.release()
            try:
                session.appDb.usersUpdateLastNotify(session.uid, postId)
            except AppDbInterface.DatabaseError, e:
                logging.debug( str( e ) )
            logging.info('all online users notified of msg posted on %s wall by %s', wallOwnerName, usrName)
            return "Successfully posted message to %s's wall" % wallOwnerName
    elif (cmd == "getWall"):
        if len(splitstr) != 2:
            return errormsg
        else:
            # translate the username string to id
            #dbquery to return uid's wall
            try:
                uid = session.appDb.usersGetId( splitstr[1] )
                t = AppUtil.makeTable( session.appDb.messageGetWall( uid ), 
                                [ 'posterName', 'wallOwnerName', 
                                  'msg', 'created'] )
            except AppDbInterface.NoRecordError, e:
                t = "%s has no messages on their wall or doesn't exist." % \
                    splitstr[1]
                logging.debug( str( e ) + ":" + t )
            return str( t )
    elif (cmd == "exit"):
        return CMD_EXIT
    else:
        return errormsg

#helper function to receive request from client
def recvmsg(sd, session=None):
    rawMsgAttr = recvn(sd, 2*NROFBYTES_INT)
    if not rawMsgAttr:
        return [-1, None]
    msgLen, msgType = struct.unpack('>II', rawMsgAttr)
    if msgType == ACKTYPE:
        if session is None:
            logging.debug( "Received ACK but couldn't identify the session" )
            return None
        uid = session.uid
        rawPostId = recvn(sd, NROFBYTES_INT)
        postId = struct.unpack('>I', rawPostId)
        # feed into a adi function to update the table
        try:
            session.appDb.usersUpdateLastNotify(uid, postId)
        except AppDbInterface.DatabaseError, e:
            logging.debug( str( e ) )
        ack = recvn(sd, msgLen)
        usrName = session.appDb.usersGetName( session.uid )
        logging.info("Received '%s' for notification %s from %s" % \
                        (ack, postId, usrName) )
        return [-1, AQUIRED_ACK]
    elif msgType == NOTIFYTYPE:
        logging.debug("[ERROR]: Received Notification message on server side.")
        return [-1, None]
    else:
        timestamp = recvn(sd, NROFBYTE_DOUBLE)
        return [timestamp, recvn(sd, msgLen)]

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
    HOST = ''
    PORT = 9091

    try: 
        msd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except socket.error, e:
        logging.debug('Error creating socket: %s', e)
        sys.exit(1)
    try:
        msd.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    except socket.error, e:
        logging.debug('Error setting socket options: %s', e)
        sys.exit(1)
    try:
        msd.bind((HOST, PORT))
    except socket.error, e:
        logging.debug('Error binding socket: %s', e)
        sys.exit(1)
    try:
        msd.listen(10)
    except socket.error, e:
        logging.debug('Error listening on socket: %s', e)
        sys.exit(1)

    while (True):
        try: 
            ssd, cliaddr = msd.accept()
        except socket.error, e:
            logging.debug('Error accepting connection: %s', e)
            continue
        logging.debug('Connection from %s on port %s', cliaddr[0], cliaddr[1])
        start_new_thread(requesthandler, (ssd,))

    try:
        close(msd)
    except socket.error, e:
        logging.debug('Could not close socket: %s', e)
        sys.exit(1)

if __name__ == '__main__': 
    Main() 