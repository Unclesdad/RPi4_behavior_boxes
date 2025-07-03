from typing import List
# import pigpio
import time
from datetime import datetime as dt
import datetime

# Constants for timecode sending
SENDING_GPIO_PIN = 6 
SENDING_BIT_LENGTH = 1 # in seconds

# Constants for timecode measuring
DECODE_BIT_PERIOD = 1 / 25000 # for now frame rate is 25 kHz
# pulse length thresholds (in seconds)
P_THRESHOLD = 0.75 * SENDING_BIT_LENGTH # for pulse length of 0.8b
ONE_THRESHOLD = 0.45 * SENDING_BIT_LENGTH # for pulse length of 0.5b

# Weights for the encoding values in an IRIG timecode
SECONDS_WEIGHTS = [1, 2, 4, 8, 10, 20, 40]
MINUTES_WEIGHTS = [1, 2, 4, 8, 10, 20, 40]
HOURS_WEIGHTS = [1, 2, 4, 8, 10, 20]
DAY_OF_YEAR_WEIGHTS = [1, 2, 4, 8, 10, 20, 40, 80, 100, 200]
DECISECONDS_WEIGHTS = [1, 2, 4, 8]
YEARS_WEIGHTS = [1, 2, 4, 8, 10, 20, 40, 80]

# Connect to pigpio daemon
pi = pigpio.pi()
if not pi.connected:
    raise RuntimeError("Could not connect to pigpio daemon. Is 'pigpiod' running?")

pi.set_mode(GPIO_PIN, pigpio.OUTPUT)

def bcd_encode(value, weights):
    """
    Encodes an integer value into Binary Coded Decimal (BCD) format using specified weights.
    """
    bcd_list = [0] * len(weights)
    for i in reversed(range(len(weights))):
        if weights[i] <= value:
            bcd_list[i] = 1
            value -= weights[i]
    return bcd_list

def bcd_decode(binary, weights):
    """
    Decodes a Binary Coded Decimal (BCD) format using a dot product with the binary list and the weights.
    """
    total = 0
    for weight, bit in zip(weights, binary):
        total += bit * weight
    return total


