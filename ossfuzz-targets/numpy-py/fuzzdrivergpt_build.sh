#!/bin/bash
# Install required Python packages
pip3 install atheris
pip3 install numpy

# Create seeds directory
mkdir -p $OUT/seeds
echo "initial" > $OUT/seeds/seed1

# Set up environment
export PYTHONPATH=/usr/local/lib/python3.8/site-packages
export ATHERIS_OPTIONS="-max_len=4096"
