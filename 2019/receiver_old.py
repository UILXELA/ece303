# Written by S. Mevawala, modified by D. Gitzel
from __future__ import division
import logging
from Segment import Segment
import channelsimulator
import utils
import sys
import socket
import math
import time
import zlib
import struct

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

'''
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
'''

class myReceiver(Receiver):
    def __init__(self):
        super(myReceiver, self).__init__()
        self.rcv_pkt = Segment()         # received packet
        self.snd_pkt = bytearray() # make the segment in initializer
        self.curr_seq = -1 # receiver sequence number (SEQ Number)
        self.max_seq=0
        self.acknum = 0 # sender sequence number (ACK Number)
        # The closing_timeout is for terminating the program, since the 
        # RTT of a normal packet is around 20ms, we set the closing_timeout
        # to a relatively long time -- 10 s
        self.closing_timeout = 10
        # set isn of receiver, which is zero
        self.start = time.time()
        #initialize
        self.prev_seq = 0
        self.prev_size = 0
        self.win_size=4
        self.MSS=0
        self.curr_data=bytearray()


    def receive(self):
        self.logger.info("Receiving on port: {} and replying with ACK on port: {}".format(self.inbound_port, self.outbound_port))
        i=0
        buf=[None]*self.win_size
        buf_seq=[]
        self.simulator.rcvr_socket.settimeout(0.5)
        f = open("rcv_file", 'wb')
        # while loop for general reception of packets
        while(True):
            if (i==self.win_size):
                i=0
                buf=[None]*self.win_size
                buf_seq=[]
            # while loop for receiving ONE packet
            while(True):
                try:
                    #buf=[]
                    rcv_seg = Segment(data=self.simulator.u_receive(),sender=False)
                    print rcv_seg.seq
                    #buf.append(rcv_seg)
                    if(rcv_seg.check_chksum):
                        if(self.curr_seq==-1):
                            self.curr_seq=-len(rcv_seg.data)
                            self.MSS=-self.curr_seq
                        break
                    else:self.start=time.time()
                except socket.timeout:
                    if (len(self.snd_pkt) != 0):
                        # if there is a previously sent packet, 
                        # resend the packet
                        self.simulator.u_send(self.snd_pkt)
                    if (time.time() - self.start > self.closing_timeout) :
                        # Very long timeout -- 10s, terminate
                        # the program
                        print "(Receiver) Receiver closing"
                        f.close()
                        return
            #expected_seq = self.prev_seq + self.prev_size
            
            self.curr_seq=rcv_seg.seq
            self.curr_data=rcv_seg.data
            if(self.curr_seq not in buf_seq):
                buf_seq.append(self.curr_seq)
                buf[int(math.ceil(self.curr_seq/self.MSS)%self.win_size)]=rcv_seg
                while (buf[i]!=None):
                    i+=1
                    if(i>=self.win_size):
                        break
                if(i>0):
                    expected_seq=self.shortAdd(buf[i-1].seq,len(buf[i-1].data))
                    print str(expected_seq) + "a"
                    print self.curr_seq
                else:
                    expected_seq=int(math.floor(self.curr_seq/self.MSS/self.win_size)*self.MSS*self.win_size)
                    print str(expected_seq) + "b"
                self.acknum=expected_seq
            else:
                pass
            #print self.acknum
            self.chksum=zlib.crc32(str(self.acknum)) & 0xffffffff
            self._chksum=struct.pack('>L', self.chksum)
            self._acknum=struct.pack('>H', self.acknum)
            self.snd_pkt= bytearray(self._chksum)+bytearray(self._acknum)
            self.simulator.u_send(self.snd_pkt)
            self.start = time.time()
            '''
            if(self.curr_seq==expected_seq):
                buf_seq.append(self.curr_seq)
                buf[int(expected_seq/self.MSS)%4]=rcv_seg.data
                self.acknum=expected_seq+len(rcv_seg.data)
                self.prev_size=len(rcv_seg.data)
                self.prev_seq=expected_seq
            else:
                self.acknum=expected_seq
                if(self.curr_seq not in buf_seq):
                    buf_seq.append(self.curr_seq)
                    buf[int(expected_seq/self.MSS)%4]=rcv_seg.data
                else:
                    pass
            '''
    @staticmethod
    def shortAdd(a,b):
        if (a+b>65535):
            return a+b-65535
        else:
            return a+b


if __name__ == "__main__":
    # test out BogoReceiver
    rcvr = myReceiver()
    rcvr.receive()
