#!/usr/bin/env bash

set -e

IMAGE_NAME="manipulation:latest"
CONTAINER_NAME="manipulation_container"

# Allow docker to access X server
xhost +local:docker >/dev/null

docker run -it --rm \
    --name ${CONTAINER_NAME} \
    --net=host \
    --ipc=host \
    --pid=host \
    --privileged \
    -e DISPLAY=$DISPLAY \
    -e QT_X11_NO_MITSHM=1 \
    -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
    -v $(pwd)/..:/root/cobot_ws \
    -w /root/cobot_ws \
    ${IMAGE_NAME} \
    bash

xhost -local:docker >/dev/null
