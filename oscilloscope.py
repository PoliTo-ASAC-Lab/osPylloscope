#  Based on https://learn.sparkfun.com/tutorials/graph-sensor-data-with-python-and-matplotlib/all
# TODO divide source code in main, library and conf
import matplotlib.pyplot as plt
import matplotlib.animation as ani
from datetime import datetime
import struct
import socket
import warnings
import threading
import numpy as np

HOST = "127.0.0.1"  # check ipconfig /all to match proper ip add
PORT = 4929  # arbitrary, chosen here, must match at the client side

# General parameters
T_VISUALIZE_ms = 100
SHOWN_TIME_WINDOW_s = 20
T_DELAY_GRAPH = 7  # to be tuned to have realistic visualized samples/s
# Subplots parameters
DATA_CARDINALITY = 3  # how many data (->subplots) have to be shown
THRESHOLD = [500.0, 500.0, 500.0, 500.0, 500.0]  # Red horizontal line will be drawn at this level
MAX_X_TICKS = [10, 10, 10, 10, 10]  #
MAX_Y_TICKS = [10, 10, 10, 10, 10]  #
MAX_EXPECTED_Y_VALUE = [700, 700, 700, 700, 700]  #
MIN_EXPECTED_Y_VALUE = [-0.1, -0.1, -0.1, -0.1, -0.1]  #
PLOT_TITLE = ['Plot1', 'Plot2', 'Plot3', 'Plot4', 'Plot5']  #
LINE_WIDTH = [0.5, 0.5, 0.5, 0.5, 0.5]  #
LINE_COLOR = ['b', 'g', 'm', 'k', 'b']  # https://matplotlib.org/stable/gallery/color/named_colors.html#css-colors

# Create figure for plotting
dim = int(SHOWN_TIME_WINDOW_s * 1000 / T_VISUALIZE_ms)  # How many samples will be shown at the same time
x_nums = list(np.linspace(0, SHOWN_TIME_WINDOW_s, dim))
xs = [x_nums] * DATA_CARDINALITY  # x-axis numbers, based on the shown time window
ys = [[0] * dim] * DATA_CARDINALITY  # initializing data to zeros, they'll be updated by the samples

fig = plt.figure()
# First Subplot
ax = [fig.add_subplot(DATA_CARDINALITY, 1, 1)]
line_list = [ax[0].plot(xs[0], ys[0])[0]]
xy = [[]]
thr_line_list = [line_list[0]]
thr_flag = [False]
thr_cnt = [dim]
# Other subplots
for i in range(1, DATA_CARDINALITY):
    ax.append(fig.add_subplot(DATA_CARDINALITY, 1, i + 1))  # https://stackoverflow.com/a/11404223
    line_list.append(ax[i].plot(xs[i], ys[i])[0])
    xy.append([])
    thr_line_list.append(line_list[i])
    thr_flag.append(False)
    thr_cnt.append(dim)
# Other globals initialization
animation = []
source_nok_flag = False
source_text = [ax[0].text(SHOWN_TIME_WINDOW_s / 2, MAX_EXPECTED_Y_VALUE[0] / 2, "", ha="center", va="center",
                          color="red", fontsize=40, fontweight="bold", bbox=dict(fc="lightgrey"))]
paused_flag = False


def socket_init():
    warnings.simplefilter("ignore", ResourceWarning)  # See https://stackoverflow.com/a/26620811
    so = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    so.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, struct.Struct('f').size)  # https://stackoverflow.com/a/30888505
    so.bind((HOST, PORT))
    so.listen()
    return so


def connector(so, connection=None):
    print("Waiting for PYNQ to connect...", end='', flush=True)
    connection, _ = so.accept()
    print("PYNQ connected.")
    _ = connection.recv(8)
    _ = connection.recv(8)
    return connection


def data_gatherer(so, connection):
    global xy
    unpacker = struct.Struct('f')
    while True:
        data = connection.recv(unpacker.size)
        if not data:
            print("\nDG: source disconnected!", end="", flush=True)
            xy.pop()  # removing valid data to be visualized
            connection = connector(so, connection)  # wait for new connection
        else:
            y = unpacker.unpack(data)[0]  # converting current measurement in float (it is sent as a bytearray)
            x = datetime.now().strftime('%H:%M:%S.%f')
            xy = [[x, y]]
            # print(xy)
        # TODO manage the gathering of multiple data from the source


