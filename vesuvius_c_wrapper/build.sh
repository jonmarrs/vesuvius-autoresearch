#!/bin/bash
set -e

# Compile the vesuvius-c wrapper shared library
gcc -shared -fPIC -O3 \
    -I../villa/vesuvius-c \
    -o libvesuvius.so \
    vesuvius_c_impl.c \
    -lcurl -lblosc2 -ljson-c -lm

echo "Successfully built libvesuvius.so"
