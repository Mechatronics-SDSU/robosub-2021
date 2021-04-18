#!/usr/bin/env python3
from pid_controller import PID_Controller
from state_estimator import State_Estimator
from maestro_driver import Maestro_Driver
import numpy as np
import time
import matplotlib.pyplot as plt

#Create a "positional" pid control system for the PICO mini auv. There will be 5 controller for
#(roll, pitch, yaw, x, z). These are the DOFs controllable by the actuator.

class Pico_PID_Controller:
    
    def __init__(self, pid_params=None):
        '''
        '''
        
        #Initialize pid controllers
        self.z_pid = PID_Controller(0.0, 0.0, 0.0)
        self.roll_pid = PID_Controller(0.0, 0.0, 0.0, angle_wrap=True)
        self.pitch_pid = PID_Controller(0.0, 0.0, 0.0, angle_wrap=True)
        self.yaw_pid = PID_Controller(0.0, 0.0, 0.0, angle_wrap=True)
        self.x_pid = PID_Controller(0.0, 0.0, 0.0)
        
        self._controllers = {"roll" : self.roll_pid, 
                             "pitch" : self.pitch_pid,
                             "yaw" : self.yaw_pid,
                             "x" : self.x_pid,
                             "z" : self.z_pid}

        #load pid parameter values from dictionary
        if(pid_params != None):
            
            for ctrl_type in self._controllers.keys():
                self._controllers[ctrl_type].k_p = pid_params[ctrl_type]["kp"]
                self._controllers[ctrl_type].k_i = pid_params[ctrl_type]["ki"]
                self._controllers[ctrl_type].k_d = pid_params[ctrl_type]["kd"]
                self._controllers[ctrl_type].cmd_offset = pid_params[ctrl_type]["cmd_offset"]
                self._controllers[ctrl_type].cmd_max = pid_params[ctrl_type]["cmd_max"]
                self._controllers[ctrl_type].cmd_min = pid_params[ctrl_type]["cmd_min"]
                self._controllers[ctrl_type].i_max = pid_params[ctrl_type]["i_max"]
                self._controllers[ctrl_type].i_min = pid_params[ctrl_type]["i_min"]
                
        print(type(self.z_pid.cmd_min))
        #matrix mapping the 5 pid controller outputs to the 6 thrusters
        # -----roll---pitch---yaw---x---z
        #| T1
        #| T2
        #| T3
        #| T4
        #| T5
        #| T6
        
        self.pid_thrust_mapper = np.array([[ 1,  1,  0,  0, 1],
                                           [ 0,  0,  -1,  1,  0],
                                           [ 1, -1,  0,  0, 1],
                                           [-1, -1,  0,  0, 1],
                                           [ 0,  0,   1,  1,  0],
                                           [-1,  1,  0,  0, 1]])
        
        
    
    def update(self, set_point=np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0]), 
                     process_point=np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
                     dt=0.010):
        '''
        Perform PID controller update step and return the thrust to each of the 6 thrusters.
        
        :param set_point - The desired state of the vehicle [roll, pitch, yaw, x, z] (np.array)
        :param process_point - The current state of the vehicle [roll, pitch, yaw, x, z] (np.array)
        :param dt - Update interval in seconds (float)
        
        :return thrusts - A list of length 6 of the thrusts to apply to each motor: Range [-100, 100] (np.array)
        '''
        
        roll_cmd, roll_error = self.roll_pid.update(set_point[0], process_point[0], dt)
        pitch_cmd, pitch_error = self.pitch_pid.update(set_point[1], process_point[1], dt)
        yaw_cmd, yaw_error = self.yaw_pid.update(set_point[2], process_point[2], dt)
        z_cmd, z_error = self.z_pid.update(set_point[5], process_point[5], dt)
        
        errors = np.array([roll_error, pitch_error, yaw_error, 0.0, z_error])
        
        cmds = np.array([
            roll_cmd,
            pitch_cmd,
            yaw_cmd,
            0.0,
            z_cmd
        ])

        #map the individual controller outputs to each thruster.
        thrusts = np.matmul(self.pid_thrust_mapper, cmds)
        return(thrusts, errors, z_cmd)

