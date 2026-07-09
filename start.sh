#!/bin/bash
set -e

cd /home/jovyan/work

exec jupyter lab \
    --ip=0.0.0.0 \
    --port=8888 \
    --no-browser \
    --notebook-dir=/home/jovyan/work
