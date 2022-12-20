# Configuration parameters for ospylloscope
HOST = "127.0.0.1"  # check "ipconfig /all" to match proper IP of this server
PORT = 4929  # arbitrary, chosen here, must match at the client side

# General parameters
T_VISUALIZE_ms = 200  # How much time [ms] between each sample and the following
SHOWN_TIME_WINDOW_s = 5  # How many seconds of samples to show in the window
TRANS_DELAY = 13.7  # ms to be tuned according to TUNING PHASE
TUNING_PHASE = False  # Tuning phase enabled/disabled

# Subplots parameters
DATA_CARDINALITY = 3  # how many data (->subplots) have to be shown
THRESHOLD = [599.0, 500.0, 500.0, 500.0, 500.0]  # Red horizontal line will be drawn at this level
MAX_X_TICKS = [SHOWN_TIME_WINDOW_s, 10, 10, 10, 10]  #
MAX_Y_TICKS = [10, 10, 10, 10, 10]  #
MAX_EXPECTED_Y_VALUE = [700, 700, 700, 700, 700]  #
MIN_EXPECTED_Y_VALUE = [-0.1, -0.1, -0.1, -0.1, -0.1]  #
PLOT_TITLE = ['Plot1', 'Plot2', 'Plot3', 'Plot4', 'Plot5']  #
LINE_WIDTH = [0.5, 0.5, 0.5, 0.5, 0.5]  #
LINE_COLOR = ['b', 'g', 'm', 'k', 'b']  # https://matplotlib.org/stable/gallery/color/named_colors.html#css-colors
