"""
Robosub External Interface's main file.

Minimal Initial Design handles base window for GUI,
a logger implemented via multiprocessing without forking the entire gui,
runs driver code for robosub's VIDEO grpc/socket connections.

GUI Core will later include driver code for all robosub grpc/socket connections,
and more features as detailed in the Git issues.

Install:
Setup a venv on python 3.8. I used Conda.
Requires PIL, opencv-python.

Operation:
1. Run video_server.py on desired test computer (can also be localhost) and wait for startup.
2. Run this file on host computer.
3. Click 'Start Video' on the top bar. This will communicate over grpc and start a socket connection.
4. Click 'Exit' to exit the program gracefully.

Process/Network Communication Pathway

                    [GUI_main (this file)]
_____________________________________________________________________________
=============   (Gui Pipe)   =============== (Parent Pipe) ==================
 tkinter GUI       --->           Router          --->       Parent Process
=============      <---      ===============      <---     ==================
^  (Frame   __________________|^  |^  |^  |^_____________________
|  Data     ||_________________|  ||  ||  |____________________||
|  Pipe)    V|     (Socket Pipes) V|  V| (Socket Pipes)        V|
==============     ================   ==================   ================
 Video Socket       Logging Socket     Telemetry Socket      Pilot Socket
==============     ================   ==================   ================
____________________________________________________________________________
[|^]  Video             [|^] Logging  Telemetry [|^]             Pilot [|^]
[||]  socket            [||] socket      socket [||]            socket [||]
[V|]  conn              [V|] conn          conn [V|]              conn [V|]
____________________________________________________________________________
==============     ================   ==================   ================
 Video Socket       Logging Socket     Telemetry Socket      Pilot Socket
==============     ================   ==================   ================
____________________________________________________________________________
                    [SUB] (All of Pico's Containers/Files)
"""

# Python
from __future__ import print_function
import multiprocessing as mp
from multiprocessing import set_start_method, get_context
import os
import sys as system  # sys is some other import
import grpc
import socket
from datetime import datetime
import time
import subprocess as sub
from functools import partial
import pickle
import struct

# GUI
import tkinter as tk
from tkinter import *
from tkinter import messagebox

# External libs
from PIL import ImageTk
from PIL import Image as PILImage  # Image is a tkinter import
import numpy as np
import cv2

# Internal
import socket_route_guide_pb2
import socket_route_guide_pb2_grpc

# Command
grpc_remote_client_hostname_default = '192.168.0.133'
grpc_remote_client_port_default = '50051'
grpc_command_port_default = '50052'

# GUI
top_bar_size = 30
edge_size = 1
resolution = (1600, 900)  # Gui root window size
remote_resolution = (640, 480)  # Remote camera
gui_update_ms = 10  # Update time for gui elements in ms

# Video
use_udp = False  # Do not touch UDP. Broken right now.
sock_video_hostname_default = 'localhost'
sock_video_port_default = '50001'
sock_logging_port_default = '50002'
sock_telemetry_port_default = '50003'
sock_pilot_port_default = '50004'


def request_to_value(r):
    """Converts grpc responses into strings, stripping quotes.
    """
    first = -1
    result = ''
    for i in range(len(r)):
        if r[i] == '\"' and first == -1:
            first = i
        elif r[i] == '\"' and first != -1:
            result = r[first+1:i]
    return result


class GrpcClient:
    """Handles GRPC clients with related methods.
    """
    def __init__(self, hostname, port, logger):
        self.remote_client = str(hostname)
        self.port = str(port)
        self._channel = grpc.insecure_channel(self.remote_client + ':' + self.port)
        self._stub = socket_route_guide_pb2_grpc.SocketGRPCStub(self._channel)
        self.logger = logger
        logger.log('[GRPC] Started up client.')

    def send(self, request):
        """Sends argument over GRPC
        @:param request to be sent over GRPC, as defined in protobuf
        """
        if (request == 2) or (request == '2'):
            self.logger.log('[GRPC] Sending socket startup request to server...')
        try:
            response = self._stub.SendSocketRequest(socket_route_guide_pb2.MsgRequest(req=(str(request))))
        except grpc._channel._InactiveRpcError:
            self.logger.log('[GRPC] Error communicating with server. (Is it on?)')
            response = '!'
        return response

    def close(self):
        """Closes GRPC channel
        """
        self._channel.close()


