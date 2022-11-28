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

global conn, PYNQ_address, s, xy

HOST = "127.0.0.1"  # check ipconfig /all to match proper ip add
PORT = 4929  # arbitrary, chosen here, must match at the client side

# General parameters
T_VISUALIZE_ms = 100
SHOWN_TIME_WINDOW_s = 20
T_DELAY_GRAPH = 7
# Subplots parameters
THRESHOLD = [500, 500]  # Red horizontal line will be drawn at this level
MAX_X_TICKS = [10, 10]
MAX_Y_TICKS = [10, 10]
MAX_EXPECTED_Y_VALUE = [700, 700]
PLOT_TITLE = ['Plot_1', 'Plot2']
LINE_WIDTH = [0.5, 0.5]
LINE_COLOR = ['blue', 'purple']  # https://matplotlib.org/stable/gallery/color/named_colors.html#css-colors

# Create figure for plotting
fig = plt.figure()
ax = [fig.add_subplot(2, 1, 1), fig.add_subplot(2, 1, 2)]  # https://stackoverflow.com/a/11404223

dim = int(SHOWN_TIME_WINDOW_s * 1000 / T_VISUALIZE_ms)  # How many samples will be shown at the same time

x_nums = list(np.linspace(0, SHOWN_TIME_WINDOW_s, dim))  #
xs = [x_nums, x_nums]  # x axis numbers, based on the shown time window
ys = [[0] * dim, [0] * dim]  # initializing data to zeros, they'll be updated by the samples

line_list = [ax[0].plot(xs[0], ys[0])[0], ax[1].plot(xs[1], ys[1])[0]]
xy = [[], []]

source_nok_flag = False


def x_format_func(value, tick_number):
    return f"T+{(SHOWN_TIME_WINDOW_s - value):.2f}"


def update_data(i, ys, line_list):
    global xy, source_nok_flag
    xy_sample = xy[0] if xy != [] else [-1, -1]
    print(f"updating {xy_sample}")

    # Updating y data
    ys[0].append(xy_sample[1])

    # reducing to timewindow
    ys[0] = ys[0][-dim:]

    # Updating xy series
    line_list[0].set_ydata(ys[0])
    line_list[1].set_ydata(ys[0])

    # Signaling the user if data source is OK/NOK
    if xy_sample[0] == -1:
        if not source_nok_flag:  # emitter says that source is not OK
            source_nok_flag = True
            line_list[0].set_linewidth(60)
            line_list[0].set_color("red")
            fig.canvas.set_window_title('SOURCE NOK')

        # TODO try to change background color here in some way OR find another graphic way to signal source is NOK

    else:  # source is OK
        if source_nok_flag:
            source_nok_flag = False
            line_list[0].set_linewidth(0.5)
            line_list[0].set_color("blue")
            fig.canvas.set_window_title('SOURCE OK')

    # TODO add text with info about last threshold trespassing
    return line_list


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


def pre_format_subplots(artist_list, line_list):
    # Formatting subplots, passed as list of artists
    for i in range(0, len(artist_list)):
        artist_list[i].set_title(PLOT_TITLE[i], loc='right')
        # X-axis formatting
        artist_list[i].set_xlim(0, SHOWN_TIME_WINDOW_s)
        plt.setp(artist_list[i].get_xticklabels(), rotation=30, ha="right", rotation_mode="anchor", fontsize=8)
        artist_list[i].xaxis.set_major_formatter(plt.FuncFormatter(x_format_func))  # set formatter for X-axis labels
        artist_list[i].xaxis.set_major_locator(plt.MaxNLocator(MAX_X_TICKS[i]))  # set number of X-axis ticks
        # Y-axis formatting
        artist_list[i].set_ylim(-.1, MAX_EXPECTED_Y_VALUE[i])
        artist_list[i].tick_params(axis='y', right=True, labelright=True)
        artist_list[i].yaxis.set_major_locator(plt.MaxNLocator(MAX_Y_TICKS[i]))  # set number of Y-axis ticks
        # Threshold line
        artist_list[i].axhline(linewidth=1, color='r', y=THRESHOLD[i])
        # Other formatting
        artist_list[i].grid(True)
        line_list[i].set_linewidth(LINE_WIDTH[i])
        line_list[i].set_color(LINE_COLOR[i])


if __name__ == '__main__':
    connection_init()
    connector()
    dg_thread = threading.Thread(target=data_gatherer, daemon=True)
    dg_thread.start()

    pre_format_subplots(ax, line_list)

    # Overall figure formatting
    fig.canvas.set_window_title('SOURCE OK')
    plt.subplots_adjust(hspace=0.8)

    _ = ani.FuncAnimation(fig, update_data, fargs=(ys, line_list,), interval=T_VISUALIZE_ms - T_DELAY_GRAPH, blit=True)
    plt.show()
