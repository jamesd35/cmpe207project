#!/usr/bin/env python

'''
   SJSU CMPE 207 Coursework File for Term Project
   Team 7
'''

import MySQLdb, datetime, pdb

class DatabaseError( Exception ):
    def __init__( self, errors=None ):
        self.errors = errors
    def __str__( self ):
        return self.errors

class NoRecordError( DatabaseError ):
    pass

class BadCmdError( DatabaseError ):
    pass

# Errors

class ADI( object ):
    '''
        Interface file to do our SQL in. ANY direct sql should be done in here
        instead of inside the server code directly  
    '''
    def __init__( self ):
        self.conn = None
        self.cursor = None
        self.results = None
        try:
            self.connect()
        except MySQLdb.OperationalError as e:
            # might need to change to a logging statement later
            print "ERROR: Couldn't establish a connection to the database"
 
    def connect( self ):
        self.conn = MySQLdb.connect( host="localhost", user="appserver", 
                                    passwd="team7", db="AppDb" )
        self.cursor = self.conn.cursor()
 
    def close( self ):
        try:
            self.conn.close()
        except MySQLdb.OperationalError, e:
            print "ERROR: Failed to close database connection"
  
    def query( self, query, params=None ):
        # for read only data operations
        try:
            self.cursor.execute( query )
        except MySQLdb.ProgrammingError, e:
            print "[ERROR]: Bad query syntax"
        else:
            self.results = self.cursor.fetchall()
        if len( self.results ) < 1:
            raise NoRecordError( "No record found" )
 
    def execute( self, command ):
        # for raw sql commands that change data, i.e. updates & inserts
        #try:
        self.cursor.execute( command )
        self.conn.commit()
        #except MySQLdb.ProgrammingError:
        #    raise MySQLdb.ProgrammingError
            #print "ERROR: Bad sql command syntax"

    def usersGetId( self, userName ):
        q = "select userId from users where fullName = '%s';" % userName
        self.query( q )
        return self.results[0][0]

    def usersGetName( self, uid ):
        q = "select fullName from users where userId = '%d';" % uid
        self.query( q )
        return self.results[0][0]

    def usersCheckPsw( self, userName, hashPsw ):
        q = "select password from users where fullName = '%s';" % userName
        self.query( q )
        if self.results[0][0] != hashPsw:
            return False
        else:
            return True
 
    def usersList( self ):
        q = "select fullName from users;"
        self.query( q )
        # can add a new function to format more later
        # return a list of user names
        users = [ x for (x,) in self.results ]
        return users

    def usersGetLastNotify( self, uid ):
        # return the message table id value for last message received
        # each user tracked separately
        q = "select lastNotification from users where "
        q += "userId = '%s';" % uid
        self.query( q )
        mostRecentNotify = self.results[0][0]
        return mostRecentNotify

    def maxNotification( self ):
        q = "select max(msgId) from messages;"
        self.query( q )
        return self.results[0][0]

    def usersUpdateLastNotify( self, uid, nid ):
        # uid = user id
        # nid = notification / message id
        c = "update users set lastNotification = '%s'" % nid
        c += " where userId = '%s';" % uid
        try:
            self.execute( c )
        except MySQLdb.ProgrammingError, e:
            raise BadCmdError( "[ERROR]: Bad sql command" )
 
    def messagePost( self, uid, usrName, recvid, recvName, msg ):
        c = "Insert into messages ( posterId, wallOwnerId, "
        c += "posterName, wallOwnerName, msg, created )"
        c += " values ( '%d', '%d', '%s', '%s', '%s', NOW() );" % \
             ( uid, recvid, usrName, recvName, MySQLdb.escape_string(msg) )
        try:
            self.execute( c )
        except MySQLdb.ProgrammingError:
            raise BadCmdError( "[ERROR]: Bad sql command" )
        return self.cursor.lastrowid
 
    def messageGetWall( self, uid ):
        q = "select posterName, wallOwnerName, msg, created from messages "
        q += "where wallOwnerId = '%d' order by created desc;" % uid
        self.query( q )
        resultLen = len( self.results )
        wall = [ { "posterName" : self.results[ i ][ 0 ],
                   "wallOwnerName" : self.results[ i ][ 1 ],
                   "msg" : self.results[ i ][ 2 ],
                   "created" : self.results[ i ][ 3 ]
                }  for i in range( resultLen ) ]
        return wall

    def messageGetSubset( self, msgId ):
        q = "select msgId, posterName, wallOwnerName, msg from messages"
        q += " where msgId > '%d';" % msgId
        self.query( q )
        resultLen = len( self.results )
        msgs = [ { "msgId":self.results[i][0],
                   "posterName":self.results[i][1],
                   "wallOwnerName":self.results[i][2],
                   "msg":self.results[i][3] 
                  } for i in range( resultLen ) ]
        return msgs