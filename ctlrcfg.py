import math

BYTES_PER_INT = 4
NUM_INTS_CTOS = 8
NUM_BYTES_CTOS = NUM_INTS_CTOS*BYTES_PER_INT
NUM_INTS_CONTROLDATUM = 6
NUM_BYTES_CONTROLDATUM = NUM_INTS_CONTROLDATUM * BYTES_PER_INT

INT_MAX = 2147483647


def dist(x1, y1, x2, y2):
  dx = x2 - x1
  dy = y2 - y1
  return math.sqrt(dx**2 + dy**2)


def nums_to_bytes(nums):
  ret = b''
  for num in nums:
    if not isinstance(num, int):
      print(num)
      print(nums)
    ret += num.to_bytes(BYTES_PER_INT, byteorder='little', signed=True)
  return ret


MSG_TYPES = {"Heartbeat":9, "Disconnect":10, "Dimensions":11, "ControlPacket":12}
class CtoS:
  def __init__(self, msg_type, w, h, ctl_packet):
    self.msg_type = msg_type
    self.w = int(w)
    self.h = int(h)
    self.ctl_packet = ctl_packet

  def to_bytes(self):
    nums = self.to_nums()
    return nums_to_bytes(nums)

  def to_nums(self):
    ret = [0] * NUM_INTS_CTOS
    ret[0] = self.msg_type
    if self.msg_type == MSG_TYPES["Disconnect"]:
      pass
    elif self.msg_type == MSG_TYPES["Dimensions"]:
      ret[1] = self.w
      ret[2] = self.h
    elif self.msg_type == MSG_TYPES["ControlPacket"]:
      ret[1] = self.ctl_packet.element_id
      ret[2] = self.ctl_packet.datum.datum_type
      if self.ctl_packet.datum.datum_type == DATUM_TYPES["Squeeze"]:
        a, b = float_to_two_ints(self.ctl_packet.datum.x)
        ret[3] = a
        ret[4] = b
      elif self.ctl_packet.datum.datum_type == DATUM_TYPES["Move"]:
        a, b = float_to_two_ints(self.ctl_packet.datum.x)
        c, d = float_to_two_ints(self.ctl_packet.datum.y)
        ret[3] = a
        ret[4] = b
        ret[5] = c
        ret[6] = d
    return ret

def float_to_two_ints(f):
  a = int(f)
  b = f - a
  b *= INT_MAX
  b = int(b)
  return a, b


class ControlPacket:
  def __init__(self, element_id, datum):
    self.element_id = element_id
    self.datum = datum


DATUM_TYPES = {"Press": 21, "Release":22, "Squeeze":23, "Move":24}    
class ControlDatum:
  def __init__(self, datum_type, x, y):
   self.datum_type = datum_type
   self.x = x
   self.y = y





class CtlrCfg:
  def __init__(self, panels, buttons, joysticks):
    self.panels = panels
    self.buttons = buttons
    self.joysticks = joysticks
    # TODO: pretty sure keeping track of index is no longer necessary
    for i, p in enumerate(self.panels):
      p.index = i
    for i, b in enumerate(self.buttons):
      b.index = i
    for i, j in enumerate(self.joysticks):
      j.index = i
    

  def from_str(s):
    parts = s.split(']')
    if len(parts) != 3:
      exit('3 sets of things for a CtlrCfg')
    pnls = [Panel.from_str(s) for s in parts[0].split(';')[:-1]]
    btns = [Button.from_str(s) for s in parts[1].split(';')[:-1]]
    jstks = [JoyStick.from_str(s) for s in parts[2].split(';')[:-1]]
    return CtlrCfg(pnls, btns, jstks)
    

  def to_str(self):
    s = ''
    for pnl in self.panels:
      s += pnl.to_str()
      s += ';'
    s += ']'
    for btn in self.buttons:
      s += btn.to_str()
      s += ';'
    s += ']'
    for jstk in self.joysticks:
      s += jstk.to_str()
      s += ';'
    return s

  def get_element_containing_point(self, x, y):
    for i, btn in enumerate(self.buttons):
      if (btn.x1 <= x and x < btn.x2 and
          btn.y1 <= y and y < btn.y2):
        return i, btn
    for i, jstk in enumerate(self.joysticks):
      if dist(x, y, jstk.x, jstk.y) < jstk.r:
        return i, jstk
    return -1, None

  def route_datum(self, datum):
    parts = datum.split(':')
    if len(parts) != 3:
      print(parts)
      exit('datums should have 3 parts: type, index, data')
    dtype = int(parts[0])
    index = int(parts[1])
    subdatum = parts[2]
    if   dtype == TYPE_BUTTON:
      self.buttons[index].handle_datum(subdatum)
    elif dtype == TYPE_JOYSTICK:
      self.joysticks[index].handle_datum(subdatum)
    else:
      print(parts)
      print(dtype)
      exit('invalid dtype')