class LoggerWrapper:
    """Provides easy methods for logging with formatting.
    """
    def __init__(self, showtime=True):
        self.queue = mp.Queue()
        self.add_timestamp = showtime

    def log(self, string):
        """Logs the string
        :param string: Adds to logger queue
        """
        if self.add_timestamp:
            self.queue.put(str(datetime.now().strftime('[%H:%M:%S]')) + str(string.strip()) + '\n')
        else:
            self.queue.put(str(string.strip()) + '\n')

    def dequeue(self):
        """Removes first element from queue
        :return:
        """
        if self.queue.qsize() > 0:
            return self.queue.get()
        else:
            return None


class Window(tk.Frame):
    """ Window class, handles the GUI's 'master' or 'root' window and all subwindows
    """
    def __init__(self, master=None):
        # Main window
        tk.Frame.__init__(self, master)
        self.master = master
        self.closing = False

        # Top Bar
        self.top_bar = tk.Frame(master=self.master, width=resolution[0], height=30, bg='black')

        # Logging Window
        self.logging_window = tk.Frame(master=self.master, width=640, height=480, bg='white')

        # Video Frame
        self.video_window = tk.Canvas(master=self.master, width=640, height=480, bg='green')
        self.video_window_no_img = ImageTk.PhotoImage(PILImage.open('img/not_loaded.png'))
        self.video_window_img = self.video_window.create_image((1, 1), anchor=tk.NW, image=self.video_window_no_img)
        # Alternate between frames on video stream because of tkinter's gc
        self.img = ImageTk.PhotoImage(PILImage.open('img/not_loaded_2.png'))
        self.img_2 = ImageTk.PhotoImage(PILImage.open('img/not_loaded_2.png'))
        self.frame_counter = 0

        # Info Window
        self.info_window = tk.Frame(master=self.master, width=300, height=640, bg='white')
        # Text
        self.info_all_text = tk.Label(master=self.info_window, text='ALL STATUSES:', bd=0, bg='white')
        self.info_all_comms_text = tk.Label(master=self.info_window, text='COMMS @' + grpc_remote_client_hostname_default, bd=0, bg='black', fg='white')
        # Config
        self.config_is_set = False
        self.config_status_button = tk.Button(master=self.info_window, text='     ', bg='red')
        self.config_status_text = tk.Label(master=self.info_window, text='[Config Set]', bd=0, anchor='w', bg='white', justify=tk.LEFT)
        # CMD GRPC
        self.cmd_connected = False  # If command's grpc server is connected
        self.cmd_status_button = tk.Button(master=self.info_window, text='     ', bg='red')
        self.cmd_status_text = tk.Label(master=self.info_window, text='[CMD_GRPC]')
        self.cmd_status_port = tk.Label(master=self.info_window, text=':' + grpc_command_port_default, bd=0, anchor='w', bg='white', justify=tk.LEFT)
        # Video GRPC (to be deprecated)
        self.video_grpc_is_connected = False
        self.video_grpc_status_button = tk.Button(master=self.info_window, text='     ', bg='red')
        self.video_grpc_status_text = tk.Label(master=self.info_window, text='[VID_GRPC]', bd=0, anchor='w', bg='white', justify=tk.LEFT)
        self.video_grpc_status_port = tk.Label(master=self.info_window, text=':' + grpc_remote_client_port_default, bd=0, anchor='w', bg='white', justify=tk.LEFT)
        # Video Socket
        self.video_socket_is_enabled = tk.BooleanVar(value=False)  # Enable
        self.video_socket_enable_button = tk.Button(master=self.info_window, text='     ', bg='black')
        self.video_socket_enable_text = tk.Label(master=self.info_window, text='[VID_ENABLED]', bd=0, anchor='w', bg='white', justify=tk.LEFT)
        self.video_socket_is_connected = False  # Connection
        self.video_socket_connected_button = tk.Button(master=self.info_window, text='     ', bg='red')
        self.video_socket_status_text = tk.Label(master=self.info_window, text='[VID_SCK]', bd=0, anchor='w', bg='white', justify=tk.LEFT)
        self.video_socket_status_port = tk.Label(master=self.info_window, text=':' + sock_video_port_default, bd=0, anchor='w', bg='white', justify=tk.LEFT)
        # Logging Socket
        self.logging_socket_level = tk.IntVar(value=0)  # Enable/Level
        self.logging_socket_enable_button = tk.Button(master=self.info_window, text='     ', bg='black')
        self.logging_socket_enable_text = tk.Label(master=self.info_window, text='[LOG_ENABLED]', bd=0, anchor='w', bg='white', justify=tk.LEFT)
        self.logging_socket_is_connected = False  # Connection
        self.logging_socket_connected_button = tk.Button(master=self.info_window, text='     ', bg='red')
        self.logging_socket_status_text = tk.Label(master=self.info_window, text='[LOG_SCK]', bd=0, anchor='w', bg='white', justify=tk.LEFT)
        self.logging_socket_status_port = tk.Label(master=self.info_window, text=':' + sock_logging_port_default, bd=0, anchor='w', bg='white', justify=tk.LEFT)
        # Telemetry Socket
        self.telemetry_socket_enabled = tk.BooleanVar(value=False)  # Enable
        self.telemetry_socket_enable_button = tk.Button(master=self.info_window, text='     ', bg='black')
        self.telemetry_socket_enable_text = tk.Label(master=self.info_window, text='[TEL_ENABLED]', bd=0, anchor='w', bg='white', justify=tk.LEFT)
        self.telemetry_socket_is_connected = False  # Connection
        self.telemetry_socket_connected_button = tk.Button(master=self.info_window, text='     ', bg='red')
        self.telemetry_socket_status_text = tk.Label(master=self.info_window, text='[TEL_SCK]', bd=0, anchor='w', bg='white', justify=tk.LEFT)
        self.telemetry_socket_status_port = tk.Label(master=self.info_window, text=':' + sock_telemetry_port_default, bd=0, anchor='w', bg='white', justify=tk.LEFT)
        # Pilot Socket
        self.pilot_socket_enabled = tk.BooleanVar(value=False)  # Enable
        self.pilot_socket_enable_button = tk.Button(master=self.info_window, text='     ', bg='black')
        self.pilot_socket_enable_text = tk.Label(master=self.info_window, text='[PLT_ENABLED]', bd=0, anchor='w', bg='white', justify=tk.LEFT)
        self.pilot_socket_is_connected = False  # Connection
        self.pilot_socket_connected_button = tk.Button(master=self.info_window, text='     ', bg='red')
        self.pilot_socket_status_text = tk.Label(master=self.info_window, text='[PLT_SCK]', bd=0, anchor='w', bg='white', justify=tk.LEFT)
        self.pilot_socket_status_port = tk.Label(master=self.info_window, text=':' + sock_pilot_port_default, bd=0, anchor='w', bg='white', justify=tk.LEFT)
        # Mission
        self.mission_config_string = tk.StringVar(value='None')  # Mission to do this run
        self.mission_config_text = tk.Label(master=self.info_window, text='[MISSION]', bd=0, anchor='w', bg='white', justify=tk.LEFT)
        self.mission_config_text_current = tk.Label(master=self.info_window, text='None', bd=0, anchor='w', bg='white', justify=tk.LEFT)

        # Data I/O to other processes
        self.in_pipe = None
        self.out_pipe = None
        self.video_stream_pipe_in = None
        self.text = Text(self.logging_window)

        # Logger
        self.logger = LoggerWrapper()

        # Build and arrange windows
        self.init_window()
        self.update()

    def init_window(self):
        """Builds the master widget and all subwidgets, arranges all elements of GUI
        """
        # Root/master window
        self.master.title('SDSU Mechatronics Robosub External Interface')

        # Top Menu Bar
        self.top_bar.grid(column=0, row=0, padx=0, sticky='W')
        self.top_bar.wait_visibility()

        # Build buttons for top menu bar
        config_button = Button(master=self.top_bar, text='Config', justify=LEFT, anchor='w', command=partial(self.config_box))
        config_button.grid(column=0, row=0, sticky=W)

        video_start_button = Button(master=self.top_bar, text='Start Video', justify=LEFT, anchor='w', command=self.init_video_socket)
        video_start_button.grid(column=1, row=0, sticky=W)
        quit_button = Button(master=self.top_bar, text='Exit', justify=LEFT, anchor='w', command=self.client_exit)
        quit_button.grid(column=2, row=0, sticky=W)

        # Logging Window
        self.logging_window.grid(column=0, row=1)
        self.text.place(x=0, y=0)
        self.logger.log('[@GUI] Logger Initialized.')

        # Video Stream Window (GRPC/Socket)
        self.video_window.grid(column=1, row=1)
        # Info Window (Communications/Statuses)
        self.info_window.grid(column=3, row=1, sticky=NW)

        # Text
        self.info_all_text.grid(column=0, row=0, sticky=W, columnspan=3)
        self.info_all_comms_text.grid(column=0, row=2, sticky=W, columnspan=3)

        # Config
        self.config_status_button.grid(column=0, row=1, sticky=W)
        self.config_status_text.grid(column=1, row=1, sticky=W)

        # Video GRPC (will be deprecated)
        self.video_grpc_status_button.grid(column=0, row=3, sticky=W)
        self.video_grpc_status_text.grid(column=1, row=3, sticky=W)
        self.video_grpc_status_port.grid(column=2, row=3, sticky=W)

        # Command GPRC
        self.cmd_status_button.grid(column=0, row=4, sticky=W)
        self.cmd_status_text.grid(column=1, row=4, sticky=W)
        self.cmd_status_port.grid(column=2, row=4, sticky=W)

        # Video Socket
        self.video_socket_enable_button.grid(column=0, row=5, sticky=W)
        self.video_socket_enable_text.grid(column=1, row=5, sticky=W, columnspan=2)
        self.video_socket_connected_button.grid(column=3, row=5, sticky=W)
        self.video_socket_status_text.grid(column=4, row=5, sticky=W)
        self.video_socket_status_port.grid(column=5, row=5, sticky=W)

        # Logging Socket
        self.logging_socket_enable_button.grid(column=0, row=6, sticky=W)
        self.logging_socket_enable_text.grid(column=1, row=6, sticky=W, columnspan=2)
        self.logging_socket_connected_button.grid(column=3, row=6, sticky=W)
        self.logging_socket_status_text.grid(column=4, row=6, sticky=W)
        self.logging_socket_status_port.grid(column=5, row=6, sticky=W)

        # Telemetry Socket
        self.telemetry_socket_enable_button.grid(column=0, row=7, sticky=W)
        self.telemetry_socket_enable_text.grid(column=1, row=7, sticky=W, columnspan=2)
        self.telemetry_socket_connected_button.grid(column=3, row=7, sticky=W)
        self.telemetry_socket_status_text.grid(column=4, row=7, sticky=W)
        self.telemetry_socket_status_port.grid(column=5, row=7, sticky=W)

        # Pilot Socket
        self.pilot_socket_enable_button.grid(column=0, row=8, sticky=W)
        self.pilot_socket_enable_text.grid(column=1, row=8, sticky=W, columnspan=2)
        self.pilot_socket_connected_button.grid(column=3, row=8, sticky=W)
        self.pilot_socket_status_text.grid(column=4, row=8, sticky=W)
        self.pilot_socket_status_port.grid(column=5, row=8, sticky=W)

        # Mission
        self.mission_config_text.grid(column=0, row=9, sticky=W, columnspan=2)
        self.mission_config_text_current.grid(column=2, row=9, sticky=W, columnspan=2)

    @staticmethod
    def diag_box(message):
        """Creates a diag box with a string.
        This is kept as a test example.
        """
        messagebox.showinfo(title='Info', message=message)

    def config_box(self):
        """Creates a diag box to set the config for the sub.
        Must use this diag box to set the configuration before anything else happens on HOST.
        Only location in the program where current config can/should be modified.
        """
        top = tk.Toplevel(self.master)  # Call top level for a separate window
        config_diag = tk.Label(top, text='Set The Current Mission Configuration:',
                               pady=10,
                               justify='left',
                               anchor='nw')
        config_diag.grid(column=0, row=0, sticky=W, columnspan=2)
        # Video
        video_title = tk.Label(top, text='Video:')
        video_diag = tk.Label(top)
        video_title.grid(column=0, row=1, sticky=W)
        video_diag.grid(column=1, row=1, sticky=W, columnspan=2)
        # Logging
        logging_title = tk.Label(top, text='Logging:')
        logging_diag = tk.Label(top)
        logging_title.grid(column=0, row=2, sticky=W)
        logging_diag.grid(column=1, row=2, sticky=W, columnspan=2)
        # Telemetry
        telemetry_title = tk.Label(top, text='Telemetry:')
        telemetry_diag = tk.Label(top)
        telemetry_title.grid(column=0, row=3, sticky=W)
        telemetry_diag.grid(column=1, row=3, sticky=W, columnspan=2)
        # Pilot
        pilot_title = tk.Label(top, text='Pilot Control:')
        pilot_diag = tk.Label(top)
        pilot_title.grid(column=0, row=4, sticky=W)
        pilot_diag.grid(column=1, row=4, sticky=W, columnspan=2)
        # Mission
        mission_title = tk.Label(top, text='Mission:')
        mission_diag = tk.Label(top)
        mission_title.grid(column=0, row=5, sticky=W)
        mission_diag.grid(column=1, row=5, sticky=W, columnspan=2)
        # Window Exit
        confirm_button = tk.Button(master=top, text='Confirm Settings', command=partial(self.confirm_settings, top))
        confirm_button.grid(column=0, row=6, sticky=W, columnspan=2)

        # Radio Buttons
        video_radio_enable = Radiobutton(video_diag,
                                         text='Enable',
                                         variable=self.video_socket_is_enabled,
                                         value=1,
                                         command=partial(self.val_set, self.video_socket_is_enabled, True)).grid(column=0, row=0)
        video_radio_disable = Radiobutton(video_diag,
                                          text='Disable',
                                          variable=self.video_socket_is_enabled,
                                          value=0,
                                          command=partial(self.val_set, self.video_socket_is_enabled, False)).grid(column=1, row=0)
        logging_radio_enable_debug = Radiobutton(logging_diag,
                                                 text='Debug',
                                                 variable=self.logging_socket_level,
                                                 value=2,
                                                 command=partial(self.val_set, self.logging_socket_level, 2)).grid(column=0, row=0)
        logging_radio_enable_info = Radiobutton(logging_diag,
                                                text='Info',
                                                variable=self.logging_socket_level,
                                                value=1,
                                                command=partial(self.val_set, self.logging_socket_level, 1)).grid(column=1, row=0)
        logging_radio_enable_disable = Radiobutton(logging_diag,
                                                   text='Disable',
                                                   variable=self.logging_socket_level,
                                                   value=0,
                                                   command=partial(self.val_set, self.logging_socket_level, 0)).grid(column=2, row=0)
        telemetry_radio_enable = Radiobutton(telemetry_diag,
                                             text='Enable',
                                             variable=self.telemetry_socket_enabled,
                                             value=1,
                                             command=partial(self.val_set, self.telemetry_socket_enabled, True)).grid(column=0, row=0)
        telemetry_radio_disable = Radiobutton(telemetry_diag,
                                              text='Disable',
                                              variable=self.telemetry_socket_enabled,
                                              value=0,
                                              command=partial(self.val_set, self.telemetry_socket_enabled, False)).grid(column=1, row=0)
        pilot_radio_enable = Radiobutton(pilot_diag,
                                         text='Enable',
                                         variable=self.pilot_socket_enabled,
                                         value=1,
                                         command=partial(self.val_set, self.pilot_socket_enabled, True)).grid(column=0, row=0)
        pilot_radio_disable = Radiobutton(pilot_diag,
                                          text='Disable',
                                          variable=self.pilot_socket_enabled,
                                          value=0,
                                          command=partial(self.val_set, self.pilot_socket_enabled, False)).grid(column=1, row=0)
        mission_radio_all = Radiobutton(mission_diag,
                                        text='All',
                                        variable=self.mission_config_string,
                                        value=4,
                                        command=partial(self.val_set, self.mission_config_string, 'All')).grid(column=0, row=0)
        mission_radio_gate = Radiobutton(mission_diag,
                                         text='Gate',
                                         variable=self.mission_config_string,
                                         value=3,
                                         command=partial(self.val_set, self.mission_config_string, 'Gate')).grid(column=1, row=0)
        mission_radio_buoy = Radiobutton(mission_diag,
                                         text='Buoy',
                                         variable=self.mission_config_string,
                                         value=2,
                                         command=partial(self.val_set, self.mission_config_string, 'Buoy')).grid(column=2, row=0)
        mission_radio_rise = Radiobutton(mission_diag,
                                         text='Rise',
                                         variable=self.mission_config_string,
                                         value=1,
                                         command=partial(self.val_set, self.mission_config_string, 'Rise')).grid(column=3, row=0)
        mission_radio_none = Radiobutton(mission_diag,
                                         text='None',
                                         variable=self.mission_config_string,
                                         value=0,
                                         command=partial(self.val_set, self.mission_config_string, 'None')).grid(column=4, row=0)

    @staticmethod
    def val_set(old, new):
        """tkinter doesn't like calling old.set() within command= arguments, so it's done here!
        """
        old.set(new)

    def confirm_settings(self, top):
        """Closes the config settings dialog box; changes variable to signify config is set.
        :param top: Window
        """
        self.config_is_set = True
        top.destroy()

    def client_exit(self):
        """Closes client.
        TODO Needs to be done more gracefully at process level.
        """
        self.master.title('Closing...')
        self.closing = True

        # Last thing done
        self.destroy()
        system.exit()

    def init_video_socket(self):
        """Initializes video socket connection from gui
        """
        self.out_pipe.send(('video', 'gui', 'initialize'))

    def run_logger(self):
        """Adds the first element in the queue to the logs.
        """
        if self.logger.queue.qsize() > 0:
            self.text.insert(END, self.logger.dequeue())
            self.text.see('end')

    @staticmethod
    def update_button(button, enabled):
        """Swaps button color if it doesn't match enabled.
        NOTE: Called for red/green buttons.
        """
        if (button.config('bg')[4] == 'red') and enabled:
            button.configure(button, bg='green')
        elif (button.config('bg')[4] == 'green') and not enabled:
            button.configure(button, bg='red')

    @staticmethod
    def update_button_enable(button, enabled):
        """Swaps button color if it doesn't match enabled.
        NOTE: Called for black/yellow buttons.
        """
        if (button.config('bg')[4] == 'black') and enabled:
            button.configure(button, bg='yellow')
        elif (button.config('bg')[4] == 'yellow') and not enabled:
            button.configure(button, bg='black')

    @staticmethod
    def update_button_int(button, status):
        """Swaps button color if it doesn't match status.
        NOTE: Called for different levels and black/yellow.
        """
        if (button.config('bg')[4] == 'black') and (status > 0):
            button.configure(button, bg='yellow')
            button.configure(button, text='  ' + str(status) + '  ')
        elif (button.config('bg')[4] == 'yellow') and (status == 0):
            button.configure(button, bg='black')
            button.configure(button, text='     ')

    @staticmethod
    def update_status_string(text, status):
        """Sets text to status.
        NOTE: Called for setting text boxes in Labels.
        """
        if text.config('text')[0] != status:
            text.configure(text, text=status)

    def update_frames(self):
        """Checks pipe for data and updates frame in box
        """
        if self.video_stream_pipe_in is not None:  # Checks for proper initialization first
            conn = mp.connection.wait([self.video_stream_pipe_in], timeout=-1)
            if len(conn) > 0:
                frame = conn[0].recv()
                b, g, r = cv2.split(frame)
                image = cv2.merge((r, g, b))
                self.frame_counter += 1
                if self.frame_counter % 2 == 1:
                    self.img_2 = ImageTk.PhotoImage(PILImage.fromarray(image))
                    self.video_window.itemconfig(self.video_window_img, image=self.img_2)
                else:
                    self.img = ImageTk.PhotoImage(PILImage.fromarray(image))
                    self.video_window.itemconfig(self.video_window_img, image=self.img)

    def read_pipe(self):
        """Checks input pipe for info from other processes, processes commands here
        """
        cmd = []
        if self.in_pipe is not None:  # Checks for proper initialization first
            conn = mp.connection.wait([self.in_pipe], timeout=-1)
            if len(conn) > 0:
                cmd = conn[0].recv()
                if cmd[2] == 'conn_grpc':
                    self.video_grpc_is_connected = True
                elif cmd[2] == 'no_conn_grpc':
                    self.video_grpc_is_connected = False
                elif cmd[2] == 'conn_socket':
                    self.video_socket_is_connected = True
                elif cmd[2] == 'no_conn_socket':
                    self.video_socket_is_connected = False

    def update(self):
        """Update function to read elements from other processes into the GUI
        Overriden from tkinter's window class
        """
        # Manual on update functions below:
        self.run_logger()
        self.update_frames()
        # Update all button statuses
        self.update_button(self.video_grpc_status_button, self.video_grpc_is_connected)
        self.update_button(self.video_socket_connected_button, self.video_socket_is_connected)
        self.update_button(self.config_status_button, self.config_is_set)
        self.update_button_enable(self.video_socket_enable_button, self.video_socket_is_enabled.get())
        self.update_button_enable(self.telemetry_socket_enable_button, self.telemetry_socket_enabled.get())
        self.update_button_enable(self.pilot_socket_enable_button, self.pilot_socket_enabled.get())
        self.update_button_int(self.logging_socket_enable_button, self.logging_socket_level.get())
        self.update_status_string(self.mission_config_text_current, self.mission_config_string.get())
        # Check for pipe updates
        self.read_pipe()
        # Loop, does not recurse despite appearance
        self.after(gui_update_ms, self.update)


