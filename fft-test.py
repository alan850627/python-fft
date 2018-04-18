"""PyAudio Example: Play a wave file."""

import wave
import sys
import config
import signals
import numpy as np

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
    mask = freq>0

    spectre = spectre[mask]
    freq = freq[mask]

    for i in range(0,len(freq)):
      print(freq[i], abs(spectre[i]))    

    print("")

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