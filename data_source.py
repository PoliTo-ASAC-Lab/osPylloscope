from datetime import datetime as dt
import time
import random
import socket
import struct

# TODO clean code and create input config file
# TODO make function to put triggers on data sampling, with related actions (e.g., beam off, DUT off)

connection_error_string = "###########################################################################" \
                          "\n###########################################################################" \
                          "\nosPylloscope not connected. Continuing logging the samples.\n" \
                          "###########################################################################" \
                          "\n###########################################################################"
conn_exceptions = (ConnectionAbortedError, ConnectionResetError, ConnectionRefusedError, TimeoutError)


def connect_osPylloscope(HOST_, PORT_, DATA_CARDINALITY_):
    so = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    so.settimeout(0.1)
    try:
        print(f"Connecting to particle count server (@{HOST_}:{PORT_})...", end='', flush=True)
        so.connect((HOST_, PORT_))
        print(f"CONNECTED\n")
        connected = True
        packer_ = struct.Struct(f'{DATA_CARDINALITY_}f')
        so.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, packer_.size)  # https://stackoverflow.com/a/30888505

    except (ConnectionAbortedError, ConnectionResetError, ConnectionRefusedError, TimeoutError) as exception:
        print("ERROR: Connection failed!")
        raise exception
    return so, connected


if __name__ == '__main__':

    #   Sampling configuration
    T_SAMPLE_ms = 30
    DATA_CARDINALITY = 3

    #   Socket configuration
    HOST = "127.0.0.1"  # check ipconfig /all to match proper ip add
    PORT = 4929  # arbitrary, chosen here, must match at the client side

    # Necessary variables initialization
    osPylloscope_OK = False
    cnt = 0
    data = [0] * DATA_CARDINALITY
    done = False
    reconnect_cnt = 0
    packer = struct.Struct(f'{DATA_CARDINALITY}f')

    # First connection to osPylloscope
    try:
        s, osPylloscope_OK = connect_osPylloscope(HOST, PORT, DATA_CARDINALITY)
    except conn_exceptions as e:
        time.sleep(1)
        print(connection_error_string)
        time.sleep(1)

    # Sampling
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
            elif reconnect_cnt > 5 * 1000 / T_SAMPLE_ms:  # try to reconnect every 5 seconds
                reconnect_cnt = 0
                s, osPylloscope_OK = connect_osPylloscope(HOST, PORT, DATA_CARDINALITY)
            else:
                reconnect_cnt += 1
        except conn_exceptions:
            print(connection_error_string)
            osPylloscope_OK = False

        time.sleep(T_SAMPLE_ms / 1000)
