#  Based on https://learn.sparkfun.com/tutorials/graph-sensor-data-with-python-and-matplotlib/all
from matplotlib.lines import Line2D
import matplotlib.pyplot as plt
import matplotlib.animation as ani
import matplotlib.ticker as plticker
from datetime import datetime
import struct
import socket
import warnings
import threading
import numpy as np

global conn, PYNQ_address, s, xy, old_timestamp

HOST = "127.0.0.1"  # check ipconfig /all to match proper ip add
PORT = 4929  # arbitrary, chosen here, must match at the client side

THRESHOLD = 500  # uA
SHOWN_TIME_WINDOW_s = 60
T_VISUALIZE_ms = 100
TRANS_LATENCY_ms = 8  # to be tuned based on observed dt
MAX_X_TICKS = 10
MAX_Y_TICKS = 10
MAX_EXPECTED_Y_VALUE = 700  # current [uA]

# Create figure for plotting
fig = plt.figure()
ax = [fig.add_subplot(2, 1, 1), fig.add_subplot(2, 1, 2)]  # https://stackoverflow.com/a/11404223

dim = int(SHOWN_TIME_WINDOW_s * 1000 / T_VISUALIZE_ms)  # How many samples will be shown at the same time

x_nums = list(np.linspace(0, SHOWN_TIME_WINDOW_s, dim))  #

xs = [x_nums, x_nums]  # x axis numbers, based on the shown time window
ys = [[0] * dim, [0] * dim]  # initializing data to zeros, they'll be updated by the samples

line = [ax[0].plot(xs[0], ys[0])[0], ax[1].plot(xs[1], ys[1])[0]]
xy = [[], []]


def x_format_func(value, tick_number):
    return f"T+{(SHOWN_TIME_WINDOW_s - value):.2f}"


def update_data(i, ys):
    global xy, old_timestamp
    xy_sample = xy[0] if xy != [] else [-1, -1]
    print(f"updating {xy_sample}")

    # Updating y data
    ys[0].append(xy_sample[1])

    # reducing to timewindow
    ys[0] = ys[0][-dim:]

    # Updating xy series
    line[0].set_ydata(ys[0])

    # Signaling the user if data source is OK/NOK (by modifying the suptitle)
    if xy_sample[0] == -1:  # emitter says that source is not OK
        line[0].set_linewidth(60)
        line[0].set_color("red")
        fig.canvas.set_window_title('SOURCE NOK')

        # TODO try to change background color here in some way OR find another graphic way to signal source is NOK

    else:  # source is OK
        line[0].set_linewidth(0.8)
        line[0].set_color("blue")
        fig.canvas.set_window_title('SOURCE OK')

    # TODO add text with info about last threshold trespassing
    return line[0],


def connection_init():
    global s
    warnings.simplefilter("ignore", ResourceWarning)  # See https://stackoverflow.com/a/26620811
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, struct.Struct('f').size)  # https://stackoverflow.com/a/30888505
    s.bind((HOST, PORT))
    s.listen()


def connector():
    global conn
    print("############################")
    print("############################")
    print("############################")
    print("Waiting for PYNQ to connect...", end='', flush=True)
    conn, _ = s.accept()
    print("PYNQ connected.")
    _ = conn.recv(8)
    _ = conn.recv(8)


def data_gatherer():
    global xy
    unpacker = struct.Struct('f')
    while True:
        data = conn.recv(unpacker.size)
        if not data:
            print("\nDG: PYNQ disconnected!")
            xy.pop()  # removing valid data to be visualized
            connector()  # wait for new connection
        else:
            y = unpacker.unpack(data)[0]  # converting current measurement in float (it is sent as a bytearray)
            x = datetime.now().strftime('%H:%M:%S.%f')
            xy = [[x, y]]
            # print(xy)


if __name__ == '__main__':
    connection_init()
    connector()
    dg_thread = threading.Thread(target=data_gatherer, daemon=True)
    dg_thread.start()

    ax[0].set_title('First Plot', loc='left')

    # X-axis formatting
    ax[0].set_xlim(0, SHOWN_TIME_WINDOW_s)
    plt.setp(ax[0].get_xticklabels(),
             rotation=30,
             ha="right",
             rotation_mode="anchor",
             fontsize=8)  # https://github.com/matplotlib/matplotlib/issues/13774#issuecomment-478250353
    ax[0].xaxis.set_major_formatter(plt.FuncFormatter(x_format_func))  # set formatter for X-axis labels
    ax[0].xaxis.set_major_locator(plt.MaxNLocator(MAX_X_TICKS))  # set number of X-axis ticks
    # Y-axis formatting
    ax[0].set_ylim(-.1, MAX_EXPECTED_Y_VALUE)
    ax[0].tick_params(axis='y',
                      right=True,
                      labelright=True)
    ax[0].yaxis.set_major_locator(plt.MaxNLocator(MAX_Y_TICKS))  # set number of Y-axis ticks
    # Threshold line
    ax[0].axhline(linewidth=1,
                  color='r',
                  y=THRESHOLD)
    # Other formatting
    ax[0].grid(True)

    # Overall figure formatting
    plt.subplots_adjust(hspace=0.8)

    # TODO find a way to display different data on different subplots
    # ax[1].title.set_text('Second Plot')
    # ax[1].set_ylim(-.1, 700)
    # ax[1].tick_params(axis='x',
    #                  labelrotation=45)
    # ax[1].yaxis.set_major_locator(plt.MaxNLocator(10))  # set number of Y-axis ticks
    # ax[1].axhline(linewidth=1,
    #              color='r',
    #              y=THRESHOLD)
    # ax[1].grid(True)

    _ = ani.FuncAnimation(fig, update_data, fargs=(ys,), interval=T_VISUALIZE_ms - TRANS_LATENCY_ms, blit=True)
    plt.show()
