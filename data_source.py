from datetime import datetime as dt
import time
import random
import socket
import struct

T_SAMPLE_ms = 30
DATA_CARDINALITY = 3
if __name__ == '__main__':
    #   Socket configuration
    HOST = "127.0.0.1"  # check ipconfig /all to match proper ip add
    PORT = 4929  # arbitrary, chosen here, must match at the client side
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    packer = struct.Struct(f'{DATA_CARDINALITY}f')
    print(packer.size)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, packer.size)  # https://stackoverflow.com/a/30888505

    print(f"Connecting to particle count server (@{HOST}:{PORT})...", end='', flush=True)
    s.connect((HOST, PORT))
    print(f"CONNECTED\n")
    cnt = 0
    data = [0] * DATA_CARDINALITY
    done = False
    osPylloscope_OK = True
    while True:

        for k in range(DATA_CARDINALITY):  # creating dummy data
            data[k] = 500 * random.random()

        # if cnt < int(2 * 1000 / T_SAMPLE_ms):
        if int(2 * 1000 / T_SAMPLE_ms) <= cnt < int(4 * 1000 / T_SAMPLE_ms):
            data[1] = 600 + 10 * random.random()
        if cnt >= int(4 * 1000 / T_SAMPLE_ms):
            cnt = 0
            # done = True # uncomment to perform a single spike/impulse
        elif not done:
            cnt += 1

        packed_data = packer.pack(*data)
        print(f"{dt.now().strftime('%H:%M:%S.%f')} -> {data}")
        try:
            if osPylloscope_OK:
                s.sendall(packed_data)
        except (ConnectionAbortedError, ConnectionResetError):
            print("###########################################################################"
                  "\n###########################################################################"
                  "\n###########################################################################")
            print("\nosPylloscope stopped receiving the samples. Continuing logging the samples.\n")
            print("###########################################################################"
                  "\n###########################################################################"
                  "\n###########################################################################")
            osPylloscope_OK = False
            # TODO try to reconnect to osPylloscope every 5 seconds without stopping the sampling

        time.sleep(T_SAMPLE_ms / 1000)
