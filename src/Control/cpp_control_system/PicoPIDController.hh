//Specialized PID controller for the Pico Mini AUV. Maps the 6DOF freedom controller to the 6 thrusters.

#pragma once

#include <Eigen/Dense>
#include <chrono>
#include "PIDController6DOF.hh"


typedef Eigen::Matrix<double, 6, 6> Matrix6d;
typedef Eigen::Matrix<double, 6, 1> Vector6d;

//  PID controller for controlling Pico the mini auv. Inherits from the more generalized 6DOF PID controller.
class PicoPIDController : public PIDController6DOF{
    
    public:
        //Default constructor 
        PicoPIDController();
        ~PicoPIDController();
       
        //  Compute set point error for each DOF (roll, pitch, yaw, x, y, z). Returns 6 Vector for the thrusts to apply to each
        //  thruster.
        Vector6d update(std::vector<double> &set_pt, std::vector<double> &process_pt, std::chrono::duration<double> &_dt);
        
    private:
       
        // Matrix to map the pid controller commands to each thruster.
        Matrix6d pid_thruster_mapper;

};