'''
The code below shows an example of using the Pico_PID_Controller(). The controller
receives a desired_states (i.e. set_point), and uses the control system to make the vehicle
achieve the desired_state. A possible implementation to send the desired_states to the control
system is via IPC (like sockets.)
'''
if __name__ == "__main__":

    desired_depth = 1.0 #1.0m depth
    desired_roll = 0.0 #rad
    desired_pitch = 0.0 #rad
    desired_yaw = 3.14 #rad

    #desired state for the control system to reach
    desired_state = np.zeros(12)
    desired_state[0] = desired_roll
    desired_state[1] = desired_pitch
    desired_state[2] = desired_yaw
    desired_state[5] = desired_depth
    
    #update rate of control system
    f = 100.0 #Hz
    dt = 1/f

    max_run_time = 20.0 #Time to run control system before exiting

    state_estimator = State_Estimator()

    maestro_driver = Maestro_Driver('/dev/picoMaestroM')
    
    #load the pid_controller  parameters from a formatted json file
    import json
    with open("pid_params_1.json") as pid_param_file:
        pid_params = json.load(pid_param_file)

    controller = Pico_PID_Controller(pid_params)
    
    ''' 
    #Tune the PID controllers
    controller.z_pid.set_gains(7.5, 0.0, 6.2)
    controller.z_pid.cmd_offset = -14.0
    controller.z_pid.cmd_min = -16.0
    controller.z_pid.cmd_max = -12.0

    controller.roll_pid.set_gains(1.0, 0.0, 0.2)
    controller.roll_pid.cmd_max
    controller.roll_pid.cmd_min

    controller.pitch_pid.set_gains(1.0, 0.0, 0.1)
    '''

    #Begin state estimation thread
    state_estimator.start()
    
    roll_data = []
    pitch_data = []
    yaw_data = []
    z_data = []
    z_cmds = []
    
    curr_time = 0.0
    start_time = time.time()
    while(curr_time < max_run_time):
            
        #Get the state of the vehicle
        curr_state = state_estimator.state
        
        #Save state data for plotting
        if(max_run_time > 0):
            roll_data.append(curr_state[0])
            pitch_data.append(curr_state[1])
            yaw_data.append(curr_state[2])
            z_data.append(curr_state[5])

        thrusts, errors, z_cmd = controller.update(desired_state, curr_state, dt)
        z_cmds.append(z_cmd)

        maestro_driver.set_thrusts(thrusts)
        
        time.sleep(dt)
        curr_time = (time.time() - start_time)
    
    maestro_driver.set_thrusts([0, 0, 0, 0, 0, 0])

    t = np.arange(len(z_data)) * dt
    fig, ((roll_plot, pitch_plot), (yaw_plot, z_plot)) = plt.subplots(2, 2)

    roll_plot.plot(t, roll_data)
    roll_plot.hlines(desired_state[0], 0, max_run_time)
    roll_plot.set_xlabel("time (s)")
    roll_plot.set_ylabel("roll (rad)")

    pitch_plot.plot(t, pitch_data)
    pitch_plot.hlines(desired_state[1], 0, max_run_time)
    pitch_plot.set_xlabel("time (s)")
    pitch_plot.set_ylabel("pitch (rad)")

    yaw_plot.plot(t, yaw_data)
    yaw_plot.hlines(desired_state[2], 0, max_run_time)
    yaw_plot.set_xlabel("time (s)")
    yaw_plot.set_ylabel("yaw (rad)")

    z_plot.plot(t, z_data)
    z_plot.hlines(desired_state[5], 0, max_run_time)
    z_plot.set_xlabel("time (s)")
    z_plot.set_ylabel("z (m)")

    plt.figure()
    plt.plot(z_cmds)
    
    plt.show()
