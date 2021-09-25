#!/bin/sh
export PYTHONPATH=$PYTHONPATH:"$(pwd)/src/utils"
export PYTHONPATH=$PYTHONPATH:"$(pwd)/src/Control"
export PYTHONPATH=$PYTHONPATH:"$(pwd)/src/Intelligence"
export PYTHONPATH=$PYTHONPATH:"$(pwd)/src/Inference"
export PYTHONPATH=$PYTHONPATH:"$(pwd)/gui"
echo "Setup Complete"