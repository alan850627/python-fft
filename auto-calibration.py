
import config
import pyaudio
import time
import signals
import sys
import math
import numpy as np
from avg import RunningAvg
from enum import Enum

class state(Enum):
  STARTED = 0
  RECORD_NOISE = 1
  RECORD_NOISE_DONE = 2
  PLAY_NOISE = 3
  MATCH_PLAYBACK = 5
  MATCH_PLAYBACK_DONE = 6
  MEASURE_BOTH_INIT = 7
  MEASURE_BOTH = 8
  DELAY_SPEAKER = 9
  EXPEDITE_SPEAKER = 10
  DONE = 11

FILE_NAME = 'out.csv'
if len(sys.argv) >= 2:
  FILE_NAME = sys.argv[1]
with open(FILE_NAME, 'w') as the_file:
  the_file.write('FREQ,AMP_MULT,DLY,PHASE\n')

COUNTER = 0
ALTERNATE_COUNTER = 0
MIN_SOUND = 0
CUR_SOUND = 0
STATE = state.STARTED
NEXT_STATE = state.DELAY_SPEAKER

FREQ_BUCKETS = np.fft.fftfreq(config.CHUNK, 1/float(config.RATE))
BUCKET_STEP = FREQ_BUCKETS[1] - FREQ_BUCKETS[0]
print("Frequency Bucket Step: %f" %BUCKET_STEP)
FREQ_BUCKET_PT = config.START_BUCKET
FREQ = FREQ_BUCKETS[FREQ_BUCKET_PT]
SILENCE = [0 for i in range(0, config.CHUNK)]

NOISE_RMS = 0
SPK_RMS = 0
PREV_SOUND = 0
SPK_MULT = config.SPK[0]
SPK_DLY = config.SPK[1]

sine = signals.SineWave(config.RATE/float(FREQ))
hp = signals.HighPass()
avg = RunningAvg(10)
recording = signals.Record()
p = pyaudio.PyAudio()
line = 0

print(STATE)

######################################################
#                                                    #
# [ch1_spk] --> [ch1_mic]    [ch2_mic] <-- [ch2_spk] #
#                   |                          |     #
#                   |_------>[computer]------>_|     #
#                                                    #
######################################################
def get_avg(data):
  return avg.get(signals.rms(hp.process(data)))

