#  Based on https://learn.sparkfun.com/tutorials/graph-sensor-data-with-python-and-matplotlib/all
# TODO divide source code in main, library and conf
import os
import socket
import struct
import threading
import warnings
from datetime import datetime

import matplotlib.animation as ani
import matplotlib.pyplot as plt
import numpy as np

HOST = "127.0.0.1"  # check ipconfig /all to match proper ip add
PORT = 4929  # arbitrary, chosen here, must match at the client side

# General parameters
T_VISUALIZE_ms = 200  # How much time [ms] between each sample and the following
SHOWN_TIME_WINDOW_s = 5  # How many seconds of samples to show in the window
TRANS_DELAY = 13.7  # ms to be tuned according to TUNING PHASE
TUNING_PHASE = False  # Tuning phase enabled/disabled
print(f"INFO: Tuning phase <{TUNING_PHASE}>")
TUNING_ITER = 1  # Used for mean value of TRANS_DELAY tuning
TUNING_CUMULATIVE = 0  # Used for mean value of TRANS_DELAY tuning

# Subplots parameters
DATA_CARDINALITY = 3  # how many data (->subplots) have to be shown
THRESHOLD = [599.0, 500.0, 500.0, 500.0, 500.0]  # Red horizontal line will be drawn at this level
MAX_X_TICKS = [SHOWN_TIME_WINDOW_s, 10, 10, 10, 10]  #
MAX_Y_TICKS = [10, 10, 10, 10, 10]  #
MAX_EXPECTED_Y_VALUE = [700, 700, 700, 700, 700]  #
MIN_EXPECTED_Y_VALUE = [-0.1, -0.1, -0.1, -0.1, -0.1]  #
PLOT_TITLE = ['Plot1', 'Plot2', 'ciao', 'Plot4', 'Plot5']  #
LINE_WIDTH = [0.5, 0.5, 0.5, 0.5, 0.5]  #
LINE_COLOR = ['b', 'g', 'm', 'k', 'b']  # https://matplotlib.org/stable/gallery/color/named_colors.html#css-colors

# Create figure for plotting
dim = int(
    SHOWN_TIME_WINDOW_s * 1000 / (T_VISUALIZE_ms + TRANS_DELAY))  # How many samples will be shown at the same time
print(f"INFO: Plot will show {dim} samples at each window update (T={T_VISUALIZE_ms / 1000}sec)")
x_nums = list(np.linspace(0, SHOWN_TIME_WINDOW_s, dim))  # Numbers to be used in the x-axis ticks
xs = [x_nums] * DATA_CARDINALITY  # Series of x-axis numbers, one for each subplot
ys = [[0] * dim] * DATA_CARDINALITY  # initializing visualized data to zeros, they'll be updated by the actual samples

fig = plt.figure()  # Main figure initialization

# First Subplot initialization
ax = [fig.add_subplot(DATA_CARDINALITY, 1, 1)]  # Matplotlib artists list
line_list = [ax[0].plot(xs[0], ys[0])[0]]  # Matplotlib lines list
xy = [[]]  # Contains the sample tuples arriving from source
thr_line_list = [line_list[0]]  # Horizontal threshold lines
thr_flag = [False]  # The threshold for the corresponding datum has been trespassed?
thr_cnt = [dim]  # To keep trace of when the over-threshold samples go out of view

# Other subplots initialization
for i in range(1, DATA_CARDINALITY):
    ax.append(fig.add_subplot(DATA_CARDINALITY, 1, i + 1))  # https://stackoverflow.com/a/11404223
    line_list.append(ax[i].plot(xs[i], ys[i])[0])
    xy.append([])
    thr_line_list.append(line_list[i])
    thr_flag.append(False)
    thr_cnt.append(dim)

# Other global vars initialization
animation = []
source_nok_flag = False  # Source is NOK?
source_text = [ax[0].text(SHOWN_TIME_WINDOW_s / 2, MAX_EXPECTED_Y_VALUE[0] / 2, "", ha="center", va="center",
                          color="red", fontsize=40, fontweight="bold", bbox=dict(fc="lightgrey"))]
paused_flag = False  # Animation is currently paused?
t_first_plot = ""  # To store timestamp of first plotted sample
t_last_plot = ""  # To store timestamp of last plotted sample
dg_stop = threading.Event()  # Event to stop data gatherer thread
ss_start_time = datetime.now().strftime("%Y%m%d_%H%M%S")  # Prefix for all the screenshots
ss_cnt = 0


def screenshot_folder_init():
    if not os.path.exists("./screenshots/"):
        os.mkdir("./screenshots/")


