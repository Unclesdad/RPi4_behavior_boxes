import numpy as np
# import matplotlib.pyplot as plt
from pathlib import Path
import readSGLX
import sys

# Add project root directory to sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from video_acquisition import irig_h_gpio


binFile = Path('/Users/charlie/Documents/code/RPi4_behavior_boxes/irig_decoding/irig_20250708/run0_g0/run0_g0_t0.nidq.bin')
meta = readSGLX.readMeta(binFile)
sampleRate = readSGLX.SampRate(meta)
nChan = int(meta['nSavedChans'])
nSamples = int(int(meta['fileSizeBytes']) / (2 * nChan))
firstSamp = 0
lastSamp = nSamples - 1  # sample ix is 0-indexed but ExtracDigital is inclusive

rawData = readSGLX.makeMemMapRaw(binFile, meta)
digArray = readSGLX.ExtractDigital(rawData, firstSamp, lastSamp, 0, [5], meta)
digArray = np.squeeze(digArray)

boolean_list = digArray.astype(bool).tolist()

full_decoded = irig_h_gpio.decode_full_measurement(boolean_list)
for timestamp in full_decoded:
    print(timestamp)

stdev = 0
avg_error = 0
length = len(full_decoded)

for duple in full_decoded:
    stdev += (abs(duple[1] - duple[0]) / length)
    avg_error += ((duple[1] - duple[0]) / length)

print(f"standard deviation: {stdev}\naverage error: {avg_error}")
# plt.plot(digArray[:int(sampleRate * 20)])  # plot first 20 seconds
# plt.show()
