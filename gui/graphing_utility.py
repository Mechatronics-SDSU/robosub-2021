"""Graphing utility code from GUI moved here for future implementation.
"""


def _update_graph(self, data_x: list, data_y: list, graph_index: int) -> None:
    """Updates the graphs with whatever is in the deques
    """
    pass
    '''
    self.graph_plt_plot_data[graph_index].set_xdata(data_x)
    self.graph_plt_plot_data[graph_index].set_ydata(data_y)
    self.graph_plt_canvases[graph_index].draw()
    '''


def _sensor_button_graph_switch(self, invert, max_val) -> None:
    """Switches what is displayed on the graph.
    """
    pass
    '''
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
    self.graph_plt_canvas_widget.grid_forget()
    self.graph_plt_canvas_widget = self.graph_plt_canvas_widgets[self.current_graph_img_index]
    self.graph_plt_canvas_widget.grid(column=0, row=0)
    '''


def _setup() -> None:
    """Setting up deques and matplotlib graphs
    """
    pass
    '''
    self.telemetry_graph_states = []
    # self.telemetry_time_series_default = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60]
    self.telemetry_time_series_default = list(range(61))
    '''
    # Graphing
    '''
    self.graph_text = tk.Canvas(master=self.controller_window, width=100, height=24, bg='green')
    self.graph_text_img = ImageTk.PhotoImage(PILImage.open('img/graph_text.png'))
    self.graph_text.create_image((2, 2), anchor=tk.NW, image=self.graph_text_img)
    self.graph_canvas = tk.Canvas(master=self.controller_window, width=427, height=244, bg='green')
    self.graph_canvas_img = ImageTk.PhotoImage(PILImage.open('img/sensors_base.png'))
    self.graph_canvas.create_image((2, 2), anchor=tk.NW, image=self.graph_canvas_img)
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
    # Graph queues for x(time) and y(data)
    self.graph_data_deques = []
    self.graph_time_deques = []
    # Input stacks for x(time) and y(data)
    self.input_data_deques = []
    self.input_time_deques = []
    # Append lists with deque objects
    for i in self.canvas_img_by_index:
        self.graph_data_deques.append(deque())
        self.graph_time_deques.append(deque())
        self.input_data_deques.append(deque())
        self.input_time_deques.append(deque())
    counter = 1
    self.start_time = datetime.utcnow().timestamp()
    for i in self.input_data_deques:
        i.append(0.0)
    self.sensor_values_exist = False
    self.iterated = False
    # Load in start data
    self.graph_deque_size = 61
    for i in range(len(self.canvas_img)):
        self.telemetry_graph_states.append([])
        for j in range(self.graph_deque_size):
            self.telemetry_graph_states[i].append(0)
        counter += 1
    self.current_graph_img_index = 0
    # matplotlib for graphing
    self.graph_plt_figures = []
    self.graph_plt_subplots = []
    self.graph_plt_plot_data = []
    self.graph_plt_canvases = []
    self.graph_plt_canvas_widgets = []
    for i in self.canvas_img_by_index:
        self.graph_plt_figures.append(Figure((5.3375, 3.05), dpi=80, frameon=True))
        self.graph_plt_subplots.append(self.graph_plt_figures[i].add_subplot(111))
        _y, = self.graph_plt_subplots[i].plot(self.telemetry_time_series_default, self.telemetry_graph_states[i])
        self.graph_plt_plot_data.append(_y)
        self.graph_plt_canvases.append(FigureCanvasTkAgg(self.graph_plt_figures[i], master=self.graph_canvas))
        self.graph_plt_canvases[i].draw()
        self.graph_plt_canvas_widgets.append(self.graph_plt_canvases[i].get_tk_widget())

    self.graph_plt_canvas_widget = self.graph_plt_canvas_widgets[1]  # Set image to canvas widget for no data
    '''
    # Data for testing update function
    '''
    self.graph_time_deques[1].append(1)
    self.graph_time_deques[1].append(2)
    self.graph_data_deques[1].append(1)
    self.graph_data_deques[1].append(2)
    self.graph_plt_plot_data[1].set_xdata(list(self.graph_time_deques[1]))
    self.graph_plt_plot_data[1].set_ydata(list(self.graph_data_deques[1]))
    self.graph_plt_canvases[1].draw()
    '''
    '''
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
                                                                '''

    # Graphing window (not __init__)
    '''
    self.graph_text.grid(column=4, row=0, sticky=W)
    self.graph_sensor_swap_window.grid(column=5, row=0, sticky=NW)
    self.graph_sensor_swap_l_button.grid(column=0, row=0, sticky=W)
    self.graph_current_sensor.grid(column=1, row=0, sticky=W)
    self.graph_sensor_swap_r_button.grid(column=2, row=0, sticky=W)
    self.graph_canvas.grid(column=4, row=1, rowspan=2, columnspan=2)
    self.graph_plt_canvas_widget.grid(column=0, row=0)
    '''


