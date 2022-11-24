from matplotlib.lines import Line2D
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.ticker as plticker
from datetime import datetime as dt
import struct
import socket
import warnings
import threading

global conn, PYNQ_address, s, xy

HOST = "127.0.0.1"  # check ipconfig /all to match proper ip add
PORT = 4929  # arbitrary, chosen here, must match at the client side

THRESHOLD = 500  # uA
SHOWN_TIME_WINDOW_s = 50
T_VISUALIZE_ms = 300


class Scope:
    def __init__(self, ax, maxt=SHOWN_TIME_WINDOW_s, dt=T_VISUALIZE_ms / 1000):
        self.ax = ax
        self.dt = dt
        self.maxt = maxt
        self.tdata = [0]
        self.ydata = [0]
        self.line = Line2D(self.tdata, self.ydata)
        self.ax.add_line(self.line)
        self.ax.set_ylim(-.1, 700)
        # self.ax.set_ylim(80, 120)
        self.ax.set_xlim(0, self.maxt)
        loc = plticker.MultipleLocator(base=5.0)  # this locator puts ticks at regular intervals
        self.ax.xaxis.set_major_locator(loc)
        self.ax.yaxis.set_major_locator(plt.MaxNLocator(40))  # set number of Y-axis ticks
        self.ax.grid(True)

    def update(self, xy_sample):
        lastt = self.tdata[-1]
        if lastt > self.tdata[0] + self.maxt:  # reset the arrays
            self.tdata = [self.tdata[-1]]
            self.ydata = [self.ydata[-1]]
            self.ax.set_xlim(self.tdata[0], self.tdata[0] + self.maxt)
            self.ax.axhline(linewidth=2, color='r', y=THRESHOLD)
            self.ax.figure.canvas.draw()
        t = self.tdata[-1] + self.dt
        # if len(self.tdata) == 1:
        #    t = self.tdata[-1] + self.dt
        # else:
        #    t = self.tdata[-1] + (self.tdata[-1] - self.tdata[-2])  # adaptive dt
        self.tdata.append(t)
        self.ydata.append(xy_sample[1])

        print(f"\t--> {dt.now().strftime('%H:%M:%S.%f')} : [{t},{xy_sample[1]}]")
        self.line.set_data(self.tdata, self.ydata)
        self.ax.axhline(linewidth=2, color='r', y=THRESHOLD)
        return self.line,


def emitter():
    global xy
    # print(f"yielding {xy}")
    yield xy[0] if xy != [] else [0, 0]  # read from global variable containing last reading


def connection_init():
    global s
    warnings.simplefilter("ignore", ResourceWarning)  # See https://stackoverflow.com/a/26620811
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    unpacker = struct.Struct('f')
    s.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, unpacker.size)  # https://stackoverflow.com/a/30888505
    s.bind((HOST, PORT))
    s.listen()


def connector():
    global conn, PYNQ_address
    print("############################")
    print("############################")
    print("############################")
    print("Waiting for PYNQ to connect...", end='', flush=True)
    conn, PYNQ_address = s.accept()
    _ = conn.recv(8)
    _ = conn.recv(8)


def data_gatherer():
    global xy
    unpacker = struct.Struct('f')
    xy = []
    while True:
        data = conn.recv(unpacker.size)
        if not data:
            print("dg: PYNQ disconnected!")
            xy.pop()  # removing valid data to be visualized
            connector()  # wait for new connection
        else:
            y = unpacker.unpack(data)[0]  # converting current measurement in float (it is sent as a bytearray)
            x = dt.now().strftime('%H:%M:%S.%f')
            xy = [[x, y]]
            # print(xy)


if __name__ == '__main__':
    connection_init()
    connector()
    dg_thread = threading.Thread(target=data_gatherer, daemon=True)
    dg_thread.start()

    fig, ax = plt.subplots()
    scope = Scope(ax)

    # pass a generator in "emitter" to produce data for the update func
    ani = animation.FuncAnimation(fig, scope.update, emitter, interval=T_VISUALIZE_ms, blit=True)

    plt.show()
