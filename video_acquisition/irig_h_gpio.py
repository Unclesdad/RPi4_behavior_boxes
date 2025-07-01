import pigpio
import time
from datetime import datetime

GPIO_PIN = 6 

BIT_LENGTH = 1 # in seconds

# Connect to pigpio daemon
pi = pigpio.pi()
if not pi.connected:
    raise RuntimeError("Could not connect to pigpio daemon. Is 'pigpiod' running?")

pi.set_mode(GPIO_PIN, pigpio.OUTPUT)

def bcd_encode(value, bits):
    """Encode a decimal value into a fixed-length BCD boolean list."""
    num_digits = (bits + 3) // 4
    bcd = []
    for digit in reversed(f"{value:0{num_digits}d}"):
        bits4 = [bool(int(b)) for b in f"{int(digit):04b}"]
        bcd = bits4 + bcd
    return bcd[-bits:]

def generate_irig_h_frame():
    frame = [False] * 60

    now = datetime.utcnow()
    seconds   = now.second
    minutes   = now.minute
    hours     = now.hour
    day_of_yr = now.timetuple().tm_yday

    print(f"\nEncoding time (UTC): {now.strftime('%Y-%m-%d %H:%M:%S')} | Day of Year: {day_of_yr}")

    # Position identifiers (every 10th bit)
    for pos in range(0, 60, 10):
        frame[pos] = True

    # BCD fields
    frame[1:9]   = bcd_encode(seconds, 8)
    frame[10:18] = bcd_encode(minutes, 8)
    frame[20:28] = bcd_encode(hours,   8)

    day_bcd = bcd_encode(day_of_yr, 17)      # exactly 17 bits
    hi = day_bcd[:10]                        # first 10 bits
    lo = day_bcd[10:]
    if len(lo) < 9:
        lo += [False] * (9 - len(lo))        # pad to 9 bits
    frame[30:40] = hi
    frame[40:49] = lo

    assert len(frame) == 60, f"Frame is {len(frame)} bits instead of 60"

    # debug print of full frame, marking position bits as P
    def mark_bit(i, b):
        if i % 10 == 0:
            return ' P '
        return '1' if b else '0'

    frame_str = ''.join(mark_bit(i, b) for i, b in enumerate(frame))
    print("IRIG-H Frame:", frame_str)

    return frame

def send_irig_h_frame(frame):
    for i, bit in enumerate(frame):
        # print bit info
        if i % 10 == 0:
            print(f"Bit {i:02d}: P")
            pi.write(GPIO_PIN, 1)
            time.sleep(BIT_LENGTH * 0.8)
            pi.write(GPIO_PIN, 0)
            time.sleep(BIT_LENGTH * 0.2)
        elif bit:
            print(f"Bit {i:02d}: 1")
            pi.write(GPIO_PIN, 1)
            time.sleep(BIT_LENGTH * 0.5)
            pi.write(GPIO_PIN, 0)
            time.sleep(BIT_LENGTH * 0.5)
        else:
            print(f"Bit {i:02d}: 0")
            pi.write(GPIO_PIN, 1)
            time.sleep(BIT_LENGTH * 0.2)
            pi.write(GPIO_PIN, 0)
            time.sleep(BIT_LENGTH * 0.8)

def send_full_irig_h_timecode(): 
    frame = generate_irig_h_frame()
    send_irig_h_frame(frame)
    print(f"Frame complete; restarting next {BIT_LENGTH * 60 * 1000} milliseconds...")
