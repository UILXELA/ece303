# Written by S. Mevawala, modified by D. Gitzel
#Zheng Liu
#ECE303
import logging
import socket

import channelsimulator
import utils
import sys

import math
import random

# Max sequence number set to 256
MAX_SEQ_NUM = 256

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
 
class newSender(BogoSender):
    # Parameter declarations
    dat = 0
    # Max segment size
    MSS = 250
    # Segment Number
    segNum = 0
    # Randomize a sequence number
    seqNum = random.randint(0, MAX_SEQ_NUM - 1)
    # Partition number
    partition = 0
    # Partition start and end
    start = 0
    end = MSS
    
    # data buffer
    buf = bytearray(MAX_SEQ_NUM)
    bufStart = seqNum
    bufEnd = seqNum

    dupNum = 0
    isSent = False
    resend = False

    # Constructor function with timeout
    def __init__(self, DATA, timeout = 0.1):
        super(newSender, self).__init__()
        self.dat = DATA
        self.timeout = timeout
        self.simulator.sndr_socket.settimeout(self.timeout)
        self.segNum = int(math.ceil(len(self.dat)/float(self.MSS)))

    # The Send() function override
    def send(self, data):
        self.logger.info("Sending on port: {} and waiting for ACK on port: {}".format(self.outbound_port, self.inbound_port))


        for segment in self.splitSegment(self.dat, self.MSS, self.partition):
            try:
                if not self.resend:
                    seg = sndrSegment(seqNum = 0, ackNum = 0, checksum = 0, data = segment)
                    seg.seqNum = sndrSegment.sequenceNum(self, self.seqNum, self.MSS)
                    self.seqNum = seg.seqNum
                    seg.ackNum = 0

                    sendArray = bytearray([seg.checksum, seg.ackNum, seg.seqNum])
                    sendArray += segment

                    # Create checksum
                    seg.checksum = sndrSegment.checkSum(self, sendArray)
                    sendArray[0] = seg.checksum
     
                    self.simulator.u_send(sendArray) 

                # Handle the action to take when receiver send ACk
                while True:
                    rcvArray = self.simulator.u_receive()

                    # Check the receiver ack
                    if self.checkReceiverACK(rcvArray):
                        if rcvArray[1] == self.seqNum:
                            self.isSent = True
                            self.simulator.u_send(sendArray)  

                        # If ACK for subsequent segment comes in, know that the prev segment was also received
                        elif rcvArray[1] == (self.seqNum + len(segment)) % MAX_SEQ_NUM: 
                            self.dupNum = 0
                            if self.timeout > 0.1:
                                self.timeout -= 0.1
                            self.simulator.sndr_socket.settimeout(self.timeout)
                            self.resend = False
                            break

                        # else resend     
                        else: 
                            self.simulator.u_send(sendArray) 
                    
                    # If the Ack is corrupted, resend
                    else:
                        self.simulator.u_send(sendArray) 
                        self.dupNum += 1
                        
                        if self.dupNum == 3 and self.isSent:
                            self.timeout *= 2
                            self.simulator.sndr_socket.settimeout(self.timeout) 
                            self.dupNum = 0
                            if self.timeout > 5:
                                self.logger.info("Timeout!")
                                exit()

            # Handle timeout
            except socket.timeout:
                self.resend = True
                self.simulator.u_send(sendArray)
                self.dupNum += 1
                if self.dupNum >= 3:
                    self.dupNum = 0
                    self.timeout *= 2
                    self.simulator.sndr_socket.settimeout(self.timeout)
                    if self.timeout > 5:
                        self.logger.info("Timeout!")
                        exit()                                           

    def checkReceiverACK(self, data):
        # Inverting the bits
        val = ~data[0]
        for i in xrange(1, len(data)):  
            # XORing the data
            val ^= data[i]
        if val == -1: 
            # Return true if the result is 11111...    
            return True
        else:
            return False

    def splitSegment(self, data, MSS, partition):
        for i in range(self.segNum):
            partition += 1
            yield data[self.start:self.end]
            # New start and end of a partition
            self.start = self.start + MSS
            self.end = self.end + MSS



# Data segment class
class sndrSegment(object):
    def __init__(self, checksum = 0, seqNum = 0, ackNum = 0, data = []):
        self.checksum = checksum
        self.ackNum = ackNum
        self.seqNum = seqNum
        self.data = data

    @staticmethod
    def sequenceNum(self, prevSeqNum, MSS):
        return (prevSeqNum + MSS) % MAX_SEQ_NUM

    # turn the data to bytearray and then do checksum
    @staticmethod
    def checkSum(self, data):
        datArray = bytearray(data)
        valCheckSum = 0
        for i in xrange(len(datArray)):
            valCheckSum ^= datArray[i]
        return valCheckSum



if __name__ == "__main__":
    # test out BogoSender
    DATA = bytearray(sys.stdin.read())
    
    sndr = newSender(DATA)
    sndr.send(DATA)