def tuning_INFO():
    if TUNING_PHASE:
        print(
            f"\n------------TRANS_DELAY TUNING (set TRANS_DELAY={TRANS_DELAY}ms, TIME_WINDOW_s={SHOWN_TIME_WINDOW_s}s)------------\n"
            f"SHOWN_TIME[s]; MEASURED_T_D[ms]; DELTA_T_D[ms]; MEAN_T_D [ms]")


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
    connection.setblocking(True)
    print("PYNQ connected.")
    return connection


def data_gatherer(so, connection):
    global xy, DATA_CARDINALITY
    unpacker = struct.Struct(f'{DATA_CARDINALITY}f')
    xy = [[0, 0]] * DATA_CARDINALITY

    try:
        while not dg_stop.is_set():
            data = connection.recv(unpacker.size)
            if not data:
                print("\nDG: source disconnected!", end="", flush=True)
                xy = []  # removing valid data to be visualized
                connection = connector(so, connection)  # wait for new connection
                xy = [[0, 0]] * DATA_CARDINALITY
            else:
                y = list(unpacker.unpack(data))  # converting current measurement in float (it is sent as a bytearray)
                x = datetime.now().strftime('%H:%M:%S.%f')
                for k in range(DATA_CARDINALITY):
                    xy[k] = [x, y[k]]
            # print(xy)
    except:
        print("Error in data gatherer thread!")


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
    text = "Double click to pause/unpause & save plot in ./screenshots/   "
    plt.figtext(1, 0, text, va="bottom", ha="right", fontweight="bold", fontsize=10)


def x_format_func(value, tick_number):
    return f"T+{(SHOWN_TIME_WINDOW_s - value):.2f}"


def frame_update(k):  # k = frame number, automatically passed by FuncAnimation
    global source_nok_flag, t_last_plot, t_first_plot, TUNING_PHASE, TUNING_ITER, TUNING_CUMULATIVE

    for i in range(0, len(line_list)):  # updating all the data series
        xy_sample = xy[i] if xy != [] else [-1, -1]
        # Updating y data for datum k
        ys[i].append(xy_sample[1])
        # cropping to time window for datum k
        ys[i] = ys[i][-dim:]

    # Updating xy series
    for i in range(0, len(line_list)):
        line_list[i].set_ydata(ys[i])

    # Signaling the user if data source is OK/NOK
    if not xy:  # same as "if xy == []"
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
            if float(ys[i][-1]) > THRESHOLD[i]:  # check last sample for each datum
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
    if TUNING_PHASE:
        if k == 0:
            t_first_plot = datetime.strptime(str(xy_sample[0]), '%H:%M:%S.%f')
        elif k == TUNING_ITER * dim - 1:
            t_last_plot = datetime.strptime(str(xy_sample[0]), '%H:%M:%S.%f')

        elif k == TUNING_ITER * dim:
            delta_t_delay_computed = (((t_last_plot - t_first_plot).total_seconds()) - SHOWN_TIME_WINDOW_s) * 1000 / dim
            TUNING_CUMULATIVE += (TRANS_DELAY + delta_t_delay_computed) if TUNING_ITER > 1 else TRANS_DELAY
            print(f" {(t_last_plot - t_first_plot).total_seconds():.3f}s\t"
                  f"| {TRANS_DELAY + delta_t_delay_computed:+.3f}ms\t"
                  f"| {delta_t_delay_computed:+.3f}ms\t"
                  f"| {(TUNING_CUMULATIVE / TUNING_ITER):+.3f}ms\t|")
            t_first_plot = t_last_plot
            TUNING_ITER += 1
        else:
            pass
            # print(k, xy_sample[0], float(xy_sample[1]))
    return line_list + source_text


def frame_init():
    return line_list


def animation_toggle_pause(event):
    # TODO add screenshot saving when pausing
    global paused_flag, animation
    if event.dblclick:
        if paused_flag:
            animation.resume()
        else:
            take_screenshot()
            animation.pause()
        paused_flag = not paused_flag


def take_screenshot():
    global ss_cnt, ss_start_time
    ss_cnt += 1
    plt.savefig(f"./screenshots/{ss_start_time}_{ss_cnt:02d}.pdf")
    print(f"INFO: <./screenshots/{ss_start_time}_{ss_cnt:02d}.pdf> created!")


if __name__ == '__main__':
    screenshot_folder_init()  # Creating, if necessary, the screenshots folder

    s = socket_init()  # Initializing the socket
    conn = connector(s)  # Connecting with the source

    tuning_INFO()  # Printing useful header for the tuning phase

    dg_thread = threading.Thread(target=data_gatherer, args=(s, conn,))
    dg_thread.start()

    pre_format_subplots(fig, ax, line_list, thr_line_list)
    animation = ani.FuncAnimation(fig, frame_update, init_func=frame_init, interval=T_VISUALIZE_ms, blit=True)
    # plt.get_current_fig_manager().window.state('zoomed')  # auto full screen https://stackoverflow.com/a/22418354
    plt.show()

    dg_stop.set()