def callback(data, frame_count, time_info, status):
  global COUNTER
  global ALTERNATE_COUNTER
  global MIN_SOUND
  global CUR_SOUND
  global STATE
  global NEXT_STATE
  global FREQ
  global FREQ_BUCKET_PT
  global SILENCE

  global NOISE_RMS
  global SPK_RMS
  global PREV_SOUND
  global SPK_MULT
  global SPK_DLY

  global sine
  global hp
  global avg
  global recording
  global p
  global line

  out = bytes([])
  de = signals.decode(data)
  head_data = de[config.CH_HEAD_MIC]
  noise_data = de[config.CH_NOISE_MIC]

  if (STATE == state.STARTED):
    MIN_SOUND = get_avg(head_data)
    out = signals.encode([SILENCE, SILENCE])
    if (COUNTER > 20):
      STATE = state.PLAY_NOISE
      COUNTER = 0
      print(STATE)

  elif (STATE == state.PLAY_NOISE):
    noise = sine.get(config.NOISE[0])
    out_arr = [[] for i in range(0,2)]
    out_arr[config.CH_CANCEL_SPK] = SILENCE
    out_arr[config.CH_NOISE_SPK] = noise
    out = signals.encode(out_arr)

    if (COUNTER > 10):
      STATE = state.RECORD_NOISE
      COUNTER = 0
      avg = RunningAvg(25)
      hp = signals.HighPass()
      print(STATE)

  elif (STATE == state.RECORD_NOISE):
    recording.record(noise_data)
    NOISE_RMS = get_avg(head_data)
    noise = sine.get(config.NOISE[0])
    out_arr = [[] for i in range(0,2)]
    out_arr[config.CH_CANCEL_SPK] = SILENCE
    out_arr[config.CH_NOISE_SPK] = noise
    out = signals.encode(out_arr)

    if (COUNTER > 50):
      print("noise RMS: %f" % NOISE_RMS)
      STATE = state.RECORD_NOISE_DONE
      COUNTER = 0
      print(STATE)

  elif (STATE == state.RECORD_NOISE_DONE):
    recorded_noise = recording.get()
    recorded_noise = [int(i * SPK_MULT) for i in recorded_noise]
    out_arr = [[] for i in range(0,2)]
    out_arr[config.CH_CANCEL_SPK] = recorded_noise
    out_arr[config.CH_NOISE_SPK] = SILENCE
    out = signals.encode(out_arr)

    if (COUNTER > 10):
      STATE = state.MATCH_PLAYBACK
      avg = RunningAvg(5)
      hp = signals.HighPass()
      COUNTER = 0
      print(STATE)

  elif (STATE == state.MATCH_PLAYBACK):
    recorded_noise = recording.get()
    recorded_noise = [int(i * SPK_MULT) for i in recorded_noise]
    out_arr = [[] for i in range(0,2)]
    out_arr[config.CH_CANCEL_SPK] = recorded_noise
    out_arr[config.CH_NOISE_SPK] = SILENCE
    out = signals.encode(out_arr)

    SPK_RMS = get_avg(head_data)

    if (COUNTER > 10):
      COUNTER = 0
      avg = RunningAvg(5)

      if (abs(SPK_RMS-NOISE_RMS) < 10):
        STATE = state.MATCH_PLAYBACK_DONE
        print(STATE)

      # NOT SURE IF GOOD
      elif (SPK_RMS > NOISE_RMS):
        SPK_MULT = SPK_MULT - (SPK_RMS - NOISE_RMS)/10000
      elif (SPK_RMS < NOISE_RMS):
        SPK_MULT = SPK_MULT + (NOISE_RMS - SPK_RMS)/10000

  elif (STATE == state.MATCH_PLAYBACK_DONE):
    ALTERNATE_COUNTER = 0
    COUNTER = 0
    avg = RunningAvg(5)
    hp = signals.HighPass()

    line = signals.Line(
      config.CH_NOISE_MIC,
      config.CH_CANCEL_SPK,
      SPK_MULT,
      SPK_DLY)

    noise = sine.get(config.NOISE[0])
    talkthrough = line.process(noise_data)
    out_arr = [[] for i in range(0,2)]
    out_arr[config.CH_CANCEL_SPK] = talkthrough
    out_arr[config.CH_NOISE_SPK] = noise
    out = signals.encode(out_arr)

    STATE = state.MEASURE_BOTH_INIT
    print(STATE)

  elif (STATE == state.MEASURE_BOTH_INIT):
    PREV_SOUND = get_avg(head_data)

    noise = sine.get(config.NOISE[0])
    talkthrough = line.process(noise_data)
    out_arr = [[] for i in range(0,2)]
    out_arr[config.CH_CANCEL_SPK] = talkthrough
    out_arr[config.CH_NOISE_SPK] = noise
    out = signals.encode(out_arr)

    if COUNTER > 10:
      avg = RunningAvg(5)
      STATE = state.DELAY_SPEAKER
      print(STATE)

  elif (STATE == state.DELAY_SPEAKER):
    NEXT_STATE = state.DELAY_SPEAKER

    dly = 1
    SPK_DLY += dly
    line.delay(dly)

    noise = sine.get(config.NOISE[0])
    talkthrough = line.process(noise_data)
    out_arr = [[] for i in range(0,2)]
    out_arr[config.CH_CANCEL_SPK] = talkthrough
    out_arr[config.CH_NOISE_SPK] = noise
    out = signals.encode(out_arr)

    STATE = state.MEASURE_BOTH

  elif (STATE == state.EXPEDITE_SPEAKER):
    NEXT_STATE = state.EXPEDITE_SPEAKER

    dly = 1
    SPK_DLY -= dly
    line.expedite(dly)

    noise = sine.get(config.NOISE[0])
    talkthrough = line.process(noise_data)
    out_arr = [[] for i in range(0,2)]
    out_arr[config.CH_CANCEL_SPK] = talkthrough
    out_arr[config.CH_NOISE_SPK] = noise
    out = signals.encode(out_arr)

    STATE = state.MEASURE_BOTH

  elif (STATE == state.MEASURE_BOTH):
    CUR_SOUND = get_avg(head_data)
    noise = sine.get(config.NOISE[0])
    talkthrough = line.process(noise_data)
    out_arr = [[] for i in range(0,2)]
    out_arr[config.CH_CANCEL_SPK] = talkthrough
    out_arr[config.CH_NOISE_SPK] = noise
    out = signals.encode(out_arr)

    if COUNTER > 10:
      COUNTER = 0

      if (CUR_SOUND <= MIN_SOUND or ALTERNATE_COUNTER > config.MAX_ALTERNATE_COUNT):
        STATE = state.DONE

      elif (CUR_SOUND < PREV_SOUND):
        STATE = NEXT_STATE
      else:
        ALTERNATE_COUNTER += 1
        if (NEXT_STATE == state.EXPEDITE_SPEAKER):
          STATE = state.DELAY_SPEAKER
        else:
          STATE = state.EXPEDITE_SPEAKER
      print(STATE)
      PREV_SOUND = CUR_SOUND
      avg = RunningAvg(5)

  elif (STATE == state.DONE):
    phase = -float(FREQ)*2*math.pi*SPK_DLY/config.RATE

    with open(FILE_NAME, 'a') as the_file:
      the_file.write('%f,%f,%d,%f\n' % (FREQ,SPK_MULT,SPK_DLY,phase))
    print('%f,%f,%d,%f\n' % (FREQ,SPK_MULT,SPK_DLY,phase))
    COUNTER = 0
    ALTERNATE_COUNTER = 0
    MIN_SOUND = 0
    CUR_SOUND = 0
    FREQ_BUCKET_PT += 1
    FREQ = FREQ_BUCKETS[FREQ_BUCKET_PT]

    sine = signals.SineWave(config.RATE/float(FREQ))
    recording = signals.Record()

    out = signals.encode([SILENCE, SILENCE])
    STATE = state.STARTED


  COUNTER += 1
  return (out, pyaudio.paContinue)

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
