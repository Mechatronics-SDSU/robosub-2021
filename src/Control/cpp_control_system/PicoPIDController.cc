#include "PicoPIDController.hh"

PicoPIDController::PicoPIDController(){
    
    // Construct base class
    PIDController6DOF();
    
    pid_thruster_mapper << 1,  1,  0,  0,  0,  -1,
                           0,  0,  1,  1,  0,  0,
                           1, -1,  0,  0,  0,  -1,
                          -1, -1,  0,  0,  0,  -1,
                           0,  0, -1,  1,  0,  0,
                          -1,  1,  0,  0,  0,  -1;  

}


Vector6d PicoPIDController::update(std::vector<double> &set_pt, std::vector<double> &process_pt, std::chrono::duration<double> &dt){
    
    Vector6d cmds;
    double error;

    // Iteratively get the update command from each pid controll.
    for(int i = 0; i < pid_controllers.size(); i++){
        
        if(i < 3)  error = angle_wrap_error(set_pt[i], process_pt[i]);
        else       error = set_pt[i] - process_pt[i];
        
        cmds[i] = pid_controllers[i].Update(-1*error, dt);
    }
    
    Vector6d thrusts = (Vector6d) (pid_thruster_mapper * cmds);
    return(thrusts);

}


PicoPIDController::~PicoPIDController(){}


