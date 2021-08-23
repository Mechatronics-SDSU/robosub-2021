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

import multiprocessing
import multiprocessing as mp
from multiprocessing import set_start_method, get_context
import os
import sys as system  # sys is some other import
import math
from collections import deque
import PIL.Image
import grpc
import socket
from datetime import datetime
import controller_translator
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

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

# Internal
import src.utils.cmd_pb2 as cmd_pb2
import src.utils.cmd_pb2_grpc as cmd_pb2_grpc
import src.utils.ip_config as ip_config
import src.utils.logger as sub_logging
import src.utils.telemetry as sensor_tel
import src.utils.pilot as ctrl_pilot
import src.utils.controller_translator
import src.utils.command_configuration as cmd


system.modules['ip_config'] = ip_config

# Ports
grpc_remote_client_port_default = 50051
default_hostname = 'localhost'
default_command_port_grpc = 50052
default_port_video_socket = 50001
default_port_logging_socket = 50002
default_port_telemetry_socket = 50003
default_port_pilot_socket = 50004
default_ports = {
    'Command': 50052,
    'Video': 50001,
    'Logging': 50002,
    'Telemetry': 50003,
    'Pilot': 50004
}


# GUI
top_bar_size = 30
edge_size = 1
resolution = (1600, 900)  # Gui root window size
remote_resolution = (640, 480)  # Remote camera
gui_update_ms = 10  # Update time for gui elements in ms
terminal_green = (74, 246, 38)
error_red = (255, 0, 3)

use_udp = False  # Do not touch UDP unless testing. Broken right now.


def request_to_value(r: any) -> str:
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


def get_int_from_bool(b: bool) -> int:
    """Returns int version of a boolean.
    """
    if b:
        return 1
    else:
        return 0


