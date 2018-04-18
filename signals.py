
import numpy as np 
import math
import copy
import config
import math
import sys
from collections import deque

class Line(object):
  def __init__(self,in_channel,out_channel,amp,dly):
    self.in_channel = in_channel
    self.out_channel = out_channel
    self.amp = amp
    self.dly = dly
    self.queue_size = math.ceil(float(dly)/config.CHUNK) + 1
    self.sample_pt = (self.queue_size-1) * config.CHUNK - dly
    self.mem = deque([[0] * config.CHUNK for i in range(0,self.queue_size)])

  def process(self,data):
    # Input here should be an array like object.
    if (len(self.mem) >= self.queue_size):
      self.mem.popleft()
    self.mem.append(copy.deepcopy(data))
    
    out = []
    for i in range(self.sample_pt, config.CHUNK + self.sample_pt):
      out.append(self.amp*self.mem[int(i/config.CHUNK)][i%config.CHUNK])

    return out

  def delay(self, amt=1):
    self.dly += amt
    self.sample_pt -= amt

    if (self.sample_pt < config.CHUNK/float(2)):
      self.queue_size += 1
      self.mem.appendleft([0]*config.CHUNK)
      self.sample_pt += config.CHUNK

  def expedite(self, amt=1):
    self.dly -= amt
    self.sample_pt += amt

    if (self.sample_pt > config.CHUNK*(self.queue_size - 1)): 
      print("OOPS BECOMING NON-CAUSAL!!!!")
      sys.exit(1)


class SineWave(object):
  get_pt_size = 0
  get_sine_pt = 0
  def __init__(self,PERIOD):
    self.get_pt_size = 2*math.pi/PERIOD
    self.get_sine_pt = 0

  def get(self,AMP):
    out = []
    for i in range(0, config.CHUNK):
      out.append(int(math.sin(self.get_sine_pt) * AMP))
      self.get_sine_pt = self.get_sine_pt + self.get_pt_size
      if (self.get_sine_pt >= math.pi * 2):
        self.get_sine_pt -= (math.pi * 2)
    
    return out

class HighPass(object):
  previous_filtered = []
  previous_raw = []
  alpha = 0.8;
  def __init__(self):
    self.previous_filtered = [0 for i in range (config.CHUNK)]
    self.previous_raw = [0 for i in range (config.CHUNK)]

  def process(self,data):
    filtered = []
    filtered.append(int(self.alpha * (self.previous_filtered[config.CHUNK - 1] + data[0] - self.previous_raw[config.CHUNK - 1])))
    for j in range(1, config.CHUNK):
      filtered.append(int(self.alpha * (filtered[j-1] + data[j] - data[j-1])))

    self.previous_filtered = copy.deepcopy(filtered)
    self.previous_raw = copy.deepcopy(data)
    return filtered

class Record(object):
  mem = []
  play_pt = 0
  def __init__(self):
    self.mem = []
    self.play_pt = 0

  def record(self,data):
    self.mem.append(copy.deepcopy(data))

  def get(self):
    data = copy.deepcopy(self.mem[self.play_pt])
    self.play_pt = (self.play_pt + 1) % len(self.mem)
    return data


# Helper Functions
def encode(data):
  encoded = bytes([])
  for i in range(0, config.CHUNK):
    for j in range(0, config.CHANNELS):
      encoded = encoded + int_to_bytes(data[j][i], config.WIDTH)

  return encoded

def decode(data):
  decoded = [[] for y in range(config.CHANNELS)] 
  for i in range(0, int(config.CHUNK * config.CHANNELS * config.WIDTH), config.WIDTH * config.CHANNELS):
    for j in range(0, config.CHANNELS):
      decoded[j].append(int.from_bytes(data[i+j*config.WIDTH:i+j*config.WIDTH+config.WIDTH], byteorder='little', signed=True))
  # return high_pass(decoded, CHANNELS, CHUNK)
  return decoded

def int_to_bytes(x, WIDTH):
    return int(x).to_bytes(WIDTH, 'little', signed=True)

def rms(y):
  y = np.array(y)
  return np.sqrt(np.mean(y**2))