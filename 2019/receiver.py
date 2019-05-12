# Written by S. Mevawala, modified by D. Gitzel

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

class myReceiver(BogoReceiver):
    seg_rcv = bytearray()
    

    resend = True  #Boolean for telling if needs resend
    dup = 0 #To handle duplicated pkts
    
    last_ack = -1 #etra place to hold the prev ack
    backupAck = bytearray() #Preserve the whole bytearray in case of resend


    def __init__(self, timeout = 0.1):
        super(myReceiver, self).__init__()  #inheritance
        self.timeout = timeout
        self.simulator.rcvr_socket.settimeout(self.timeout)

    def receive(self):  #override
        # start the general process
        while True:
            try:
                self.seg_rcv = self.simulator.u_receive()
                # TImeout needs to be checked manually
                if self.timeout > 0.1:
                    self.timeout -= 0.1
                    self.dup = 0

                #Handle received segs
                curr_seg = rcvrSegment()  #create data structure
                good_pkt = curr_seg.validate(self.seg_rcv, self.last_ack)

                #decide ack values
                if good_pkt:
                    self.last_ack = curr_seg.ack_num
                if curr_seg.ack_num < 0:
                    curr_seg.ack_num = 0

                #send ack
                curr_seg.checksum = curr_seg.checkSum()
                seg_rcv = bytearray([curr_seg.checksum, curr_seg.ack_num])
                backupAck = seg_rcv
                self.simulator.u_send(seg_rcv)

            # Timeout
            except socket.timeout:
                self.resend = True
                self.simulator.u_send(self.backupAck)
                self.dup += 1

                if self.dup >= 3:   #like fast retx
                    self.dup = 0
                    self.timeout *= 2
                    self.simulator.rcvr_socket.settimeout(self.timeout)
                    if self.timeout > 30:
                        sys.exit()
                        

class rcvrSegment(object):
    def __init__(self, checksum = 0, seq = 0, ack_num = 0, data = []):
        self.checksum = checksum
        self.seq = seq
        self.ack_num = ack_num
        self.data = data
         
    # Just onee byte
    def checkSum(self):        
        return self.ack_num
        

    # Traditional check method for one's comp chksum, found on wikipedia
    def checkACK(self,data):
        val =~ data[0]   
        for i in xrange(1,len(data)):
            val ^= data[i]
        if val ==- 1:
            return True 
        else:
            return False
    
    # Validate the packet
    def validate(self, data, last_ack):
        check = self.checkACK(data)
        if check:
            self.ack_num = (data[2] + len(data[3:])) % 256
            if data[2] == last_ack or last_ack == -1:
                sys.stdout.write("{}".format(data[3:]))
                sys.stdout.flush()
                return True
        else:
            pass

        return False

if __name__ == "__main__":
    rcvr = myReceiver()
    rcvr.receive()