def log_parse(input_data: bytes) -> list:
    """Logs sometimes arrive in >1 at a time.
    Parses them out and returns a list.
    :param input_data: bytes object of potentially multiple log strings.
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


def peek(d: deque) -> any:
    """Deque doesn't come with a peek method, definining similar functionality here.
    :param d: deque object
    :return: anything a deque can hold, None if IndexError happens
    """
    try:
        ret_val = d.pop()
    except IndexError as e:  # Empty deque
        return None
    d.append(ret_val)
    return ret_val


class LoggerWrapper:
    """Provides easy methods for logging with formatting.
    """
    def __init__(self, showtime=True) -> None:
        self.queue = mp.Queue()
        self.add_timestamp = showtime

    def log(self, string: str, strip=True) -> None:
        """Logs the string
        :param string: Adds to logger queue
        :param strip: Whether to strip newlines
        """
        if self.add_timestamp and (strip is True):
            self.queue.put(str(datetime.now().strftime('[%H:%M:%S]')) + str(string.strip()) + '\n')
        elif self.add_timestamp and (strip is True):
            self.queue.put(str(datetime.now().strftime('[%H:%M:%S]')) + str(string) + '\n')
        elif (not self.add_timestamp) and (strip is False):
            self.queue.put(str(string.strip()) + '\n')
        else:
            self.queue.put(str(string) + '\n')

    def dequeue(self) -> any:
        """Removes first element from queue
        :return:
        """
        if self.queue.qsize() > 0:
            return self.queue.get()
        else:
            return None


class PortConfigWrapper:
    """Allows for real time changes to ports in the prompt.
    """
    def __init__(self, command: any, video: any, logger: any, telemetry: any, pilot: any) -> None:
        self.port_config_labels = {
            'Command': command,
            'Video': video,
            'Logging': logger,
            'Telemetry': telemetry,
            'Pilot': pilot
        }


class CMDGrpcClient:
    """Handles GRPC clients with related methods.
    """
    def __init__(self, hostname: str, port: int, logger: LoggerWrapper) -> None:
        self.remote_client = str(hostname)
        self.port = str(port)
        self._channel = grpc.insecure_channel(self.remote_client + ':' + self.port)
        self._stub = cmd_pb2_grpc.CommandGRPCStub(self._channel)
        self.logger = logger
        logger.log('[GRPC] Started up client. ' + self.remote_client + ':' + self.port)

    def send(self, request: any) -> str:
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

    def close(self) -> None:
        """Closes GRPC channel
        """
        self._channel.close()


class Window(tk.Frame):
    """Window class, handles the GUI's 'master' or 'root' window and all subwindows
    """
    def __init__(self, pilot_pipe: mp.Pipe, master=None) -> None:
        # Load ports from config file or set to defaults
        self.remote_hostname = default_hostname
        self.ports_dict = {
            'Command': default_command_port_grpc,
            'Video': default_port_video_socket,
            'Logging': default_port_logging_socket,
            'Telemetry': default_port_telemetry_socket,
            'Pilot': default_port_pilot_socket
        }
        self.ports_dict_conn_type = {
            'Command': 'GRPC',
            'Video': 'TCP',
            'Logging': 'TCP',
            'Telemetry': 'TCP',
            'Pilot': 'TCP'
        }
        self.ports_dict_by_shorthand = {
            'Command': 'CMD',
            'Video': 'VID',
            'Logging': 'LOG',
            'Telemetry': 'TEL',
            'Pilot': 'PLT'
        }
        self.conn_dict_by_string = {
            'Command': False,
            'Video': False,
            'Logging': False,
            'Telemetry': False,
            'Pilot': False
        }
        self.enable_dict_by_string = {
            'Video': 0,
            'Logging': 0,
            'Telemetry': 0,
            'Pilot': 0
        }

        self.port_command_grpc = self.ports_dict['Command']
        self.port_video_socket = self.ports_dict['Video']
        self.port_logging_socket = self.ports_dict['Logging']
        self.port_telemetry_socket = self.ports_dict['Telemetry']
        self.port_pilot_socket = self.ports_dict['Pilot']

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
        self.ct = controller_translator.ControllerTranslator(
            joystick_drift_compensation=0.1,
            base_net_turn=20,
            base_net_strafe=-20)

        # Main window
        tk.Frame.__init__(self, master)
        self.master = master
        master.iconbitmap('img/mech_icon.ico')
        self.closing = False

        # Top Bar
        self.top_bar = tk.Frame(master=self.master, width=resolution[0], height=30, bg='white')

        # Logging Window
        self.logging_window_text = tk.Canvas(master=self.master, width=100, height=24, bg='green')
        self.logging_window_text_img = ImageTk.PhotoImage(PILImage.open('img/logging_text.png'))
        self.logging_window_text.create_image((2, 2), anchor=tk.NW, image=self.logging_window_text_img)
        self.logging_window = tk.Frame(master=self.master, width=640, height=480, bg='white')

        # Video Frame
        self.video_window_text = tk.Canvas(master=self.master, width=120, height=24, bg='green')
        self.video_window_text_img = ImageTk.PhotoImage(PILImage.open('img/video_text.png'))
        self.video_window_text.create_image((2, 2), anchor=tk.NW, image=self.video_window_text_img)
        self.video_window = tk.Canvas(master=self.master, width=640, height=480, bg='green')
        self.video_window_no_img = ImageTk.PhotoImage(PILImage.open('img/not_loaded.png'))
        self.video_window_img = self.video_window.create_image((2, 2), anchor=tk.NW, image=self.video_window_no_img)
        # Alternate between frames on video stream because of tkinter's gc
        self.img = ImageTk.PhotoImage(PILImage.open('img/not_loaded_2.png'))
        self.img_2 = ImageTk.PhotoImage(PILImage.open('img/not_loaded_2.png'))
        self.frame_counter = 0

        # Info Window
        self.info_window_comms_text = tk.Canvas(master=self.master, width=120, height=24, bg='green')
        self.info_window_comms_text_img = ImageTk.PhotoImage(PILImage.open('img/comms_status_text.png'))
        self.info_window_comms_text.create_image((2, 2), anchor=tk.NW, image=self.info_window_comms_text_img)
        self.info_window = tk.Frame(master=self.master, width=300, height=640, bg='white')
        self.info_window_host_text = tk.Canvas(master=self.info_window, width=120, height=24, bg='green')
        self.info_window_host_text_img = ImageTk.PhotoImage(PILImage.open('img/host_status_text.png'))
        self.info_window_host_text.create_image((2, 2), anchor=tk.NW, image=self.info_window_host_text_img)
        self.info_window_pico_text = tk.Canvas(master=self.info_window, width=120, height=24, bg='green')
        self.info_window_pico_text_img = ImageTk.PhotoImage(PILImage.open('img/pico_status_text.png'))
        self.info_window_pico_text.create_image((2, 2), anchor=tk.NW, image=self.info_window_pico_text_img)

        # Config
        self.config_is_set = False
        self.cmd_config = None
        # CMD GRPC
        self.cmd_connected = False  # If command's grpc server is connected
        self.conn_dict_by_string['Command'] = self.cmd_connected
        # Video Socket
        self.video_socket_is_enabled = tk.BooleanVar(value=False)  # Enable
        self.enable_dict_by_string['Video'] = int(self.video_socket_is_enabled.get() is True)
        self.video_socket_is_connected = False  # Connection
        self.conn_dict_by_string['Video'] = self.video_socket_is_connected
        # Logging Socket
        self.logging_socket_level = tk.IntVar(value=0)  # Enable/Level
        self.enable_dict_by_string['Logging'] = self.logging_socket_level.get()
        self.logging_socket_is_connected = False  # Connection
        self.conn_dict_by_string['Logging'] = self.logging_socket_is_connected
        self.remote_logging_queue = []
        # Telemetry Socket
        self.telemetry_socket_is_enabled = tk.BooleanVar(value=False)  # Enable
        self.enable_dict_by_string['Telemetry'] = int(self.telemetry_socket_is_enabled.get() is True)
        self.telemetry_socket_is_connected = False  # Connection
        self.conn_dict_by_string['Telemetry'] = self.telemetry_socket_is_connected
        self.telemetry_current_state = sensor_tel.Telemetry()
        # Pilot Socket
        self.pilot_socket_is_enabled = tk.BooleanVar(value=False)  # Enable
        self.enable_dict_by_string['Pilot'] = int(self.telemetry_socket_is_enabled.get() is True)
        self.pilot_socket_is_connected = False  # Connection
        self.conn_dict_by_string['Pilot'] = self.pilot_socket_is_connected
        # Mission
        self.mission_config_string = tk.StringVar(value='None')  # Mission to do this run
        # Hostname and conn status w/ opencv
        self.hostname_img_canvas = tk.Canvas(master=self.info_window, width=250, height=180, bg='green')
        self.hostname_img_cv = cv2.imread('img/comms_frame.png')
        self.hostname_img_cv = self.draw_hostname_conn_base(image=self.hostname_img_cv)
        self.hostname_img = ImageTk.PhotoImage(PILImage.fromarray(self.hostname_img_cv))
        self.hostname_img_tk = self.hostname_img_canvas.create_image((2, 2), anchor=tk.NW, image=self.hostname_img)
        # Host status w/ opencv
        self.host_img_canvas = tk.Canvas(master=self.info_window, width=250, height=180, bg='green')
        self.host_img_cv = cv2.imread('img/comms_frame.png')
        self.host_img = ImageTk.PhotoImage(PILImage.fromarray(self.host_img_cv))
        self.host_img_tk = self.host_img_canvas.create_image((2, 2), anchor=tk.NW, image=self.host_img)
        self.update_host_display()
        # Pico status w/ opencv
        self.pico_img_canvas = tk.Canvas(master=self.info_window, width=250, height=180, bg='green')
        self.pico_img_cv = cv2.imread('img/comms_frame.png')
        self.pico_img = ImageTk.PhotoImage(PILImage.fromarray(self.pico_img_cv))
        self.pico_img_tk = self.pico_img_canvas.create_image((2, 2), anchor=tk.NW, image=self.pico_img)
        # Telemetry Window
        self.tel_window_old = tk.Frame(master=self.master, bg='white')
        self.base_sensor_frame = cv2.imread('img/sensor_base_new.png')
        self.telemetry_window = tk.Frame(master=self.master, width=1050, height=244, bg='black')
        self.telemetry_canvas_0 = tk.Canvas(master=self.telemetry_window, width=1050, height=244, bd=0, bg='green')
        self.telemetry_canvas_0_img = ImageTk.PhotoImage(PILImage.open('img/sensor_base_new.png'))
        self.telemetry_canvas_1_img = ImageTk.PhotoImage(PILImage.open('img/sensor_base_new.png'))
        self.telemetry_frame_counter = 0
        self.telemetry_canvas_0_config = self.telemetry_canvas_0.create_image((2, 2),
                                                                              anchor=tk.NW,
                                                                              image=self.telemetry_canvas_0_img)
        self.sensors_text = tk.Canvas(master=self.master, width=100, height=24, bd=0, bg='green')
        self.sensors_text_img = ImageTk.PhotoImage(PILImage.open('img/sensors_text.png'))
        self.sensors_text.create_image((2, 2), anchor=tk.NW, image=self.sensors_text_img)

        # Controller Window
        self.controller_window = tk.Canvas(master=self.master, width=213, height=140, bg='white')
        self.thruster_window = tk.Canvas(master=self.master, width=213, height=130, bg='white')
        self.controller_text = tk.Canvas(master=self.master, width=213, height=24, bg='green')
        self.controller_text_img = ImageTk.PhotoImage(PILImage.open('img/inputs_thrusters_text.png'))
        self.controller_text.create_image((2, 2), anchor=tk.NW, image=self.controller_text_img)
        self.controller_window_buttons = tk.Canvas(master=self.controller_window, width=55, bg='white')
        self.controller_window_joysticks_l = tk.Canvas(master=self.controller_window, width=102, bg='white')
        self.controller_window_joysticks_r = tk.Canvas(master=self.controller_window, width=55, bg='white')

        # Controller inputs
        self.current_control_inputs = None
        self.maestro_controls = None
        self.ctrl_n_button = tk.Button(master=self.controller_window_buttons, text='  N  ', bg='white')
        self.ctrl_s_button = tk.Button(master=self.controller_window_buttons, text='  S  ', bg='white')
        self.ctrl_e_button = tk.Button(master=self.controller_window_buttons, text='  E  ', bg='white')
        self.ctrl_w_button = tk.Button(master=self.controller_window_buttons, text='  W  ', bg='white')
        self.ctrl_l1_button = tk.Button(master=self.controller_window_joysticks_l, text='  L1  ', bg='white')
        self.ctrl_r1_button = tk.Button(master=self.controller_window_joysticks_r, text='  R1  ', bg='white')
        self.ctrl_l_button = tk.Button(master=self.controller_window_buttons, text=' Sel ', bg='white')
        self.ctrl_r_button = tk.Button(master=self.controller_window_buttons, text='  St ', bg='white')
        # Images to draw L2/R2 inputs
        self.l2_text = tk.Label(master=self.controller_window_joysticks_l, text='L2', bd=0, anchor='e',
                                bg='white',
                                justify=tk.RIGHT)
        self.ctrl_l2_button = tk.Canvas(master=self.controller_window_joysticks_l, width=40, height=40, bg='blue')
        self.r2_text = tk.Label(master=self.controller_window_joysticks_r, text='R2', bd=0, anchor='w',
                                bg='white',
                                justify=tk.LEFT)
        self.ctrl_r2_button = tk.Canvas(master=self.controller_window_joysticks_r, width=40, height=40, bg='blue')
        self.lr_button_base = cv2.imread('img/l2r2_base.png')
        self.l_button_img = ImageTk.PhotoImage(PILImage.open('img/l2r2_base.png'))
        self.l_button_img_2 = ImageTk.PhotoImage(PILImage.open('img/l2r2_base.png'))
        self.r_button_img = ImageTk.PhotoImage(PILImage.open('img/l2r2_base.png'))
        self.r_button_img_2 = ImageTk.PhotoImage(PILImage.open('img/l2r2_base.png'))
        self.lr_button_frame_counter = 0
        self.l_window_img = self.ctrl_l2_button.create_image((2, 2), anchor=tk.NW, image=self.l_button_img)
        self.r_window_img = self.ctrl_r2_button.create_image((2, 2), anchor=tk.NW, image=self.r_button_img)
        # Images to draw joystick map
        self.joystick_l = tk.Canvas(master=self.controller_window_joysticks_l, width=40, height=40, bg='green')
        self.joystick_l_text = tk.Label(master=self.controller_window_joysticks_l, text='LJ', bd=0, anchor='e',
                                bg='white',
                                justify=tk.RIGHT)
        self.joystick_r = tk.Canvas(master=self.controller_window_joysticks_r, width=40, height=40, bg='green')
        self.joystick_r_text = tk.Label(master=self.controller_window_joysticks_r, text='RJ', bd=0, anchor='w',
                                        bg='white',
                                        justify=tk.LEFT)
        self.joystick_window_no_img = ImageTk.PhotoImage(PILImage.open('img/default_joystick.png'))
        self.joystick_l_img = ImageTk.PhotoImage(PILImage.open('img/joystick_base_img.png'))
        self.joystick_l_img_2 = ImageTk.PhotoImage(PILImage.open('img/joystick_base_img.png'))
        self.joystick_r_img = ImageTk.PhotoImage(PILImage.open('img/joystick_base_img.png'))
        self.joystick_r_img_2 = ImageTk.PhotoImage(PILImage.open('img/joystick_base_img.png'))
        self.joystick_frame_counter = 0
        self.joystick_window_l_img = self.joystick_l.create_image((2, 2), anchor=tk.NW, image=self.joystick_l_img)
        self.joystick_window_r_img = self.joystick_r.create_image((2, 2), anchor=tk.NW, image=self.joystick_r_img)
        # Controller outputs to maestro
        self.thruster_canvas = tk.Canvas(master=self.controller_window, width=173, height=130, bg='green')
        self.thruster_img_1 = ImageTk.PhotoImage(PILImage.open('img/maestro_no_conn.png'))
        self.thruster_img_2 = ImageTk.PhotoImage(PILImage.open('img/maestro_no_conn.png'))
        self.thruster_frame_counter = 0
        self.thruster_window_img = self.thruster_canvas.create_image((2, 2), anchor=tk.NW, image=self.thruster_img_1)

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

    def init_window(self) -> None:
        """Builds the master widget and all subwidgets, arranges all elements of GUI with grid
        """
        # Root/master window
        self.master.title('SDSU Mechatronics Robosub External Interface')

        # Top Menu Bar
        self.top_bar.grid(column=0, row=0, padx=0, sticky='W', columnspan=3)
        self.top_bar.wait_visibility()
        # Build buttons for top menu bar
        # Config
        config_text = Label(master=self.top_bar, text='Config: ', justify=LEFT, anchor='w')
        config_text.grid(column=0, row=0, sticky=W)
        # Set Hostname
        hostname_config_button = Button(master=self.top_bar, text='Remote IP', justify=LEFT, anchor='w',
                                        command=self.set_hostname)
        hostname_config_button.grid(column=1, row=0, sticky=W)
        # Set
        config_button = Button(master=self.top_bar, text='Enable Sockets', justify=LEFT, anchor='w',
                               command=partial(self.config_box))
        config_button.grid(column=2, row=0, sticky=W)
        port_config_button = Button(master=self.top_bar, text='Change Ports', justify=LEFT, anchor='w',
                                    command=partial(self.port_config_box))
        port_config_button.grid(column=3, row=0, sticky=W)
        # Send Command Config
        send_config_button = Button(master=self.top_bar, text='Send', justify=LEFT, anchor='w',
                                    command=self.cmd_grpc_button)
        send_config_button.grid(column=4, row=0, sticky=W)
        # Sockets
        config_text = Label(master=self.top_bar, text='Sockets: ', justify=LEFT, anchor='w')
        config_text.grid(column=5, row=0, sticky=W)
        # All
        start_all_sockets_button = Button(master=self.top_bar, text='Start', justify=LEFT, anchor='w',
                                          command=self.init_all_enabled_sockets)
        start_all_sockets_button.grid(column=6, row=0, sticky=W)
        # Quit Button
        quit_button = Button(master=self.top_bar, text='Exit', justify=LEFT, anchor='w', command=self.client_exit)
        quit_button.grid(column=9, row=0, sticky=W)

        # Text bars
        self.logging_window_text.grid(column=0, row=1, sticky=W, columnspan=3)
        self.video_window_text.grid(column=3, row=1, sticky=NW)
        self.info_window_comms_text.grid(column=4, row=1, sticky=NW)
        self.sensors_text.grid(column=1, row=3, sticky=NW)

        # Logging Window
        self.logging_window.grid(column=0, row=2, sticky=W, columnspan=3)
        self.text.place(x=0, y=0)
        self.logger.log('[Info]: Logger Initialized.')

        # Video Stream Window
        self.video_window.grid(column=3, row=2)

        # Info Window (Communications/Statuses)
        self.info_window.grid(column=4, row=2, sticky=NW, rowspan=3)
        self.hostname_img_canvas.grid(column=0, row=0, sticky=W, columnspan=6)
        self.host_img_canvas.grid(column=0, row=2, sticky=W, columnspan=6)
        self.pico_img_canvas.grid(column=0, row=4, sticky=W, columnspan=6)
        # Text
        self.info_window_host_text.grid(column=0, row=1, sticky=W, columnspan=3)
        self.info_window_pico_text.grid(column=0, row=3, sticky=W, columnspan=3)
        # Telemetry Window
        self.telemetry_window.grid(column=1, row=4, sticky=NW, columnspan=3, rowspan=3)
        self.telemetry_canvas_0.grid(column=0, row=0)

        # Controller Window
        self.controller_window.grid(column=0, row=4, sticky=NW)
        self.controller_text.grid(column=0, row=3, sticky=NW)
        self.controller_window_joysticks_l.grid(column=0, row=1)
        self.controller_window_buttons.grid(column=1, row=1)
        self.controller_window_joysticks_r.grid(column=2, row=1)
        self.l2_text.grid(column=0, row=0)
        self.ctrl_l2_button.grid(column=1, row=0)
        self.ctrl_l1_button.grid(column=1, row=1)
        self.joystick_l_text.grid(column=0, row=2)
        self.joystick_l.grid(column=1, row=2)
        self.ctrl_l_button.grid(column=0, row=0)
        self.ctrl_n_button.grid(column=1, row=0)
        self.ctrl_r_button.grid(column=2, row=0)
        self.ctrl_w_button.grid(column=0, row=1)
        self.ctrl_e_button.grid(column=2, row=1)
        self.ctrl_s_button.grid(column=1, row=2)
        self.r2_text.grid(column=1, row=0)
        self.ctrl_r2_button.grid(column=0, row=0)
        self.ctrl_r1_button.grid(column=0, row=1)
        self.joystick_r_text.grid(column=1, row=2)
        self.joystick_r.grid(column=0, row=2)
        self.thruster_canvas.grid(column=0, row=2, sticky=N, columnspan=3)

    @staticmethod
    def diag_box(message: str) -> None:
        """Creates a pop-up dialog box with a string.
        """
        messagebox.showinfo(title='Info', message=message)

    def config_box(self) -> None:
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
                                         command=partial(self.val_set, self.video_socket_is_enabled,
                                                         True)).grid(column=0, row=0)
        video_radio_disable = Radiobutton(video_diag,
                                          text='Disable',
                                          variable=self.video_socket_is_enabled,
                                          value=0,
                                          command=partial(self.val_set, self.video_socket_is_enabled,
                                                          False)).grid(column=1, row=0)
        logging_radio_enable_debug = Radiobutton(logging_diag,
                                                 text='Debug',
                                                 variable=self.logging_socket_level,
                                                 value=2,
                                                 command=partial(self.val_set, self.logging_socket_level,
                                                                 2)).grid(column=0, row=0)
        logging_radio_enable_info = Radiobutton(logging_diag,
                                                text='Info',
                                                variable=self.logging_socket_level,
                                                value=1,
                                                command=partial(self.val_set, self.logging_socket_level,
                                                                1)).grid(column=1, row=0)
        logging_radio_enable_disable = Radiobutton(logging_diag,
                                                   text='Disable',
                                                   variable=self.logging_socket_level,
                                                   value=0,
                                                   command=partial(self.val_set, self.logging_socket_level,
                                                                   0)).grid(column=2, row=0)
        telemetry_radio_enable = Radiobutton(telemetry_diag,
                                             text='Enable',
                                             variable=self.telemetry_socket_is_enabled,
                                             value=1,
                                             command=partial(self.val_set, self.telemetry_socket_is_enabled,
                                                             True)).grid(column=0, row=0)
        telemetry_radio_disable = Radiobutton(telemetry_diag,
                                              text='Disable',
                                              variable=self.telemetry_socket_is_enabled,
                                              value=0,
                                              command=partial(self.val_set, self.telemetry_socket_is_enabled,
                                                              False)).grid(column=1, row=0)
        pilot_radio_enable = Radiobutton(pilot_diag,
                                         text='Enable',
                                         variable=self.pilot_socket_is_enabled,
                                         value=1,
                                         command=partial(self.val_set, self.pilot_socket_is_enabled,
                                                         True)).grid(column=0, row=0)
        pilot_radio_disable = Radiobutton(pilot_diag,
                                          text='Disable',
                                          variable=self.pilot_socket_is_enabled,
                                          value=0,
                                          command=partial(self.val_set, self.pilot_socket_is_enabled,
                                                          False)).grid(column=1, row=0)
        mission_radio_all = Radiobutton(mission_diag,
                                        text='All',
                                        variable=self.mission_config_string,
                                        value=4,
                                        command=partial(self.val_set, self.mission_config_string,
                                                        'All')).grid(column=0, row=0)
        mission_radio_gate = Radiobutton(mission_diag,
                                         text='Gate',
                                         variable=self.mission_config_string,
                                         value=3,
                                         command=partial(self.val_set, self.mission_config_string,
                                                         'Gate')).grid(column=1, row=0)
        mission_radio_buoy = Radiobutton(mission_diag,
                                         text='Buoy',
                                         variable=self.mission_config_string,
                                         value=2,
                                         command=partial(self.val_set, self.mission_config_string,
                                                         'Buoy')).grid(column=2, row=0)
        mission_radio_rise = Radiobutton(mission_diag,
                                         text='Rise',
                                         variable=self.mission_config_string,
                                         value=1,
                                         command=partial(self.val_set, self.mission_config_string,
                                                         'Rise')).grid(column=3, row=0)
        mission_radio_none = Radiobutton(mission_diag,
                                         text='None',
                                         variable=self.mission_config_string,
                                         value=0,
                                         command=partial(self.val_set, self.mission_config_string,
                                                         'None')).grid(column=4, row=0)

    def port_config_box(self) -> None:
        """Creates a diag box to set the config for the ports.
        This configuration is optional and not necessary if using default ports.
        """
        top = tk.Toplevel(self.master)  # Make a separate window
        port_config_diag = tk.Label(top, text='Set IPV4 Port Configuration:',
                                    pady=10,
                                    justify='left',
                                    anchor='nw')
        port_config_diag.grid(column=0, row=0, sticky=W, columnspan=2)
        # GRPC Command
        port_grpc_title = tk.Label(top, text='GRPC')
        port_grpc_diag = tk.Label(top)
        port_video_title = tk.Label(top, text='Video')
        port_video_diag = tk.Label(top)
        port_logger_title = tk.Label(top, text='Logging')
        port_logger_diag = tk.Label(top)
        port_telemetry_title = tk.Label(top, text='Telemetry')
        port_telemetry_diag = tk.Label(top)
        port_pilot_title = tk.Label(top, text='Pilot')
        port_pilot_diag = tk.Label(top)
        port_grpc_title.grid(column=0, row=1, sticky=W)
        port_grpc_diag.grid(column=1, row=1, sticky=W, columnspan=2)
        port_video_title.grid(column=0, row=2, sticky=W)
        port_video_diag.grid(column=1, row=2, sticky=W, columnspan=2)
        port_logger_title.grid(column=0, row=3, sticky=W)
        port_logger_diag.grid(column=1, row=3, sticky=W, columnspan=2)
        port_telemetry_title.grid(column=0, row=4, sticky=W)
        port_telemetry_diag.grid(column=1, row=4, sticky=W, columnspan=2)
        port_pilot_title.grid(column=0, row=5, sticky=W)
        port_pilot_diag.grid(column=1, row=5, sticky=W, columnspan=2)

        # Labels
        port_grpc_text = tk.Label(master=port_grpc_diag, text=str(self.port_command_grpc))
        port_video_text = tk.Label(master=port_video_diag, text=str(self.port_video_socket))
        port_logger_text = tk.Label(master=port_logger_diag, text=str(self.port_logging_socket))
        port_telemetry_text = tk.Label(master=port_telemetry_diag, text=str(self.port_telemetry_socket))
        port_pilot_text = tk.Label(master=port_pilot_diag, text=str(self.port_pilot_socket))
        pcr = PortConfigWrapper(command=port_grpc_text,
                                video=port_video_text,
                                logger=port_logger_text,
                                telemetry=port_telemetry_text,
                                pilot=port_pilot_text)
        # Buttons
        port_grpc_button = tk.Button(master=port_grpc_diag, text='Set', command=partial(
                        self.port_text_box, 'Command', self.port_command_grpc, top, pcr, port_grpc_text))
        port_video_button = tk.Button(master=port_video_diag, text='Set', command=partial(
                        self.port_text_box, 'Video', self.port_video_socket, top, pcr, port_video_text))
        port_logger_button = tk.Button(master=port_logger_diag, text='Set', command=partial(
                        self.port_text_box, 'Logging', self.port_logging_socket, top, pcr, port_logger_text))
        port_telemetry_button = tk.Button(master=port_telemetry_diag, text='Set', command=partial(
                        self.port_text_box, 'Telemetry', self.port_telemetry_socket, top, pcr, port_telemetry_text))
        port_pilot_button = tk.Button(master=port_pilot_diag, text='Set', command=partial(
                        self.port_text_box, 'Pilot', self.port_pilot_socket, top, pcr, port_pilot_text))

        port_grpc_text.grid(column=0, row=0, sticky=W)
        port_grpc_button.grid(column=1, row=0, sticky=W)
        port_video_text.grid(column=0, row=1, sticky=W)
        port_video_button.grid(column=1, row=1, sticky=W)
        port_logger_text.grid(column=0, row=2, sticky=W)
        port_logger_button.grid(column=1, row=2, sticky=W)
        port_telemetry_text.grid(column=0, row=3, sticky=W)
        port_telemetry_button.grid(column=1, row=3, sticky=W)
        port_pilot_text.grid(column=0, row=4, sticky=W)
        port_pilot_button.grid(column=1, row=4, sticky=W)

    def port_text_box(self, port_name: str, current_port: int, parent_window: any, config: PortConfigWrapper,
                      label: any) -> None:
        """Generates a text box for setting the port.
        :param port_name: Dictionary reference for what port is being changed
        :param current_port: Current port, used to display to diag box
        :param parent_window: Top window object calling this function
        :param config: PortConfigWrapper object that holds text box objects
        :param label: Label object for setting top window
        """
        prompt = simpledialog.askstring('Input', f'Set the {port_name} port here: (Currently {current_port})',
                                        parent=parent_window)
        if isinstance(prompt, str):  # None returned if window is closed
            try:
                new_port = int(prompt)
            except ValueError as e:
                new_port = default_ports[port_name]
                self.logger.log(f'[Warn]: Attempt to pass invalid port {prompt}, defaulting to {new_port}')
            self.ports_dict[port_name] = new_port
            self.port_command_grpc = self.ports_dict['Command']
            self.port_video_socket = self.ports_dict['Video']
            self.port_logging_socket = self.ports_dict['Logging']
            self.port_telemetry_socket = self.ports_dict['Telemetry']
            self.port_pilot_socket = self.ports_dict['Pilot']
            # Set the called window's port
            config.port_config_labels[port_name].configure(label, text=self.ports_dict[port_name])
            self.update_comms_host()
            parent_window.update()

    def val_set(self, old: any, new: any) -> None:
        """tkinter doesn't like calling old.set() within command= arguments, so it's done here
        """
        old.set(new)
        self.update_host_display()

    def confirm_settings(self, top: any) -> None:
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
        self.update_host_display()
        top.destroy()

    def client_exit(self) -> None:
        """Closes client.
        TODO Needs to be done more gracefully at process level.
        """
        self.master.title('Closing...')
        self.closing = True

        # Last thing done
        self.destroy()
        system.exit()

    def cmd_grpc_button(self) -> None:
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
            self.conn_dict_by_string['Command'] = self.cmd_connected
            self.update_comms_host()
            if self.cmd_config is not None:
                # Send Packet with command
                print('Sending config...')
                request = pickle.dumps(self.cmd_config).hex()
                client.send(request)
            else:
                self.diag_box('Error, config not set')

    def init_all_enabled_sockets(self) -> None:
        """Initializes all sockets enabled.
        """
        self.init_video_socket()
        self.init_logging_socket()
        self.init_telemetry_socket()
        self.init_pilot_socket()
        self.diag_box('Initialized all enabled sockets.')

    def init_video_socket(self) -> None:
        """Initializes video socket connection from gui
        """
        if self.video_socket_is_enabled.get():
            self.out_pipe.send(('video', 'gui', 'initialize', self.remote_hostname, self.port_video_socket))

    def init_logging_socket(self) -> None:
        """Initializes logging socket connection from gui
        """
        if self.logging_socket_level.get() > 0:
            self.out_pipe.send(('logging', 'gui', 'initialize', self.remote_hostname, self.port_logging_socket))

    def init_telemetry_socket(self) -> None:
        """Initializes telemetry socket connection from gui
        """
        if self.telemetry_socket_is_enabled.get():
            self.out_pipe.send(('telemetry', 'gui', 'initialize', self.remote_hostname, self.port_telemetry_socket))

    def init_pilot_socket(self) -> None:
        """Initializes pilot socket connection from gui
        """
        if self.pilot_socket_is_enabled.get():
            self.out_pipe.send(('pilot', 'gui', 'initialize', self.remote_hostname, self.port_pilot_socket))

    def set_hostname(self) -> None:
        """Sets the hostname of the remote client.
        """
        prompt = simpledialog.askstring('Input', 'Set the remote hostname here:', parent=self.master)
        if (isinstance(prompt, str)) and (prompt != ''):
            self.remote_hostname = prompt
            self.logger.log('[Info]: Set IP to ' + prompt)
            self.update_comms_host()
        else:
            self.remote_hostname = default_hostname
            self.logger.log('[Warn]: Attempt to pass invalid ip address, defaulting to localhost.')
            self.update_comms_host()

    def run_logger(self) -> None:
        """Adds all elements in the queue to the logs.
        """
        if self.logger.queue.qsize() > 0:
            counter = self.logger.queue.qsize()
            for i in range(counter):
                self.text.insert(END, self.logger.dequeue())
            self.text.see('end')
        if len(self.remote_logging_queue) > 0:
            counter = self.remote_logging_queue
            for i in counter:
                text = self.remote_logging_queue[0].strip() + '\n'
                self.text.insert(END, text)
                self.remote_logging_queue = self.remote_logging_queue[1:]
            self.text.see('end')

    def draw_hostname_conn_base(self, image: any) -> any:
        """Draw the hostname base image
        :param image: OpenCV image object
        :return: OpenCV image objectg with drawn text
        """
        # Connection Status
        if self.cmd_connected:
            cv2.line(img=image, pt1=(16, 24), pt2=(12, 20), color=terminal_green, thickness=1)  # Checkmark
            cv2.line(img=image, pt1=(16, 24), pt2=(24, 8), color=terminal_green, thickness=1)  # Checkmark
            cv2.putText(img=image, text=f"Connected", org=(35, 22), fontFace=cv2.FONT_HERSHEY_PLAIN, fontScale=1.3,
                        color=terminal_green, thickness=1)
            cv2.putText(img=image, text=f"@ {self.remote_hostname}", org=(10, 45), fontFace=cv2.FONT_HERSHEY_PLAIN,
                        fontScale=1.3, color=terminal_green, thickness=1)
        else:
            cv2.circle(img=image, center=(15, 15), radius=8, color=error_red, thickness=1)  # Null character
            cv2.line(img=image, pt1=(24, 6), pt2=(6, 24), color=error_red, thickness=1)  # Null character
            cv2.putText(img=image, text=f"Not Connected", org=(35, 22), fontFace=cv2.FONT_HERSHEY_PLAIN, fontScale=1.3,
                        color=error_red, thickness=1)
            cv2.putText(img=image, text=f"@ {self.remote_hostname}", org=(10, 45), fontFace=cv2.FONT_HERSHEY_PLAIN,
                        fontScale=1.3, color=error_red, thickness=1)
        # Ports
        coordinates_y = [70, 95, 120, 145, 170]
        counter = 0
        color = terminal_green
        for i in self.ports_dict:  # Render port list for all port
            if self.conn_dict_by_string[i]:  # Connected, draw in green
                color = terminal_green
            else:  # Not connected, draw in red
                color = error_red
            cv2.putText(img=image, text=f"[{self.ports_dict_by_shorthand[i]}] {self.ports_dict_conn_type[i]}",
                        org=(8, coordinates_y[counter]), fontFace=cv2.FONT_HERSHEY_PLAIN, fontScale=1.3,
                        color=color, thickness=1)
            cv2.putText(img=image, text=f"@{self.ports_dict[i]}", org=(155, coordinates_y[counter]),
                        fontFace=cv2.FONT_HERSHEY_PLAIN, fontScale=1.3, color=color, thickness=1)
            counter += 1
        return image

    def update_comms_host(self) -> None:
        """Updates the image showing connection status
        """
        self.hostname_img_cv = cv2.imread('img/comms_frame.png')
        self.hostname_img_cv = self.draw_hostname_conn_base(image=self.hostname_img_cv)
        self.hostname_img = ImageTk.PhotoImage(PILImage.fromarray(self.hostname_img_cv))
        self.hostname_img_canvas.itemconfig(self.hostname_img_tk, image=self.hostname_img)

    def draw_host_status_base(self, image: any) -> any:
        """Draw host status base image
        """
        # Config
        if self.config_is_set:
            cv2.line(img=image, pt1=(16, 24), pt2=(12, 20), color=terminal_green, thickness=1)  # Checkmark
            cv2.line(img=image, pt1=(16, 24), pt2=(24, 8), color=terminal_green, thickness=1)  # Checkmark
            cv2.putText(img=image, text=f"Config Set", org=(35, 22), fontFace=cv2.FONT_HERSHEY_PLAIN, fontScale=1.3,
                        color=terminal_green, thickness=1)
        else:
            cv2.circle(img=image, center=(15, 15), radius=8, color=error_red, thickness=1)  # Null character
            cv2.line(img=image, pt1=(24, 6), pt2=(6, 24), color=error_red, thickness=1)  # Null character
            cv2.putText(img=image, text=f"Config Not Set", org=(35, 22), fontFace=cv2.FONT_HERSHEY_PLAIN, fontScale=1.3,
                        color=error_red, thickness=1)
        # Mission
        mission = self.mission_config_string.get().upper()
        color = terminal_green
        if mission == 'NONE':
            color = error_red
        cv2.putText(img=image, text=f"Mission: {mission}", org=(8, 45), fontFace=cv2.FONT_HERSHEY_PLAIN, fontScale=1.3,
                    color=color, thickness=1)
        # Enabled Sockets
        coordinates_y = [70, 95, 120, 145, 170]
        counter = 0
        color = terminal_green
        enable_text = ''
        for i in self.enable_dict_by_string:
            if self.enable_dict_by_string[i] > 0:  # Green, enabled
                color = terminal_green
                enable_text = 'ENABLED'
            else:
                color = error_red
                enable_text = 'DISABLED'
            cv2.putText(img=image, text=f"[{self.ports_dict_by_shorthand[i]}]",
                        org=(8, coordinates_y[counter]), fontFace=cv2.FONT_HERSHEY_PLAIN, fontScale=1.3,
                        color=color, thickness=1)
            cv2.putText(img=image, text=enable_text, org=(100, coordinates_y[counter]), fontFace=cv2.FONT_HERSHEY_PLAIN,
                        fontScale=1.3, color=color, thickness=1)
            counter += 1
        return image

    def update_host_display(self) -> None:
        """Updates the image showing HOST status
        """
        self.enable_dict_by_string['Video'] = int(self.video_socket_is_enabled.get() is True)
        self.enable_dict_by_string['Logging'] = self.logging_socket_level.get()
        self.enable_dict_by_string['Telemetry'] = int(self.telemetry_socket_is_enabled.get() is True)
        self.enable_dict_by_string['Pilot'] = int(self.pilot_socket_is_enabled.get() is True)
        self.host_img_cv = cv2.imread('img/comms_frame.png')
        self.host_img_cv = self.draw_host_status_base(image=self.host_img_cv)
        self.host_img = ImageTk.PhotoImage(PILImage.fromarray(self.host_img_cv))
        self.host_img_canvas.itemconfig(self.host_img_tk, image=self.host_img)

    @staticmethod
    def update_button(button: any, enabled: bool) -> bool:
        """Swaps button color if it doesn't match enabled. Called for red/green buttons.
        :param button: tkinter button object or object w/ background component
        :param enabled: boolean for switching a button's color
        :return if it worked
        """
        if (button.config('bg')[4] == 'red') and enabled:
            button.configure(button, bg='green')
            return True
        elif (button.config('bg')[4] == 'green') and not enabled:
            button.configure(button, bg='red')
            return True
        else:
            return False

    @staticmethod
    def update_button_enable(button: any, enabled: bool) -> None:
        """Swaps button color if it doesn't match enabled. Called for black/yellow buttons.
        :param button: tkinter button object or object w/ background component
        :param enabled: boolean for switching a button's color
        """
        if (button.config('bg')[4] == 'black') and enabled:
            button.configure(button, bg='yellow')
        elif (button.config('bg')[4] == 'yellow') and not enabled:
            button.configure(button, bg='black')

    @staticmethod
    def update_button_int(button: any, status: int) -> None:
        """Swaps button color if it doesn't match status. Called for different levels and black/yellow.
        :param button: tkinter button object or object w/ background component and text
        :param status: int that contains new code to place in button
        """
        if (button.config('bg')[4] == 'black') and (status > 0):
            button.configure(button, bg='yellow')
            button.configure(button, text='  ' + str(status) + '  ')
        elif (button.config('bg')[4] == 'yellow') and (status == 0):
            button.configure(button, bg='black')
            button.configure(button, text='     ')

    @staticmethod
    def update_status_string(text: any, status: str) -> None:
        """Sets text to status. Called for setting text boxes in labels.
        :param text: tkinter text box object or object w/ text component
        :param status: str that contains new status
        """
        if text.config('text')[0] != status:
            text.configure(text, text=status)

    def update_frames(self) -> None:
        """Checks pipe for data and updates frame in video window if we have a new frame.
        """
        if self.video_stream_pipe_in is not None:  # Check for proper initialization first
            conn = mp.connection.wait([self.video_stream_pipe_in], timeout=-1)
            if len(conn) > 0:  # Frame in pipe
                frame = conn[0].recv()
                # Convert from BGR to RGB
                b, g, r = cv2.split(frame)
                image = cv2.merge((r, g, b))
                # Alternate between frames. Calling ImageTk then video_window itemconfig garbage collects the old frame
                # A second frame that is alternated to is still garbage collected but not visibly.
                self.frame_counter += 1
                if self.frame_counter % 2 == 1:
                    self.img_2 = ImageTk.PhotoImage(PILImage.fromarray(image))
                    self.video_window.itemconfig(self.video_window_img, image=self.img_2)
                else:
                    self.img = ImageTk.PhotoImage(PILImage.fromarray(image))
                    self.video_window.itemconfig(self.video_window_img, image=self.img)

    def send_controller_state(self) -> None:
        """Sends current controller state to Pilot process, then updates controller visualizer in GUI
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
            # self.pilot_pipe_out.send((control_in.tobytes()))
            self.maestro_controls = self.ct.translate_to_maestro_controller(self.current_control_inputs)
            self.pilot_pipe_out.send((struct.pack('>6b',
                                                  self.maestro_controls[0],
                                                  self.maestro_controls[1],
                                                  self.maestro_controls[2],
                                                  self.maestro_controls[3],
                                                  self.maestro_controls[4],
                                                  self.maestro_controls[5])))
            # L2/R2 threshold update
            button_frame = cv2.imread('img/l2r2_base.png')
            button_frame_2 = cv2.imread('img/l2r2_base.png')
            step = 0.05
            l_half = 0
            r_half = 0
            level_l = self.current_control_inputs[0][4]
            level_r = self.current_control_inputs[0][5]
            if level_l >= 0:
                l_half = 1
            else:
                l_half = 2
            if level_r >= 0:
                r_half = 1
            else:
                r_half = 2
            level_l = math.fabs(level_l)
            level_r = math.fabs(level_r)
            start_pos_lr_top = (0, 19)
            end_pos_lr_top = (39, 0)
            start_pos_lr_bot = (0, 39)
            end_pos_lr_bot = (39, 19)
            steps_l = 0
            steps_r = 0
            while (steps_l * step) < level_l:
                steps_l += 1
            if steps_l > 19:
                steps_l = 19
            while (steps_r * step) < level_r:
                steps_r += 1
            if steps_r > 19:
                steps_r = 19
            result_l2_x_top = 39
            result_l2_y_top = 0
            result_l2_x_bot = 0
            result_l2_y_bot = 39
            result_r2_x_top = 39
            result_r2_y_top = 0
            result_r2_x_bot = 0
            result_r2_y_bot = 39
            if l_half == 2:
                result_l2_y_top = int(math.fabs(int(math.fabs(19 - steps_l)) - 19)) + 19
            else:
                result_l2_y_top = 19 - steps_l
            if r_half == 2:
                result_r2_y_top = int(math.fabs(int(math.fabs(19 - steps_r)) - 19)) + 19
            else:
                result_r2_y_top = 19 - steps_r
            button_frame = cv2.rectangle(img=button_frame,
                                    pt1=(result_l2_x_top, result_l2_y_top),
                                    pt2=(result_l2_x_bot, result_l2_y_bot),
                                    color=(255, 0, 0),
                                    thickness=-1)
            button_frame_2 = cv2.rectangle(img=button_frame_2,
                                         pt1=(result_r2_x_top, result_r2_y_top),
                                         pt2=(result_r2_x_bot, result_r2_y_bot),
                                         color=(255, 0, 0),
                                         thickness=-1)
            # Alternate between frames similar to update_frames function
            self.lr_button_frame_counter += 1
            if self.joystick_frame_counter % 2 == 1:
                self.l_button_img = ImageTk.PhotoImage(PILImage.fromarray(button_frame))
                self.r_button_img = ImageTk.PhotoImage(PILImage.fromarray(button_frame_2))
                self.ctrl_l2_button.itemconfig(self.l_window_img, image=self.l_button_img)
                self.ctrl_r2_button.itemconfig(self.r_window_img, image=self.r_button_img)
            else:
                self.l_button_img_2 = ImageTk.PhotoImage(PILImage.fromarray(button_frame))
                self.r_button_img_2 = ImageTk.PhotoImage(PILImage.fromarray(button_frame_2))
                self.ctrl_l2_button.itemconfig(self.l_window_img, image=self.l_button_img_2)
                self.ctrl_r2_button.itemconfig(self.r_window_img, image=self.r_button_img_2)
            # Joystick position update
            frame = cv2.imread('img/joystick_base_img.png')
            frame_2 = cv2.imread('img/joystick_base_img.png')
            # Calculate new joystick location, index is cartesian plane equivalent
            l_quadrant = 0
            r_quadrant = 0
            pointer_l_x = self.current_control_inputs[0][0]
            pointer_l_y = self.current_control_inputs[0][1]
            pointer_r_x = self.current_control_inputs[0][2]
            pointer_r_y = self.current_control_inputs[0][3]
            # l quadrant calculation
            if (pointer_l_x >= 0) and (pointer_l_y < 0):
                l_quadrant = 1
            elif (pointer_l_x < 0) and (pointer_l_y < 0):
                l_quadrant = 2
            elif (pointer_l_x < 0) and (pointer_l_y >= 0):
                l_quadrant = 3
            else:
                l_quadrant = 4
            # r quadrant calculation
            if (pointer_r_x >= 0) and (pointer_r_y < 0):
                r_quadrant = 1
            elif (pointer_r_x < 0) and (pointer_r_y < 0):
                r_quadrant = 2
            elif (pointer_r_x < 0) and (pointer_r_y >= 0):
                r_quadrant = 3
            else:
                r_quadrant = 4
            pointer_l_x = math.fabs(pointer_l_x)
            pointer_l_y = math.fabs(pointer_l_y)
            pointer_r_x = math.fabs(pointer_r_x)
            pointer_r_y = math.fabs(pointer_r_y)
            coord_l_x = 0
            step_l_x = 0
            coord_l_y = 0
            step_l_y = 0
            coord_r_x = 0
            step_r_x = 0
            coord_r_y = 0
            step_r_y = 0
            while coord_l_x < pointer_l_x:
                coord_l_x += step
                step_l_x += 1
            if step_l_x > 19:
                step_l_x = 19
            while coord_l_y < pointer_l_y:
                coord_l_y += step
                step_l_y += 1
            if step_l_y > 19:
                step_l_y = 19
            while coord_r_x < pointer_r_x:
                coord_r_x += step
                step_r_x += 1
            if step_r_x > 19:
                step_r_x = 19
            while coord_r_y < pointer_r_y:
                coord_r_y += step
                step_r_y += 1
            if step_r_y > 19:
                step_r_y = 19
            start_pos_l = []
            start_pos_r = []
            if l_quadrant == 1:  # This is why Python needs switch case
                start_pos_l = [(19, 19), (20, 20)]
            elif l_quadrant == 2:
                start_pos_l = [(0, 19), (1, 20)]
            elif l_quadrant == 3:
                start_pos_l = [(0, 38), (1, 39)]
            else:  # cartesian quadrant 4
                start_pos_l = [(19, 38), (20, 39)]
            if r_quadrant == 1:
                start_pos_r = [(19, 19), (20, 20)]
            elif r_quadrant == 2:
                start_pos_r = [(0, 19), (1, 20)]
            elif r_quadrant == 3:
                start_pos_r = [(0, 38), (1, 39)]
            else:  # cartesian quadrant 4
                start_pos_r = [(19, 38), (20, 39)]
            if l_quadrant == 1:
                result_l_x_top = start_pos_l[0][0] + step_l_x
                result_l_y_top = start_pos_l[0][1] - step_l_y
                result_l_x_bot = result_l_x_top + 1
                result_l_y_bot = result_l_y_top + 1
            elif l_quadrant == 2:
                result_l_x_top = start_pos_l[0][0] + (19 - step_l_x)
                result_l_y_top = start_pos_l[0][1] - step_l_y
                result_l_x_bot = result_l_x_top + 1
                result_l_y_bot = result_l_y_top + 1
            elif l_quadrant == 3:
                result_l_x_top = start_pos_l[0][0] + (19 - step_l_x)
                result_l_y_top = start_pos_l[0][1] - (19 - step_l_y)
                result_l_x_bot = result_l_x_top + 1
                result_l_y_bot = result_l_y_top + 1
            else:
                result_l_x_top = start_pos_l[0][0] + step_l_x
                result_l_y_top = start_pos_l[0][1] - (19 - step_l_y)
                result_l_x_bot = result_l_x_top + 1
                result_l_y_bot = result_l_y_top + 1
            if r_quadrant == 1:
                result_r_x_top = start_pos_r[0][0] + step_r_x
                result_r_y_top = start_pos_r[0][1] - step_r_y
                result_r_x_bot = result_r_x_top + 1
                result_r_y_bot = result_r_y_top + 1
            elif r_quadrant == 2:
                result_r_x_top = start_pos_r[0][0] + (19 - step_r_x)
                result_r_y_top = start_pos_r[0][1] - step_r_y
                result_r_x_bot = result_r_x_top + 1
                result_r_y_bot = result_r_y_top + 1
            elif r_quadrant == 3:
                result_r_x_top = start_pos_r[0][0] + (19 - step_r_x)
                result_r_y_top = start_pos_r[0][1] - (19 - step_r_y)
                result_r_x_bot = result_r_x_top + 1
                result_r_y_bot = result_r_y_top + 1
            else:
                result_r_x_top = start_pos_r[0][0] + step_r_x
                result_r_y_top = start_pos_r[0][1] - (19 - step_r_y)
                result_r_x_bot = result_r_x_top + 1
                result_r_y_bot = result_r_y_top + 1
            frame_l = cv2.line(frame, pt1=(result_l_x_top, 0), pt2=(result_l_x_bot-1, 39), color=(0, 180, 0),
                               thickness=1)
            frame_l = cv2.line(frame_l, pt1=(0, result_l_y_top), pt2=(39, result_l_y_bot-1), color=(0, 180, 0),
                               thickness=1)
            frame_l = cv2.rectangle(img=frame_l,
                                  pt1=(result_l_x_top, result_l_y_top),
                                  pt2=(result_l_x_bot, result_l_y_bot),
                                  color=(255, 255, 255),
                                  thickness=1)
            frame_r = cv2.line(frame_2, pt1=(result_r_x_top, 0), pt2=(result_r_x_bot - 1, 39), color=(0, 180, 0),
                               thickness=1)
            frame_r = cv2.line(frame_r, pt1=(0, result_r_y_top), pt2=(39, result_r_y_bot - 1), color=(0, 180, 0),
                               thickness=1)
            frame_r = cv2.rectangle(img=frame_r,
                                    pt1=(result_r_x_top, result_r_y_top),
                                    pt2=(result_r_x_bot, result_r_y_bot),
                                    color=(255, 255, 255),
                                    thickness=1)
            self.joystick_frame_counter += 1
            if self.joystick_frame_counter % 2 == 1:
                self.joystick_l_img = ImageTk.PhotoImage(PILImage.fromarray(frame_l))
                self.joystick_r_img = ImageTk.PhotoImage(PILImage.fromarray(frame_r))
                self.joystick_l.itemconfig(self.joystick_window_l_img, image=self.joystick_l_img)
                self.joystick_r.itemconfig(self.joystick_window_r_img, image=self.joystick_r_img)
            else:
                self.joystick_l_img_2 = ImageTk.PhotoImage(PILImage.fromarray(frame_l))
                self.joystick_r_img_2 = ImageTk.PhotoImage(PILImage.fromarray(frame_r))
                self.joystick_l.itemconfig(self.joystick_window_l_img, image=self.joystick_l_img_2)
                self.joystick_r.itemconfig(self.joystick_window_r_img, image=self.joystick_r_img_2)

            # Button state update
            # Note: comment this out if having trouble with gui freezing, means pilot can't connect
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
            if self.ctrl_l_button.config('bg')[4] == 'white' and (1 == int(self.current_control_inputs[0, 12])):
                self.ctrl_l_button.configure(self.ctrl_l_button, bg='red')
            elif self.ctrl_l_button.config('bg')[4] == 'red' and (0 == int(self.current_control_inputs[0, 12])):
                self.ctrl_l_button.configure(self.ctrl_l_button, bg='white')
            if self.ctrl_r_button.config('bg')[4] == 'white' and (1 == int(self.current_control_inputs[0, 13])):
                self.ctrl_r_button.configure(self.ctrl_r_button, bg='red')
            elif self.ctrl_r_button.config('bg')[4] == 'red' and (0 == int(self.current_control_inputs[0, 13])):
                self.ctrl_r_button.configure(self.ctrl_r_button, bg='white')

            # Thruster update
            thruster_frame = cv2.imread('img/maestro_conn.png')
            thruster_remap = [self.maestro_controls[0],
                     self.maestro_controls[1],
                     self.maestro_controls[5],
                     self.maestro_controls[2],
                     self.maestro_controls[4],
                     self.maestro_controls[3]]
            halves = [0, 0, 0, 0, 0, 0]
            x_bot_vals = [3, 32, 61, 90, 119, 148]
            x_top_vals = [24, 53, 82, 111, 140, 169]
            for i in range(len(thruster_remap)):
                if thruster_remap[i] > 0:
                    halves[i] = 1
                    px_add_y_count = -1 * math.ceil(math.fabs(thruster_remap[i] / 2) - 50)
                    thruster_frame = cv2.rectangle(img=thruster_frame,
                                            pt1=(x_bot_vals[i], 53),
                                            pt2=(x_top_vals[i], int(3 + px_add_y_count)),
                                            color=(0, 0, 255),
                                            thickness=-1)
                elif thruster_remap[i] < 0:
                    halves[i] = -1
                    thruster_remap[i] = math.fabs(thruster_remap[i])
                    px_add_y_count = math.ceil(thruster_remap[i] / 2)
                    thruster_frame = cv2.rectangle(img=thruster_frame,
                                                   pt1=(x_top_vals[i], 55),
                                                   pt2=(x_bot_vals[i], int(55 + px_add_y_count)),
                                                   color=(0, 0, 255),
                                                   thickness=-1)
                else:
                    pass
            self.thruster_frame_counter += 1
            if self.thruster_frame_counter % 2 == 1:
                self.thruster_img_2 = ImageTk.PhotoImage(PILImage.fromarray(thruster_frame))
                self.thruster_canvas.itemconfig(self.thruster_window_img, image=self.thruster_img_2)
            else:
                self.thruster_img_1 = ImageTk.PhotoImage(PILImage.fromarray(thruster_frame))
                self.thruster_canvas.itemconfig(self.thruster_window_img, image=self.thruster_img_1)

    def update_telemetry(self) -> None:
        """Updates the telemetry display with updated data.
        """
        if self.telemetry_socket_is_connected:  # Check for conn before updating data
            sensor_frame = cv2.imread('img/sensor_base_new.png')
            cv2.putText(img=sensor_frame,
                        text='Accelerometer',
                        org=(8, 25),
                        fontFace=cv2.FONT_HERSHEY_PLAIN,
                        fontScale=1.2,
                        color=terminal_green,
                        thickness=1)
            cv2.putText(img=sensor_frame,
                        text=f'X: {round(self.telemetry_current_state.sensors["accelerometer_x"], 3)}',
                        org=(8, 50),
                        fontFace=cv2.FONT_HERSHEY_DUPLEX,
                        fontScale=0.8,
                        color=terminal_green,
                        thickness=1)
            cv2.putText(img=sensor_frame,
                        text=f'Y: {round(self.telemetry_current_state.sensors["accelerometer_y"], 3)}',
                        org=(8, 75),
                        fontFace=cv2.FONT_HERSHEY_DUPLEX,
                        fontScale=0.8,
                        color=terminal_green,
                        thickness=1)
            cv2.putText(img=sensor_frame,
                        text=f'Z: {round(self.telemetry_current_state.sensors["accelerometer_z"], 3)}',
                        org=(8, 100),
                        fontFace=cv2.FONT_HERSHEY_DUPLEX,
                        fontScale=0.8,
                        color=terminal_green,
                        thickness=1)
            cv2.putText(img=sensor_frame,
                        text='Voltmeter',
                        org=(8, 125),
                        fontFace=cv2.FONT_HERSHEY_PLAIN,
                        fontScale=1.2,
                        color=terminal_green,
                        thickness=1)
            cv2.putText(img=sensor_frame,
                        text=f'{round(self.telemetry_current_state.sensors["voltmeter"], 3)}',
                        org=(8, 150),
                        fontFace=cv2.FONT_HERSHEY_DUPLEX,
                        fontScale=0.8,
                        color=terminal_green,
                        thickness=1)
            cv2.putText(img=sensor_frame,
                        text='Battery Current',
                        org=(8, 175),
                        fontFace=cv2.FONT_HERSHEY_PLAIN,
                        fontScale=1.2,
                        color=terminal_green,
                        thickness=1)
            cv2.putText(img=sensor_frame,
                        text=f'{round(self.telemetry_current_state.sensors["battery_current"], 3)}',
                        org=(8, 200),
                        fontFace=cv2.FONT_HERSHEY_DUPLEX,
                        fontScale=0.8,
                        color=terminal_green,
                        thickness=1)
            # cv2.putText(img=sensor_frame, text=str(self.telemetry_frame_counter), org=(8, 225),
            #            fontFace=cv2.FONT_HERSHEY_DUPLEX, fontScale=0.8, color=terminal_green, thickness=1)
            cv2.putText(img=sensor_frame,
                        text='Gyroscope',
                        org=(248, 25),
                        fontFace=cv2.FONT_HERSHEY_PLAIN,
                        fontScale=1.2,
                        color=terminal_green,
                        thickness=1)
            cv2.putText(img=sensor_frame,
                        text=f'X: {round(self.telemetry_current_state.sensors["gyroscope_x"], 3)}',
                        org=(248, 50),
                        fontFace=cv2.FONT_HERSHEY_DUPLEX,
                        fontScale=0.8,
                        color=terminal_green,
                        thickness=1)
            cv2.putText(img=sensor_frame,
                        text=f'Y: {round(self.telemetry_current_state.sensors["gyroscope_y"], 3)}',
                        org=(248, 75),
                        fontFace=cv2.FONT_HERSHEY_DUPLEX,
                        fontScale=0.8,
                        color=terminal_green,
                        thickness=1)
            cv2.putText(img=sensor_frame,
                        text=f'Z: {round(self.telemetry_current_state.sensors["gyroscope_z"], 3)}',
                        org=(248, 100),
                        fontFace=cv2.FONT_HERSHEY_DUPLEX,
                        fontScale=0.8,
                        color=terminal_green,
                        thickness=1)
            cv2.putText(img=sensor_frame,
                        text='Battery 1 Volts',
                        org=(248, 125),
                        fontFace=cv2.FONT_HERSHEY_PLAIN,
                        fontScale=1.2,
                        color=terminal_green,
                        thickness=1)
            cv2.putText(img=sensor_frame,
                        text=f'{round(self.telemetry_current_state.sensors["battery_1_voltage"], 3)}',
                        org=(248, 150),
                        fontFace=cv2.FONT_HERSHEY_DUPLEX,
                        fontScale=0.8,
                        color=terminal_green,
                        thickness=1)
            cv2.putText(img=sensor_frame,
                        text='Battery 2 Volts',
                        org=(248, 175),
                        fontFace=cv2.FONT_HERSHEY_PLAIN,
                        fontScale=1.2,
                        color=terminal_green,
                        thickness=1)
            cv2.putText(img=sensor_frame,
                        text=f'{round(self.telemetry_current_state.sensors["battery_2_voltage"], 3)}',
                        org=(248, 200),
                        fontFace=cv2.FONT_HERSHEY_DUPLEX,
                        fontScale=0.8,
                        color=terminal_green,
                        thickness=1)
            cv2.putText(img=sensor_frame,
                        text='Magnetometer',
                        org=(488, 25),
                        fontFace=cv2.FONT_HERSHEY_PLAIN,
                        fontScale=1.2,
                        color=terminal_green,
                        thickness=1)
            cv2.putText(img=sensor_frame,
                        text=f'X: {round(self.telemetry_current_state.sensors["magnetometer_x"], 3)}',
                        org=(488, 50),
                        fontFace=cv2.FONT_HERSHEY_DUPLEX,
                        fontScale=0.8,
                        color=terminal_green,
                        thickness=1)
            cv2.putText(img=sensor_frame,
                        text=f'Y: {round(self.telemetry_current_state.sensors["magnetometer_y"], 3)}',
                        org=(488, 75),
                        fontFace=cv2.FONT_HERSHEY_DUPLEX,
                        fontScale=0.8,
                        color=terminal_green,
                        thickness=1)
            cv2.putText(img=sensor_frame,
                        text=f'Z: {round(self.telemetry_current_state.sensors["magnetometer_z"], 3)}',
                        org=(488, 100),
                        fontFace=cv2.FONT_HERSHEY_DUPLEX,
                        fontScale=0.8,
                        color=terminal_green,
                        thickness=1)
            cv2.putText(img=sensor_frame,
                        text='Pressure Transducer',
                        org=(488, 125),
                        fontFace=cv2.FONT_HERSHEY_PLAIN,
                        fontScale=1.2,
                        color=terminal_green,
                        thickness=1)
            cv2.putText(img=sensor_frame,
                        text=f'{round(self.telemetry_current_state.sensors["pressure_transducer"], 3)}',
                        org=(488, 150),
                        fontFace=cv2.FONT_HERSHEY_DUPLEX,
                        fontScale=0.8,
                        color=terminal_green,
                        thickness=1)
            cv2.putText(img=sensor_frame,
                        text='Roll',
                        org=(728, 25),
                        fontFace=cv2.FONT_HERSHEY_PLAIN,
                        fontScale=1.2,
                        color=terminal_green,
                        thickness=1)
            cv2.putText(img=sensor_frame,
                        text=f'{round(self.telemetry_current_state.sensors["roll"], 3)}',
                        org=(728, 50),
                        fontFace=cv2.FONT_HERSHEY_DUPLEX,
                        fontScale=0.8,
                        color=terminal_green,
                        thickness=1)
            cv2.putText(img=sensor_frame,
                        text='Pitch',
                        org=(728, 75),
                        fontFace=cv2.FONT_HERSHEY_PLAIN,
                        fontScale=1.2,
                        color=terminal_green,
                        thickness=1)
            cv2.putText(img=sensor_frame,
                        text=f'{round(self.telemetry_current_state.sensors["pitch"], 3)}',
                        org=(728, 100),
                        fontFace=cv2.FONT_HERSHEY_DUPLEX,
                        fontScale=0.8,
                        color=terminal_green,
                        thickness=1)
            cv2.putText(img=sensor_frame,
                        text='Yaw',
                        org=(728, 125),
                        fontFace=cv2.FONT_HERSHEY_PLAIN,
                        fontScale=1.2,
                        color=terminal_green,
                        thickness=1)
            cv2.putText(img=sensor_frame,
                        text=f'{round(self.telemetry_current_state.sensors["yaw"], 3)}',
                        org=(728, 150),
                        fontFace=cv2.FONT_HERSHEY_DUPLEX,
                        fontScale=0.8,
                        color=terminal_green,
                        thickness=1)
            self.telemetry_frame_counter += 1
            if self.telemetry_frame_counter % 2 == 1:
                self.telemetry_canvas_1_img = ImageTk.PhotoImage(PILImage.fromarray(sensor_frame))
                self.telemetry_canvas_0.itemconfig(self.telemetry_canvas_0_config, image=self.telemetry_canvas_1_img)
            else:
                self.telemetry_canvas_0_img = ImageTk.PhotoImage(PILImage.fromarray(sensor_frame))
                self.telemetry_canvas_0.itemconfig(self.telemetry_canvas_0_config, image=self.telemetry_canvas_0_img)

    def read_pipe(self) -> None:
        """Checks input pipe for info from other processes, processes commands here
        """
        gui_cmd = []
        if self.in_pipe is not None:  # Checks for proper initialization first
            conn = mp.connection.wait([self.in_pipe], timeout=-1)
            if len(conn) > 0:
                gui_cmd = conn[0].recv()
                if gui_cmd[1] == 'video':
                    if gui_cmd[2] == 'conn_socket':
                        self.video_socket_is_connected = True
                        self.conn_dict_by_string['Video'] = self.video_socket_is_connected
                        self.update_comms_host()
                    elif gui_cmd[2] == 'no_conn_socket':
                        self.video_socket_is_connected = False
                        self.conn_dict_by_string['Video'] = self.video_socket_is_connected
                        self.update_comms_host()
                elif gui_cmd[1] == 'logging':
                    if gui_cmd[2] == 'conn_socket':
                        self.logging_socket_is_connected = True
                        self.conn_dict_by_string['Logging'] = self.logging_socket_is_connected
                        self.update_comms_host()
                    elif gui_cmd[2] == 'no_conn_socket':
                        self.logging_socket_is_connected = False
                        self.conn_dict_by_string['Logging'] = self.logging_socket_is_connected
                        self.update_comms_host()
                    else:
                        self.remote_logging_queue.append(gui_cmd[2])
                elif gui_cmd[1] == 'telemetry':
                    if isinstance(gui_cmd[2], str):
                        if gui_cmd[2] == 'conn_socket':
                            self.telemetry_socket_is_connected = True
                            self.conn_dict_by_string['Telemetry'] = self.telemetry_socket_is_connected
                            self.update_comms_host()
                        elif gui_cmd[2] == 'no_conn_socket':
                            self.telemetry_socket_is_connected = False
                            self.conn_dict_by_string['Telemetry'] = self.telemetry_socket_is_connected
                            self.update_comms_host()
                    elif isinstance(gui_cmd[2], bytes):
                        self.telemetry_current_state.load_data_from_bytes(gui_cmd[2])
                elif gui_cmd[1] == 'pilot':
                    if gui_cmd[2] == 'conn_socket':
                        self.pilot_socket_is_connected = True
                        self.conn_dict_by_string['Pilot'] = self.pilot_socket_is_connected
                        self.update_comms_host()
                    elif gui_cmd[2] == 'no_conn_socket':
                        self.pilot_socket_is_connected = False
                        self.conn_dict_by_string['Pilot'] = self.pilot_socket_is_connected
                        self.update_comms_host()

    def update(self) -> None:
        """Update function to read elements from other processes into the GUI
        Overriden from tkinter's window class
        """
        # Manual on update functions below:
        self.run_logger()
        self.update_frames()  # Update video frame
        if self.pilot_socket_is_connected:
            self.send_controller_state()  # Send current inputs
        self.update_telemetry()  # Update telemetry displayed
        self.read_pipe() # Check for pipe updates
        self.after(gui_update_ms, self.update) # Call this function again after gui_update_ms


