from datetime import datetime as dt
import time
import random
import socket
import struct

# TODO clean code and create input config file

connection_error_msg = "###########################################################################" \
                       "\nosPylloscope disconnected. Continuing sampling the data.\n" \
                       "###########################################################################"
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


def data_sampling(data_, cnt_, T_SAMPLE_ms_):
    # Dummy data creation
    for k in range(len(data_)):
        data_[k] = 500 * random.random()

    if int(7 * 1000 / T_SAMPLE_ms_) <= cnt_ < int(10 * 1000 / T_SAMPLE_ms_):
        data_[1] = 600 + 10 * random.random()
    if cnt_ >= int(10 * 1000 / T_SAMPLE_ms_):
        cnt_ = 0
    else:
        cnt_ += 1
    return data_, cnt_


def eval_triggers(data_, THRESHOLD_):
    for k in range(len(data_)):
        # print(f"{data_[k]} vs {[THRESHOLD_[k]]}")
        if data_[k] >= THRESHOLD_[k]:
            # DO SOMETHING
            # DO SOMETHING
            # DO SOMETHING
            print(f"\tDATA[{k}] alert: {data_[k]:.4f} (thr_lvl={THRESHOLD_[k]})")
            # DO SOMETHING
            # DO SOMETHING
            # DO SOMETHING


if __name__ == '__main__':

    #   Sampling configuration
    T_SAMPLE_ms = 30
    DATA_CARDINALITY = 3
    THRESHOLD = [500.0, 500.0, 500.0]  # Thresholds for the data

    #   Socket configuration
    HOST = "127.0.0.1"  # check ipconfig /all to match proper ip add
    PORT = 4929  # arbitrary, chosen here, must match at the client side

    # Necessary variables initialization
    data = [0] * DATA_CARDINALITY
    packer = struct.Struct(f'{DATA_CARDINALITY}f')
    osPylloscope_OK = False
    reconnect_cnt = 0
    cnt = 0

    # First connection to osPylloscope
    try:
        s, osPylloscope_OK = connect_osPylloscope(HOST, PORT, DATA_CARDINALITY)
    except conn_exceptions as e:
        print(connection_error_msg)
        time.sleep(2)

    # Sampling
    while True:

        data, cnt = data_sampling(data, cnt, T_SAMPLE_ms)

        eval_triggers(data, THRESHOLD)

        # print(f"{dt.now().strftime('%H:%M:%S.%f')} -> {data}[{cnt}]")

        packed_data = packer.pack(*data)

        # Sending the sample
        try:
            if osPylloscope_OK:
                s.sendall(packed_data)
            elif reconnect_cnt > 5 * 1000 / T_SAMPLE_ms:  # try to reconnect every 5 seconds
                reconnect_cnt = 0
                s, osPylloscope_OK = connect_osPylloscope(HOST, PORT, DATA_CARDINALITY)
            else:
                reconnect_cnt += 1
        except conn_exceptions:
            print(connection_error_msg)
            osPylloscope_OK = False

        time.sleep(T_SAMPLE_ms / 1000)
