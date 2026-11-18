import queue
import sys, time, array, cv2, numpy, threading
sys.path.append('../../Loaf/Programs/USB-CAN Card')
from mcp2515 import MCP2515, open_first_mcp2210

#Bus config
CS_PIN = 3
INT_PIN = 4
OSC_HZ = 16_000_000
BITRATE = 500_000        # was 1 Mbps ("whichever worked") in mainLoaf.py
CONVEYOR_ID = 0x12         # extended ID used by the old sendCANMessage()
txBuf = array.array("B", [0,0,0,0,0,0,0,0])

can = None
_queue = queue.Queue(maxsize=64)
_thread = None

#Initialize CAN
def init() -> bool:
    global can, _thread
    if can is not None:
        return True
    try:
        mcp = open_first_mcp2210()
        can = MCP2515(mcp, cs_pin=CS_PIN, int_pin=INT_PIN,
                       osc_hz=OSC_HZ, bitrate=BITRATE)
        can.set_mode(MCP2515.MODE_NORMAL)
    except Exception as e:
        can = None
        print(f"CAN init failed, running without CAN: {e}")
        return False

    _thread = threading.Thread(target=_worker, name="can-tx", daemon=True)
    _thread.start()
    print(f"CAN ready at {BITRATE} bps")
    return True

def shutdown():
    if _thread is not None:
        _queue.put(None)
        _thread.join(timeout=1.0)

def _worker():
    while True:
        item = _queue.get()
        if item is None:
            break
        can_id, payload, extended = item
        try:
            _can.send(can_id, payload, extended=extended)
            print(f"Sent CAN 0x{can_id:X}: {payload.hex(' ').upper()}")
        except TimeoutError as e:
            print(f"CAN send timed out: {e}")
        except Exception as e:
            print(f"Error sending CAN message: {e}")

class Raw:
    def read(address, mode, pin, bulkPins):

        #Error checking and display
        if mode > 3 or mode < 0:
            print("ERORR: Invalid mode bits set!")
            return -1

        if (pin > 15 or pin < 0) and mode != 2:
            print("ERROR: Invalid pin bits set!")
            return -1

        #Byte setup
        txBuf[0] = 0

        if mode != 2:
            txBuf[0] = pin + (mode << 4)


        if mode == 2:
            txBuf[0] = (mode << 4)
            txBuf[2] = bulkPins & 0b0000000011111111
            txBuf[3] = (bulkPins & 0b1111111100000000) >> 8
        else:
            txBuf[2] = 0; txBuf[3] = 0;

        #Set unnessecary bytes to zero
        txBuf[1] = 0; txBuf[4] = 0; txBuf[5] = 0; txBuf[6] = 0; txBuf[7] = 0;
        #print(bin(txBuf[0]))
        can.send(address, txBuf, extended = True)

    def write(address, mode, pin, bulkPins, data, duty):

        #Error checking and display
        if mode > 3 or mode < 0:
            print("ERORR: Invalid mode bits set!")
            return -1

        if (pin > 15 or pin < 0):
            print("ERROR: Invalid pin bits set!")
            return -1

        if mode == 0 and data > 4095:
            print("ERROR: Invalid data segment for analog write!")
            return -1

        if duty > 255:
            print("ERROR: Invalid duty cycle (0-255)")
            return -1

        #Byte setup
        txBuf[0] = 0

        if mode != 2:
            txBuf[0] = pin + (mode << 4) + (1 << 6)


        if mode == 2:
            txBuf[0] = (mode << 4) + (1 << 6)
            txBuf[3] = bulkPins & 0b0000000011111111
            txBuf[2] = (bulkPins & 0b1111111100000000) >> 8
        else:
            txBuf[2] = 0; txBuf[3] = 0;

        #Set unnessecary bytes to zero
        txBuf[1] = 0; txBuf[4] = duty; txBuf[5] = (data & 0b111111110000000000000000) >> 16; txBuf[6] = (data & 0b000000001111111100000000) >> 8; txBuf[7] = (data & 0b000000000000000011111111);
        #print(bin(txBuf[0]))
        can.send(address, txBuf, extended = True)

        return 1

class Write:
    def analog(address, pin, value):
        Raw.write(address, 0, pin, 0, value, 0)

    def digital(address, pin, value):
        Raw.write(address, 1, pin, 0, value, 0)

    def bulkDigi(address, pins, values):
        Raw.write(address, 2, 0, pins, values, 0)

    def pwm(address, pin, value, duty):
        Raw.write(address, 3, pin, 0, value, duty)

class Read:
    def analog(address, pin):
        Raw.read(address, 0, pin, 0)

    def digital(address, pin):
        Raw.read(address, 1, pin, 0)

    def bulkDigi(address, pins):
        Raw.read(address, 2, 0, pins)

    def pwm(address, pin, value):
        Raw.read(address, 3, pin, 0)