def generate_irig_h_frame():
    """
    Generates a 60-bit IRIG-H timecode list based on the provided image's bit assignments.
    Includes seconds, minutes, hours, day of year, tenths of seconds, and year.
    'P' is used for position identifiers.
    """
    now = dt.now() # Get the current local time

    seconds_bcd = bcd_encode(now.second, SECONDS_WEIGHTS)
    minutes_bcd = bcd_encode(now.minute, MINUTES_WEIGHTS)
    hours_bcd = bcd_encode(now.hour, HOURS_WEIGHTS)
    day_of_year_bcd = bcd_encode(now.timetuple().tm_yday, DAY_OF_YEAR_WEIGHTS)
    deciseconds_bcd = bcd_encode(now.microsecond // 100000, DECISECONDS_WEIGHTS)
    year_bcd = bcd_encode(now.year % 100, YEARS_WEIGHTS)

    irig_h_list = []

    # i had to write this all manually bc chatgpt is too stupid to do it i guess

    # Bit 00: Pr (Frame marker)
    irig_h_list.append('P')

    # Bits 01-04: Seconds (Units) - Weights: 1, 2, 4, 8
    irig_h_list.extend(seconds_bcd[0:4])
    # Bit 05: Unused (0)
    irig_h_list.append(0)
    # Bits 06-08: Seconds (Tens) - Weights: 10, 20, 40
    irig_h_list.extend(seconds_bcd[4:7])

    # Bit 09: P1 (Position identifier)
    irig_h_list.append('P')

    # Bits 10-13: Minutes (Units) - Weights: 1, 2, 4, 8
    irig_h_list.extend(minutes_bcd[0:4])
    # Bit 14: Unused (0)
    irig_h_list.append(0)
    # Bits 15-17: Minutes (Tens) - Weights: 10, 20, 40
    irig_h_list.extend(minutes_bcd[4:7])
    # Bit 18: Unused (0)
    irig_h_list.append(0)

    # Bit 19: P2 (Position identifier)
    irig_h_list.append('P')

    # Bits 20-23: Hours (Units) - Weights: 1, 2, 4, 8
    irig_h_list.extend(hours_bcd[0:4])
    # Bir 24: Unused (0)
    irig_h_list.append(0)
    # Bits 25-26: Hours (Tens) - Weights: 10, 20
    irig_h_list.extend(hours_bcd[4:6]) # Only 2 bits for tens (10, 20)
    # Bit 27-28: Unused (0)
    irig_h_list.extend([0,0])

    # Bit 29: P3 (Position identifier)
    irig_h_list.append('P')

    # Bits 30-33: Day of year (Units) - Weights: 1, 2, 4, 8
    irig_h_list.extend(day_of_year_bcd[0:4])
    # Bit 34: Unused (0)
    irig_h_list.append(0)
    # Bits 35-38: Day of year (Tens) - Weights: 10, 20, 40, 80
    irig_h_list.extend(day_of_year_bcd[4:8])
    # Bit 39: P4 (Position identifier)
    irig_h_list.append('P')
    # Bits 40-41: Day of year (Hundreds) - Weights: 100, 200
    irig_h_list.extend(day_of_year_bcd[8:10])

    # Bits 42-44: Unused (0)
    irig_h_list.extend([0,0,0])

    # Bits 45-48: Deciseconds - Weights: 1, 2, 4, 8
    irig_h_list.extend(deciseconds_bcd[0:4])

    # Bit 49: P5 (Position identifier)
    irig_h_list.append('P')

    # Bits 50-53: Years (Units) - Weights: 1, 2, 4, 8
    irig_h_list.extend(year_bcd[0:4])
    # Bit 54: Unused (0)
    irig_h_list.append(0)
    # Bit 55-58: Years (Tens) - Weights: 10, 20, 40, 80
    irig_h_list.extend(year_bcd[4:8])

    # Bit 59: P6 (Position identifier)
    irig_h_list.append('P')

    return irig_h_list

def send_irig_h_frame(frame):
    """
    Sends a full IRIG-H timecode through the GPIO pin.
    """
    for i, bit in enumerate(frame):
        # print bit info
        if bit == 'P':
            print(f"Bit {i:02d}: P")
            pi.write(SENDING_GPIO_PIN, 1)
            time.sleep(SENDING_BIT_LENGTH * 0.8)
            pi.write(SENDING_GPIO_PIN, 0)
            time.sleep(SENDING_BIT_LENGTH * 0.2)
        elif bit == 1:
            print(f"Bit {i:02d}: 1")
            pi.write(SENDING_GPIO_PIN, 1)
            time.sleep(SENDING_BIT_LENGTH * 0.5)
            pi.write(SENDING_GPIO_PIN, 0)
            time.sleep(SENDING_BIT_LENGTH * 0.5)
        else:
            print(f"Bit {i:02d}: 0")
            pi.write(SENDING_GPIO_PIN, 1)
            time.sleep(SENDING_BIT_LENGTH * 0.2)
            pi.write(SENDING_GPIO_PIN, 0)
            time.sleep(SENDING_BIT_LENGTH * 0.8)

def decode_to_irig_h(binary_list: List[bool]) -> List:
    """
    Decodes a sample of measured electrical signals into an list-represented IRIG-H frame.
    """
    pulse_length_list = []
    length = 0
    for i in binary_list:
        if i:
            length += DECODE_BIT_PERIOD
        elif length == 0:
            continue
        else:
            pulse_length_list.append(length)
            length = 0
                
    def identify_pulse_length(length):
        if length > P_THRESHOLD:
            return 'P'
        if length > ONE_THRESHOLD:
            return 1
        else:
            return 0

    return [identify_pulse_length(length) for length in pulse_length_list]

def irig_h_to_datetime(irig_list):
    """
    Converts a list-represented IRIG-H frame into a Unix timecode (Measured in milliseconds since 00:00:00 UTC, January 1st, 1970)
    Since IRIG does not encode century, this code assumes that the IRIG timecode is being sent in the same century as when this function is called.
    """
    seconds = bcd_decode(irig_list[1:5], SECONDS_WEIGHTS[0:4]) + bcd_decode(irig_list[6:9], SECONDS_WEIGHTS[4:7])
    minutes = bcd_decode(irig_list[10:14], MINUTES_WEIGHTS[0:4]) + bcd_decode(irig_list[15:18], MINUTES_WEIGHTS[4:7])
    hours = bcd_decode(irig_list[20:24], HOURS_WEIGHTS[0:4]) + bcd_decode(irig_list[25:27], HOURS_WEIGHTS[4:6])
    day_of_year = bcd_decode(irig_list[30:34], DAY_OF_YEAR_WEIGHTS[0:4]) + bcd_decode(irig_list[35:39], DAY_OF_YEAR_WEIGHTS[4:8]) + bcd_decode(irig_list[40:42], DAY_OF_YEAR_WEIGHTS[8:10])
    deciseconds = bcd_decode(irig_list[45:49], DECISECONDS_WEIGHTS)
    year = bcd_decode(irig_list[50:54], YEARS_WEIGHTS[0:4]) + bcd_decode(irig_list[55:59], YEARS_WEIGHTS[4:8]) + (dt.now().year // 100) * 100 # add in century
    return dt.combine(datetime.date(year, 1, 1) + datetime.timedelta(days=(day_of_year - 1)), datetime.time(hours, minutes, seconds, deciseconds * 10_000))

def irig_h_to_unix(irig_list):
    return irig_h_to_datetime(irig_list).timestamp()
    
def generate_and_send_irig_h(): 
    """
    Generates a full IRIG-H frame for when this is called, then sends it over the course of a frame interval
    """
    frame = generate_irig_h_frame()
    send_irig_h_frame(frame)
    print(f"Frame complete; restarting next {SENDING_BIT_LENGTH * 60 * 1000} milliseconds...")

def finish():
    """
    Something to run when no more timecodes are being sent
    """
    pi.write(SENDING_GPIO_PIN, 0)
    pi.stop()