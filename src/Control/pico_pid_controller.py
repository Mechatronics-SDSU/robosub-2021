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
    
    def __init__(self):
        '''
        '''
        
        #Initialize pid controllers
        self.z_pid = PID_Controller(0.0, 0.0, 0.0)
        self.roll_pid = PID_Controller(0.0, 0.0, 0.0, angle_wrap=True)
        self.pitch_pid = PID_Controller(0.0, 0.0, 0.0, angle_wrap=True)
        
        #matrix mapping the 5 pid controller outputs to the 6 thrusters
        # -----roll---pitch---yaw---x---z
        #| T1
        #| T2
        #| T3
        #| T4
        #| T5
        #| T6
        
        self.pid_thrust_mapper = np.array([[ 1,  1,  0,  0, 1],
                                           [ 0,  0,  1,  1,  0],
                                           [ 1, -1,  0,  0, 1],
                                           [-1, -1,  0,  0, 1],
                                           [ 0,  0, -1,  1,  0],
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
        z_cmd, z_error = self.z_pid.update(set_point[5], process_point[5], dt)
        
        errors = np.array([roll_error, pitch_error, 0.0, 0.0, z_error])
        
        cmds = np.array([
            roll_cmd,
            pitch_cmd,
            0.0,
            0.0,
            z_cmd
        ])

        #map the individual controller outputs to each thruster.
        thrusts = np.matmul(self.pid_thrust_mapper, cmds)
        return(thrusts, errors)


if __name__ == "__main__":

    desired_depth = 1.0 #1.0m depth
    desired_roll = 0.0 #rad
    desired_pitch = 0.0 #rad
    desired_yaw = 0.0 #rad

    #desired state for the control system to reach
    desired_state = np.zeros(12)
    desired_state[0] = desired_roll
    desired_state[1] = desired_pitch
    desired_state[2] = desired_yaw
    desired_state[5] = desired_depth
    
    #update rate of control system
    f = 100.0 #Hz
    dt = 1/f

    state_estimator = State_Estimator()

    maestro_driver = Maestro_Driver('/dev/picoMaestroM')

    controller = Pico_PID_Controller()
    
    controller.z_pid.set_gains(3.0, 0.0, 5.0)
    controller.z_pid.cmd_offset = -15.0
    controller.z_pid.cmd_min = -18.0
    controller.z_pid.cmd_max = -8.0

    controller.roll_pid.set_gains(1.0, 0.0, 0.1)
    controller.roll_pid.cmd_max
    controller.roll_pid.cmd_min

    controller.pitch_pid.set_gains(1.0, 0.0, 0.1)

    state_estimator.start()
    

    while(True):
            
        #Get the state of the vehicle
        curr_state = state_estimator.state

        thrusts, errors = controller.update(desired_state, curr_state, dt)

        maestro_driver.set_thrusts(thrusts)
        
        time.sleep(dt)


