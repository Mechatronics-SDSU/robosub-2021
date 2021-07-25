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
import math

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
import matplotlib
from matplotlib.backends.backend_tkagg import FigureCanvasTk, NavigationToolbar2Tk
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


def request_to_value(r) -> str:
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


def get_int_from_bool(b) -> int:
    """Returns int version of a boolean.
    """
    if b:
        return 1
    else:
        return 0


def log_parse(input_data) -> list:
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
    def __init__(self, hostname, port, logger) -> None:
        self.remote_client = str(hostname)
        self.port = str(port)
        self._channel = grpc.insecure_channel(self.remote_client + ':' + self.port)
        self._stub = cmd_pb2_grpc.CommandGRPCStub(self._channel)
        self.logger = logger
        logger.log('[GRPC] Started up client. ' + self.remote_client + ':' + self.port)

    def send(self, request) -> str:
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


class LoggerWrapper:
    """Provides easy methods for logging with formatting.
    """
    def __init__(self, showtime=True) -> None:
        self.queue = mp.Queue()
        self.add_timestamp = showtime

    def log(self, string, strip=True) -> None:
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
    def __init__(self, pilot_pipe, master=None) -> None:
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
        self.info_window_host_text = tk.Canvas(master=self.master, width=120, height=24, bg='green')
        self.info_window_host_text_img = ImageTk.PhotoImage(PILImage.open('img/host_status_text.png'))
        self.info_window_host_text.create_image((2, 2), anchor=tk.NW, image=self.info_window_host_text_img)
        self.info_window = tk.Frame(master=self.master, width=300, height=640, bg='white')
        # Text
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
        self.telemetry_graph_states = []
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
        self.tel_window_old = tk.Frame(master=self.master, bg='white')
        self.telemetry_window = tk.Frame(master=self.master, width=640, height=244, bg='black')
        self.telemetry_canvas_1 = tk.Canvas(master=self.telemetry_window, width=640, height=88, bd=0, bg='green')
        self.telemetry_canvas_1_img = ImageTk.PhotoImage(PILImage.open('img/sensors_img_1.png'))
        self.telemetry_canvas_1_config = self.telemetry_canvas_1.create_image((2, 2),
                                                                              anchor=tk.NW,
                                                                              image=self.telemetry_canvas_1_img)
        self.telemetry_canvas_2 = tk.Canvas(master=self.telemetry_window, width=640, height=150, bg='green')
        self.telemetry_canvas_2_img = ImageTk.PhotoImage(PILImage.open('img/sensors_img_2.png'))
        self.telemetry_canvas_2_config = self.telemetry_canvas_2.create_image((2, 2),
                                                                              anchor=tk.NW,
                                                                              image=self.telemetry_canvas_2_img)
        self.sensors_text = tk.Canvas(master=self.master, width=100, height=24, bd=0, bg='green')
        self.sensors_text_img = ImageTk.PhotoImage(PILImage.open('img/sensors_text.png'))
        self.sensors_text.create_image((2, 2), anchor=tk.NW, image=self.sensors_text_img)
        self.telemetry_window_names = tk.Frame(master=self.tel_window_old)
        self.telemetry_window_values = tk.Frame(master=self.tel_window_old)
        """
        self.telemetry_colpad = tk.Label(master=self.telemetry_window_names, text='Telemetry Data:', bd=0, anchor='w', bg='white',
                                         justify=tk.LEFT)
        self.telemetry_colpad_2 = tk.Label(master=self.telemetry_window_values, text='          ', bd=0, anchor='w',
                                         bg='white',
                                         justify=tk.LEFT)
                                         """
        # Sensors

        self.accelerometer_text = tk.Label(master=self.telemetry_window_names, text='Accelerometer', bd=0, anchor='w', bg='white',
                                           justify=tk.LEFT)
        self.accelerometer_val = tk.Label(master=self.telemetry_window_values, text=str(
            self.telemetry_current_state.sensors['accelerometer_x']), bd=0, anchor='w', bg='white', justify=tk.LEFT)
        self.magnetometer_text = tk.Label(master=self.telemetry_window_names, text='Magnetometer', bd=0, anchor='w', bg='white',
                                          justify=tk.LEFT)
        self.magnetometer_val = tk.Label(master=self.telemetry_window_values, text=str(
            self.telemetry_current_state.sensors['magnetometer_x']), bd=0, anchor='w', bg='white', justify=tk.LEFT)
        self.pressure_trans_text = tk.Label(master=self.telemetry_window_names, text='Pressure_Transducer', bd=0, anchor='w', bg='white',
                                            justify=tk.LEFT)
        self.pressure_trans_val = tk.Label(master=self.telemetry_window_values, text=str(
            self.telemetry_current_state.sensors['pressure_transducer']), bd=0, anchor='w', bg='white', justify=tk.LEFT)
        self.gyroscope_text = tk.Label(master=self.telemetry_window_names, text='Gyroscope', bd=0, anchor='w', bg='white',
                                       justify=tk.LEFT)
        self.gyroscope_val = tk.Label(master=self.telemetry_window_values, text=str(
            self.telemetry_current_state.sensors['gyroscope_x']), bd=0, anchor='w', bg='white', justify=tk.LEFT)
        self.voltmeter_text = tk.Label(master=self.telemetry_window_names, text='Voltmeter', bd=0, anchor='w', bg='white',
                                       justify=tk.LEFT)
        self.voltmeter_val = tk.Label(master=self.telemetry_window_values, text=str(
            self.telemetry_current_state.sensors['voltmeter']), bd=0, anchor='w', bg='white', justify=tk.LEFT)
        self.battery_current_text = tk.Label(master=self.telemetry_window_names, text='Battery_Current', bd=0, anchor='w', bg='white',
                                             justify=tk.LEFT)
        self.battery_current_val = tk.Label(master=self.telemetry_window_values, text=str(
            self.telemetry_current_state.sensors['battery_current']), bd=0, anchor='w', bg='white', justify=tk.LEFT)
        self.roll_text = tk.Label(master=self.telemetry_window_names, text='Roll', bd=0, anchor='w', bg='white',
                                  justify=tk.LEFT)
        self.roll_val = tk.Label(master=self.telemetry_window_values, text=str(
            self.telemetry_current_state.sensors['roll']), bd=0, anchor='w', bg='white', justify=tk.LEFT)
        self.pitch_text = tk.Label(master=self.telemetry_window_names, text='Pitch', bd=0, anchor='w', bg='white',
                                   justify=tk.LEFT)
        self.pitch_val = tk.Label(master=self.telemetry_window_values, text=str(
            self.telemetry_current_state.sensors['pitch']), bd=0, anchor='w', bg='white', justify=tk.LEFT)
        self.yaw_text = tk.Label(master=self.telemetry_window_names, text='Yaw', bd=0, anchor='w', bg='white',
                                 justify=tk.LEFT)
        self.yaw_val = tk.Label(master=self.telemetry_window_values, text=str(
            self.telemetry_current_state.sensors['yaw']), bd=0, anchor='w', bg='white', justify=tk.LEFT)
        self.auto_button_text = tk.Label(master=self.telemetry_window_names, text='Button_Auto', bd=0, anchor='w', bg='white',
                                         justify=tk.LEFT)
        self.auto_button_val = tk.Label(master=self.telemetry_window_values, text=str(
            self.telemetry_current_state.sensors['auto_button']), bd=0, anchor='w', bg='white', justify=tk.LEFT)
        self.kill_button_text = tk.Label(master=self.telemetry_window_names, text='Button_Kill', bd=0, anchor='w', bg='white',
                                         justify=tk.LEFT)
        self.kill_button_val = tk.Label(master=self.telemetry_window_values, text=str(
            self.telemetry_current_state.sensors['kill_button']), bd=0, anchor='w', bg='white', justify=tk.LEFT)

        # Controller Window
        self.controller_window = tk.Canvas(master=self.master, width=213, height=140, bg='white')
        self.thruster_window = tk.Canvas(master=self.master, width=213, height=130, bg='white')
        self.controller_text = tk.Canvas(master=self.controller_window, width=213, height=24, bg='green')
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
        # Graphing
        self.graph_text = tk.Canvas(master=self.controller_window, width=100, height=24, bg='green')
        self.graph_text_img = ImageTk.PhotoImage(PILImage.open('img/graph_text.png'))
        self.graph_text.create_image((2, 2), anchor=tk.NW, image=self.graph_text_img)
        self.graph_canvas = tk.Canvas(master=self.controller_window, width=427, height=244, bg='green')
        self.graph_canvas_img = ImageTk.PhotoImage(PILImage.open('img/sensors_base.png'))
        self.graph_canvas.create_image((2, 2), anchor=tk.NW, image=self.graph_canvas_img)
        """ Fix later
        self.graph_plt_figure = Figure((5, 5), dpi=100)
        self.graph_plt_subplots = self.graph_plt_figure.add_subplot(111)
        self.graph_plt_subplots.plot([1, 2, 3, 4], [1, 2, 3, 4])
        self.graph_plt_canvas = FigureCanvasTk(self.graph_plt_figure, self.controller_window)
        """

        self.graph_sensor_swap_window = tk.Frame(master=self.controller_window, width=220, height=24, bg='green')
        self.graph_current_sensor = tk.Canvas(master=self.graph_sensor_swap_window, width=180, height=24, bg='green')
        self.canvas_img = {
            'not_loaded': ImageTk.PhotoImage(PILImage.open('img/graph_img/not_loaded.png')),
            'accelerometer_x': ImageTk.PhotoImage(PILImage.open('img/graph_img/accelerometer_x.png')),
            'accelerometer_y': ImageTk.PhotoImage(PILImage.open('img/graph_img/accelerometer_y.png')),
            'accelerometer_z': ImageTk.PhotoImage(PILImage.open('img/graph_img/accelerometer_z.png')),
            'magnetometer_x': ImageTk.PhotoImage(PILImage.open('img/graph_img/magnetometer_x.png')),
            'magnetometer_y': ImageTk.PhotoImage(PILImage.open('img/graph_img/magnetometer_y.png')),
            'magnetometer_z': ImageTk.PhotoImage(PILImage.open('img/graph_img/magnetometer_z.png')),
            'pressure_transducer': ImageTk.PhotoImage(PILImage.open('img/graph_img/pressure_transducer.png')),
            'gyroscope_x': ImageTk.PhotoImage(PILImage.open('img/graph_img/gyro_x.png')),
            'gyroscope_y': ImageTk.PhotoImage(PILImage.open('img/graph_img/gyro_y.png')),
            'gyroscope_z': ImageTk.PhotoImage(PILImage.open('img/graph_img/gyro_z.png')),
            'voltmeter': ImageTk.PhotoImage(PILImage.open('img/graph_img/voltmeter.png')),
            'battery_current': ImageTk.PhotoImage(PILImage.open('img/graph_img/battery_ammeter.png')),
            'battery_1_voltage': ImageTk.PhotoImage(PILImage.open('img/graph_img/battery_1_voltage.png')),
            'battery_2_voltage': ImageTk.PhotoImage(PILImage.open('img/graph_img/battery_2_voltage.png')),
            'roll': ImageTk.PhotoImage(PILImage.open('img/graph_img/roll.png')),
            'pitch': ImageTk.PhotoImage(PILImage.open('img/graph_img/pitch.png')),
            'yaw': ImageTk.PhotoImage(PILImage.open('img/graph_img/yaw.png'))
        }
        self.canvas_img_by_index = {
            0: self.canvas_img['not_loaded'],
            1: self.canvas_img['accelerometer_x'],
            2: self.canvas_img['accelerometer_y'],
            3: self.canvas_img['accelerometer_z'],
            4: self.canvas_img['magnetometer_x'],
            5: self.canvas_img['magnetometer_y'],
            6: self.canvas_img['magnetometer_z'],
            7: self.canvas_img['pressure_transducer'],
            8: self.canvas_img['gyroscope_x'],
            9: self.canvas_img['gyroscope_y'],
            10: self.canvas_img['gyroscope_z'],
            11: self.canvas_img['voltmeter'],
            12: self.canvas_img['battery_current'],
            13: self.canvas_img['battery_1_voltage'],
            14: self.canvas_img['battery_2_voltage'],
            15: self.canvas_img['roll'],
            16: self.canvas_img['pitch'],
            17: self.canvas_img['yaw']
        }
        self.current_graph_img_index = 0
        self.graph_current_sensor_config = self.graph_current_sensor.create_image((2, 2),
                                                                                  anchor=tk.NW,
                                                                                  image=self.canvas_img_by_index[
                                                                                      self.current_graph_img_index])
        self.graph_sensor_swap_l_button = tk.Button(master=self.graph_sensor_swap_window,
                                                    text='<',
                                                    justify=RIGHT,
                                                    anchor='e',
                                                    command=partial(self.sensor_button_graph_switch,
                                                                    invert=True,
                                                                    max_val=17))
        self.graph_sensor_swap_r_button = tk.Button(master=self.graph_sensor_swap_window,
                                                    text='>',
                                                    justify=LEFT,
                                                    anchor='w',
                                                    command=partial(self.sensor_button_graph_switch,
                                                                    invert=False,
                                                                    max_val=17))
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

        # Text bars
        self.logging_window_text.grid(column=0, row=1, sticky=W, columnspan=3)
        self.video_window_text.grid(column=3, row=1, sticky=NW)
        self.info_window_host_text.grid(column=4, row=1, sticky=NW)
        self.sensors_text.grid(column=3, row=3, sticky=NW)

        # Logging Window
        self.logging_window.grid(column=0, row=2, sticky=W, columnspan=3)
        self.text.place(x=0, y=0)
        self.logger.log('[Info]: Logger Initialized.')

        # Video Stream Window
        self.video_window.grid(column=3, row=2)

        # Info Window (Communications/Statuses)
        self.info_window.grid(column=4, row=2, sticky=NW)

        # Text
        self.info_all_comms_text.grid(column=0, row=0, sticky=W, columnspan=3)

        # Config
        self.config_status_button.grid(column=0, row=1, sticky=W)
        self.config_status_text.grid(column=1, row=1, sticky=W)

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
        self.telemetry_window.grid(column=3, row=4)
        self.tel_window_old.grid(column=4, row=4)
        self.telemetry_canvas_1.grid(column=0, row=0, sticky=N)
        self.telemetry_canvas_2.grid(column=0, row=1, sticky=N)

        self.telemetry_window_names.grid(column=0, row=0)
        self.telemetry_window_values.grid(column=1, row=0)
        # self.telemetry_colpad.grid(column=0, row=0, sticky=W, columnspan=2)
        # self.telemetry_colpad_2.grid(column=0, row=0, sticky=W)
        self.accelerometer_text.grid(column=0, row=1, sticky=W, columnspan=2)
        self.accelerometer_val.grid(column=0, row=1, sticky=W)
        self.magnetometer_text.grid(column=0, row=2, sticky=W, columnspan=2)
        self.magnetometer_val.grid(column=0, row=2, sticky=W)
        self.pressure_trans_text.grid(column=0, row=3, sticky=W, columnspan=2)
        self.pressure_trans_val.grid(column=0, row=3, sticky=W)
        self.gyroscope_text.grid(column=0, row=4, sticky=W, columnspan=2)
        self.gyroscope_val.grid(column=0, row=4, sticky=W)
        self.voltmeter_text.grid(column=0, row=5, sticky=W, columnspan=2)
        self.voltmeter_val.grid(column=0, row=5, sticky=W)
        self.battery_current_text.grid(column=0, row=6, sticky=W, columnspan=2)
        self.battery_current_val.grid(column=0, row=6, sticky=W)
        self.roll_text.grid(column=0, row=7, sticky=W, columnspan=2)
        self.roll_val.grid(column=0, row=7, sticky=W)
        self.pitch_text.grid(column=0, row=8, sticky=W, columnspan=2)
        self.pitch_val.grid(column=0, row=8, sticky=W)
        self.yaw_text.grid(column=0, row=9, sticky=W, columnspan=2)
        self.yaw_val.grid(column=0, row=9, sticky=W)
        self.auto_button_text.grid(column=0, row=10, sticky=W, columnspan=2)
        self.auto_button_val.grid(column=0, row=10, sticky=W)
        self.kill_button_text.grid(column=0, row=11, sticky=W, columnspan=2)
        self.kill_button_val.grid(column=0, row=11, sticky=W)


        # Controller Window
        self.controller_window.grid(column=0, row=3, sticky=NW, rowspan=2)
        self.controller_text.grid(column=0, row=0, columnspan=3)
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

        # Graphing window
        self.graph_text.grid(column=4, row=0, sticky=W)
        self.graph_sensor_swap_window.grid(column=5, row=0, sticky=NW)
        self.graph_sensor_swap_l_button.grid(column=0, row=0, sticky=W)
        self.graph_current_sensor.grid(column=1, row=0, sticky=W)
        self.graph_sensor_swap_r_button.grid(column=2, row=0, sticky=W)
        self.graph_canvas.grid(column=4, row=1, rowspan=2, columnspan=2)
        # self.graph_plt_canvas.get_tk_widget().grid(column=4, row=1, rowspan=2, columnspan=2)

    @staticmethod
    def diag_box(message) -> None:
        """Creates a diag box with a string.
        This is kept as a test example.
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
    def val_set(old, new) -> None:
        """tkinter doesn't like calling old.set() within command= arguments, so it's done here!
        """
        old.set(new)

    def confirm_settings(self, top) -> None:
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

    def sensor_button_graph_switch(self, invert, max_val) -> None:
        """Switches what is displayed on the graph.
        """
        if invert:
            if self.current_graph_img_index == 0:
                self.current_graph_img_index = max_val
            else:
                self.current_graph_img_index -= 1
        else:
            if self.current_graph_img_index == max_val:
                self.current_graph_img_index = 0
            else:
                self.current_graph_img_index += 1
        self.graph_current_sensor.itemconfig(self.graph_current_sensor_config,
                                             image=self.canvas_img_by_index[self.current_graph_img_index])

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
            self.info_all_comms_text.configure(self.info_all_comms_text, text='COMMS @' + self.remote_hostname)
            self.logger.log('[Info]: Set IP to ' + prompt)
        else:
            self.remote_hostname = default_hostname
            self.info_all_comms_text.configure(self.info_all_comms_text, text='COMMS @' + self.remote_hostname)
            self.logger.log('[Warn]: Attempt to pass invalid ip address, defaulting to localhost.')

    def run_logger(self) -> None:
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
    def update_button(button, enabled) -> None:
        """Swaps button color if it doesn't match enabled.
        NOTE: Called for red/green buttons.
        """
        if (button.config('bg')[4] == 'red') and enabled:
            button.configure(button, bg='green')
        elif (button.config('bg')[4] == 'green') and not enabled:
            button.configure(button, bg='red')

    @staticmethod
    def update_button_enable(button, enabled) -> None:
        """Swaps button color if it doesn't match enabled.
        NOTE: Called for black/yellow buttons.
        """
        if (button.config('bg')[4] == 'black') and enabled:
            button.configure(button, bg='yellow')
        elif (button.config('bg')[4] == 'yellow') and not enabled:
            button.configure(button, bg='black')

    @staticmethod
    def update_button_int(button, status) -> None:
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
    def update_status_string(text, status) -> None:
        """Sets text to status.
        NOTE: Called for setting text boxes in Labels.
        """
        if text.config('text')[0] != status:
            text.configure(text, text=status)

    def update_frames(self) -> None:
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

    def send_controller_state(self) -> None:
        """Sends current controller state to Pilot process
        Updates frames
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
        """Updates the telemetry window.
        """
        if self.telemetry_socket_is_connected:
            pass

            self.accelerometer_val.configure(self.accelerometer_val,
                                             text=str(self.telemetry_current_state.sensors['accelerometer_x']))
            self.magnetometer_val.configure(self.magnetometer_val,
                                            text=str(self.telemetry_current_state.sensors['magnetometer_x']))
            self.pressure_trans_val.configure(self.pressure_trans_val,
                                             text=str(self.telemetry_current_state.sensors['pressure_transducer']))
            self.gyroscope_val.configure(self.gyroscope_val,
                                        text=str(self.telemetry_current_state.sensors['gyroscope_x']))
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
                    elif gui_cmd[2] == 'no_conn_socket':
                        self.video_socket_is_connected = False
                elif gui_cmd[1] == 'logging':
                    if gui_cmd[2] == 'conn_socket':
                        self.logging_socket_is_connected = True
                    elif gui_cmd[2] == 'no_conn_socket':
                        self.logging_socket_is_connected = False
                    else:
                        self.remote_logging_queue.append(gui_cmd[2])
                elif gui_cmd[1] == 'telemetry':
                    if isinstance(gui_cmd[2], str):
                        if gui_cmd[2] == 'conn_socket':
                            self.telemetry_socket_is_connected = True
                        elif gui_cmd[2] == 'no_conn_socket':
                            self.telemetry_socket_is_connected = False
                    elif isinstance(gui_cmd[2], bytes):
                        tel = sensor_tel.Telemetry()
                        tel.load_data_from_bytes(gui_cmd[2])
                        self.telemetry_current_state = tel
                elif gui_cmd[1] == 'pilot':
                    if gui_cmd[2] == 'conn_socket':
                        self.pilot_socket_is_connected = True
                    elif gui_cmd[2] == 'no_conn_socket':
                        self.pilot_socket_is_connected = False

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
        # Update all button statuses
        self.update_button(self.cmd_status_button, self.cmd_connected)
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


