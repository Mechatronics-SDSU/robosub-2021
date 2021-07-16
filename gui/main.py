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
___________________________________________________________________________________
                            (Controller Input Pipe)
           |-------------------------------------------------------------------
           |                                                                   |
=============   (Gui Pipe)   =============== (Parent Pipe) ==================  |
=tkinter GUI=      --->      =    Router   =      --->     = Parent Process =  |
=============      <---      ===============      <---     ==================  |
^  (Frame   __________________|^  |^  |^  |^_____________________              |
|  Data     ||_________________|  ||  ||  |____________________||              |
|  Pipe)    V|     (Socket Pipes) V|  V| (Socket Pipes)        V|              |
==============     ================   ==================   ================    |
=Video Socket=     =Logging Socket=   =Telemetry Socket=   = Pilot Socket = <--|
==============     ================   ==================   ================
___________________________________________________________________________________
[|^]  Video             [|^] Logging  Telemetry [|^]             Pilot [|^]
[||]  socket            [||] socket      socket [||]            socket [||]
[V|]  conn              [V|] conn          conn [V|]              conn [V|]
____________________________________________________________________________
==============     ================   ==================   ================
=Video Socket=     =Logging Socket=   =Telemetry Socket=   = Pilot Socket =
==============     ================   ==================   ================
___________________________________________________________________________________
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
import pygame as pg

# GUI
import tkinter as tk
from tkinter import *
from tkinter import messagebox, simpledialog

# External libs
from PIL import ImageTk
from PIL import Image as PILImage  # Image is a tkinter import
import numpy as np
import cv2

# Internal
import src.utils.cmd_pb2 as cmd_pb2
import src.utils.cmd_pb2_grpc as cmd_pb2_grpc
import src.utils.ip_config as ip_config
import src.utils.logger as sub_logging
import src.utils.telemetry as sensor_tel
import src.utils.pilot as ctrl_pilot
import src.utils.command_configuration as cmd


system.modules['ip_config'] = ip_config

# Command
grpc_remote_client_port_default = '50051'
default_hostname = 'localhost'
default_command_port_grpc = 50052
default_port_video_socket = 50001
default_port_logging_socket = 50002
default_port_telemetry_socket = 50003
default_port_pilot_socket = 50004

# GUI
top_bar_size = 30
edge_size = 1
resolution = (1600, 900)  # Gui root window size
remote_resolution = (640, 480)  # Remote camera
gui_update_ms = 10  # Update time for gui elements in ms

use_udp = False  # Do not touch UDP unless testing. Broken right now.


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


def get_int_from_bool(b):
    """Returns int version of a boolean.
    """
    if b:
        return 1
    else:
        return 0


def log_parse(input_data):
    """Logs sometimes arrive in >1 at a time.
    Parses them out and returns a list.
    :return: List of all logs.
    """
    input_data = bytes.decode(input_data, encoding='utf-8')
    result = []
    s = ''
    j = 0
    for i in range(len(input_data)):
        if (input_data[i] == '{') and (s == ''):
            j = i
            s = '{'
        elif (input_data[i] == '}') and (s == '{'):
            result.append(input_data[(j + 1):(i - 1)])
            s = ''
    return result