def _graph_update() -> None:
    """Graph Update code with deque objects
    """
    pass
    '''
                if not self.iterated:  # Append initial start time to time deques
                    counter = 0
                    for i in self.input_time_deques:
                        i.append(self.telemetry_current_state.time_series[
                                     self.telemetry_current_state.index_reference[counter]])
                    self.start_time = peek(self.input_time_deques[0])
                counter = 0
                for i in self.input_time_deques:  # Append all new data to input deques
                    # if self.sensor_values_exist:
                    # If we have different timestamps, we got a new entry, so add it
                    top = peek(i)
                    if (top is not None) and (not self.sensor_values_exist):  # No data yet
                        if top < self.telemetry_current_state.time_series[self.telemetry_current_state.index_reference[counter]]:
                            i.append(self.telemetry_current_state.time_series[self.telemetry_current_state.index_reference[counter]])
                            self.input_data_deques[counter].append(
                                self.telemetry_current_state.sensors[self.telemetry_current_state.index_reference[counter]])
                    elif top is None and self.sensor_values_exist:  # No data, but it's incoming
                        i.append(
                            self.telemetry_current_state.time_series[self.telemetry_current_state.index_reference[counter]])
                        self.input_data_deques[counter].append(
                            self.telemetry_current_state.sensors[self.telemetry_current_state.index_reference[counter]])
                    elif top is not None and self.sensor_values_exist:  # Have data stored and incoming
                        if top < self.telemetry_current_state.time_series[self.telemetry_current_state.index_reference[counter]]:
                            i.append(self.telemetry_current_state.time_series[self.telemetry_current_state.index_reference[counter]])
                            self.input_data_deques[counter].append(
                                self.telemetry_current_state.sensors[self.telemetry_current_state.index_reference[counter]])
                    counter += 1
                counter = 0
                for i in self.input_time_deques:  # Check time series for >= 1 second elapsed, append data if true
                    if self.telemetry_current_state.time_series[self.telemetry_current_state.index_reference[counter]] != 0.0:
                        if self.iterated and self.sensor_values_exist:
                            top = peek(self.graph_time_deques[counter])
                            top2 = peek(self.input_time_deques[counter])
                            #print(f'top: {top} top2: {top2}')
                            if (top is not None) and (top2 is not None):
                                delta = math.floor(self.telemetry_current_state.time_series[
                                                       self.telemetry_current_state.index_reference[counter]] - top)
                                if delta >= 1:
                                    #print('t_delta >= 1')
                                    # Move data from stacks to queues, clear stack, send queue to graph
                                    if len(self.graph_time_deques[counter]) > self.graph_deque_size:
                                        self.graph_time_deques[counter].popleft()
                                        self.graph_data_deques[counter].popleft()
                                    _t = round(i.pop() - self.start_time)
                                    _d = self.input_data_deques[counter].pop()
                                    i.clear()
                                    self.input_data_deques[counter].clear()
                                    self.graph_time_deques[counter].append(_t)
                                    self.graph_data_deques[counter].append(_d)
                                    #print(f'{self.graph_time_deques[counter]}')
                                    #print(f'{self.graph_data_deques[counter]}')
                                    self.update_graph(data_x=list(self.graph_time_deques[counter]),
                                        data_y=list(self.graph_data_deques[counter]),
                                        graph_index=counter)
                        else:  # First entry, push to deques
                            _t = round(i.pop() - self.start_time)
                            _d = self.input_data_deques[counter].pop()
                            i.clear()
                            self.input_data_deques[counter].clear()
                            self.graph_time_deques[counter].append(_t)
                            self.graph_data_deques[counter].append(_d)
                            self.update_graph(data_x=list(self.graph_time_deques[counter]),
                                              data_y=list(self.graph_data_deques[counter]),
                                              graph_index=counter)
                            self.sensor_values_exist = True
                    counter += 1
                if self.sensor_values_exist and (not self.iterated):
                    self.iterated = True
                '''


if __name__ == '__main__':
    print(f'This is currently under construction, don\'t run as main!')