def gui_proc_main(gui_input, gui_output, gui_logger, video_stream_pipe_in):
    """GUI Driver code
    """
    # Build Application
    root_window = tk.Tk()
    root_window.geometry(str(resolution[0] - edge_size - edge_size) + "x" + str(resolution[1] - top_bar_size - edge_size - edge_size))
    application = Window(master=root_window)

    # Queues for multiprocessing passed into object
    application.logger = gui_logger
    application.in_pipe = gui_input
    application.out_pipe = gui_output
    application.video_stream_pipe_in = video_stream_pipe_in
    root_window.mainloop()


def video_proc_udp(logger, video_pipe_in, video_pipe_out, video_stream_out):
    """Video socket driver code, run on a UDP connection.
    NOTE: Only work on this function if trying to fix for better performance.
    Should not be called otherwise. Left in place for testing purposes.
    """
    code = ''
    client = None
    socket_started = False
    socket_port = 0
    while True:
        # Wait for initialization code
        conn = mp.connection.wait([video_pipe_in], timeout=-1)
        if len(conn) > 0:
            code = str(conn[0].recv()[2])
        if code == '':
            pass
        elif code == 'initialize':
            # Start up a GRPC client
            client = GrpcClient(hostname=grpc_remote_client_hostname_default,
                                port=grpc_remote_client_port_default,
                                logger=logger)
            response = client.send(2)
            response = request_to_value(str(response))
            if response[0] == '@':
                video_pipe_out.send(('gui', 'video', 'conn_grpc'))
                socket_port = int(response[1:])
                code = 'start_socket'
        if code == 'start_socket':
            socket_started = True
            video_pipe_out.send(('gui', 'video', 'conn_socket'))
            code = ''
        elif code == 'stop_socket':
            socket_started = False
            video_pipe_out.send(('gui', 'video', 'no_conn_socket'))
        # Connect over UDP
        if socket_started:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect((sock_video_hostname_default, socket_port))
                s.settimeout(1)
                sock_resp = b'1'
                s.sendall(sock_resp)
                data = s.recv(1200)

                buffering = True
                t1 = time.time()
                while buffering:
                    more = s.recv(1200)

                    if more == b'STOP_CODE':
                        buffering = False
                    else:
                        data += more
                t2 = time.time()
                print(t1)
                print(t2)
                print(str(t2-t1) + ' seconds')
                print(len(data))
                print('[@VPROC] Received data of size ' + str(len(data)))
                data = np.frombuffer(buffer=data, dtype=np.uint8)
                sc_current = data.reshape(data, (480, 640, 3))
                video_stream_out.send(sc_current)
            s.close()