class CMDGrpcClient:
    """Handles GRPC clients with related methods.
    """
    def __init__(self, hostname, port, logger):
        self.remote_client = str(hostname)
        self.port = str(port)
        self._channel = grpc.insecure_channel(self.remote_client + ':' + self.port)
        self._stub = cmd_pb2_grpc.CommandGRPCStub(self._channel)
        self.logger = logger
        logger.log('[GRPC] Started up client. ' + self.remote_client + ':' + self.port)

    def send(self, request):
        """Sends argument over GRPC
        @:param request to be sent over GRPC, as defined in protobuf
        """
        if (request == 1) or (request == '1'):
            self.logger.log('[GRPC] Sending socket startup request to server...')
        try:
            response = self._stub.SendCommandRequest(cmd_pb2.MsgRequest(req=(str(request))))
            response = request_to_value(str(response))
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
    """Window class, handles the GUI's 'master' or 'root' window and all subwindows
    """
    def __init__(self, pilot_pipe, master=None):
        # Load ports from config file or set to defaults
        self.remote_hostname = default_hostname
        self.port_command_grpc = default_command_port_grpc
        self.port_video_socket = default_port_video_socket
        self.port_logging_socket = default_port_logging_socket
        self.port_telemetry_socket = default_port_telemetry_socket
        self.port_pilot_socket = default_port_pilot_socket
        self.cfg_file_path = 'config.pickle'
        if os.path.exists(self.cfg_file_path):
            ip = ip_config.load_config_from_file(self.cfg_file_path)
            self.port_command_grpc = ip.grpc_port
            self.port_video_socket = ip.video_port
            self.port_logging_socket = ip.logging_port
            self.port_telemetry_socket = ip.telemetry_port
            self.port_pilot_socket = ip.pilot_port

        # Pygame for controller
        pg.init()
        pg.joystick.init()
        self.js = pg.joystick.Joystick(0)
        self.js.init()

        # Main window
        tk.Frame.__init__(self, master)
        self.master = master
        self.closing = False

        # Top Bar
        self.top_bar = tk.Frame(master=self.master, width=resolution[0], height=30, bg='white')

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
        self.info_all_comms_text = tk.Label(master=self.info_window, text='COMMS @' + self.remote_hostname, bd=0, bg='black', fg='white')
        # Config
        self.config_is_set = False
        self.cmd_config = None
        self.config_status_button = tk.Button(master=self.info_window, text='     ', bg='red')
        self.config_status_text = tk.Label(master=self.info_window, text='[Config Set]', bd=0, anchor='w', bg='white', justify=tk.LEFT)
        # CMD GRPC
        self.cmd_connected = False  # If command's grpc server is connected
        self.cmd_status_button = tk.Button(master=self.info_window, text='     ', bg='red')
        self.cmd_status_text = tk.Label(master=self.info_window, text='[CMD_GRPC]')
        self.cmd_status_port = tk.Label(master=self.info_window, text=':' + str(self.port_command_grpc), bd=0, anchor='w', bg='white', justify=tk.LEFT)
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
        self.video_socket_status_port = tk.Label(master=self.info_window, text=':' + str(self.port_video_socket), bd=0, anchor='w', bg='white', justify=tk.LEFT)
        # Logging Socket
        self.logging_socket_level = tk.IntVar(value=0)  # Enable/Level
        self.logging_socket_enable_button = tk.Button(master=self.info_window, text='     ', bg='black')
        self.logging_socket_enable_text = tk.Label(master=self.info_window, text='[LOG_ENABLED]', bd=0, anchor='w', bg='white', justify=tk.LEFT)
        self.logging_socket_is_connected = False  # Connection
        self.logging_socket_connected_button = tk.Button(master=self.info_window, text='     ', bg='red')
        self.logging_socket_status_text = tk.Label(master=self.info_window, text='[LOG_SCK]', bd=0, anchor='w', bg='white', justify=tk.LEFT)
        self.logging_socket_status_port = tk.Label(master=self.info_window, text=':' + str(self.port_logging_socket), bd=0, anchor='w', bg='white', justify=tk.LEFT)
        self.remote_logging_queue = []
        # Telemetry Socket
        self.telemetry_socket_is_enabled = tk.BooleanVar(value=False)  # Enable
        self.telemetry_socket_enable_button = tk.Button(master=self.info_window, text='     ', bg='black')
        self.telemetry_socket_enable_text = tk.Label(master=self.info_window, text='[TEL_ENABLED]', bd=0, anchor='w', bg='white', justify=tk.LEFT)
        self.telemetry_socket_is_connected = False  # Connection
        self.telemetry_socket_connected_button = tk.Button(master=self.info_window, text='     ', bg='red')
        self.telemetry_socket_status_text = tk.Label(master=self.info_window, text='[TEL_SCK]', bd=0, anchor='w', bg='white', justify=tk.LEFT)
        self.telemetry_socket_status_port = tk.Label(master=self.info_window, text=':' + str(self.port_telemetry_socket), bd=0, anchor='w', bg='white', justify=tk.LEFT)
        self.telemetry_current_state = sensor_tel.Telemetry()
        # Pilot Socket
        self.pilot_socket_is_enabled = tk.BooleanVar(value=False)  # Enable
        self.pilot_socket_enable_button = tk.Button(master=self.info_window, text='     ', bg='black')
        self.pilot_socket_enable_text = tk.Label(master=self.info_window, text='[PLT_ENABLED]', bd=0, anchor='w', bg='white', justify=tk.LEFT)
        self.pilot_socket_is_connected = False  # Connection
        self.pilot_socket_connected_button = tk.Button(master=self.info_window, text='     ', bg='red')
        self.pilot_socket_status_text = tk.Label(master=self.info_window, text='[PLT_SCK]', bd=0, anchor='w', bg='white', justify=tk.LEFT)
        self.pilot_socket_status_port = tk.Label(master=self.info_window, text=':' + str(self.port_pilot_socket), bd=0, anchor='w', bg='white', justify=tk.LEFT)
        # Mission
        self.mission_config_string = tk.StringVar(value='None')  # Mission to do this run
        self.mission_config_text = tk.Label(master=self.info_window, text='[MISSION]', bd=0, anchor='w', bg='white', justify=tk.LEFT)
        self.mission_config_text_current = tk.Label(master=self.info_window, text='None', bd=0, anchor='w', bg='white', justify=tk.LEFT)

        # Telemetry Window
        self.telemetry_window = tk.Frame(master=self.master, width=640, height=350, bg='white')
        self.telemetry_colpad = tk.Label(master=self.telemetry_window, text='Telemetry Data:', bd=0, anchor='w', bg='white',
                                         justify=tk.LEFT)
        # Sensors
        self.accelerometer_text = tk.Label(master=self.telemetry_window, text='Accel', bd=0, anchor='w', bg='white',
                                           justify=tk.LEFT)
        self.accelerometer_val = tk.Label(master=self.telemetry_window, text=str(
            self.telemetry_current_state.sensors['accelerometer']), bd=0, anchor='w', bg='white', justify=tk.LEFT)
        self.magnetometer_text = tk.Label(master=self.telemetry_window, text='Mag', bd=0, anchor='w', bg='white',
                                          justify=tk.LEFT)
        self.magnetometer_val = tk.Label(master=self.telemetry_window, text=str(
            self.telemetry_current_state.sensors['magnetometer']), bd=0, anchor='w', bg='white', justify=tk.LEFT)
        self.pressure_trans_text = tk.Label(master=self.telemetry_window, text='Pres_T', bd=0, anchor='w', bg='white',
                                            justify=tk.LEFT)
        self.pressure_trans_val = tk.Label(master=self.telemetry_window, text=str(
            self.telemetry_current_state.sensors['pressure_transducer']), bd=0, anchor='w', bg='white', justify=tk.LEFT)
        self.gyroscope_text = tk.Label(master=self.telemetry_window, text='Gyro', bd=0, anchor='w', bg='white',
                                       justify=tk.LEFT)
        self.gyroscope_val = tk.Label(master=self.telemetry_window, text=str(
            self.telemetry_current_state.sensors['gyroscope']), bd=0, anchor='w', bg='white', justify=tk.LEFT)
        self.voltmeter_text = tk.Label(master=self.telemetry_window, text='Volts', bd=0, anchor='w', bg='white',
                                       justify=tk.LEFT)
        self.voltmeter_val = tk.Label(master=self.telemetry_window, text=str(
            self.telemetry_current_state.sensors['voltmeter']), bd=0, anchor='w', bg='white', justify=tk.LEFT)
        self.battery_current_text = tk.Label(master=self.telemetry_window, text='Bat_I', bd=0, anchor='w', bg='white',
                                             justify=tk.LEFT)
        self.battery_current_val = tk.Label(master=self.telemetry_window, text=str(
            self.telemetry_current_state.sensors['battery_current']), bd=0, anchor='w', bg='white', justify=tk.LEFT)
        self.roll_text = tk.Label(master=self.telemetry_window, text='Roll', bd=0, anchor='w', bg='white',
                                  justify=tk.LEFT)
        self.roll_val = tk.Label(master=self.telemetry_window, text=str(
            self.telemetry_current_state.sensors['roll']), bd=0, anchor='w', bg='white', justify=tk.LEFT)
        self.pitch_text = tk.Label(master=self.telemetry_window, text='Pitch', bd=0, anchor='w', bg='white',
                                   justify=tk.LEFT)
        self.pitch_val = tk.Label(master=self.telemetry_window, text=str(
            self.telemetry_current_state.sensors['pitch']), bd=0, anchor='w', bg='white', justify=tk.LEFT)
        self.yaw_text = tk.Label(master=self.telemetry_window, text='Yaw', bd=0, anchor='w', bg='white',
                                 justify=tk.LEFT)
        self.yaw_val = tk.Label(master=self.telemetry_window, text=str(
            self.telemetry_current_state.sensors['yaw']), bd=0, anchor='w', bg='white', justify=tk.LEFT)
        self.auto_button_text = tk.Label(master=self.telemetry_window, text='B_Auto', bd=0, anchor='w', bg='white',
                                       justify=tk.LEFT)
        self.auto_button_val = tk.Label(master=self.telemetry_window, text=str(
            self.telemetry_current_state.sensors['auto_button']), bd=0, anchor='w', bg='white', justify=tk.LEFT)
        self.kill_button_text = tk.Label(master=self.telemetry_window, text='B_Kill', bd=0, anchor='w', bg='white',
                                       justify=tk.LEFT)
        self.kill_button_val = tk.Label(master=self.telemetry_window, text=str(
            self.telemetry_current_state.sensors['kill_button']), bd=0, anchor='w', bg='white', justify=tk.LEFT)

        # Controller Window
        self.controller_window = tk.Frame(master=self.master, width=640, height=350, bg='white')
        # Controller inputs
        self.current_control_inputs = None
        self.ctrl_n_button = tk.Button(master=self.controller_window, text='  N  ', bg='white')
        self.ctrl_s_button = tk.Button(master=self.controller_window, text='  S  ', bg='white')
        self.ctrl_e_button = tk.Button(master=self.controller_window, text='  E  ', bg='white')
        self.ctrl_w_button = tk.Button(master=self.controller_window, text='  W  ', bg='white')
        self.ctrl_l1_button = tk.Button(master=self.controller_window, text=' L1  ', bg='white')
        self.ctrl_r1_button = tk.Button(master=self.controller_window, text='  R1 ', bg='white')

        # Data I/O to other processes
        self.in_pipe = None
        self.out_pipe = None
        self.pilot_pipe_out = pilot_pipe
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
        # Config
        config_text = Label(master=self.top_bar, text='Config: ', justify=LEFT, anchor='w')
        config_text.grid(column=0, row=0, sticky=W)
        # Set Hostname
        hostname_config_button = Button(master=self.top_bar, text='Remote IP', justify=LEFT, anchor='w', command=self.set_hostname)
        hostname_config_button.grid(column=1, row=0, sticky=W)
        # Set
        config_button = Button(master=self.top_bar, text='Enable Sockets', justify=LEFT, anchor='w', command=partial(self.config_box))
        config_button.grid(column=2, row=0, sticky=W)
        # Send Command Config
        send_config_button = Button(master=self.top_bar, text='Send', justify=LEFT, anchor='w', command=self.cmd_grpc_button)
        send_config_button.grid(column=3, row=0, sticky=W)
        # Sockets
        config_text = Label(master=self.top_bar, text='Sockets: ', justify=LEFT, anchor='w')
        config_text.grid(column=4, row=0, sticky=W)
        # All
        start_all_sockets_button = Button(master=self.top_bar, text='Start', justify=LEFT, anchor='w', command=self.init_all_enabled_sockets)
        start_all_sockets_button.grid(column=5, row=0, sticky=W)
        # Quit Button
        quit_button = Button(master=self.top_bar, text='Exit', justify=LEFT, anchor='w', command=self.client_exit)
        quit_button.grid(column=9, row=0, sticky=W)

        # Logging Window
        self.logging_window.grid(column=0, row=1)
        self.text.place(x=0, y=0)
        self.logger.log('[@GUI] Logger Initialized.')

        self.logger.log('  ___ ___  ___ _   _ ')
        self.logger.log(' / __|   \\/ __| | | |')
        self.logger.log(' \\__ \\ |) \\__ \\ |_| |')
        self.logger.log(' |___/___/|___/\\___/ ')
        self.logger.log(' _____         _       _               _         ')
        self.logger.log('|     |___ ___| |_ ___| |_ ___ ___ ___|_|___ ___ ')
        self.logger.log('| | | | -_|  _|   | .\'|  _|  _| . |   | |  _|_ -')
        self.logger.log('|_|_|_|___|___|_|_|__,|_| |_| |___|_|_|_|___|___|')

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

        # Telemetry Window
        self.telemetry_window.grid(column=1, row=2)
        self.telemetry_colpad.grid(column=0, row=0, sticky=W, columnspan=2)
        self.accelerometer_text.grid(column=0, row=1, sticky=W, columnspan=2)
        self.accelerometer_val.grid(column=2, row=1, sticky=W)
        self.magnetometer_text.grid(column=0, row=2, sticky=W, columnspan=2)
        self.magnetometer_val.grid(column=2, row=2, sticky=W)
        self.pressure_trans_text.grid(column=0, row=3, sticky=W, columnspan=2)
        self.pressure_trans_val.grid(column=2, row=3, sticky=W)
        self.gyroscope_text.grid(column=0, row=4, sticky=W, columnspan=2)
        self.gyroscope_val.grid(column=2, row=4, sticky=W)
        self.voltmeter_text.grid(column=0, row=5, sticky=W, columnspan=2)
        self.voltmeter_val.grid(column=2, row=5, sticky=W)
        self.battery_current_text.grid(column=0, row=6, sticky=W, columnspan=2)
        self.battery_current_val.grid(column=2, row=6, sticky=W)
        self.roll_text.grid(column=0, row=7, sticky=W, columnspan=2)
        self.roll_val.grid(column=2, row=7, sticky=W)
        self.pitch_text.grid(column=0, row=8, sticky=W, columnspan=2)
        self.pitch_val.grid(column=2, row=8, sticky=W)
        self.yaw_text.grid(column=0, row=9, sticky=W, columnspan=2)
        self.yaw_val.grid(column=2, row=9, sticky=W)
        self.auto_button_text.grid(column=0, row=10, sticky=W, columnspan=2)
        self.auto_button_val.grid(column=2, row=10, sticky=W)
        self.kill_button_text.grid(column=0, row=11, sticky=W, columnspan=2)
        self.kill_button_val.grid(column=2, row=11, sticky=W)

        # Controller Window
        self.controller_window.grid(column=0, row=2)
        self.ctrl_n_button.grid(column=1, row=0)
        self.ctrl_s_button.grid(column=1, row=2)
        self.ctrl_e_button.grid(column=2, row=1)
        self.ctrl_w_button.grid(column=0, row=1)
        self.ctrl_l1_button.grid(column=0, row=0)
        self.ctrl_r1_button.grid(column=2, row=0)

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
                                             variable=self.telemetry_socket_is_enabled,
                                             value=1,
                                             command=partial(self.val_set, self.telemetry_socket_is_enabled, True)).grid(column=0, row=0)
        telemetry_radio_disable = Radiobutton(telemetry_diag,
                                              text='Disable',
                                              variable=self.telemetry_socket_is_enabled,
                                              value=0,
                                              command=partial(self.val_set, self.telemetry_socket_is_enabled, False)).grid(column=1, row=0)
        pilot_radio_enable = Radiobutton(pilot_diag,
                                         text='Enable',
                                         variable=self.pilot_socket_is_enabled,
                                         value=1,
                                         command=partial(self.val_set, self.pilot_socket_is_enabled, True)).grid(column=0, row=0)
        pilot_radio_disable = Radiobutton(pilot_diag,
                                          text='Disable',
                                          variable=self.pilot_socket_is_enabled,
                                          value=0,
                                          command=partial(self.val_set, self.pilot_socket_is_enabled, False)).grid(column=1, row=0)
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
        # Generate command configuration packet verifying inputs
        config = cmd.CommandConfiguration(socket_codes=[self.logging_socket_level.get(),
                                                        get_int_from_bool(self.video_socket_is_enabled.get()),
                                                        get_int_from_bool(self.telemetry_socket_is_enabled.get())],
                                        pilot_control=self.pilot_socket_is_enabled.get(),
                                        mission=self.mission_config_string.get().lower())
        self.cmd_config = config.gen_packet()
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

    def cmd_grpc_button(self):
        """Attempts to send a GRPC command packet to the SUB.
        """
        # Start up a GRPC client
        client = CMDGrpcClient(hostname=self.remote_hostname,
                            port=self.port_command_grpc,
                            logger=self.logger)
        response = client.send(1)
        if response == '!':
            self.diag_box('Error communicating with server. (Is it on?)')
        elif response == '1':  # Got acknowledge to set the config, send config
            self.cmd_connected = True
            if self.cmd_config is not None:
                # Send Packet with command
                print('Sending config...')
                request = pickle.dumps(self.cmd_config).hex()
                client.send(request)
            else:
                self.diag_box('Error, config not set')

    def init_all_enabled_sockets(self):
        """Initializes all sockets enabled.
        """
        self.init_video_socket()
        self.init_logging_socket()
        self.init_telemetry_socket()
        self.init_pilot_socket()
        self.diag_box('Initialized all enabled sockets.')

    def init_video_socket(self):
        """Initializes video socket connection from gui
        """
        if self.video_socket_is_enabled.get():
            self.out_pipe.send(('video', 'gui', 'initialize', self.remote_hostname, self.port_video_socket))

    def init_logging_socket(self):
        """Initializes logging socket connection from gui
        """
        if self.logging_socket_level.get() > 0:
            self.out_pipe.send(('logging', 'gui', 'initialize', self.remote_hostname, self.port_logging_socket))

    def init_telemetry_socket(self):
        """Initializes telemetry socket connection from gui
        """
        if self.telemetry_socket_is_enabled.get():
            self.out_pipe.send(('telemetry', 'gui', 'initialize', self.remote_hostname, self.port_telemetry_socket))

    def init_pilot_socket(self):
        """Initializes pilot socket connection from gui
        """
        if self.pilot_socket_is_enabled.get():
            self.out_pipe.send(('pilot', 'gui', 'initialize', self.remote_hostname, self.port_pilot_socket))

    def set_hostname(self):
        """Sets the hostname of the remote client.
        """
        prompt = simpledialog.askstring('Input', 'Set the remote hostname here:', parent=self.master)
        self.remote_hostname = prompt
        self.info_all_comms_text.configure(self.info_all_comms_text, text='COMMS @' + self.remote_hostname)

    def run_logger(self):
        """Adds the first element in the queue to the logs.
        """
        if self.logger.queue.qsize() > 0:
            self.text.insert(END, self.logger.dequeue())
            self.text.see('end')
        if len(self.remote_logging_queue) > 0:
            text = self.remote_logging_queue[0].strip() + '\n'
            self.text.insert(END, text)
            self.remote_logging_queue = self.remote_logging_queue[1:]
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

    def send_controller_state(self):
        """Sends current controller state to Pilot process
        """
        if self.js.get_init() and self.pilot_socket_is_connected:
            control_in = np.zeros(shape=(1,
                                    self.js.get_numaxes()
                                     + self.js.get_numbuttons()
                                     + self.js.get_numhats()))
            for i in range(self.js.get_numaxes()):
                control_in.put(i, self.js.get_axis(i))
            for i in range(self.js.get_numaxes(), self.js.get_numbuttons()):  # Buttons
                control_in.put(i, self.js.get_button(i - self.js.get_numaxes()))
            control_in.put((self.js.get_numaxes() + self.js.get_numbuttons()), self.js.get_hat(0))  # Hat
            self.current_control_inputs = control_in
            self.pilot_pipe_out.send((control_in.tobytes()))
            """ BROKEN in testing with some other socket commented out until I can fix it
            if self.ctrl_n_button.config('bg')[4] == 'white' and (1 == int(self.current_control_inputs[0, 9])):
                self.ctrl_n_button.configure(self.ctrl_n_button, bg='red')
            elif self.ctrl_n_button.config('bg')[4] == 'red' and (0 == int(self.current_control_inputs[0, 9])):
                self.ctrl_n_button.configure(self.ctrl_n_button, bg='white')
            if self.ctrl_s_button.config('bg')[4] == 'white' and (1 == int(self.current_control_inputs[0, 6])):
                self.ctrl_s_button.configure(self.ctrl_s_button, bg='red')
            elif self.ctrl_s_button.config('bg')[4] == 'red' and (0 == int(self.current_control_inputs[0, 6])):
                self.ctrl_s_button.configure(self.ctrl_s_button, bg='white')
            if self.ctrl_e_button.config('bg')[4] == 'white' and (1 == int(self.current_control_inputs[0, 7])):
                self.ctrl_e_button.configure(self.ctrl_e_button, bg='red')
            elif self.ctrl_e_button.config('bg')[4] == 'red' and (0 == int(self.current_control_inputs[0, 7])):
                self.ctrl_e_button.configure(self.ctrl_e_button, bg='white')
            if self.ctrl_w_button.config('bg')[4] == 'white' and (1 == int(self.current_control_inputs[0, 8])):
                self.ctrl_w_button.configure(self.ctrl_w_button, bg='red')
            elif self.ctrl_w_button.config('bg')[4] == 'red' and (0 == int(self.current_control_inputs[0, 8])):
                self.ctrl_w_button.configure(self.ctrl_w_button, bg='white')
            if self.ctrl_l1_button.config('bg')[4] == 'white' and (1 == int(self.current_control_inputs[0, 10])):
                self.ctrl_l1_button.configure(self.ctrl_l1_button, bg='red')
            elif self.ctrl_l1_button.config('bg')[4] == 'red' and (0 == int(self.current_control_inputs[0, 10])):
                self.ctrl_l1_button.configure(self.ctrl_l1_button, bg='white')
            if self.ctrl_r1_button.config('bg')[4] == 'white' and (1 == int(self.current_control_inputs[0, 11])):
                self.ctrl_r1_button.configure(self.ctrl_r1_button, bg='red')
            elif self.ctrl_r1_button.config('bg')[4] == 'red' and (0 == int(self.current_control_inputs[0, 11])):
                self.ctrl_r1_button.configure(self.ctrl_r1_button, bg='white')
            """

    def update_telemetry(self):
        """Updates the telemetry window.
        """
        if self.telemetry_socket_is_connected:
            self.accelerometer_val.configure(self.accelerometer_val,
                                             text=str(self.telemetry_current_state.sensors['accelerometer']))
            self.magnetometer_val.configure(self.magnetometer_val,
                                            text=str(self.telemetry_current_state.sensors['magnetometer']))
            self.pressure_trans_val.configure(self.pressure_trans_val,
                                             text=str(self.telemetry_current_state.sensors['pressure_transducer']))
            self.gyroscope_val.configure(self.gyroscope_val,
                                        text=str(self.telemetry_current_state.sensors['gyroscope']))
            self.voltmeter_val.configure(self.voltmeter_val,
                                        text=str(self.telemetry_current_state.sensors['voltmeter']))
            self.battery_current_val.configure(self.battery_current_val,
                                             text=str(self.telemetry_current_state.sensors['battery_current']))
            self.roll_val.configure(self.roll_val,
                                    text=str(self.telemetry_current_state.sensors['roll']))
            self.pitch_val.configure(self.pitch_val,
                                    text=str(self.telemetry_current_state.sensors['pitch']))
            self.yaw_val.configure(self.yaw_val,
                                   text=str(self.telemetry_current_state.sensors['yaw']))
            self.auto_button_val.configure(self.auto_button_val,
                                           text=str(self.telemetry_current_state.sensors['auto_button']))
            self.kill_button_val.configure(self.kill_button_val,
                                           text=str(self.telemetry_current_state.sensors['kill_button']))

    def read_pipe(self):
        """Checks input pipe for info from other processes, processes commands here
        """
        gui_cmd = []
        if self.in_pipe is not None:  # Checks for proper initialization first
            conn = mp.connection.wait([self.in_pipe], timeout=-1)
            if len(conn) > 0:
                gui_cmd = conn[0].recv()
                if gui_cmd[1] == 'video':
                    if gui_cmd[2] == 'conn_grpc':
                        self.video_grpc_is_connected = True
                    elif gui_cmd[2] == 'no_conn_grpc':
                        self.video_grpc_is_connected = False
                    elif gui_cmd[2] == 'conn_socket':
                        self.video_socket_is_connected = True
                    elif gui_cmd[2] == 'no_conn_socket':
                        self.video_socket_is_connected = False
                elif gui_cmd[1] == 'logging':
                    if gui_cmd[2] == 'conn_socket':
                        self.logging_socket_is_connected = True
                    else:
                        self.remote_logging_queue.append(gui_cmd[2])
                elif gui_cmd[1] == 'telemetry':
                    if isinstance(gui_cmd[2], str):
                        if gui_cmd[2] == 'conn_socket':
                            self.telemetry_socket_is_connected = True
                    elif isinstance(gui_cmd[2], bytes):
                        tel = sensor_tel.Telemetry()
                        tel.load_data_from_bytes(gui_cmd[2])
                        self.telemetry_current_state = tel
                elif gui_cmd[1] == 'pilot':
                    if gui_cmd[2] == 'conn_socket':
                        self.pilot_socket_is_connected = True

    def update(self):
        """Update function to read elements from other processes into the GUI
        Overriden from tkinter's window class
        """
        # Manual on update functions below:
        self.run_logger()
        self.update_frames()  # Update video frame
        self.send_controller_state()  # Send current inputs
        self.update_telemetry()  # Update telemetry displayed
        # Update all button statuses
        self.update_button(self.cmd_status_button, self.cmd_connected)
        self.update_button(self.video_grpc_status_button, self.video_grpc_is_connected)
        self.update_button(self.video_socket_connected_button, self.video_socket_is_connected)
        self.update_button(self.logging_socket_connected_button, self.logging_socket_is_connected)
        self.update_button(self.telemetry_socket_connected_button, self.telemetry_socket_is_connected)
        self.update_button(self.pilot_socket_connected_button, self.pilot_socket_is_connected)
        self.update_button(self.config_status_button, self.config_is_set)
        self.update_button_enable(self.video_socket_enable_button, self.video_socket_is_enabled.get())
        self.update_button_enable(self.telemetry_socket_enable_button, self.telemetry_socket_is_enabled.get())
        self.update_button_enable(self.pilot_socket_enable_button, self.pilot_socket_is_enabled.get())
        self.update_button_int(self.logging_socket_enable_button, self.logging_socket_level.get())
        self.update_status_string(self.mission_config_text_current, self.mission_config_string.get())
        # DEMO PURPOSES ONLY
        # print(self.telemetry_current_state.sensors['accelerometer'])  # Print accel data to show it's in GUI

        # Check for pipe updates
        self.read_pipe()
        # Loop, does not recurse despite appearance
        self.after(gui_update_ms, self.update)


