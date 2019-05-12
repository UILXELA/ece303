import logging

import channelsimulator
import utils
import sys
import zlib
import socket
import struct
class Segment():
	def __init__(self, chksum=0,seq=0, data=bytearray(),to_send=bytearray(),sender=True):
		#A segment contains data, checksum, ack and sequence number
		if sender:
			
			self.seq=seq
			self._seq=struct.pack('>H', self.seq)	#2 bytes
			self.data=data
			self.to_send=bytearray(self._seq)+self.data #0-1 chksum, 2-3 ack, 4-5 seq, 6:end data
			self.chksum=zlib.crc32(to_send.decode()) & 0xffffffff
			self._chksum=struct.pack('>L', self.chksum)	#4 bytes
			self.to_send=bytearray(self._chksum)+self.to_send
		else:
			self._chksum=data[0:4]
			self._seq=seq=data[4:6]
			self.chksum=struct.unpack('>L', self._chksum)[0]	#4 bytes
			self.seq=struct.unpack('>H', self._seq)[0]		#2 bytes
			self.chk=data[4:]
			self.data=data[6:]

	def checkSum(self):
		zlib.crc32(self.data.decode()) & 0xffffffff
		return chksum

	def check_chksum(self):
		return self.chksum==zlib.crc32(self.chk.decode()) & 0xffffffff