def gui_proc_main(gui_input: mp.Pipe, gui_output: mp.Pipe, gui_logger: LoggerWrapper, video_stream_pipe_in: mp.Pipe,
                  pilot_pipe_out: mp.Pipe) -> None:
    """GUI Driver code
    """
    # Build Application
    root_window = tk.Tk()
    root_window.geometry(str(resolution[0] - edge_size - edge_size) + "x" + str(resolution[1] - top_bar_size -
                                                                                edge_size - edge_size))
    application = Window(pilot_pipe_out, master=root_window)

    # Queues for multiprocessing passed into object
    application.logger = gui_logger
    application.in_pipe = gui_input
    application.out_pipe = gui_output
    application.video_stream_pipe_in = video_stream_pipe_in
    root_window.mainloop()


def video_proc_udp(logger: LoggerWrapper, video_pipe_in: mp.Pipe, video_pipe_out: mp.Pipe,
                   video_stream_out: mp.Pipe) -> None:
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


def video_proc_tcp(logger: LoggerWrapper, video_pipe_in: mp.Pipe, video_pipe_out: mp.Pipe,
                   video_stream_out: mp.Pipe) -> None:
    """Video socket driver code, running on a TCP connection.
    """
    hostname = ''
    port = ''
    socket_started = False
    server_conn = False
    rcon_try_counter_max = 3
    rcon_try_count = 0
    while True:
        # Wait for this process to receive info from the pipe, read it in when it does
        conn = mp.connection.wait([video_pipe_in], timeout=-1)
        if len(conn) > 0:
            result = conn[0].recv()
            if result[2] == 'initialize':
                hostname = result[3]
                port = result[4]
                socket_started = True
                rcon_try_count = 0
        # Connect over TCP
        if socket_started:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                try:
                    s.connect((hostname, port))
                    server_conn = True
                    rcon_try_count = 0
                    video_pipe_out.send(('gui', 'video', 'conn_socket'))
                except ConnectionRefusedError as e:
                    rcon_try_count += 1
                    logger.log('[@VID] ERROR: Failed to connect to remote server. '
                               + 'Retrying: ' + str(rcon_try_count) + '/' + str(rcon_try_counter_max))
                    server_conn = False
                    if rcon_try_count >= rcon_try_counter_max:
                        socket_started = False
                        video_pipe_out.send(('gui', 'video', 'no_conn_socket'))
                data = b''
                payload_size = struct.calcsize('>L')
                # Get frame data and send to video_stream_out
                while server_conn:
                    try:
                        s.sendall(b'1')
                    except (ConnectionAbortedError, ConnectionResetError) as e:
                        server_conn = False
                        break
                    data_size = 0
                    data_size_last = 0
                    while (len(data) < payload_size) and server_conn:
                        try:
                            data += s.recv(4096)
                            data_size_last = data_size
                            data_size = len(data)
                        except (ConnectionAbortedError, ConnectionResetError):
                            server_conn = False
                            break
                        else:
                            if data_size_last == data_size:
                                server_conn = False
                                break
                    packed_msg_size = data[:payload_size]
                    data = data[payload_size:]
                    try:
                        msg_size = struct.unpack('>L', packed_msg_size)[0]
                    except struct.error as e:  # Server connection interrupt mid frame send
                        server_conn = False
                        break
                    while len(data) < msg_size:
                        try:
                            data += s.recv(4096)
                        except (ConnectionAbortedError, ConnectionResetError) as e:
                            server_conn = False
                            break
                    frame_data = data[:msg_size]
                    data = data[msg_size:]
                    frame = pickle.loads(frame_data, fix_imports=True, encoding='bytes')
                    frame = cv2.imdecode(frame, cv2.IMREAD_COLOR)
                    # Pipe video output to gui
                    video_stream_out.send(frame)


