"""
Minimal MCP2515 CAN controller driver over an MCP2210 USB-to-SPI bridge.

Usage:
    from mcp2210 import Mcp2210
    from mcp2515 import MCP2515, open_first_mcp2210

    mcp = open_first_mcp2210()
    can = MCP2515(mcp, cs_pin=4, int_pin=3, osc_hz=16_000_000, bitrate=500_000)
    can.set_mode(MCP2515.MODE_LISTEN_ONLY)   # safe sniffing
    while True:
        frame = can.recv(timeout=1.0)
        if frame:
            print(frame)
"""
import time
from dataclasses import dataclass, field

import hid
from mcp2210 import Mcp2210, Mcp2210GpioDesignation, Mcp2210GpioDirection
"""
For Windows:
pip install hidapi
pip install mcp2210-python
"""

# SPI instructions
_RESET = 0xC0
_READ = 0x03
_WRITE = 0x02
_BIT_MODIFY = 0x05
_READ_STATUS = 0xA0
_LOAD_TX0 = 0x40      # load TXB0 starting at TXB0SIDH
_RTS_TX0 = 0x81       # request-to-send TXB0
_READ_RX0 = 0x90      # read RXB0 starting at RXB0SIDH (auto-clears RX0IF)
_READ_RX1 = 0x94      # read RXB1 starting at RXB1SIDH (auto-clears RX1IF)

# Registers
_CANSTAT = 0x0E
_CANCTRL = 0x0F
_TEC = 0x1C
_REC = 0x1D
_CNF3 = 0x28
_CNF2 = 0x29
_CNF1 = 0x2A
_CANINTE = 0x2B
_CANINTF = 0x2C
_EFLG = 0x2D
_TXB0CTRL = 0x30
_RXB0CTRL = 0x60
_RXB1CTRL = 0x70

# (oscillator Hz, bitrate) -> (CNF1, CNF2, CNF3)
# 16 time quanta per bit -> 87.5% sample point; 8 quanta -> 75%.
# If the target bus uses a different sample point, adjust CNF2/CNF3 here.
_BIT_TIMING = {
    (8_000_000, 500_000): (0x00, 0x91, 0x01),
    (8_000_000, 250_000): (0x00, 0xAE, 0x01),
    (8_000_000, 125_000): (0x01, 0xAE, 0x01),
    (16_000_000, 1_000_000): (0x00, 0x91, 0x01),
    (16_000_000, 500_000): (0x00, 0xAE, 0x01),
    (16_000_000, 250_000): (0x01, 0xAE, 0x01),
    (16_000_000, 125_000): (0x03, 0xAE, 0x01),
}


@dataclass
class CanFrame:
    can_id: int
    data: bytes = b""
    extended: bool = False
    rtr: bool = False
    timestamp: float = field(default_factory=time.time)

    def __str__(self):
        id_str = f"{self.can_id:08X}" if self.extended else f"{self.can_id:03X}"
        kind = " RTR" if self.rtr else ""
        return f"{id_str} [{len(self.data)}] {self.data.hex(' ').upper()}{kind}"


def encode_id(can_id: int, extended: bool) -> bytes:
    """Return SIDH, SIDL, EID8, EID0 for an identifier."""
    if extended:
        if not 0 <= can_id <= 0x1FFFFFFF:
            raise ValueError("Extended ID must be 29 bits")
        sidh = (can_id >> 21) & 0xFF
        sidl = (((can_id >> 18) & 0x07) << 5) | 0x08 | ((can_id >> 16) & 0x03)
        return bytes([sidh, sidl, (can_id >> 8) & 0xFF, can_id & 0xFF])
    if not 0 <= can_id <= 0x7FF:
        raise ValueError("Standard ID must be 11 bits")
    return bytes([(can_id >> 3) & 0xFF, (can_id & 0x07) << 5, 0, 0])


def decode_frame(buf: bytes) -> CanFrame:
    """Decode 13 bytes: SIDH SIDL EID8 EID0 DLC D0..D7."""
    sidh, sidl, eid8, eid0, dlc = buf[:5]
    extended = bool(sidl & 0x08)
    if extended:
        can_id = (sidh << 21) | ((sidl & 0xE0) << 13) | ((sidl & 0x03) << 16) | (eid8 << 8) | eid0
        rtr = bool(dlc & 0x40)
    else:
        can_id = (sidh << 3) | (sidl >> 5)
        rtr = bool(sidl & 0x10)
    length = min(dlc & 0x0F, 8)
    data = b"" if rtr else bytes(buf[5:5 + length])
    return CanFrame(can_id, data, extended, rtr)


def open_first_mcp2210() -> Mcp2210:
    devices = hid.enumerate(0x04D8, 0x00DE)
    if not devices:
        raise RuntimeError("No MCP2210 found. Is it plugged in?")
    serial = devices[0]["serial_number"]
    if not serial:
        raise RuntimeError("MCP2210 found but not accessible (Linux: install the udev rule, then replug).")
    return Mcp2210(serial_number=serial)


