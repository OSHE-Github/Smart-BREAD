import queue
import sys, time, array, cv2, numpy, threading
sys.path.append('../../Loaf/Programs/USB-CAN Card')
from mcp2515 import MCP2515, open_first_mcp2210

#Bus config
CS_PIN = 4
INT_PIN = 3
OSC_HZ = 16_000_000
BITRATE = 1_000_000        # was 1 Mbps ("whichever worked") in mainLoaf.py
CONVEYOR_ID = 0x12         # extended ID used by the old sendCANMessage()
txBuf = array.array("b", [0,0,0,0,0,0,0,0])

canBus = None
_queue = queue.Queue(maxsize=64)
_thread = None


def init() -> bool:
    global canBus, _thread
    if canBus is not None:
        return True
    try:
        mcp = open_first_mcp2210()
        canBus = MCP2515(mcp, cs_pin=CS_PIN, int_pin=INT_PIN,
                       osc_hz=OSC_HZ, bitrate=BITRATE)
        canBus.set_mode(MCP2515.MODE_NORMAL)
    except Exception as e:
        canBus = None
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

#Read a specific pin or range of pins from the input slice. Returns recieved CAN message
def read(address, IO, mode, pin, bulkPins):

    #Error checking and display
    if IO > 3 or IO < 0:
        print("ERORR: Invalid IO bits set!")
        return -1

    if mode > 3 or mode < 0:
        print("ERORR: Invalid mode bits set!")
        return -1

    if pin > 15 or pin < 0:
        print("ERROR: Invalid pin bits set!")
        return -1



    #Byte setup
    txBuf[0] = 0
    txBuf[0] = pin + (mode << 4) + (IO << 6)
    if mode == 2:
        txBuf[2] = bulkPins & 0b0000000011111111
        txBuf[3] = (bulkPins & 0b1111111100000000) >> 8
    else:
        txBuf[2] = 0; txBuf[3] = 0;

    #Set unnessecary bytes to zero
    txBuf[1] = 0; txBuf[4] = 0; txBuf[5] = 0; txBuf[6] = 0; txBuf[7] = 0;

    canBus.send(address, txBuf, extended = True)
    print(b"Sent: {tx_msg}")

    return canBus.recv(timeout=1)
