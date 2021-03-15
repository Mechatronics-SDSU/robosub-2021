cmake_minimum_required(VERSION 3.16 FATAL_ERROR)

project(Control)

find_package(gazebo REQUIRED)
find_package(Eigen3 REQUIRED)
find_package(ignition-math6 REQUIRED)

include_directories(${GAZEBO_INCLUDE_DIRS})
link_directories(${GAZEBO_LIBRARY_DIRS})
list(APPEND CMAKE_CXX_FLAGS "${GAZEBO_CXX_FLAGS}")

add_library(PIDController6DOF PIDController6DOF.cc)
target_link_libraries(PIDController6DOF Eigen3::Eigen ignition-math6::ignition-math6)

add_library(PicoPIDController PicoPIDController.cc)
target_link_libraries(PicoPIDController Eigen3::Eigen PIDController6DOF)