def pre_format_subplots(figure, a_list, l_list, threshold_line_list):
    # Formatting subplots, passed as list of artists
    for i in range(0, len(a_list)):
        # Subplot formatting
        a_list[i].set_title(PLOT_TITLE[i], loc='left')
        # X-axis formatting
        a_list[i].set_xlim(0, SHOWN_TIME_WINDOW_s)
        plt.setp(a_list[i].get_xticklabels(), rotation=30, ha="right", rotation_mode="anchor", fontsize=8)
        a_list[i].xaxis.set_major_formatter(plt.FuncFormatter(x_format_func))  # set formatter for X-axis labels
        a_list[i].xaxis.set_major_locator(plt.MaxNLocator(MAX_X_TICKS[i]))  # set number of X-axis ticks
        # Y-axis formatting
        a_list[i].set_ylim(MIN_EXPECTED_Y_VALUE[i], MAX_EXPECTED_Y_VALUE[i])
        a_list[i].tick_params(axis='y', right=True, labelright=True)
        a_list[i].yaxis.set_major_locator(plt.MaxNLocator(MAX_Y_TICKS[i]))  # set number of Y-axis ticks
        # Threshold line
        threshold_line_list[i] = a_list[i].axhline(linewidth=1, color='r', y=THRESHOLD[i])
        # Other formatting
        a_list[i].grid(True)
        l_list[i].set_linewidth(LINE_WIDTH[i])
        l_list[i].set_color(LINE_COLOR[i])
    # Overall figure formatting
    figure.tight_layout()
    figure.subplots_adjust(hspace=0.5)
    figure.canvas.manager.set_window_title('osPylloscope')
    fig.canvas.mpl_connect('button_press_event', animation_toggle_pause)
    text = "Double click anywhere to pause/unpause the visualization.\n" \
           "(ATTENTION: incoming samples won't be shown during pause!)"
    plt.figtext(1, 0, text, va="bottom", ha="right", fontweight="bold", fontsize=10)


def x_format_func(value, tick_number):
    return f"T+{(SHOWN_TIME_WINDOW_s - value):.2f}"


def frame_update(k):  # k = frame number, automatically passed by FuncAnimation
    global source_nok_flag
    xy_sample = xy[0] if xy != [] else [-1, -1]
    # print(f"updating {xy_sample}")

    # Updating y data
    ys[0].append(xy_sample[1])

    # cropping to time window
    ys[0] = ys[0][-dim:]

    # Updating xy series
    for i in range(0, len(line_list)):
        line_list[i].set_ydata(ys[0])

    # Signaling the user if data source is OK/NOK
    if xy_sample[0] == -1:
        if not source_nok_flag:  # emitter says that source is not OK
            source_nok_flag = True
            for i in range(0, len(line_list)):
                line_list[i].set_linewidth(60)
                line_list[i].set_color("dimgrey")
            source_text[0].set_text("SOURCE NOK")
            source_text[0].set_color("red")

    else:  # source is OK
        if source_nok_flag:
            source_nok_flag = False
            for i in range(0, len(line_list)):
                line_list[i].set_linewidth(LINE_WIDTH[i])
                line_list[i].set_color(LINE_COLOR[i])
                thr_flag[i] = False
                thr_cnt[i] = dim
            source_text[0].set_text("")

    # Checking threshold trespassing
    if not source_nok_flag:  # only if source is OK
        for i in range(0, len(line_list)):
            if float(xy_sample[1]) > THRESHOLD[i]:
                if not thr_flag[i]:
                    thr_flag[i] = True
                    line_list[i].set_linewidth(LINE_WIDTH[i] + 2)
                    line_list[i].set_color("red")
                    thr_cnt[i] = 0
            else:
                if thr_cnt[i] < dim:
                    thr_cnt[i] += 1
                elif thr_flag[i]:
                    thr_flag[i] = False
                    line_list[i].set_linewidth(LINE_WIDTH[i])
                    line_list[i].set_color(LINE_COLOR[i])

    return line_list + source_text


def animation_toggle_pause(event):
    global paused_flag, animation
    if event.dblclick:
        if paused_flag:
            animation.resume()
        else:
            animation.pause()
        paused_flag = not paused_flag


if __name__ == '__main__':
    s = socket_init()
    conn = connector(s)
    dg_thread = threading.Thread(target=data_gatherer, args=(s, conn,), daemon=True)
    dg_thread.start()

    pre_format_subplots(fig, ax, line_list, thr_line_list)

    animation = ani.FuncAnimation(fig, frame_update, interval=T_VISUALIZE_ms - T_DELAY_GRAPH, blit=True)

    plt.get_current_fig_manager().window.state('zoomed')  # auto full screen https://stackoverflow.com/a/22418354
    plt.show()