def logging_proc(logger: LoggerWrapper, logging_pipe_in: mp.Pipe, logging_pipe_out: mp.Pipe) -> None:
    """Receives logs from Intelligence over TCP connection.
    """
    hostname = ''
    port = ''
    started = False
    server_conn = False
    rcon_try_counter_max = 3
    rcon_try_count = 0
    while True:
        conn = mp.connection.wait([logging_pipe_in], timeout=-1)
        if len(conn) > 0:
            result = conn[0].recv()
            if result[2] == 'initialize':
                hostname = result[3]
                port = result[4]
                started = True
                rcon_try_count = 0
        if started:
            lc = sub_logging.LoggerClient(save_logs=False)
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                try:
                    s.connect((hostname, port))
                    server_conn = True
                    logging_pipe_out.send(('gui', 'logging', 'conn_socket'))
                except ConnectionRefusedError as e:
                    rcon_try_count += 1
                    logger.log('[@LOG] ERROR: Failed to connect to remote server. '
                               + 'Retrying: ' + str(rcon_try_count) + '/' + str(rcon_try_counter_max))
                    server_conn = False
                    if rcon_try_count >= rcon_try_counter_max:
                        started = False
                        logging_pipe_out.send(('gui', 'logging', 'no_conn_socket'))
                while server_conn:
                    try:
                        s.sendall(b'1')
                    except (ConnectionAbortedError, ConnectionResetError) as e:
                        server_conn = False
                        break
                    try:
                        data = s.recv(4096)
                        # Parse logs
                        log_list = log_parse(data)
                        # Send to GUI
                        for i in range(len(log_list)):
                            lc.logging_queue.append(log_list[i])
                            logging_pipe_out.send(('gui', 'logging', lc.dequeue()))
                    except (ConnectionAbortedError, ConnectionResetError) as e:
                        server_conn = False
                        break


