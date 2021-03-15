#include "PIDController6DOF.hh"


PIDController6DOF::PIDController6DOF(){
    
    pid_controllers.push_back(roll_pid);
    pid_controllers.push_back(pitch_pid);
    pid_controllers.push_back(yaw_pid);
    pid_controllers.push_back(x_pid);
    pid_controllers.push_back(y_pid);
    pid_controllers.push_back(z_pid);

}


void PIDController6DOF::set_roll_gains(double kp, double ki, double kd){
    
    PIDController6DOF::_set_gains(kp, ki, kd, 0);

}

void PIDController6DOF::set_pitch_gains(double kp, double ki, double kd){
    
    PIDController6DOF::_set_gains(kp, ki, kd, 1);

}

void PIDController6DOF::set_yaw_gains(double kp, double ki, double kd){
    
    PIDController6DOF::_set_gains(kp, ki, kd, 2);

}

void PIDController6DOF::set_x_gains(double kp, double ki, double kd){
    
    PIDController6DOF::_set_gains(kp, ki, kd, 3);

}

void PIDController6DOF::set_y_gains(double kp, double ki, double kd){
    
    PIDController6DOF::_set_gains(kp, ki, kd, 4);

}

void PIDController6DOF::set_z_gains(double kp, double ki, double kd){
    
    PIDController6DOF::_set_gains(kp, ki, kd, 5);

}

void PIDController6DOF::_set_gains(double kp, double ki, double kd, int _index){

    pid_controllers[_index].SetPGain(kp);
    pid_controllers[_index].SetIGain(ki);
    pid_controllers[_index].SetDGain(kd);

}

void PIDController6DOF::set_roll_I_limits(double I_min, double I_max){
    _set_I_limits(I_min, I_max, 0);
}


void PIDController6DOF::set_pitch_I_limits(double I_min, double I_max){
    _set_I_limits(I_min, I_max, 1);
}


void PIDController6DOF::set_yaw_I_limits(double I_min, double I_max){
    _set_I_limits(I_min, I_max, 2);
}


void PIDController6DOF::set_x_I_limits(double I_min, double I_max){
    _set_I_limits(I_min, I_max, 3);
}


void PIDController6DOF::set_y_I_limits(double I_min, double I_max){
    _set_I_limits(I_min, I_max, 4);
}


void PIDController6DOF::set_z_I_limits(double I_min, double I_max){

    _set_I_limits(I_min, I_max, 5);
}

void PIDController6DOF::_set_I_limits(double _I_min, double _I_max, int _index){

    pid_controllers[_index].SetIMin(_I_min);
    pid_controllers[_index].SetIMax(_I_max);

}

void PIDController6DOF::set_roll_cmd_limits(double cmd_min, double cmd_max){
    
    _set_cmd_limits(cmd_min, cmd_max, 0);
}


void PIDController6DOF::set_pitch_cmd_limits(double cmd_min, double cmd_max){
    
    _set_cmd_limits(cmd_min, cmd_max, 1);
}

void PIDController6DOF::set_yaw_cmd_limits(double cmd_min, double cmd_max){

    _set_cmd_limits(cmd_min, cmd_max, 2);
}

void PIDController6DOF::set_x_cmd_limits(double cmd_min, double cmd_max){
    _set_cmd_limits(cmd_min, cmd_max, 3);
}

void PIDController6DOF::set_y_cmd_limits(double cmd_min, double cmd_max){
    _set_cmd_limits(cmd_min, cmd_max, 4);

}

void PIDController6DOF::set_z_cmd_limits(double cmd_min, double cmd_max){
    _set_cmd_limits(cmd_min, cmd_max, 5);
}


void PIDController6DOF::_set_cmd_limits(double _cmd_min, double _cmd_max, int _index){
    
    pid_controllers[_index].SetCmdMin(_cmd_min);
    pid_controllers[_index].SetCmdMax(_cmd_max);
}

void PIDController6DOF::set_roll_cmd_offsets(double offset){
    
    _set_cmd_offsets(offset, 0);
}

void PIDController6DOF::set_pitch_cmd_offsets(double offset){
    _set_cmd_offsets(offset, 1);
}

void PIDController6DOF::set_yaw_cmd_offsets(double offset){
    _set_cmd_offsets(offset, 2);
}

void PIDController6DOF::set_x_cmd_offsets(double offset){
    
    _set_cmd_offsets(offset, 3);
}

void PIDController6DOF::set_y_cmd_offsets(double offset){


    _set_cmd_offsets(offset, 4);
}
    
void PIDController6DOF::set_z_cmd_offsets(double offset){


    _set_cmd_offsets(offset, 5);
}

void PIDController6DOF::_set_cmd_offsets(double _offset, int _index){
    
    pid_controllers[_index].SetCmdOffset(_offset);

}


//Angles must be in radians
double PIDController6DOF::angle_wrap_error(double des_angle, double curr_angle){
   
    double _error;
    ignition::math::Angle angle_helper;
    _error = des_angle - curr_angle;
    
    //perform angle wrapping for the angular error. Makes sure error is monotonic
    if(_error > angle_helper.Pi()) _error = _error - (2.0 * angle_helper.Pi());
    else if (_error < -1.0 * angle_helper.Pi()) _error = _error + (2.0 * angle_helper.Pi());
    
    return _error;
}

void PIDController6DOF::print_gains(){
    
    std::vector<std::string> controller_names = {"Roll", "Pitch", "Yaw", "X", "Y", "Z"};

    for(int i = 0; i < controller_names.size(); i++){
        
        std::cout << controller_names[i] << " Gains:" << '\n';
        std::cout << "\tkp = " << pid_controllers[i].PGain() << '\n';
        std::cout << "\tki = " << pid_controllers[i].IGain() << '\n';
        std::cout << "\tkd = " << pid_controllers[i].DGain() << '\n';
    }

}

void PIDController6DOF::print_limits(){

     std::vector<std::string> controller_names = {"Roll", "Pitch", "Yaw", "X", "Y", "Z"};

    for(int i = 0; i < controller_names.size(); i++){
        
        std::cout << controller_names[i] << " Limits:" << '\n';
        std::cout << "\tI Min = " << pid_controllers[i].IMin() << '\n';
        std::cout << "\tI Max = " << pid_controllers[i].IMax() << '\n';
        std::cout << "\tCMD Min = " << pid_controllers[i].CmdMin() << '\n';
        std::cout << "\tCMD Max = " << pid_controllers[i].CmdMax() << '\n';
    }

   
}

std::vector<double> PIDController6DOF::update(std::vector<double> &set_pt, std::vector<double> &process_pt, const std::chrono::duration< double > &dt){
   
    //  cmds are the output of the PID controller, which is typically written to the actuators as input.
    std::vector<double> cmds;
    double error;
    for(int i = 0; i < pid_controllers.size(); i++){
        
        //assumes roll, pitch, and yaw use [-pi, pi] as angular input range.
        if(i < 3)  error = angle_wrap_error(set_pt[i], process_pt[i]);
        else       error = set_pt[i] - process_pt[i];
        
        cmds.push_back(pid_controllers[i].Update(1*error, dt));
    }

    return(cmds);

}

PIDController6DOF::~PIDController6DOF(){}