def video_proc_tcp(logger, video_pipe_in, video_pipe_out, video_stream_out):
    """Video socket driver code, running on a TCP connection.
    Notes:
        This is first establishes ITS OWN grpc conection when the pipe sends in a request to start.
        This is known as the 'video_grpc' connection on port 50051.
        This will be changed later so the socket connection is enabled directly.
    """
    code = ''
    client = None
    socket_started = False
    socket_port = 0
    while True:
        # Wait for this process to receive info from the pipe, read it in when it does
        conn = mp.connection.wait([video_pipe_in], timeout=-1)
        if len(conn) > 0:
            code = str(conn[0].recv()[2])
            print('video_proc_tcp received :' + str(code))
        if code == '':
            pass
        elif code == 'initialize':
            # Start up a GRPC client
            client = GrpcClient(hostname=grpc_remote_client_hostname_default,
                                port=grpc_remote_client_port_default,
                                logger=logger)
            response = client.send(2)  # Error handles, returning ! on fail
            if response == '!':
                code = ''
                video_pipe_out.send(('gui', 'video', 'no_conn_grpc'))
            else:
                logger.log('[@VPROC TCP]' + str(response))
                response = request_to_value(str(response))
            if response[0] == '@':
                # Tell gui grpc for video is connected
                video_pipe_out.send(('gui', 'video', 'conn_grpc'))
                socket_port = int(response[1:])
                code = 'start_socket'
        if code == 'start_socket':
            socket_started = True
            video_pipe_out.send(('gui', 'video', 'conn_socket'))
            code = ''
        elif code == 'stop_socket':
            socket_started = False
            video_pipe_out.send(('gui', 'video', 'no_conn_socket'))
        # Connect over TCP
        if socket_started:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.connect((sock_video_hostname_default, socket_port))
                data = b''
                payload_size = struct.calcsize('>L')
                # Get frame data and send to video_stream_out
                while True:
                    s.sendall(b'1')
                    while len(data) < payload_size:
                        data += s.recv(4096)

                    packed_msg_size = data[:payload_size]
                    data = data[payload_size:]
                    msg_size = struct.unpack('>L', packed_msg_size)[0]
                    while len(data) < msg_size:
                        data += s.recv(4096)
                    frame_data = data[:msg_size]
                    data = data[msg_size:]
                    frame = pickle.loads(frame_data, fix_imports=True, encoding='bytes')
                    frame = cv2.imdecode(frame, cv2.IMREAD_COLOR)
                    # Pipe video output to gui
                    video_stream_out.send(frame)


