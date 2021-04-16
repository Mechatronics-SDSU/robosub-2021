#!/usr/bin/env python3
import threading
from motherboard_driver import Motherboard_Driver
import numpy as np
import time

class State_Estimator(threading.Thread):
    
    def __init__(self, dt=0.010):
        '''
        '''
        threading.Thread.__init__(self)
        
        self.run_thread = True
        
        self.motherboard = Motherboard_Driver('/dev/picoM', 115200)
        
        #[roll, pitch, yaw, x, y, z, droll, dpitch, dyaw, dx, dy, dz]
        self.state = np.zeros(12)
        self.prev_state = np.zeros(12)
        self.dt = dt #update rate of receiving requests
        
        self.daemon = True
        
    def _angle_wrapped_error(self, angle_1, angle_2):
        
        error = angle_1 - angle_2
        
        if(error > np.pi):
            error = error - 2*np.pi
        elif(error < -1 * np.pi):
            error = error + 2*np.pi
        
        return(error)
        
    def run(self):
        self.cnt = 0
        
        while(self.run_thread):
            
            try:
                
                #Receive all the sensor data
                sensor_data = self.motherboard.get_all_sensor_data()
                if(sensor_data != None):
                    [roll, pitch, yaw, z] = sensor_data
                    x = 0.0
                    self.state[0] = roll
                    self.state[1] = pitch
                    self.state[2] = yaw
                    self.state[3] = x
                    self.state[4] = 0.0 #needs to be solved by state estimator
                    self.state[5] = z
                    
                    self.state[6] = self._angle_wrapped_error(roll, self.prev_state[0]) / self.dt
                    self.state[7] = self._angle_wrapped_error(pitch, self.prev_state[1]) / self.dt
                    self.state[8] = self._angle_wrapped_error(yaw, self.prev_state[2]) / self.dt
                    self.state[9] = (x - self.prev_state[3]) / self.dt
                    self.state[10] = 0.0
                    self.state[11] = (z - self.prev_state[5]) / self.dt
                        
                    
                    self.prev_state = np.copy(self.state)
                #TODO: Perform EKF
                self.cnt = self.cnt + 1
                
                time.sleep(self.dt)

            except Exception as e:
                print("[ERROR]: State Estimator ran into an error: ", e)