# datum type constants
TYPE_PANEL    = 10
TYPE_BUTTON   = 11
TYPE_JOYSTICK = 12


class Panel:
  def __init__(self, elem_id, x1, y1, x2, y2, color):
    self.elem_type = TYPE_PANEL
    self.elem_id = elem_id
    self.x1 = x1
    self.y1 = y1
    self.x2 = x2
    self.y2 = y2
    self.color = int.from_bytes(color, 'little')

  def from_str(s):
    parts = s.split(',')
    if len(parts) != 6:
      exit('there must be 6 args to Panel')
    elem_id = int(parts[0])
    x = float(parts[1])
    y = float(parts[2])
    w = float(parts[3])
    h = float(parts[4])
    color = int(parts[5])
    c_bytes = color.to_bytes(4, 'little')
    return Panel(elem_id, x, y, x + w, y + h, c_bytes)

  def to_str(self):
    return (str(self.x1) + ',' + str(self.y1) + ',' + str(self.x2) +
            ',' + str(self.y2) + ',' + str(self.color.to_bytes(4, 'little')))


class Button:
  def __init__(self, elem_id, x1, y1, x2, y2):
    self.elem_type = TYPE_BUTTON
    self.elem_id = elem_id
    self.x1 = x1
    self.y1 = y1
    self.x2 = x2
    self.y2 = y2
    self.index = None
    self.depressed = False # should we keep track of state within the elements
    # themselves or just use the elements as stateless conduits?
    self.on_press = None
    self.on_release = None

  def set_on_press(self, func):
    self.on_press = func

  def set_on_release(self, func):
    self.on_release = func
    
  def from_str(s):
    parts = s.split(',')
    if len(parts) != 5:
      exit('there must be 5 args to Button')
    elem_id = int(parts[0])
    x = float(parts[1])
    y = float(parts[2])
    w = float(parts[3])
    h = float(parts[4])
    return Button(elem_id, x, y, x + w, y + h)

  def to_str(self):
    return (str(self.x1) + ',' + str(self.y1) + ',' + str(self.x2) +
            ',' + str(self.y2))

  def handle_datum(self, datum):
    self.depressed = datum == 'true'
    if self.depressed:
      if self.on_press:
        self.on_press()
    else:
      if self.on_release:
        self.on_release()
  
  # touch began
  def datum_from_TB(self, x, y):
    print("press from " + str(self.elem_id))
    self.depressed = True
    ctos = CtoS(MSG_TYPES["ControlPacket"], 0, 0, ControlPacket
                   (self.elem_id, ControlDatum(DATUM_TYPES["Press"], 0, 0)))
    return ctos.to_bytes()

  def datum_from_TM(self, x, y):
    return None
  
  def datum_from_TE(self, x, y):
    self.depressed = False
    ctos = CtoS(MSG_TYPES["ControlPacket"], 0, 0, ControlPacket
                   (self.elem_id, ControlDatum(DATUM_TYPES["Release"], 0, 0)))
    return ctos.to_bytes()

  

