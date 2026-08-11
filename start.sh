#!/bin/bash
set -e

cd /home/jovyan/work

exec jupyter lab \
    --ip=0.0.0.0 \
    --port=8888 \
    --no-browser \
    --notebook-dir=/home/jovyan/work \
    --ServerApp.base_url=/apps/jupyter \
    --ServerApp.allow_origin_pat='https://.*\.corp\.shiqiao\.com'
