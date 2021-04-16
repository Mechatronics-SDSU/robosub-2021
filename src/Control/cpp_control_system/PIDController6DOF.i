/*  File: PIDController6DOF.i */

%include "std_vector.i"

%module PIDController6DOF_py
%{

    #include "PIDController6DOF.hh"
%}

namespace std {
    %template(IntVector) vector<int>;
    %template(DoubleVector) vector<double>;
}
class PIDController6DOF{
    
    public:
        //Default Constructor
        PIDController6DOF();
        
        ~PIDController6DOF();
        
        //Set the gains for each DOF;
        void set_roll_gains(double kp, double ki, double kd);
        void set_pitch_gains(double kp, double ki, double kd);
        void set_yaw_gains(double kp, double ki, double kd);
        void set_x_gains(double kp, double ki, double kd);
        void set_y_gains(double kp, double ki, double kd);
        void set_z_gains(double kp, double ki, double kd);
        void _set_gains(double _kp, double _ki, double _kd, int _index);
        
        void set_roll_I_limits(double I_min, double I_max);
        void set_pitch_I_limits(double I_min, double I_max);
        void set_yaw_I_limits(double I_min, double I_max);
        void set_x_I_limits(double I_min, double I_max);
        void set_y_I_limits(double I_min, double I_max);
        void set_z_I_limits(double I_min, double I_max);
        void _set_I_limits(double _I_min, double I_max, int _index);
        
        void set_roll_cmd_limits(double cmd_min, double cmd_max);
        void set_pitch_cmd_limits(double cmd_min, double cmd_max);
        void set_yaw_cmd_limits(double cmd_min, double cmd_max);
        void set_x_cmd_limits(double cmd_min, double cmd_max);
        void set_y_cmd_limits(double cmd_min, double cmd_max);
        void set_z_cmd_limits(double cmd_min, double cmd_max);
        void _set_cmd_limits(double _cmd_min, double _cmd_max, int _index);

        void set_roll_cmd_offsets(double offset);
        void set_pitch_cmd_offsets(double offset);
        void set_yaw_cmd_offsets(double offset);
        void set_x_cmd_offsets(double offset);
        void set_y_cmd_offsets(double offset);
        void set_z_cmd_offsets(double offset);
        void _set_cmd_offsets(double _offset, int _index);


        //  Determine correct error value for angle values between -pi and pi.
        double angle_wrap_error(double des_angle, double curr_angle);
        
        //  Convient function to print out all the gains.
        void print_gains();
        
        //  Print out all the limits for each controller.
        void print_limits();
        
        //  run an update step for the PID controller.
    

        std::vector<double> update(std::vector<double> &set_pt, std::vector<double> &process_pt, double dt);
    
    private:
        
        //  PID for each DOF
        ignition::math::PID roll_pid;
        ignition::math::PID pitch_pid;
        ignition::math::PID yaw_pid;
        ignition::math::PID x_pid;
        ignition::math::PID y_pid;
        ignition::math::PID z_pid;
        

    protected:

        //Store all the pid controllers in a single vector for convenience.
        std::vector<ignition::math::PID> pid_controllers;
};
