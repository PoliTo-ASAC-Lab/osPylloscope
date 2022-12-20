#  Based on https://learn.sparkfun.com/tutorials/graph-sensor-data-with-python-and-matplotlib/all
import threading
import matplotlib.pyplot as plt
import ospy_lib as ospy

if __name__ == '__main__':
    # Creating, if necessary, the screenshots folder
    ospy.init_screenshot_folder()

    # Initializing the socket + connecting with the source
    s = ospy.init_socket()
    conn = ospy.connector(s)

    # Printing useful header for the tuning phase
    ospy.print_tuning_INFO()

    # Stopping the data gatherer thread
    dg_thread = threading.Thread(target=ospy.data_gatherer, args=(s, conn,))
    dg_thread.start()

    # Pre-formatting the plots based on configuration inputs
    ospy.pre_format_subplots(ospy.fig, ospy.ax, ospy.line_list, ospy.thr_line_list)

    # Initializing and starting animation
    ospy.init_animation()
    # plt.get_current_fig_manager().window.state('zoomed')  # auto full screen https://stackoverflow.com/a/22418354
    plt.show()

    # Stopping the data gatherer thread when closing the fig window
    ospy.dg_stop.set()
