#!/bin/bash
# Install required Node.js packages
npm install lodash
npm install @jazzer.js/core

# Create seeds directory
mkdir -p $OUT/seeds
echo "initial" > $OUT/seeds/seed1

# Set up environment
export NODE_PATH=/usr/local/lib/node_modules
export JAZZER_OPTS="-max_len=4096"
