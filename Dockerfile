FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Etc/UTC \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    ROS_DISTRO=jazzy \
    PIP_BREAK_SYSTEM_PACKAGES=1

SHELL ["/bin/bash", "-c"]

# ----------------------------
# 1) Minimal base packages
# ----------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl gnupg2 dirmngr lsb-release \
    locales tzdata \
    wget git build-essential \
    bash-completion \
    sudo \
    vim nano htop \
    iputils-ping usbutils \
    software-properties-common \
    libserial-dev \
    python3-pip python3-argcomplete \
    && rm -rf /var/lib/apt/lists/*

# ----------------------------
# 2) Add ROS2 apt repo
# ----------------------------
RUN curl -L -s -o /tmp/ros2-apt-source.deb \
    https://github.com/ros-infrastructure/ros-apt-source/releases/download/1.1.0/ros2-apt-source_1.1.0.noble_all.deb && \
    echo "35441f3092fd05773a3c397fab38661bec466584c7a1f1c05366579997cb5fe7 /tmp/ros2-apt-source.deb" | sha256sum --strict --check && \
    apt-get update && apt-get install -y /tmp/ros2-apt-source.deb && \
    rm -f /tmp/ros2-apt-source.deb && \
    rm -rf /var/lib/apt/lists/*

# ----------------------------
# 3) ROS2 + MoveIt2
# ----------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    ros-${ROS_DISTRO}-ros-base \
    ros-${ROS_DISTRO}-rviz2 \
    ros-${ROS_DISTRO}-joint-state-publisher-gui \
    ros-${ROS_DISTRO}-xacro \
    ros-${ROS_DISTRO}-rqt-reconfigure \
    ros-${ROS_DISTRO}-moveit \
    ros-${ROS_DISTRO}-moveit-setup-assistant \
    ros-${ROS_DISTRO}-tf-transformations \
    python3-colcon-common-extensions \
    python3-colcon-mixin \
    python3-rosdep \
    python3-vcstool \
    python3-networkx \
    && rm -rf /var/lib/apt/lists/*

# rosdep init/update
RUN rosdep init || true && rosdep update --rosdistro $ROS_DISTRO

# ----------------------------
# 4) Mesa (optional)
# ----------------------------
RUN add-apt-repository -y ppa:kisak/kisak-mesa

# ----------------------------
# 5) Workspace
# ----------------------------
WORKDIR /root/ros2_ws
RUN mkdir -p src

COPY docker/entrypoint.sh /root/entrypoint.sh
RUN chmod +x /root/entrypoint.sh

RUN echo "source /opt/ros/${ROS_DISTRO}/setup.bash" >> /root/.bashrc

# ----------------------------
# 6) Copy source LAST (fast rebuild)
# ----------------------------
COPY . /root/ros2_ws/src/mycobot_ros2

RUN source /opt/ros/${ROS_DISTRO}/setup.bash && \
    rosdep install --from-paths src --ignore-src -r -y && \
    colcon build --symlink-install

RUN echo "source /root/ros2_ws/install/setup.bash" >> /root/.bashrc

ENTRYPOINT ["/root/entrypoint.sh"]
CMD ["bash"]