def gui_proc_main(gui_input, gui_output, gui_logger, video_stream_pipe_in, pilot_pipe_out) -> None:
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


def video_proc_udp(logger, video_pipe_in, video_pipe_out, video_stream_out) -> None:
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


def video_proc_tcp(logger, video_pipe_in, video_pipe_out, video_stream_out) -> None:
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


def logging_proc(logger, logging_pipe_in, logging_pipe_out) -> None:
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


def telemetry_proc(logger, telemetry_pipe_in, telemetry_pipe_out) -> None:
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


def pilot_proc(logger, pilot_pipe_in, pilot_pipe_out, pipe_in_from_gui) -> None:
    """Sends controller input to Control over TCP connection.
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


def router(logger,  # Gui logger
           from_gui_pipe_in, to_gui_pipe_out,  # Gui pipe
           from_video_pipe_in, to_video_pipe_out,  # Video pipe
           from_logger_pipe_in, to_logger_pipe_out,
           from_telemetry_pipe_in, to_telemetry_pipe_out,
           from_pilot_pipe_in, to_pilot_pipe_out
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

    # Gui
    gui_logger = LoggerWrapper()

    pipe_to_gui_from_router, gui_pipe_in_from_router = context.Pipe()
    pipe_to_router_from_gui, pipe_in_from_gui = context.Pipe()
    gui_proc = context.Process(target=gui_proc_main, args=(gui_pipe_in_from_router, pipe_to_router_from_gui, gui_logger, pipe_in_from_video_stream, pipe_to_pilot_from_gui))
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
    print(' ')

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
