import time
from datetime import datetime as dt
import random
import socket
import struct
import math

T_SAMPLE_ms = 10
T_VISUALIZE_ms = 75
samples_between_visualization = math.floor(T_VISUALIZE_ms / T_SAMPLE_ms)
samples_cnt = 0

if __name__ == '__main__':
    #   Socket configuration
    HOST = "127.0.0.1"  # check ipconfig /all to match proper ip add
    PORT = 4929  # arbitrary, chosen here, must match at the client side
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    packer = struct.Struct('f')
    s.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, packer.size)  # https://stackoverflow.com/a/30888505

    print(f"Connecting to particle count server (@{HOST}:{PORT})...", end='', flush=True)
    s.connect((HOST, PORT))
    print(f"CONNECTED\n")

    while True:
        samples_cnt += 1
        data = 500 * random.random()
        print(f"{dt.now().strftime('%H:%M:%S.%f')},{data}")

        if samples_cnt == samples_between_visualization:
            packed_data = packer.pack(data)
            s.sendall(packed_data)
            samples_cnt = 0

        time.sleep(T_SAMPLE_ms/1000)
