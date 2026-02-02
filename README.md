Vision-Based Pick and Place in Gazebo using myCobot 280 M5 (ROS 2)
------------------------------------------------------------------

This project is a complete simulation-based implementation of a **vision-guided pick and place task** using the **myCobot 280 M5 robotic arm** in **Gazebo** with **ROS 2**.

The robot detects an **ArUco marker** placed on top of a cube using an **eye-in-hand camera (intel realsense 435di depth camera)** mounted at the end-effector and performs pick-and-place using pose feedback.

This work is developed by taking reference from the official Elephant Robotics ROS 2 repository:

🔗 Official Repository: [https://github.com/elephantrobotics/mycobot\_ros2](https://github.com/elephantrobotics/mycobot_ros2)

📌 Project Overview
-------------------

The simulation environment contains:

*   **myCobot 280 M5 robot model** (from official ROS 2 packages)
    
*   A custom mounting setup where the robot base is placed on a platform parallel to the ground
    
*   Robot arm oriented downward for pick-and-place reachability
    
*   **20 cm × 20 cm × 20 cm**
    
*   An **ArUco marker pasted on the cube’s top face**
    
*   An **eye-in-hand camera** attached to the end-effector
    
*   Marker pose detection used for robotic alignment
    
*   A complete pick-and-place pipeline executed through ROS 2 launch files
    

📂 Workspace Structure
----------------------

```text
cobot_manipulation/
 ├── cobot_moveit_config     # MoveIt configuration for myCobot arm
 ├── mycobot_bringup         # Robot bringup launch and controllers
 ├── mycobot_description     # URDF and robot model files
 ├── mycobot_gazebo          # Gazebo simulation + world integration
 ├── ros2_aruco              # ArUco marker detection package
 └── src                     # Custom pick-and-place logic and nodes
 ```

⚙️ Requirements
---------------

This project was tested with:

*   ROS 2 Jazzy
    
*   Gazebo Harmonic
    
*   OpenCV ArUco detection
    
*   MoveIt 2 (for arm motion)
    
*   TF2 for coordinate transformations
    

Install dependencies:

```text   sudo apt update  
sudo apt install ros-humble-gazebo-ros-pkgs  sudo apt install ros-humble-vision-opencv  sudo apt install ros-humble-moveit   
```

 How to Run the Task
----------------------
## Use docker 

```text 
./build.sh #build the docker image from Dockerfile
./run.sh #once build run the docker container usign the image 
./terminal.sh #attach another terminal to the same container 
```

To run the full pipeline, you need to launch **three components** in sequence:

1️ Launch Gazebo Simulation
============================

Start the Gazebo world with robot + cube + platform:

`   ros2 launch mycobot_gazebo gazebo.launch.py   `

This spawns:

*   myCobot arm mounted properly
    
*   Cube with marker on ground
    
*   Eye-in-hand camera configuration

* ros2 controllers for the arm joints
    

2️ Run ArUco Marker Detection
==============================

Start the marker detection node:

`   ros2 launch ros2_aruco aruco.launch.py   `

This detects the marker and publishes its pose relative to the camera frame.

3️ Run Pick and Place Execution
================================

Finally, start the pick-and-place controller:

`   ros2 launch cobot_moveit_config pick_place.launch.py   `

Robot behavior:

*   Move to a pose so that aruco markers can be detected
    
*   Align end-effector properly
    
*   Pick cube using attach plugin
    
*   Lift and move to place position
    
*   Detach cube and complete task
    

 Grasp Simulation Using Gazebo Detach Plugin
----------------------------------------------

Since a real suction pump gripper is not available in simulation, this project uses the **Gazebo link attach/detach plugin**.

This plugin is used to **fake the vacuum pump behavior**:

*   During pick → cube is attached to end-effector
    
*   During place → cube is detached
    

This made it possible to complete the manipulation task realistically without complex gripper physics.

 Control Strategy
-------------------

The approach followed is:

1.  Camera detects ArUco marker pose
    
2.  Pose is transformed into robot base frame using TF2
    
3.  Robot moves to a pre-grasp pose
    
4.  Robot moves down for pickup
    
5.  Attach plugin activates
    
6.  Robot lifts and moves to drop pose
    
7.  Object is detached successfully
    

The system is structured in a modular ROS 2 way:

*   Gazebo simulation
    
*   Vision feedback
    
*   TF conversion
    
*   Motion execution
    

 Challenges Faced (Real Effort Behind This Work)
--------------------------------------------------

This project required some hard work, especially in setting up and debugging the simulation .

Some major challenges included:

###  Environment Setup Was Not Easy

Setting up the full ROS 2 + Gazebo + MoveIt + myCobot simulation environment took significant time.

There were repeated issues with:

*   missing dependencies
    
*   controller loading failures
    
*   Gazebo plugin errors
    
*   MoveIt planning configuration
    


###  TF Rotation and Frame Alignment Issues



###  Eye-in-Hand Camera Placement Challenges

Mounting the camera on the end-effector required careful adjustment of:

*   camera joint rotation
    
*   optical frame correctness
    
*   marker visibility
    

Without proper alignment, detection was unstable.


###  Gripper Simulation Limitations

Since no real gripper was present, simulating suction using attach/detach plugin was essential.

Integrating this plugin properly inside Gazebo was another major debugging task.

 Final Outcome
---------------

Despite these challenges, the final system successfully demonstrates:

*   Vision-based ArUco pose detection
    
*   Eye-in-hand perception
    
*   TF-based pose transformation
    
*   Pick-and-place manipulation in Gazebo
    
*   Object grasp simulation using attach/detach plugin
    


 Run Summary
-------------

To run the complete demo:

```text
ros2 launch mycobot_gazebo gazebo.launch.py  
ros2 launch ros2_aruco aruco.launch.py  
ros2 launch cobot_moveit_config pick_place.launch.py   
```

 Thank You
============

This submission demonstrates the integration of:

*   myCobot 280 M5 simulation
    
*   ArUco-based vision feedback
    
*   Eye-in-hand camera setup
    
*   Pick-and-place execution in ROS 2 Gazebo
    