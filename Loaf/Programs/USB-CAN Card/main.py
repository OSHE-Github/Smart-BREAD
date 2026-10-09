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


while True:
    print(can.recv(timeout=2))
