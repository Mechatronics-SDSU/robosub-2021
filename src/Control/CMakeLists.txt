cmake_minimum_required(VERSION 3.16 FATAL_ERROR)

project(Control)

find_package(Eigen3 REQUIRED)
find_package(ignition-math6 REQUIRED)

find_package(SWIG REQUIRED)
include(${SWIG_USE_FILE})

find_package(PythonLibs)
include_directories(${PYTHON_INCLUDE_PATH})

set(CMAKE_SWIG_FLAGS "")

include_directories(${CMAKE_CURRENT_SOURCE_DIR})

add_library(PIDController6DOF PIDController6DOF.cc)
target_link_libraries(PIDController6DOF Eigen3::Eigen ignition-math6::ignition-math6)

add_library(PicoPIDController PicoPIDController.cc)
target_link_libraries(PicoPIDController Eigen3::Eigen PIDController6DOF)

SET_SOURCE_FILES_PROPERTIES(PIDController6DOF.i PROPERTIES CPLUSPLUS ON)
SET_SOURCE_FILES_PROPERTIES(PIDController6DOF.i PROPERTIES SWIG_FLAGS "-includeall")

SWIG_ADD_MODULE(PIDController6DOF_py python PIDController6DOF.i PIDController6DOF.cc)
#add_dependencies(PIDController6DOFpy PIDController6DOF)
SWIG_LINK_LIBRARIES(PIDController6DOF_py ${PYTHON_LIBRARIES} ignition-math6::ignition-math6)
