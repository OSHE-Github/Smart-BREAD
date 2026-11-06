from mcp2515 import MCP2515, open_first_mcp2210
import array

#Bitrate debug flags
debugBitrate = 0

#Set up can interface
mcp = open_first_mcp2210()
can = MCP2515(mcp, cs_pin=3, int_pin=4, osc_hz=16_000_000, bitrate=500_000)

txBuf = array.array("b", [0,0,0,0,0,0,0,0])


if debugBitrate:
    for br in (500_000, 250_000, 125_000, 1_000_000):
        can.set_bitrate(16_000_000, br)
        can.set_mode(MCP2515.MODE_LISTEN_ONLY)
        frames = [f for _ in range(20) if (f := can.recv(timeout=0.1))]
        print(f"{br:>9} bps: {len(frames)} frames, errors={can.errors()['rx_errors']}")

can.set_bitrate(16_000_000, 500_000)   # whichever worked
can.set_mode(MCP2515.MODE_NORMAL)

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
    #print(bin(txBuf[0]))
    can.send(address, txBuf, extended = True)

while True:
    pin = input("What Digital pin should I read? ")
    read(0x1A3, 0, 3, int(pin), 0)
    recieved = can.recv(timeout=2);
    if recieved is not None:
        print(f"PWM Frequency: {(recieved.data[5] << 16) + (recieved.data[6] << 8) + recieved.data[7]} Hz")
        print(f"PWM Duty: {(recieved.data[4] / 255) * 100}%")

        

    
