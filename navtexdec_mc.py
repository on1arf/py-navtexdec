import sys # for version check and argv

"""
NAVTEX decoder
input: 100 bps bits, encoded as bytes 0x00 or 0x01
output: text

Usage:
python3 navtexdec_mc.py [multicast-ip-address] [udp-port]


Version 0.1.0: 2020/Sep/19
(C) Kristoff Bonne (ON1ARF)

This code is distributed under GPL license v. 3.0
https://www.gnu.org/licenses/gpl-3.0.en.html



"""

# python version check
if sys.version_info.major < 3:
	raise RuntimeError("Python version 3 or newer required")
#end if

import socket
import struct

# global data
defaultip="225.0.0.1"
defaultport=10000

# some debug options
# (check the code to see what they do)
printalldata=False
printposition=False



def navtexdec_mc(mcip=defaultip, mcport=defaultport, flushall=True, flushnl=True):

	# if flushall is true, set also flush cr/lf
	if flushall: flushnl=True

	# CCIR 476 character set
	# source: http://search.itu.int/history/HistoryDigitalCollectionDocLibrary/1.43.48.en.104.pdf

	ccir476={
		b'\x00\x00\x00\x01\x01\x01\x01':('<ALPHA>','<ALPHA>'),

		b'\x00\x00\x01\x00\x01\x01\x01':('J','\a'), # \a = BELL (aka \x07)
		b'\x00\x00\x01\x01\x00\x01\x01':('F','!'),
		b'\x00\x00\x01\x01\x01\x00\x01':('C',':'),
		b'\x00\x00\x01\x01\x01\x01\x00':('K','('),

		b'\x00\x01\x00\x00\x01\x01\x01':('W','2'),
		b'\x00\x01\x00\x01\x00\x01\x01':('Y','6'),
		b'\x00\x01\x00\x01\x01\x00\x01':('P','0'),
		b'\x00\x01\x00\x01\x01\x01\x00':('Q','1'),

		b'\x00\x01\x01\x00\x00\x01\x01':('<BETA>','<BETA>'),
		b'\x00\x01\x01\x00\x01\x00\x01':('G','&'),
		b'\x00\x01\x01\x00\x01\x01\x00':('<FIGS>','<FIGS>'),
		b'\x00\x01\x01\x01\x00\x00\x01':('M','.'),
		b'\x00\x01\x01\x01\x00\x01\x00':('X','/'),
		b'\x00\x01\x01\x01\x01\x00\x00':('V','='),

		b'\x01\x00\x00\x00\x01\x01\x01':('A','-'),
		b'\x01\x00\x00\x01\x00\x01\x01':('S','\''),
		b'\x01\x00\x00\x01\x01\x00\x01':('I','8'),
		b'\x01\x00\x00\x01\x01\x01\x00':('U','7'),

		b'\x01\x00\x01\x00\x00\x01\x01':('D','$'),
		b'\x01\x00\x01\x00\x01\x00\x01':('R','4'),
		b'\x01\x00\x01\x00\x01\x01\x00':('E','3'),
		b'\x01\x00\x01\x01\x00\x00\x01':('N',','),
		b'\x01\x00\x01\x01\x00\x01\x00':('<LTRS>','<LTRS>'),
		b'\x01\x00\x01\x01\x01\x00\x00':(' ',' '),

		b'\x01\x01\x00\x00\x00\x01\x01':('Z','+'),
		b'\x01\x01\x00\x00\x01\x00\x01':('L',')'),
		b'\x01\x01\x00\x00\x01\x01\x00':('<RC>','<RC>'),
		b'\x01\x01\x00\x01\x00\x00\x01':('H','#'),
		b'\x01\x01\x00\x01\x00\x01\x00':('<CH32>','<CH32>'),
		b'\x01\x01\x00\x01\x01\x00\x00':("\r","\r"),


		b'\x01\x01\x01\x00\x00\x00\x01':('O','9'),
		b'\x01\x01\x01\x00\x00\x01\x00':('B','?'),
		b'\x01\x01\x01\x00\x01\x00\x00':('T','5'),
		b'\x01\x01\x01\x01\x00\x00\x00':("\n","\n")}
	#end CCIR 476 table

	# CCIR 476 characters '<ALPHA>' and '<RC>' defined as list.
	# used seperately in the program
	alpha=[0,0,0,1,1,1,1]
	rc=[1,1,0,0,1,1,0]


	# some internal support functions

	def __isvalidresponse__(x1,x2):
		# returns true if
		# 		x1 = x2
		#		'ALPHA' as response to 'Sync Response'
		return True if (x1 == x2) or (x1,x2) == (rc,alpha) else False
	#end def equal response


	# "printchar" defined as class, as it needs to maintain the "table" state
	class printchar():

		def __init__(self,table=0,printall=False, flushall=flushall, flushnl=flushnl):
			self.table=table
			self.printall=printall
			self.flushall=flushall
			self.flushnl=flushnl
		#end def __init__

		def out(self,inchar):
			try:
				towritechar=ccir476[inchar][self.table]
			except KeyError:
				towritechar=inchar
			#end try


			if towritechar == '<LTRS>':
				# change to "letters" table
				if self.printall: print('<LTRS>',flush=self.flushall,end='')
				self.table=0
			elif towritechar == '<FIGS>':
				# change to "figures" table
				if self.printall: print('<FIGS>',flush=self.flushall,end='')
				self.table=1
			elif towritechar in ('<ALPHA>','<BETA>','<RC>','<CH32>'):
				# do not print special characters
				if self.printall: print(towritechar,flush=self.flushall,end='')
				#pass
			elif towritechar in ('\r',):
				# do not print LF
				pass
			elif towritechar:
				# is there actually something to print?
				thisflush = self.flushnl if towritechar=="\n" else self.flushall
				print(towritechar, end='',flush=thisflush)
			#end elif - elif - elif - if

			return table
		#end def
	#end class 'printchar'


	# get input bits from multicast stream
	class getinbits():
		def __init__ (self,sock):
			self.buff = []
			self.bufptr = 0
			self.bufsize = 0
			self.sock=sock
		#end def __init__

		def get(self,n):
			bits2get=n
			retbuf=[]

			while True:
				# get data from socket if buffer is completely read
				if self.bufptr == self.bufsize:
					newbytes = self.sock.recv(10240)

					newbl=len(newbytes)
					if newbl == 0: continue # try again if no data read
					
					# store data in buffer and set pointer and size 
					self.buff=struct.unpack('B'*newbl,newbytes)
					self.bufptr=0
					self.bufsize=newbl
				#end if

				# get as much data from the buffer as possible
				nbits=min(bits2get,(self.bufsize-self.bufptr))

				retbuf += self.buff[self.bufptr:self.bufptr+nbits] # copy data from buffer

				self.bufptr += nbits # move buffer pointer upwards
				bits2get -= nbits

				if bits2get == 0: return retbuf # we have sufficient data, return

				# not yet enough data, get some more
				continue # return in loop to grab more data
			#end endless loop
		#end def get

	#end class getinbits():




	# ####################################
	######################################
	# main part of the function start here

	# receiving multicast in python, shameless stolen from
	# https://stackoverflow.com/questions/603852/how-do-you-udp-multicast-in-python

	# assert bind_group in groups + [None], \
	#     'bind group not in groups to join'
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)

	# allow reuse of socket (to allow another instance of python to run this
	# script binding to the same ip/port)
	sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

	sock.bind(('',mcport)) # bind to any ip-address

	#igmp join
	mreq=struct.pack('4sl',socket.inet_aton(mcip),socket.INADDR_ANY)
	sock.setsockopt(socket.IPPROTO_IP,socket.IP_ADD_MEMBERSHIP,mreq)


	indata=getinbits(sock)
	pch=printchar()

	# init some vars
	fecscore=0

	# "letter" or "figures"
	table=0

	#fec memory buffer
	# create with same structure as used in the code
	fecmem=[[True,[0 in range(7)]],[True,[0 in range(7)]],[True,[0 in range(7)]]]
	fecmemptr=0
	fecstate=0

	#total byte counter
	totalbitcount=0



	#endless loop, break out with 'break' at the end of the file

	while True:

		if totalbitcount == 0:
			print("\n### Syncronizing",flush=True)
		else:
			print("\n### Syncronisation lost ... Resyncronizing",flush=True)
		#end if

		# DEBUG
		if printposition: print("## Position:",totalbitcount)



		# state 1: look for sync

		# start with 10 char buffer (= 70 bits)
		# only done at the beginning of the file / stdin
		if totalbitcount == 0:
			buf=indata.get(70)
			
			totalbitcount+=70
		else:
			n=indata.get(1)

			if len(n) < 1: return False # break out on end of file
			
			buf.pop(0)
			buf.append(n[0])
			totalbitcount+=1
		#end if

		# clear tempory buffer used to transfer data from "state 1' (sync) to "state 2"
		tmpbuff=[]


		#endless loop (for 'sync' state)

		while True:
			# convert 70 bits into 10 * 7bit char
			char7=[buf[i*7:(i+1)*7] for i in range(10)]


			# count the number of '1' bits
			nbit=[len(list(filter(lambda x: x,c7))) for c7 in char7] 


			# sync check:

			# rule 1: all 7chars should contain 4 '1' bits
			# rule 2: not all chars should be the same
			# rule 3: char 5, 7 and 9 should be a reply to 0, 2 and 4
			if (len(list(filter(lambda x: x != 4, nbit))) != 0) or (char7[9]==char7[7]==char7[5]) or  (not __isvalidresponse__(char7[9][::-1],char7[4][::-1])) or (not __isvalidresponse__(char7[7][::-1],char7[2][::-1])) or (not __isvalidresponse__(char7[5][::-1],char7[0][::-1])):

				# not yet syncronised -> get next bit
				n=indata.get(1)

				# shift down stack and add new bit at the end
				buf.pop(0)
				buf.append(n[0])

				totalbitcount+=1
				continue
			#end if


			# syncronisation success: we have valid data

			# init data for state 2:

			# write 3 first 7chars to tempory buffer
			tmpbuff=[char7[0],char7[2],char7[4]]

			# store previously received data in fecmemory
			fecmem[0]=(True,char7[6][::-1])
			fecmem[1]=(True,char7[8][::-1])
			fecmemptr_wr=2 # init "write" pointer
			fecmemptr_rd=0 # init "read " pointer

			# fecstate: 0: read data 1ste time, 1: read data 2nd  time -> check if the same as read during "fecstate"
			# note: the 'fecstate=1' character is received 5 characters of the 'fecstate=0' character
			# more info:
			# source: http://search.itu.int/history/HistoryDigitalCollectionDocLibrary/1.43.48.en.104.pdf
			# http://www.frisnit.com/navtex/?id=navtex_data_format
			fecstate=0 # next byte we are going to read is a "1st data" byte
			fecscore=2 # we have two correct characters -> score is 2

			# jump out of loop
			break
		#end while (state 1)



		print("### Syncronisation Success",flush=True)
		if printposition: print("## Position:",totalbitcount, flush=True)


		# output characters in tempory buffer (see "state 1" above)
		for buffelem in tmpbuff:
			pch.out(bytes(buffelem[::-1]))
		#end for

		# state 2:
		# read data 7bitchar per 7bitchar

		while True:
			# read 7 bits
			p=indata.get(7)
			pl=list(p)

			totalbitcount+=7

			if len(p) < 7: return False # break out at end of file

			# invert the order of the bits
			pl=pl[::-1]

			# cntok is 'true' if 4 'one' bits
			cnt=len(list(filter(lambda x: x,p)))
			cntok=True if cnt == 4 else False

			# FEC state, 0: read character 1st time, 1: read character 2nd time -> compair to character received during fecstate 0

			if fecstate == 0:
				# FEC state 0: store character in fec memory
				fecmem[fecmemptr_wr]=(cntok,pl)

				#move up fecmem "write" pointer
				fecmemptr_wr+=1
				if fecmemptr_wr >= 3: fecmemptr_wr = 0

				fecstate = 1
				continue # get next character

			#end if (fecstate 0)

			if fecstate == 1:
				#fec state 1: compaire data with previously stored data

				#init vars
				towritechar=""
				donotchangefecstate=False

				# read earlier received character from fecmem
				(prev_cntok,prev_pl)=fecmem[fecmemptr_rd]
				# move up fecmem pointer
				fecmemptr_rd+=1
				if fecmemptr_rd >= 3: fecmemptr_rd=0

				# rule 0: Special casse:
				# receive a 'rc' in responds to an 'alpha' ... reverse RX/TX order -> change fecstate
				# so process this as 'fecstate = 0' state
				if (prev_cntok,cntok,prev_pl,pl) == (True,True,alpha,rc):
					# do same as "fecstate = 0' above
					# store data in fec memory
					fecmem[fecmemptr_wr]=(cntok,pl)

					#inclease fecmem pointer
					fecmemptr_wr+=1
					if fecmemptr_wr >= 3: fecmemptr_wr = 0

					# do not change fec-state anymore (so it stays at 1)
					donotchangefecstate=True

				# rule1: if current char and previous char are ok (i.e. four '1' bits)
				elif prev_cntok and cntok:
					# are they the same?
					if __isvalidresponse__(prev_pl,pl):
						# yes, new and previous character match -> output it
						towritechar=bytes(pl)

						# increase score
						if fecscore < 20: fecscore+=1

					else:
						# we received two different chars -> Error -> output a '*'
						towritechar="*"
					#end if

				elif prev_cntok and not cntok:
					# new character is not correct (not four '1' bits) -> output previous character
					towritechar=bytes(prev_pl)

				elif not prev_cntok and cntok:
					# previous character was not correct (not four '1' bits) -> output new character
					towritechar=bytes(pl)

				else:
					# both previous and new character are not correct (not four '1' bits) -< error -> output a '*'
					towritechar='*'

					# decrease score
					if fecscore > 0: fecscore-=1
				#end else - elsif - elsif - ik


				# actually output character, if not rule 0
				if not donotchangefecstate:
					# not 'special rule 0'
					pch.out(towritechar)
					fecstate = 0
				#end if
						

				# break out of phase 2 (printing data) if the fecscore has dropped to 0
				if fecscore < 1:
					break
				#end if

				continue # get next character
			#end else - if

			# invalid value for fecstate
			# we should never -> reiinit
			break

		# end while (state 2)

	#end while (endless loop)

	print("done",flush=True)
	f.close()

# end 


def main():
	try:
		mcip=sys.argv[1]
	except IndexError:
		mcip=defaultip
	#endtry

	try:
		mcport=sys.argv[2]
	except IndexError:
		mcport=defaultport
	#end try
	navtexdec_mc(mcip,mcport, flushall=True)
	print("Main done!",flush=True)

#end main

if __name__ == "__main__": main()
