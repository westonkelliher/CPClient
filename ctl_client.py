import socket
import math
import datetime

from scene import *
import ui
import canvas
import atexit

import common
import ctlrcfg as cc
from ctlrcfg import CtlrCfg, Button, JoyStick

SLIDER_X  = 0 #set later
ROUNDNESS = 8
SPACE = 2

BUTTON_CLR   = '#999999'
JOYPAD_CLR   = '#888888'
JOYSTICK_CLR = '#9999A2'

def color_int_to_str(num):
  byts = num.to_bytes(4, 'little')
  s = '#'
  s += hex(byts[0]).split('x')[1]
  s += hex(byts[1]).split('x')[1]
  s += hex(byts[2]).split('x')[1]
  return s


def arctan(x, y):
  if x == 0:
    if y > 0:
      math.pi/2
    else:
      -math.pi/2
  return math.atan(y/x)


def cc_create_Test(width, height):
  b1 = Button(0, 0, width/3, height/2)
  b2 = Button(0, height/2, width/3, height)
  js = JoyStick(width*2/3, height*1/2, height*1/2)
  cc = CtlrCfg([b1,b2], [js])
  return cc


# rounded rect shape node
def get_RRSN(x, y, w, h, color):
  shape = ui.Path.rounded_rect(0, 0, w-SPACE*2, h-SPACE*2, ROUNDNESS)
  shape_node = ShapeNode(shape, color)
  shape_node.position = (SPACE+x+w/2, SPACE+y+h/2)
  return shape_node


# rounded rect shape node
def get_RRSN2(x1, y1, x2, y2, color):
  w = x2 - x1
  h = y2 - y1
  shape = ui.Path.rounded_rect(0, 0, w-SPACE*2, h-SPACE*2, ROUNDNESS)
  shape_node = ShapeNode(shape, color)
  shape_node.position = (SPACE+x1+w/2, SPACE+y1+h/2)
  return shape_node

def get_RSN2(x1, y1, x2, y2, color):
  w = x2 - x1
  h = y2 - y1
  shape = ui.Path.rect(0, 0, w-SPACE*2, h-SPACE*2)
  shape_node = ShapeNode(shape, color_int_to_str(color))
  shape_node.position = (SPACE+x1+w/2, SPACE+y1+h/2)
  return shape_node

# circle shape node
def get_CircSN(x, y, r, color):
  shape = ui.Path.oval(0, 0, (r-SPACE)*2, (r-SPACE)*2)
  shape_node = ShapeNode(shape, color)
  shape_node.position = (x, y)
  return shape_node



class DragSender (Scene):
  def setup(self):
    self.conn = common.Conn()
    self.conn.connect('192.168.0.100', 50079)
    dims_ctos = cc.CtoS(cc.MSG_TYPES["Dimensions"], self.size.x, self.size.y,
                       cc.ControlPacket(0, None))
    #str(self.size.x) + ',' + str(self.size.y)
    # TODO: can probably just use self.send_datum
    self.conn.send_bytes(dims_ctos.to_bytes())
    self.time_of_last_heartbeat = datetime.datetime.now()
    print("sent " + str(dims_ctos.to_bytes()))
    valid, msg = self.conn.recv_bytes(5)
    if not valid:
      exit('failed to receive initial controller config: ' + str(msg))
    print("msg:")
    print(msg)
    if msg[0] != 32:
      print("msg id not 32")
    str_spec_len = int.from_bytes(msg[1:], byteorder='little')
    print('str_spec_len ' + str(str_spec_len))
    valid, msg = self.conn.recv_bytes(str_spec_len)
    msg_str = msg.decode('utf-8')
    self.config = CtlrCfg.from_str(msg_str)
    self.ctouches = {}
    self.display_config()

  def update(self):
    now = datetime.datetime.now()
    time_since = now - self.time_of_last_heartbeat
    if time_since.seconds > 0 or time_since.microseconds >= 250000:
      self.send_datum(cc.CtoS(cc.MSG_TYPES["Heartbeat"], 0, 0, None).to_bytes())
      self.time_of_last_heartbeat = now
    

  def display_config(self):
    # TODO: do we need to clear previous children?
    for pnl in self.config.panels:
      # reverse y dimension
      y1 = self.size.y - pnl.y2
      y2 = self.size.y - pnl.y1
      btn_node = get_RSN2(pnl.x1, y1,
                          pnl.x2, y2, pnl.color)
      self.add_child(btn_node)
    for btn in self.config.buttons:
      # reverse y dimension
      y1 = self.size.y - btn.y2
      y2 = self.size.y - btn.y1
      btn_node = get_RRSN2(btn.x1, y1,
                          btn.x2, y2, BUTTON_CLR)
      self.add_child(btn_node)
    for jstk in self.config.joysticks:
      # reverse y dimension
      y = self.size.y - jstk.y
      jpd_node = get_CircSN(jstk.x, y,
                           jstk.r, JOYPAD_CLR)
      jstk_node = get_CircSN(jstk.x, y,
                           .48*jstk.r, JOYSTICK_CLR)
      jstk.jstk_node = jstk_node
      self.add_child(jpd_node)
      self.add_child(jstk_node)


  def send_datum(self, datum):
    self.conn.send_bytes(datum)
    valid, msg = self.conn.recv_bytes(5)
    if not valid:
      exit('failed to receive a 5 byter: ' + str(msg))
    if msg[0] != 31:
      print("msg:")
      print(msg)
    if msg[0] == 31: # StoC::None
      return
    elif msg[0] == 32: # StoC::StringSpec
      str_spec_len = int.from_bytes(msg[1:], byteorder='little')
      print('str_spec_len ' + str(str_spec_len))
      valid, msg = self.conn.recv_bytes(str_spec_len)
      msg_str = msg.decode('utf-8')
      self.config = CtlrCfg.from_str(msg_str)
      self.display_config()
    else:
      print("StoC magic number " + str(msg[0]) + " cannot be handled")
    

  def touch_began(self, touch):
    tx = touch.location.x
    ty = touch.location.y
    # have to reverse y dimension
    i, elem = self.config.get_element_containing_point(tx, self.size.y - ty)
    self.ctouches[touch.touch_id] = elem
    if elem:
      datum = elem.datum_from_TB(tx, ty)
      if datum:
              self.send_datum(datum)
    self.ctouches

    
  def touch_moved(self, touch):
    tx = touch.location.x
    ty = touch.location.y
    elem = self.ctouches[touch.touch_id]
    if elem:
      datum = elem.datum_from_TM(tx, ty)
      if datum:
        self.conn.send_bytes(datum)

        
  def touch_ended(self, touch):
    tx = touch.location.x
    ty = touch.location.y
    elem = self.ctouches[touch.touch_id]
    if elem:
      datum = elem.datum_from_TE(tx, ty)
      if datum:
        self.conn.send_bytes(datum)
    del self.ctouches[touch.touch_id]


  def stop(self):
    self.conn.close()

    

ds = DragSender()
run(ds)