class JoyStick:
  def __init__(self, elem_id, x, y, r):
    self.elem_type = TYPE_JOYSTICK
    self.elem_id = elem_id
    self.x = x
    self.y = y
    self.r = r
    self.index = None
    self.depressed = False
    self.stick_x = 0
    self.stick_y = 0
    self.jstk_node = None
    self.on_press = None
    self.on_release = None
    self.on_move = None

  def from_str(s):
    parts = s.split(',')
    if len(parts) != 4:
      exit('there must be 4 args to JoyStick')
    elem_id = int(parts[0])
    x = float(parts[1])
    y = float(parts[2])
    r = float(parts[3])
    return JoyStick(elem_id, x, y, r)

  def to_str(self):
    return (str(self.x) + ',' + str(self.y) + ',' + str(self.r))

  def set_on_press(self, func):
    self.on_press = func

  def set_on_release(self, func):
    self.on_release = func

  def set_on_move(self, func):
    self.on_move = func
    
  def handle_datum(self, datum):
    parts = datum.split(',')
    if parts[0] != 'true' and parts[0] != 'false':
      exit('JS datum part[0] must be true or false')
    if not self.depressed and parts[0] == 'false':
      exit('JS double release')

    self.stick_x = float(parts[1])
    self.stick_y = float(parts[2])
    if not self.depressed and parts[0] == 'true':
      if self.on_press:
        self.on_press(self.stick_x, self.stick_y)
      self.depressed = True
    if self.depressed and parts[0] == 'false':
      if self.on_release:
        self.on_release(self.stick_x, self.stick_y)
      self.depressed = False
    if self.depressed and parts[0] == 'true':
      if self.on_move:
        self.on_move(self.stick_x, self.stick_y)
      

  def datum_from_TB(self, tx, ty):
    x = tx - self.x
    y = ty - self.y
    self.depressed = True
    self.magnitude = dist(0,0, x,y)/self.r
    if self.magnitude > 1:
      x /= self.magnitude
      y /= self.magnitude
      self.magnitude = 1
    self.stick_x = round(x/self.r, 2)
    self.stick_y = round(y/self.r, 2)
    self.jstk_node.position = (self.x+x, self.y+y)
    #return (str(TYPE_JOYSTICK) + ':' + str(self.index) + ':true,'
    #        + str(self.stick_x) + ',' + str(self.stick_y))
    ctos = CtoS(MSG_TYPES["ControlPacket"], 0, 0, ControlPacket
                   (self.elem_id, ControlDatum(DATUM_TYPES["Move"], self.stick_x, -self.stick_y)))
    return ctos.to_bytes()
  
    
  
  def datum_from_TM(self, tx, ty):
    return self.datum_from_TB(tx, ty)

  def datum_from_TE(self, tx, ty):
    self.depressed = False
    self.magnitude = 0
    self.stick_x = 0
    self.stick_y = 0
    self.jstk_node.position = (self.x, self.y)
    ctos = CtoS(MSG_TYPES["ControlPacket"], 0, 0, ControlPacket
                   (self.elem_id, ControlDatum(DATUM_TYPES["Move"], self.stick_x, -self.stick_y)))
    return ctos.to_bytes()

# datum: element type, element index,


'''
TestController = CtlrCfg([Button(0, 0,   600/3, 400/2),
                          Button(0, 400/2, 600/3, 400)],
                         [JoyStick(600*2/3, 400*1/2, 400*1/2)])
'''




maybe_event_later ='''
class Event:
  def __init__(self, etype, subtype, press, release, x, y):
    self.etype = etype
    self.subtype = subtype
    self.press = press
    self.release = release
    self.x = x
    self.y = y
'''    



# File IO
'''
def RequestCtlrCfg(ctlrcfg):
  # ipc to the dedicated ctl_serv process
  with Locked('cc0'):
    f = open('newcfg', 'w')
    f.write(ctlrcfg.to_str())
    f.close()

def CheckForNewCtlrCfg():
  ret = None
  with Locked('cc0'):
    f = open('newcfg')
    q = f.read()
    if len(q):
      ret = CtlrCfg.from_str(q)
    f.close()
    f = open('newcfg', 'w')
    f.close()
  return ret

def GetCtlrCfgDatums():
  # ipc from the dedicated ctl_serv process
  datums = []
  with Locked('cc0'):
    f = open('io')
    datums = f.read().split('\n')[:-1]
    f.close()
    f = open('io', 'w')
    f.close()
  return datums

def WriteDatums(datums):
  with Locked('cc0'):
    f = open('io', 'a')
    for d in datums:
      f.write(d+'\n')

def ReadDims():
  with Locked('cc0'):
    f = open('ctlpads')
    parts = f.read().strip().split(',')
    f.close()
    return float(parts[0]), float(parts[1])
  

def WriteDims(w, h):
  with Locked('cc0'):
    f = open('ctlpads', 'w')
    f.write(str(w)+','+str(h)+'\n')
    f.close()
'''
