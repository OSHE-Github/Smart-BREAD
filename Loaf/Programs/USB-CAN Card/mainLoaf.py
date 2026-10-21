from mcp2515 import MCP2515, open_first_mcp2210

#Bitrate debug flags
debugBitrate = 0

#Set up can interface
mcp = open_first_mcp2210()
can = MCP2515(mcp, cs_pin=4, int_pin=3, osc_hz=16_000_000, bitrate=500_000)

if debugBitrate:
    for br in (500_000, 250_000, 125_000, 1_000_000):
        can.set_bitrate(16_000_000, br)
        can.set_mode(MCP2515.MODE_LISTEN_ONLY)
        frames = [f for _ in range(20) if (f := can.recv(timeout=0.1))]
        print(f"{br:>9} bps: {len(frames)} frames, errors={can.errors()['rx_errors']}")

can.set_bitrate(16_000_000, 1_000_000)   # whichever worked
can.set_mode(MCP2515.MODE_NORMAL)

#
while True:
    print(can.recv(timeout=2))
    msg = input("Scream back: ")
    can.send(0x12, msg.encode(), extended = True)

def sendCANMessage(address, IO, mode, pin, bDigi, pwmDuty, data):

    byte1 = 0; byte4 = 0;


    tx_msg = can.Message(address, extended=True, data=[byte0, byte1, byte2, byte3, byte4, byte5, byte6, byte7])
    can.send(tx_msg)
    print(f"Sent: {tx_msg}")

def buttonPress(buttonID: int, state: int = 1):
    match buttonID:
        case 1: 
                msg = "Button left pressed"
                sendCANMessage(0x12, 0b10000000, 0b00000000)

        case 2:
                msg = "Button right pressed"
                sendCANMessage(0x12, 0b00100000, 0b00000000)
        case 3:
                msg = "Button increase pressed"
                sendCANMessage(0x12, 0b01000000, 0b00000000)
        case 4:
                msg = "Button decrease pressed"
                sendCANMessage(0x12, 0b00010000, 0b00000000)

                tx_msg.data[0] = 0b00010000;
                
''' tx_msg.data[1] = 0b00000000;
  tx_msg.data[2] = 0b00000000;
  tx_msg.data[3] = 0b00000000;
  tx_msg.data[4] = 0b00000000;
  tx_msg.data[5] = 0b00000000;
  tx_msg.data[6] = 0b00000000;
  tx_msg.data[7] = 0b00000000;'''
        

    
