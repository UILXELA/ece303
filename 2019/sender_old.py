# Written by S. Mevawala, modified by D. Gitzel
from __future__ import division

import logging
import socket
from Segment import Segment
import channelsimulator
import utils
import sys
import math
import struct
import zlib


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

class mySender(Sender):
	def __init__(self, timeout = 0.1):
		super(mySender, self).__init__()
		self.timeout=timeout
		self.simulator.sndr_socket.settimeout(self.timeout)
		self.MSS=256
		self.send_base=0
		self.win_size=4
		self.curr_pkt=0
		self.last_ack=0
		self.curr_seq=-self.MSS


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

	def send(self,DATA):
		self.logger.info("Sending on port: {} and waiting for ACK on port: {}".format(self.outbound_port, self.inbound_port))
		data_all=self.splitter(DATA,self.MSS)
		while True:
			buf=[]
			self.dup_ack=0
			self.curr_pkt=int(math.ceil(self.send_base/self.MSS))
			if(self.curr_pkt==len(data_all)):
				return
			elif((self.curr_pkt+self.win_size)<len(data_all)):
				iter_count=self.win_size
			else:
				iter_count=len(data_all)-self.curr_pkt
			for i in range(iter_count):
				curr_data=data_all[self.curr_pkt]
				self.curr_seq=self.shortAdd(len(curr_data),self.curr_seq)
				curr_seg=Segment(seq=self.curr_seq, data=curr_data)
				buf.append(curr_seg)
				self.simulator.u_send(curr_seg.to_send)
				self.curr_pkt+=1

			while True:
				try:
					rcv_seg=self.simulator.u_receive()

					ack_chksum=struct.unpack('>L', rcv_seg[0:4])[0]
					ack_num=struct.unpack('>H', rcv_seg[4:6])[0]
					#print ack_num
					if(ack_chksum==self.checkSum(str(ack_num))):
						ack_num=int(ack_num)
						if(ack_num>self.last_ack|(ack_num<=256&self.last_ack>(65535-256))):
							self.last_ack=ack_num
							
						elif(ack_num==self.last_ack):
							self.dup_ack+=1
							if(self.dup_ack==3):
								self.simulator.u_send(buf[self.last_ack/self.MSS+1].to_send)
						self.dup_ack=0
						if(self.last_ack==self.curr_seq):
							self.send_base=self.last_ack
							break
				except socket.timeout:
					self.last_ack=self.send_base
					break


	@staticmethod
	def checkSum(data):
		chksum=zlib.crc32(data) & 0xffffffff
		return chksum


	@staticmethod
	def shortAdd(a,b):
		if (a+b>65535):
			return a+b-65535
		else:
			return a+b
			

			
				

				
		
	





if __name__ == "__main__":
	# test out BogoSender
	DATA = bytearray(sys.stdin.read())
	sndr = mySender()
	sndr.send(DATA)
