#  Based on https://matplotlib.org/stable/gallery/animation/strip_chart.html#oscilloscope
from matplotlib.lines import Line2D
import matplotlib.pyplot as plt
import matplotlib.animation as ani
import matplotlib.ticker as plticker
from datetime import datetime
import struct
import socket
import warnings
import threading

global conn, PYNQ_address, s, xy, old_timestamp

HOST = "127.0.0.1"  # check ipconfig /all to match proper ip add
PORT = 4929  # arbitrary, chosen here, must match at the client side

THRESHOLD = 500  # uA
SHOWN_TIME_WINDOW_s = 50
T_VISUALIZE_ms = 100
TRANS_LATENCY_ms = 8  # to be tuned based on observed dt


class Scope:
    def __init__(self, ax, maxt=SHOWN_TIME_WINDOW_s, dt=T_VISUALIZE_ms / 1000):
        self.ax = ax
        self.dt = dt
        self.maxt = maxt
        self.tdata = [0]
        self.ydata = [0]
        self.line = Line2D(self.tdata, self.ydata, linewidth=0.8, color="blue")
        self.ax.add_line(self.line)
        self.ax.set_ylim(-.1, 700)
        # self.ax.set_ylim(80, 120)
        self.ax.set_xlim(0, self.maxt)
        loc = plticker.MultipleLocator(base=5.0)  # this locator puts ticks at regular intervals
        self.ax.xaxis.set_major_locator(loc)
        self.ax.yaxis.set_major_locator(plt.MaxNLocator(40))  # set number of Y-axis ticks
        self.ax.grid(True)

    def update(self, xy_sample):
        global xy, old_timestamp
        xy_sample = xy[0] if xy != [] else [-1, -1]
        current_timestamp = datetime.now()

        # Resetting view if time goes beyond [SHOWN_TIME_WINDOW_s]
        lastt = self.tdata[-1]
        if lastt > self.tdata[0] + self.maxt:  # reset the arrays
            self.tdata = [self.tdata[-1]]
            self.ydata = [self.ydata[-1]]
            self.ax.set_xlim(self.tdata[0], self.tdata[0] + self.maxt)
            self.ax.axhline(linewidth=1, color='r', y=THRESHOLD)
            self.ax.figure.canvas.draw()

        # Updating x data
        if len(self.tdata) == 1:
            t = self.tdata[-1] + self.dt
            old_timestamp = current_timestamp
        else:
            dt = (current_timestamp - old_timestamp).total_seconds()
            t = self.tdata[-1] + dt
            print(f"\tDEBUG: {current_timestamp}->[t={t},y={xy_sample[1]}](dt={dt},dev={dt - (T_VISUALIZE_ms / 1000)})")
            old_timestamp = current_timestamp
        self.tdata.append(t)

        # Updating y data
        self.ydata.append(xy_sample[1])

        # Updating xy series
        self.line.set_data(self.tdata, self.ydata)

        # Setting threshold line
        self.ax.axhline(linewidth=1, color='r', y=THRESHOLD)

        # Signaling the user if data source is OK/NOK
        if xy_sample[0] == -1:  # emitter says that source is not OK
            self.line.set_linewidth(6)
            self.line.set_color("red")
            self.ax.set_title('SOURCE NOT OK', fontsize=15, color='red', fontweight='bold', loc='right')
        else:  # source is OK
            self.line.set_linewidth(0.8)
            self.line.set_color("blue")
            self.ax.set_title('SOURCE OK', fontsize=15, color='green', fontweight='bold', loc='right')

        # TODO add text with info about last threshold trespassing
        return self.line,


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
    xy = []
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

    fig, ax = plt.subplots()
    scope = Scope(ax)
    # ani = animation.FuncAnimation(fig, scope.update, data_emitter, init_func=frame_init, interval=T_VISUALIZE_ms)
    _ = ani.FuncAnimation(fig, scope.update,
                          interval=T_VISUALIZE_ms - TRANS_LATENCY_ms)  # do not turn on blitting! had problems with repetition of update function
    plt.show()