def gui_proc_main(gui_input, gui_output, gui_logger, video_stream_pipe_in, pilot_pipe_out):
    """GUI Driver code
    """
    # Build Application
    root_window = tk.Tk()
    root_window.geometry(str(resolution[0] - edge_size - edge_size) + "x" + str(resolution[1] - top_bar_size - edge_size - edge_size))
    application = Window(pilot_pipe_out, master=root_window)

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
            client = CMDGrpcClient(hostname=default_hostname,
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
                s.connect((default_hostname, socket_port))
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
    """
    code = ''
    client = None
    socket_started = False
    hostname = ''
    port = ''
    while True:
        # Wait for this process to receive info from the pipe, read it in when it does
        conn = mp.connection.wait([video_pipe_in], timeout=-1)
        if len(conn) > 0:
            result = conn[0].recv()
            code = str(result[2])
            hostname = result[3]
            port = result[4]
        if code == '':
            pass
        elif code == 'initialize':
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
                s.connect((hostname, port))
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


def logging_proc(logger, logging_pipe_in, logging_pipe_out):
    """Receives logs from Intelligence over TCP connection.
    """
    hostname = ''
    port = ''
    started = False
    while True:
        conn = mp.connection.wait([logging_pipe_in], timeout=-1)
        if len(conn) > 0:
            result = conn[0].recv()
            if result[2] == 'initialize':
                hostname = result[3]
                port = result[4]
                started = True
        if started:
            lc = sub_logging.LoggerClient(save_logs=False)
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.connect((hostname, port))
                logging_pipe_out.send(('gui', 'logging', 'conn_socket'))
                while True:
                    # TODO add a check for mp connection here
                    s.sendall(b'1')
                    data = s.recv(4096)
                    # Parse logs
                    log_list = log_parse(data)
                    # Send to GUI
                    for i in range(len(log_list)):
                        lc.logging_queue.append(log_list[i])
                        logging_pipe_out.send(('gui', 'logging', lc.dequeue()))
                    print(log_list)


def telemetry_proc(logger, telemetry_pipe_in, telemetry_pipe_out):
    """Receives telemetry from Control over TCP connection.
    """
    hostname = ''
    port = ''
    started = False
    while True:
        conn = mp.connection.wait([telemetry_pipe_in], timeout=-1)
        if len(conn) > 0:
            result = conn[0].recv()
            if result[2] == 'initialize':
                hostname = result[3]
                port = result[4]
                started = True
        if started:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.connect((hostname, port))
                telemetry_pipe_out.send(('gui', 'telemetry', 'conn_socket'))
                while True:
                    # TODO add a check for mp connection here
                    s.sendall(b'1')
                    data = s.recv(4096)
                    telemetry_pipe_out.send(('gui', 'telemetry', data))


def pilot_proc(logger, pilot_pipe_in, pilot_pipe_out, pipe_in_from_gui):
    """Sends controller input to Control over TCP connection.
    """
    port = ''
    hostname = ''
    last_input = np.zeros(shape=(1, 1))
    started = False
    while True:
        conn = mp.connection.wait([pilot_pipe_in], timeout=-1)
        if len(conn) > 0:
            result = conn[0].recv()
            if isinstance(result[2], str):
                if result[2] == 'initialize':
                    hostname = result[3]
                    port = result[4]
                    started = True
        if started:
            # Controller
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.connect((hostname, port))
                pilot_pipe_out.send(('gui', 'pilot', 'conn_socket'))
                while True:
                    data = s.recv(1024)
                    if data == b'1':
                        controller_input = mp.connection.wait([pipe_in_from_gui], timeout=-1)
                        if len(controller_input) > 0:
                            last_input = controller_input[len(controller_input)-1].recv()
                            s.sendall(last_input)
                            controller_input.clear()  # Clear input after sending latest
                        else:  # Send previous input
                            s.sendall(last_input)


def router(logger,  # Gui logger
           from_gui_pipe_in, to_gui_pipe_out,  # Gui pipe
           from_video_pipe_in, to_video_pipe_out,  # Video pipe
           from_logger_pipe_in, to_logger_pipe_out,
           from_telemetry_pipe_in, to_telemetry_pipe_out,
           from_pilot_pipe_in, to_pilot_pipe_out
           ):
    """Routes messages between pipes, given destination of the message.
    """
    while True:
        # Wait on all pipe ins. See documentation for system communication pathways for more information.
        conn = mp.connection.wait([from_gui_pipe_in,
                                   from_video_pipe_in,
                                   from_logger_pipe_in,
                                   from_telemetry_pipe_in,
                                   from_pilot_pipe_in], timeout=-1)
        if len(conn) > 0:
            result = conn[0].recv()
            if result[0] == 'video':  # Send to video
                to_video_pipe_out.send(result)
            elif result[0] == 'gui':  # Send to gui
                to_gui_pipe_out.send(result)
            elif result[0] == 'logging':  # Send to logging
                to_logger_pipe_out.send(result)
            elif result[0] == 'telemetry':  # Send to telemetry
                to_telemetry_pipe_out.send(result)
            elif result[0] == 'pilot':  # Send to pilot
                to_pilot_pipe_out.send(result)


def main():
    """Main driver code, handles all processes.
    """
    if os.name == 'nt':  # Fix for linux
        context = get_context('spawn')
    else:
        context = get_context('fork')

    # Dedicated Video stream pipe
    pipe_to_gui_from_video, pipe_in_from_video_stream = context.Pipe()

    # Dedicated Controller/Pilot stream pipe
    pipe_to_pilot_from_gui, pilot_pipe_in_from_gui = context.Pipe()

    # Gui
    gui_logger = LoggerWrapper()

    pipe_to_gui_from_router, gui_pipe_in_from_router = context.Pipe()
    pipe_to_router_from_gui, pipe_in_from_gui = context.Pipe()
    gui_proc = context.Process(target=gui_proc_main, args=(gui_pipe_in_from_router, pipe_to_router_from_gui, gui_logger, pipe_in_from_video_stream, pipe_to_pilot_from_gui))
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
    logger_proc = context.Process(target=logging_proc, args=(gui_logger, log_pipe_in_from_router, pipe_to_router_from_logger))
    logger_proc.start()

    # Telemetry socket
    pipe_to_telemetry_from_router, tel_pipe_in_from_router = context.Pipe()
    pipe_to_router_from_telemetry, pipe_in_from_telemetry = context.Pipe()
    tel_proc = context.Process(target=telemetry_proc, args=(gui_logger, tel_pipe_in_from_router, pipe_to_router_from_telemetry))
    tel_proc.start()

    # Pilot socket
    pipe_to_pilot_from_router, plt_pipe_in_from_router = context.Pipe()
    pipe_to_router_from_pilot, pipe_in_from_pilot = context.Pipe()
    plt_proc = context.Process(target=pilot_proc, args=(gui_logger, plt_pipe_in_from_router, pipe_to_router_from_pilot, pilot_pipe_in_from_gui))
    plt_proc.start()

    # Router
    router_proc = context.Process(target=router, args=(gui_logger,
                                                    pipe_in_from_gui, pipe_to_gui_from_router,  # Gui
                                                    pipe_in_from_video, pipe_to_video_from_router,  # Video
                                                    pipe_in_from_logger, pipe_to_logger_from_router,  # Logger
                                                    pipe_in_from_telemetry, pipe_to_telemetry_from_router,  # Telemetry
                                                    pipe_in_from_pilot, pipe_to_pilot_from_router,))  # Pilot
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
