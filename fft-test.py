"""PyAudio Example: Play a wave file."""

import wave
import sys
import config
import signals
import numpy as np
import cmath

if len(sys.argv) < 3:
  print("Plays a wave file.\n\nUsage: %s filename.wav out.wave" % sys.argv[0])
  sys.exit(-1)

wf = wave.open(sys.argv[1], 'rb')


# read data
data = wf.readframes(config.CHUNK)
frames = []

# play stream (3)
while len(data) > 0:
  decoded = signals.decode(data)

  # FFT HERE!
  spectre = np.fft.fft(decoded[0])
  freq = np.fft.fftfreq(spectre.size, 1/float(config.RATE))

  for i in range(1,int(spectre.size/2)):
    polar = cmath.polar(spectre[i])
    newAmp = polar[0]/2
    newPhase = polar[1]+3.141592653589

    # a[0] should contain the zero frequency term,
    # a[1:n//2] should contain the positive-frequency terms,
    # a[n//2 + 1:] should contain the negative-frequency terms, in increasing order starting from the most negative frequency.
    # Negative frequency terms are simply conjugates of the positive ones.
    spectre[i] = cmath.rect(newAmp, newPhase)
    spectre[spectre.size-i] = np.conj(spectre[i])

  # Get rid of very small complex components that probably result from 
  # not so precise calculations in python's part.
  decoded = [np.real(np.fft.ifft(spectre))]

  # Append into WAVE to use later.
  encoded = signals.encode(decoded)
  frames.append(encoded)
  data = wf.readframes(config.CHUNK)

waveFile = wave.open(sys.argv[2], 'wb')
waveFile.setnchannels(config.CHANNELS)
waveFile.setsampwidth(config.WIDTH)
waveFile.setframerate(config.RATE)
waveFile.writeframes(b''.join(frames))
waveFile.close()