def telemetry_proc(logger: LoggerWrapper, telemetry_pipe_in: mp.Pipe, telemetry_pipe_out: mp.Pipe) -> None:
    """Receives telemetry from Control over TCP connection.
    """
    hostname = ''
    port = ''
    started = False
    server_conn = False
    rcon_try_counter_max = 3
    rcon_try_count = 0
    while True:
        conn = mp.connection.wait([telemetry_pipe_in], timeout=-1)
        if len(conn) > 0:
            result = conn[0].recv()
            if result[2] == 'initialize':
                hostname = result[3]
                port = result[4]
                started = True
                rcon_try_count = 0
        if started:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                try:
                    s.connect((hostname, port))
                    server_conn = True
                    telemetry_pipe_out.send(('gui', 'telemetry', 'conn_socket'))
                except ConnectionRefusedError as e:
                    rcon_try_count += 1
                    logger.log('[@TEL] ERROR: Failed to connect to remote server. '
                               + 'Retrying: ' + str(rcon_try_count) + '/' + str(rcon_try_counter_max))
                    server_conn = False
                    if rcon_try_count >= rcon_try_counter_max:
                        started = False
                        telemetry_pipe_out.send(('gui', 'telemetry', 'no_conn_socket'))
                while server_conn:
                    try:
                        s.sendall(b'1')
                    except (ConnectionAbortedError, ConnectionResetError) as e:
                        server_conn = False
                        break
                    try:
                        data = s.recv(4096)
                        telemetry_pipe_out.send(('gui', 'telemetry', data))
                    except (ConnectionAbortedError, ConnectionResetError) as e:
                        server_conn = False


