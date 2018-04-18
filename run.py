import csv 
import sys
import config
import signals
import pyaudio
import time
import numpy as np
import cmath
from bisect import bisect_left

if len(sys.argv) < 2:
  print("* Runs noise cancellation device. \n* Usage: %s table.csv" % sys.argv[0])
  print("* table.csv need to have FREQ,AMP_MULT,DLY,PHASE as table header.")
  print("* Rows are sorted in ascending order by frequency.")
  sys.exit(-1)

f = open(sys.argv[1], 'r')
reader = csv.reader(f)

# Build the lookup table in lists, probably faster.
FREQ_LIST = []
AMP_LIST = []
PHASE_LIST = []
FREQ_BUCKETS = np.fft.fftfreq(config.CHUNK, 1/float(config.RATE))
BUCKET_STEP = FREQ_BUCKETS[1] - FREQ_BUCKETS[0]

# Skip the header
next(reader)
for row in reader:
  FREQ_LIST.append(float(row[0]))
  AMP_LIST.append(float(row[1]))
  PHASE_LIST.append(float(row[3]))

p = pyaudio.PyAudio()

def find_closest(myList, myNumber, reset=False):
  pos = bisect_left(myList, myNumber)
  if pos >= len(myList) - 2:
    return len(myList) - 2
  return pos


def interpolate(leftX, rightX, leftY, rightY, X):
  if (leftX > X):
    return leftY
  if (X > rightX):
    return rightY
  return float(rightY-leftY)/(rightX-leftX)*(X-leftX)+leftY

# Given the frequency, and the FFT data, calculate new data based on lookup table.
# returns a pair (amp, phase)
def table_lookup(freq, reset=False):
  pos = find_closest(FREQ_LIST, freq, reset)
  leftF = FREQ_LIST[pos]
  rightF = FREQ_LIST[pos+1]
  amp_mul = interpolate(leftF, rightF, AMP_LIST[pos], AMP_LIST[pos+1], freq)
  phase_dly = interpolate(leftF, rightF, PHASE_LIST[pos], PHASE_LIST[pos+1], freq)
  return amp_mul, phase_dly


def callback(data, frame_count, time_info, status):
  decoded = signals.decode(data)
  noise = decoded[config.CH_NOISE_MIC]
  out = [[0]*config.CHUNK for i in range(0,config.CHANNELS)]

  # FFT HERE!
  spectre = np.fft.fft(noise)
  newSpectre = spectre
  for i in range(1,int(config.CHUNK/2)):
    polar = cmath.polar(spectre[i])
    amp_mul, phase_dly = table_lookup(FREQ_BUCKETS[i])
    newAmp = polar[0] * amp_mul
    newPhase = polar[1] + phase_dly

    # Somehow the signal clips a lot
    if newAmp > 2**(config.WIDTH * 8 - 1):
      newAmp = 2**(config.WIDTH * 8 - 1) * np.sign(newAmp)

    # a[0] should contain the zero frequency term,
    # a[1:n//2] should contain the positive-frequency terms,
    # a[n//2 + 1:] should contain the negative-frequency terms, in increasing order starting from the most negative frequency.
    # Negative frequency terms are simply conjugates of the positive ones.
    comp = cmath.rect(newAmp, newPhase)
    newSpectre[i] = comp
    newSpectre[config.CHUNK-i] = np.conj(comp)

  # Get rid of very small complex components that probably result from 
  # not so precise calculations in python's part.
  out[config.CH_CANCEL_SPK] = np.real(np.fft.ifft(newSpectre))

  return (signals.encode(out), pyaudio.paContinue)

stream = p.open(format=p.get_format_from_width(config.WIDTH),
                channels=config.CHANNELS,
                rate=config.RATE,
                frames_per_buffer=config.CHUNK,
                input=True,
                output=True,
                stream_callback=callback)

stream.start_stream()

while True:
  time.sleep(0.1)

stream.stop_stream()
stream.close()

p.terminate()
f.close()