#/usr/bin/env python3
import numpy as np

class PID_Controller():
    '''
    PID controller typically used in control feed back systems.
    '''
    def __init__(self, k_p, k_i, k_d, i_min=1.0, i_max=-1.0, cmd_min=1.0, cmd_max=-1.0, cmd_offset=0.0, angle_wrap=False):
        '''
        Initialize the the PID controller parameters.
        Parameters:
            k_p: Proportional gain
            k_i: Integral gain
            k_d: Derivative gain
            i_min: minimum value the integral can accumulate
            i_max: maximum value the integral can accumulate
                Setting i_max < i_min will mean that no limits are set for integral term
            cmd_min: minimum output command
            cmd_max: maximum output command
                Setting cmd_max < cmd_min will mean no limits are set for the output cmd on update.
            cmd_offset: Offset to add to the command output on each update step.
            angle_wrap: if true, it assumes the input set point and process point are angles in range
            
                        [-pi, pi]. Thus it will clamp the error in range [-pi, pi]
        Returns:
            N/A
        '''
        self.k_p = k_p
        self.k_i = k_i
        self.k_d = k_d
        self.i_min = i_min
        self.i_max = i_max
        self.cmd_min = cmd_min
        self.cmd_max = cmd_max
        self.cmd_offset = cmd_offset
        self.angle_wrap = angle_wrap

        self.integral = 0.0
        self.previous_error = 0.0

    def set_gains(self, k_p, k_i, k_d):
        '''
        Reset the gain parameters.
        Parameters:
            k_p: Proportional gain
            k_i: Integral gain
            k_d: Derivative gain
        '''
        self.k_p = k_p
        self.k_i = k_i
        self.k_d = k_d


    def update(self, set_point, process_point, dt):
        '''
        Perfrom a control step to correct for error in control system.
        
        Parameters:
            set_point: The current state of the system
            process_point: The desired state of the system
            dt: The interval between update steps.
        Returns:
            cmd: An PID output control value to correct for error in system
        '''
        
        #compute the error
        error = process_point - set_point
        
        #if error is for angular inputs, perform angle wrapping.
        if(self.angle_wrap):
            if(error > np.pi):
                error = error - 2*np.pi
            elif(error < -1 * np.pi):
                error = error + 2*np.pi
            
        p = (self.k_p * error) #proportional term

        self.integral = self.integral + (error * dt)
        
        if(self.i_min < self.i_max):
            if(self.integral < self.i_min):
                self.integral = self.i_min
            elif(self.integral > self.i_max):
                self.integral = self.i_max

        i = self.k_i * self.integral

        d = self.k_d * (error - self.previous_error) / dt
        self.previous_error = error

        cmd = p + i + d + self.cmd_offset
                  
        if(self.cmd_min < self.cmd_max):
            if(cmd < self.cmd_min):
                cmd = self.cmd_min
            elif(cmd > self.cmd_max):
                cmd = self.cmd_max

        return cmd, error
