#!/usr/bin/env python3
# -*- coding: UTF_8 -*-

# @copyright  this code is the property of Ubertone. 
# You may use this code for your personal, informational, non-commercial purpose. 
# You may not distribute, transmit, display, reproduce, publish, license, create derivative works from, transfer or sell any information, software, products or services based on this code.
# @author Stéphane Fischer

# lecture du fichier de données de données brutes

from struct import calcsize, unpack

class ubt_raw_file:
	def __init__(self, _filename):
		"""Function that initiates a ubt_raw_file object which allows to read a raw.udt file chunk by chunk.
		Works only for raw.udt files from webui2 (UB-Lab P).

		Args:
		    _filename (string): file path of raw.udt file

		Returns:
			None
		"""
		self.fd=open(_filename,'rb') # 1er argument : fichier raw
		self.total_size=0

		header = self.fd.read(42).decode("utf-8").split(" ")
		self.version=header[0]
		print("raw header : ", self.version)
		self.board = header[1]
		print("board : ", self.board)
		header = header[2].split("/")
		self.webui2 = header[0]
		print("webui2 : ", self.webui2)
		print("header extension : ", header[1:])

	def __read_file__ (self, _size):
		"""Function that reads a certain sized chunk of the file.

		Args:
		    _size (int): size of chunk to read

		Returns:
			_data (bytes object): read chunk
		"""
		# print "_size in read file %d"%_size
		_data=self.fd.read(_size)
		# print "_data in read file %s"%_data
		if _data == '':
			print("%d byte read in the file"%(self.total_size))
			raise EOFError
		else:
			if _size!=len(_data):
				raise EOFError
			self.total_size+=_size
			#print("total size in read file %d"%self.total_size)
			return _data

	def read_chunk(self) :
		"""Function that reads a certain sized chunk of the file.

		Args:
		    _size (int): size of chunk to read

		Returns:
			flag (int): identification flag for data in the chunk
			size (int): size of the data in the chunk
			data (bytes object): data in the chunk
		"""
		flag = unpack('h', self.__read_file__(calcsize('h')))[0]
		size = unpack('h', self.__read_file__(calcsize('h')))[0]
		# print "flag in read chunk %d"%flag
		# print "size in read chunk %d"%size
		if size:
			data=self.__read_file__(size)
		else :
			print("chunck vide")
			data = ''

		# crc = unpack('h', self.__read_file__(calcsize('h')))[0]
		return flag, size, data