class MCP2515:
    MODE_NORMAL = 0
    MODE_SLEEP = 1
    MODE_LOOPBACK = 2
    MODE_LISTEN_ONLY = 3
    MODE_CONFIG = 4

    def __init__(self, mcp: Mcp2210, cs_pin: int = 4, int_pin: int = 3,
                 osc_hz: int = 16_000_000, bitrate: int = 500_000):
        """int_pin: MCP2210 GP pin wired to the MCP2515 INT output (active low),
        or None to poll the MCP2515 over SPI instead."""
        self.mcp = mcp
        self.cs = cs_pin
        self.int_pin = int_pin
        mcp.set_gpio_designation(cs_pin, Mcp2210GpioDesignation.CHIP_SELECT)
        if int_pin is not None:
            mcp.set_gpio_designation(int_pin, Mcp2210GpioDesignation.GPIO)
            mcp.set_gpio_direction(int_pin, Mcp2210GpioDirection.INPUT)
        mcp.set_spi_mode(0)  # MCP2515 supports SPI mode 0,0 and 1,1
        mcp.configure_spi_timing(chip_select_to_data_delay=0,
                                 last_data_byte_to_cs=0,
                                 delay_between_bytes=0)
        self.reset()
        self.set_bitrate(osc_hz, bitrate)
        # Receive every frame (filters off), let RXB0 roll over into RXB1
        self.write_reg(_RXB0CTRL, 0x64)
        self.write_reg(_RXB1CTRL, 0x60)
        self.write_reg(_CANINTE, 0x03)  # drive INT low while a frame is waiting in RXB0/RXB1
        self.write_reg(_CANINTF, 0x00)

    # ---- low-level SPI ----
    def _xfer(self, data) -> bytes:
        return self.mcp.spi_exchange(bytes(data), cs_pin_number=self.cs)

    def reset(self):
        self._xfer([_RESET])
        time.sleep(0.01)
        stat = self.read_reg(_CANSTAT)
        if stat >> 5 != self.MODE_CONFIG:
            raise RuntimeError(
                f"MCP2515 not responding (CANSTAT=0x{stat:02X}, expected 0x80). "
                "Check CS pin number, MOSI/MISO/SCK wiring, and power.")

    def read_reg(self, addr: int, count: int = 1):
        rx = self._xfer([_READ, addr] + [0] * count)
        return rx[2] if count == 1 else rx[2:]

    def write_reg(self, addr: int, *values: int):
        self._xfer([_WRITE, addr, *values])

    def bit_modify(self, addr: int, mask: int, value: int):
        self._xfer([_BIT_MODIFY, addr, mask, value])

    def read_status(self) -> int:
        return self._xfer([_READ_STATUS, 0])[1]

    # ---- configuration ----
    def set_bitrate(self, osc_hz: int, bitrate: int):
        try:
            cnf1, cnf2, cnf3 = _BIT_TIMING[(osc_hz, bitrate)]
        except KeyError:
            raise ValueError(f"No timing for {osc_hz} Hz crystal at {bitrate} bps. "
                             f"Supported: {sorted(_BIT_TIMING)}")
        self.set_mode(self.MODE_CONFIG)
        self.write_reg(_CNF3, cnf3, cnf2, cnf1)  # CNF3, CNF2, CNF1 are consecutive

    def set_mode(self, mode: int, timeout: float = 0.5):
        self.bit_modify(_CANCTRL, 0xE0, mode << 5)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.read_reg(_CANSTAT) >> 5 == mode:
                return
        raise RuntimeError(f"MCP2515 did not enter mode {mode}")

    # ---- transmit / receive ----
    def send(self, can_id: int, data: bytes = b"", extended: bool = False,
             rtr: bool = False, timeout: float = 0.5):
        data = bytes(data)
        if len(data) > 8:
            raise ValueError("Classic CAN frames carry at most 8 bytes")
        # wait for TXB0 to be free
        deadline = time.monotonic() + timeout
        while self.read_reg(_TXB0CTRL) & 0x08:
            if time.monotonic() > deadline:
                self.bit_modify(_CANCTRL, 0x10, 0x10)   # ABAT: abort pending TX
                self.bit_modify(_CANCTRL, 0x10, 0x00)
                raise TimeoutError(
                    "Previous frame never sent: no other node ACKed it. Check bitrate, "
                    "wiring, termination, and that you're not in listen-only mode.")
        dlc = len(data) | (0x40 if rtr else 0)
        self._xfer([_LOAD_TX0, *encode_id(can_id, extended), dlc, *data])
        self._xfer([_RTS_TX0])

    def recv(self, timeout: float = 0.0):
        """Return the next CanFrame, or None if nothing arrives within timeout."""
        deadline = time.monotonic() + timeout
        while True:
            # INT is active low: high means nothing waiting, so skip the SPI status read
            if self.int_pin is not None and self.mcp.get_gpio_value(self.int_pin):
                if time.monotonic() >= deadline:
                    return None
                continue
            status = self.read_status()
            if status & 0x01:
                return decode_frame(self._xfer([_READ_RX0] + [0] * 13)[1:])
            if status & 0x02:
                return decode_frame(self._xfer([_READ_RX1] + [0] * 13)[1:])
            if time.monotonic() >= deadline:
                return None

    def errors(self) -> dict:
        eflg = self.read_reg(_EFLG)
        return {
            "tx_errors": self.read_reg(_TEC),
            "rx_errors": self.read_reg(_REC),
            "bus_off": bool(eflg & 0x20),
            "rx_overflow": bool(eflg & 0xC0),
            "eflg": eflg,
        }

    def clear_overflow(self):
        self.bit_modify(_EFLG, 0xC0, 0x00)