def router(logger,  # Gui logger
           from_gui_pipe_in, to_gui_pipe_out,  # Gui pipe
           from_video_pipe_in, to_video_pipe_out,  # Video pipe
           from_logger_pipe_in, to_logger_pipe_out,
           from_telemetry_pipe_in, to_telemetry_pipe_out,
           from_pilot_pipe_in, to_pilot_pipe_out,
           from_main_pipe_in, to_main_pipe_out
           ):
    """Routes messages between pipes, given destination of the message.
    """
    while True:
        # Wait on all pipe ins. See documentation for system communication pathways for more information.
        conn = mp.connection.wait([from_gui_pipe_in,
                                   from_video_pipe_in], timeout=-1)
        if len(conn) > 0:
            result = conn[0].recv()
            if result[0] == 'video':  # Send to video
                to_video_pipe_out.send(result)
            elif result[0] == 'gui':  # Send to gui
                to_gui_pipe_out.send(result)


def main():
    """Main driver code, handles all processes.
    """
    if os.name == 'nt':  # Fix for linux
        context = get_context('spawn')
    else:
        context = get_context('fork')

    # Main pipe (for this function)
    pipe_to_main_from_router, main_pipe_in_from_router = context.Pipe()
    pipe_to_router_from_main, pipe_in_from_main = context.Pipe()

    # Video stream pipe
    pipe_to_gui_from_video, pipe_in_from_video_stream = context.Pipe()

    # Gui
    gui_logger = LoggerWrapper()
    pipe_to_gui_from_router, gui_pipe_in_from_router = context.Pipe()
    pipe_to_router_from_gui, pipe_in_from_gui = context.Pipe()
    gui_proc = context.Process(target=gui_proc_main, args=(gui_pipe_in_from_router, pipe_to_router_from_gui, gui_logger, pipe_in_from_video_stream))
    gui_proc.start()
    gui_logger.log('[@GUI] Gui Initialized.')  # Log to Gui from main process

    # Video socket
    pipe_to_video_from_router, vid_pipe_in_from_router = context.Pipe()
    pipe_to_router_from_video, pipe_in_from_video = context.Pipe()
    if use_udp:
        video_proc = context.Process(target=video_proc_udp, args=(gui_logger, vid_pipe_in_from_router, pipe_to_router_from_video, pipe_to_gui_from_video))
    else:
        video_proc = context.Process(target=video_proc_tcp, args=(gui_logger, vid_pipe_in_from_router, pipe_to_router_from_video, pipe_to_gui_from_video))
    video_proc.start()

    # Logging socket
    pipe_to_logger_from_router, log_pipe_in_from_router = context.Pipe()
    pipe_to_router_from_logger, pipe_in_from_logger = context.Pipe()

    # Telemetry socket
    pipe_to_telemetry_from_router, tel_pipe_in_from_router = context.Pipe()
    pipe_to_router_from_telemetry, pipe_in_from_telemetry = context.Pipe()

    # Pilot socket
    pipe_to_pilot_from_router, plt_pipe_in_from_router = context.Pipe()
    pipe_to_router_from_pilot, pipe_in_from_pilot = context.Pipe()

    # Router
    router_proc = context.Process(target=router, args=(gui_logger,
                                                    pipe_in_from_gui, pipe_to_gui_from_router,  # Gui
                                                    pipe_in_from_video, pipe_to_video_from_router,  # Video
                                                    pipe_in_from_logger, pipe_to_logger_from_router,  # Logger
                                                    pipe_in_from_telemetry, pipe_to_telemetry_from_router,  # Telemetry
                                                    pipe_in_from_pilot, pipe_to_pilot_from_router,  # Pilot
                                                    pipe_in_from_main, pipe_to_main_from_router))  # Main
    router_proc.start()


# Program Entry Point
if __name__ == '__main__':
    n = os.name
    if n == 'nt':  # Fix for Linux
        set_start_method('spawn')
    else:
        set_start_method('fork')
    print(__name__ + 'started on ' + n + ' at ' + str(os.getpid()))  # Kept for testing
    main()

else:
    print('Spawned multiprocess at PID: ' + __name__ + ' ' + str(os.getpid()))  # Kept for testing
