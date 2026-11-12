from mcp2515 import MCP2515, open_first_mcp2210
import array

#Bitrate debug flags
debugBitrate = 0

time = 0.5

#Set up can interface
mcp = open_first_mcp2210()
can = MCP2515(mcp, cs_pin=3, int_pin=4, osc_hz=16_000_000, bitrate=500_000)

txBuf = array.array("B", [0,0,0,0,0,0,0,0])


if debugBitrate:
    for br in (500_000, 250_000, 125_000, 1_000_000):
        can.set_bitrate(16_000_000, br)
        can.set_mode(MCP2515.MODE_LISTEN_ONLY)
        frames = [f for _ in range(20) if (f := can.recv(timeout=0.1))]
        print(f"{br:>9} bps: {len(frames)} frames, errors={can.errors()['rx_errors']}")

can.set_bitrate(16_000_000, 500_000)   # whichever worked
can.set_mode(MCP2515.MODE_NORMAL)

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

write(0x1A3, 1, 1, 0, 1, 0)
recieved = can.recv(time);
if recieved is not None:
    print("Recieved Data: " + bin((recieved.data[5] << 16) + (recieved.data[6] << 8) + recieved.data[7]))
write(0x1A3, 1, 2, 0, 1, 0)
recieved = can.recv(time);
if recieved is not None:
    print("Recieved Data: " + bin((recieved.data[5] << 16) + (recieved.data[6] << 8) + recieved.data[7]))

while True:
    pin = input("Which PWM pin do I address? ")
    speed = input("What speed should the motor run at? ")

    write(0x1A3, 3, int(pin), 0, 500, int(255.0*(int(speed)/100.0)))
    recieved = can.recv(time);
    if recieved is not None:
        print("Recieved Data: " + bin((recieved.data[5] << 16) + (recieved.data[6] << 8) + recieved.data[7]))




        

    
