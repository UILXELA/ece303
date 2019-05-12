# Written by S. Mevawala, modified by D. Gitzel
from __future__ import division
import logging
import socket
import channelsimulator
import utils
import sys
import math



class Sender(object):

    def __init__(self, inbound_port=50006, outbound_port=50005, timeout=10, debug_level=logging.INFO):
        self.logger = utils.Logger(self.__class__.__name__, debug_level)

        self.inbound_port = inbound_port
        self.outbound_port = outbound_port
        self.simulator = channelsimulator.ChannelSimulator(inbound_port=inbound_port, outbound_port=outbound_port,
                                                           debug_level=debug_level)
        self.simulator.sndr_setup(timeout)
        self.simulator.rcvr_setup(timeout)

    def send(self, data):
        raise NotImplementedError("The base API class has no implementation. Please override and add your own.")


class BogoSender(Sender):

    def __init__(self):
        super(BogoSender, self).__init__()

    def send(self, data):
        self.logger.info("Sending on port: {} and waiting for ACK on port: {}".format(self.outbound_port, self.inbound_port))
        while True:
            try:
                self.simulator.u_send(data)  # send data
                ack = self.simulator.u_receive()  # receive ACK
                self.logger.info("Got ACK from socket: {}".format(
                    ack.decode('ascii')))  # note that ASCII will only decode bytes in the range 0-127
                break
            except socket.timeout:
                pass

#global
MAX_SEQ_NUM = 256

class mySender(BogoSender):
    data = 0    #placeholder for data
    MSS = 256   #max seg size!!
    # Segment Number
    seg_num = 0
    # Randomize a sequence number
    seq = 0
    
    # data buffer
    buf = bytearray(MAX_SEQ_NUM)    #buffer to avoid data liss, probably too big

    dup = 0 #duplicates, same as for the rcvr
    
    #Booleans foe control
    isSent = False
    resend = False

    # Constructor function with timeout
    def __init__(self, DATA, timeout = 0.1):
        super(mySender, self).__init__()
        self.data = DATA
        self.timeout = timeout
        self.simulator.sndr_socket.settimeout(self.timeout)
        self.seg_num = int(math.ceil(len(self.data)/float(self.MSS)))

    # The Send() function override
    def send(self, data):
        self.logger.info("Sending on port: {} and waiting for ACK on port: {}".format(self.outbound_port, self.inbound_port))
        data_all=self.splitter(self.data, self.MSS) #split the whole file into segs
        for seg_data in data_all:
            try:
                if not self.resend:
                    seg = sndrSegment(seq = 0, ack_num = 0, checksum = 0, data = seg_data)
                    seg.seq = sndrSegment.sequenceNum(self, self.seq, self.MSS)
                    self.seq = seg.seq
                    seg.ack_num = 0

                    #chksum,acknum,seq all single byte, 4: is data. chksum includes seq and ack
                    to_send = bytearray([seg.checksum, seg.ack_num, seg.seq])
                    to_send += seg_data
                    seg.checksum = sndrSegment.checkSum(self, to_send)
                    to_send[0] = seg.checksum
     
                    self.simulator.u_send(to_send) 

                # rcv acks
                while True:
                    curr_ack = self.simulator.u_receive()

                    # validate
                    if self.checkReceiverACK(curr_ack):
                        if (curr_ack[1] == self.seq):
                            self.isSent = True
                            self.simulator.u_send(to_send)
                        #cumulative approach
                        elif (curr_ack[1] == (self.seq + len(seg_data)) % MAX_SEQ_NUM): 
                            self.dup = 0
                            if self.timeout > 0.1:
                                self.timeout -= 0.1
                            self.simulator.sndr_socket.settimeout(self.timeout)
                            self.resend = False
                            break

                        # resend     
                        else: 
                            self.simulator.u_send(to_send) 
                    
                    # bad chksum, does not deal missing
                    else:
                        self.simulator.u_send(to_send) 
                        self.dup += 1
                        
                        #fast retx
                        if self.dup == 3 and self.isSent:
                            self.timeout *= 2
                            self.simulator.sndr_socket.settimeout(self.timeout) 
                            self.dup = 0
                            if self.timeout > 5:
                                self.logger.info("timeout")
                                sys.exit()

            # Handle timeout
            except socket.timeout:
                self.resend = True
                self.simulator.u_send(to_send)
                self.dup += 1
                if self.dup >= 3:
                    self.dup = 0
                    self.timeout *= 2
                    self.simulator.sndr_socket.settimeout(self.timeout)
                    if self.timeout > 5:
                        self.logger.info("Timeout!")
                        sys.exit()                                           

    #simple one's comp, coomented out crc which did not work
    def checkReceiverACK(self, data):
        val = ~data[0]
        for i in xrange(1, len(data)):  
            val ^= data[i]
        if val == -1: 
            return True
        else:
            return False

    #split the whole file into a list
    def splitter(self,DATA,MSS):
        data_size=len(DATA)
        seg_count=int(math.ceil(data_size/MSS))
        data_all=[]
        lb=0
        for i in range(seg_count-1):
            data_all.append(DATA[lb:lb+MSS])
            lb+=MSS
        data_all.append(DATA[lb:])
        return data_all



# Data seg_data class
class sndrSegment(object):
    def __init__(self, checksum = 0, seq = 0, ack_num = 0, data = []):
        self.checksum = checksum
        self.ack_num = ack_num
        self.seq = seq
        self.data = data

    @staticmethod
    def sequenceNum(self, prevSeqNum, MSS):
        return (prevSeqNum + MSS) % MAX_SEQ_NUM

    # find chksum 1 comp
    @staticmethod
    def checkSum(self, data):
        data_byte = bytearray(data)
        chksum = 0
        for i in xrange(len(data_byte)):
            chksum ^= data_byte[i]
        return chksum



if __name__ == "__main__":
    DATA = bytearray(sys.stdin.read())  
    sndr = mySender(DATA)
    sndr.send(DATA)
