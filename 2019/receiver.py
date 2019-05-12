# Written by S. Mevawala, modified by D. Gitzel
#Zheng Liu
#ECE303

import logging

import channelsimulator
import utils
import sys
import socket

class Receiver(object):

    def __init__(self, inbound_port=50005, outbound_port=50006, timeout=10, debug_level=logging.INFO):
        self.logger = utils.Logger(self.__class__.__name__, debug_level)

        self.inbound_port = inbound_port
        self.outbound_port = outbound_port
        self.simulator = channelsimulator.ChannelSimulator(inbound_port=inbound_port, outbound_port=outbound_port,
                                                           debug_level=debug_level)
        self.simulator.rcvr_setup(timeout)
        self.simulator.sndr_setup(timeout)

    def receive(self):
        raise NotImplementedError("The base API class has no implementation. Please override and add your own.")


class BogoReceiver(Receiver):
    ACK_DATA = bytes(123)

    def __init__(self):
        super(BogoReceiver, self).__init__()

    def receive(self):
        self.logger.info("Receiving on port: {} and replying with ACK on port: {}".format(self.inbound_port, self.outbound_port))
        while True:
            try:
                 data = self.simulator.u_receive()  # receive data
                 self.logger.info("Got data from socket: {}".format(
                     data.decode('ascii')))  # note that ASCII will only decode bytes in the range 0-127
	         sys.stdout.write(data)
                 self.simulator.u_send(BogoReceiver.ACK_DATA)  # send ACK
            except socket.timeout:
                sys.exit()

class newReceiver(BogoReceiver):
    rcvArray = bytearray([0,0,0,0])
    # Back-up Ack message
    backupAck = bytearray([0,0,0])
    lastAckNum = -1 
    resend = True
    dupNum = 0

    # Constructor
    def __init__(self, timeout = 0.1):
        super(newReceiver, self).__init__()
        self.timeout = timeout
        self.simulator.rcvr_socket.settimeout(self.timeout)

    def receive(self):
        # Waiting for the coming data
        while True:
            try:
                self.rcvArray = self.simulator.u_receive()
                # Checking timeout
                if self.timeout > 0.1:
                    self.timeout -= 0.1
                    self.dupNum = 0

                # Send the ACK message
                self.send()

            # When Timeout, resend the back-up ACK  
            except socket.timeout:
                self.resend = True
                self.simulator.u_send(self.backupAck)
                self.dupNum += 1

                if self.dupNum >= 3:
                    self.dupNum = 0
                    self.timeout *= 2
                    self.simulator.rcvr_socket.settimeout(self.timeout)
                    if self.timeout > 5:
                        exit()
                        
    def send(self):
        # Inplement the Sending of the ACK messgae
        AckSegment = rcvrSegment()
        AckSuccess = AckSegment.ack(self.rcvArray, self.lastAckNum)
        if AckSuccess:
            self.lastAckNum = AckSegment.AckNum
        if AckSegment.AckNum < 0:
            AckSegment.AckNum = 0
        AckSegment.checksum = AckSegment.checkSum()
        rcvArray = bytearray([AckSegment.checksum, AckSegment.AckNum])
        backupAck = rcvArray
        self.simulator.u_send(rcvArray)

class rcvrSegment(object):
    def __init__(self, checksum = 0, seqNum = 0, AckNum = 0, data = []):
        self.checksum = checksum
        self.seqNum = seqNum
        self.AckNum = AckNum
        self.data = data
         
    # The checksum will be the ack number itself since this is the receiver side
    def checkSum(self):        
        return self.AckNum
        

    # Check the ack
    def checkACK(self,data):
        # Inverting the bits
        val =~ data[0]   
        for i in xrange(1,len(data)):
            # XORing the data
            val ^= data[i]
        if val ==- 1:
            # Return true if the result is 11111...    
            return True 
        else:
            return False
    
    # Check the ACK
    def ack(self, data, lastAckNum):
        check = self.checkACK(data)
        if check:
            self.AckNum = (data[2] + len(data[3:])) % 256
            if data[2] == lastAckNum or lastAckNum == -1:
                sys.stdout.write("{}".format(data[3:]))
                sys.stdout.flush()
                return True
        else:
            pass

        return False

if __name__ == "__main__":
    # test out BogoReceiver
    rcvr = newReceiver()
    rcvr.receive()