def pilot_proc(logger: LoggerWrapper, pilot_pipe_in: mp.Pipe, pilot_pipe_out: mp.Pipe,
               pipe_in_from_gui: mp.Pipe) -> None:
    """Sends controller input to Pico's Control over TCP connection.
    """
    hostname = ''
    port = ''
    last_input = np.zeros(shape=(1, 1))
    started = False
    server_conn = False
    rcon_try_counter_max = 3
    rcon_try_count = 0
    while True:
        conn = mp.connection.wait([pilot_pipe_in], timeout=-1)
        if len(conn) > 0:
            result = conn[0].recv()
            if isinstance(result[2], str):
                if result[2] == 'initialize':
                    hostname = result[3]
                    port = result[4]
                    started = True
                    rcon_try_count = 0
        if started:
            # Controller
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                try:
                    s.connect((hostname, port))
                    server_conn = True
                    pilot_pipe_out.send(('gui', 'pilot', 'conn_socket'))
                except ConnectionRefusedError as e:
                    print(e)
                    pilot_pipe_out.send(('gui', 'pilot', 'no_conn_socket'))
                    rcon_try_count += 1
                    logger.log('[@PLT] ERROR: Failed to connect to remote server. '
                               + 'Retrying: ' + str(rcon_try_count) + '/' + str(rcon_try_counter_max))
                    server_conn = False
                    if rcon_try_count >= rcon_try_counter_max:
                        started = False
                while server_conn:
                    try:
                        data = s.recv(1024)
                    except (ConnectionAbortedError, ConnectionResetError) as e:
                        print(e)
                        pilot_pipe_out.send(('gui', 'pilot', 'no_conn_socket'))
                        server_conn = False
                        break
                    if data == b'1':
                        data = None
                        controller_input = mp.connection.wait([pipe_in_from_gui], timeout=-1)
                        if len(controller_input) > 0:
                            last_input = controller_input[len(controller_input)-1].recv()
                            try:
                                s.sendall(last_input)
                            except (ConnectionAbortedError, ConnectionResetError) as e:
                                print(e)
                                pilot_pipe_out.send(('gui', 'pilot', 'no_conn_socket'))
                                server_conn = False
                                break
                            controller_input.clear()  # Clear input after sending latest
                        else:  # Send previous input
                            try:
                                s.sendall(last_input)
                            except (ConnectionAbortedError, ConnectionResetError) as e:
                                print(e)
                                pilot_pipe_out.send(('gui', 'pilot', 'no_conn_socket'))
                                server_conn = False
                                break
                    else:
                        pilot_pipe_out.send(('gui', 'pilot', 'no_conn_socket'))
                        server_conn = False
                        break
                    controller_input = mp.connection.wait([pipe_in_from_gui], timeout=-1)
                    if len(controller_input) > 0:
                        controller_input.clear()


