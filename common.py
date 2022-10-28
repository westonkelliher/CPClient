#!/usr/bin/python
import socket
import sys


DELMT = '\n'

class Conn:
  def __init__(self, sock=None):
    if sock is None:
      self.sock = socket.socket(
        socket.AF_INET, socket.SOCK_STREAM)
    else:
      self.sock = sock
    self.partial_msg = ''
      
  def connect(self, host, port):
    self.sock.settimeout(1)
    self.sock.connect((host, port))
    
  def send(self, msg):
    if DELMT in msg:
      print('Cannot use delimiter in msg (probably newline)')
      self.sock.close()
      return
    totalsent = 0
    emsg = (msg+DELMT).encode()
    while totalsent < len(emsg):
      sent = self.sock.send(emsg[totalsent:])
      if sent == 0:
        raise RuntimeError("socket connection broken")
      totalsent = totalsent + sent


  # returns (connection still valid, full message)
  def recv(self):
    msg = self.partial_msg
    while not DELMT in msg:
      chunk = self.sock.recv(10)
      if chunk == b'':
        return (False, msg)
      msg = msg + chunk.decode('utf-8')
    parts = msg.split(DELMT)
    if len(parts) == 3:
      print('Error: doubly overflowing message')
    self.partial_msg = parts[1]
    msg = parts[0]
    while msg[-1].isspace():
      msg = msg[:-1]
    return (True, msg)

  # returns (connection still valid, full message)
  def new_recv(self):
    msg = self.partial_msg
    while not DELMT in msg:
      try:
        chunk = self.sock.recv(10)
      except ConnectionResetError:
        print('Port was scanned')
        continue
      if chunk == b'':
        return (False, msg)
      msg = msg + chunk.decode('utf-8')
    parts = msg.split(DELMT)
    if len(parts) == 3:
      print('Error: doubly overflowing message')
    self.partial_msg = parts[1]
    msg = parts[0]
    while msg[-1].isspace():
      msg = msg[:-1]
    return (True, msg)


  
  def send_bytes(self, msg):
    totalsent = 0
    while totalsent < len(msg):
      sent = self.sock.send(msg[totalsent:])
      if sent == 0:
        raise RuntimeError("socket connection broken")
      totalsent = totalsent + sent

  def recv_bytes(self, num_bytes):
    self.sock.settimeout(2)
    msg = b''
    while len(msg) < num_bytes:
      try:
        chunk = self.sock.recv(num_bytes - len(msg))
      except:
        self.sock.close()
        print('timed out; len ' + str(len(msg)) + ", num_bytes " + str(num_bytes))
        sys.exit(1)
      if chunk == b'':
        return (False, msg)
      msg += chunk
    return (True, msg)
    
    



  def close(self):
    self.sock.close()

    


  
