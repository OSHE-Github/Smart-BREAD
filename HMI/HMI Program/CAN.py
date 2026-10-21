"""
CAN interface for the Bread HMI (main.py).

main.py only ever calls:
    CAN.init()                       # once at startup (CAN.sanity() is an alias)
    CAN.send_conveyor(speed, dir)    # on button presses
    CAN.shutdown()                   # optional, on exit

All SPI traffic to the MCP2515 happens on one background thread, so a slow or
un-ACKed frame (MCP2515.send can block up to 0.5 s) never freezes the UI.
If no CAN hardware is found, the HMI still runs and sends are just dropped.
"""
import queue
import sys, time, array, cv2, numpy, threading
sys.path.append('../../Loaf/Programs/USB-CAN Card')
from mcp2515 import MCP2515, open_first_mcp2210

# ---- bus configuration ----
CS_PIN = 4
INT_PIN = 3
OSC_HZ = 16_000_000
BITRATE = 1_000_000        # was 1 Mbps ("whichever worked") in mainLoaf.py
CONVEYOR_ID = 0x12         # extended ID used by the old sendCANMessage()

_can = None
_queue = queue.Queue(maxsize=64)
_thread = None


def init() -> bool:
    """Open the MCP2210/MCP2515, enter normal mode, start the TX thread.
    Returns True if the bus is ready. Safe to call more than once."""
    global _can, _thread
    if _can is not None:
        return True
    try:
        mcp = open_first_mcp2210()
        _can = MCP2515(mcp, cs_pin=CS_PIN, int_pin=INT_PIN,
                       osc_hz=OSC_HZ, bitrate=BITRATE)
        _can.set_mode(MCP2515.MODE_NORMAL)
    except Exception as e:
        _can = None
        print(f"CAN init failed, running without CAN: {e}")
        return False

    _thread = threading.Thread(target=_worker, name="can-tx", daemon=True)
    _thread.start()
    print(f"CAN ready at {BITRATE} bps")
    return True


sanity = init  # main.py's multithreaded branch calls CAN.sanity()


def send(can_id: int, data, extended: bool = True):
    """Queue a frame for transmission (non-blocking). Data is padded to 8 bytes."""
    if _can is None:
        return
    payload = bytes(b & 0xFF for b in data)[:8]
    payload = payload.ljust(8, b"\x00")
    try:
        _queue.put_nowait((can_id, payload, extended))
    except queue.Full:
        print("CAN TX queue full, dropping frame")


def send_conveyor(speed: int, direction: int):
    """byte 0 = speed (0-100), byte 1 = direction (1 = right, 0xFF = left, 0 = none)."""
    send(CONVEYOR_ID, [speed, direction])  # & 0xFF in send() turns -1 into 0xFF


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