def router(logger: LoggerWrapper,  # Gui logger
           from_gui_pipe_in: mp.Pipe, to_gui_pipe_out: mp.Pipe,  # Gui Message Pipe
           from_video_pipe_in: mp.Pipe, to_video_pipe_out: mp.Pipe,  # Video Message Pipe
           from_logger_pipe_in: mp.Pipe, to_logger_pipe_out: mp.Pipe,  # Logger Message Pipe
           from_telemetry_pipe_in: mp.Pipe, to_telemetry_pipe_out: mp.Pipe,  # Sensor/Telemetry Message Pipe
           from_pilot_pipe_in: mp.Pipe, to_pilot_pipe_out: mp.Pipe  # Pilot Message Pipe
           ) -> None:
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


def main() -> None:
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

    # Gui Process
    gui_logger = LoggerWrapper()
    pipe_to_gui_from_router, gui_pipe_in_from_router = context.Pipe()
    pipe_to_router_from_gui, pipe_in_from_gui = context.Pipe()
    gui_proc = context.Process(target=gui_proc_main, args=(gui_pipe_in_from_router,
                                                           pipe_to_router_from_gui,
                                                           gui_logger,
                                                           pipe_in_from_video_stream,
                                                           pipe_to_pilot_from_gui))
    gui_proc.start()
    gui_logger.log('[Info]: Gui Initialized.')  # Log to Gui from main process
    gui_logger.log('+----------------------------+', strip=False)
    gui_logger.log('||    ___ ___  ___ _   _    ||', strip=False)
    gui_logger.log('||   / __|   \\/ __| | | |   ||', strip=False)
    gui_logger.log('||   \\__ \\ |) \\__ \\ |_| |   ||', strip=False)
    gui_logger.log('||   |___/___/|___/\\___/    ||', strip=False)
    gui_logger.log('||                          ||', strip=False)
    gui_logger.log('+----------------------------+--------------------------+', strip=False)
    gui_logger.log('||   _____         _       _               _           ||', strip=False)
    gui_logger.log('||  |     |___ ___| |_ ___| |_ ___ ___ ___|_|___ ___   ||', strip=False)
    gui_logger.log('||  | | | | -_|  _|   | .\'|  _|  _| . |   | |  _|_ -   ||', strip=False)
    gui_logger.log('||  |_|_|_|___|___|_|_|__,|_| |_| |___|_|_|_|___|___|  ||', strip=False)
    gui_logger.log('||                                                     ||', strip=False)
    gui_logger.log('+----------------------------+--------------------------+', strip=False)
    gui_logger.log(' ', strip=False)

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

    # Message Router between processes
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
    print(f'{__name__} started on {n} at {os.getpid()}')  # Kept for testing
    main()

else:
    print(f'Spawned multiprocess at PID: {__name__} {os.getpid()}')  # Kept for testing
