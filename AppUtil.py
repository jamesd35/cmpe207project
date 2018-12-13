#!/usr/bin/env python

from prettytable import PrettyTable
import datetime, socket
import AppDbInterface

def makeTable( data, headers ):
    # data should be in list format
    table = PrettyTable( headers )
    if type( data[0] ) == dict:
        for i in data:
            x = []
            for h in headers:
                x.append( i[ h ] )
            table.add_row( x )
        return table
    else:
        for i in data:
            table.add_row( [i] )
        return table

class Session( object ):
    '''
        Class to handle session related tasks
        Tracks states while connection is valid
    '''
    def __init__( self, sockDes ):
        self.uid = None
        self.wallView = self.uid        # uid of current wall being viewed
        self.appDb = AppDbInterface.ADI()