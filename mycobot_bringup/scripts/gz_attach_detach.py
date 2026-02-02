#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool
from geometry_msgs.msg import Pose
from rclpy.qos import QoSProfile
import time

# Service messages
from gz_msgs.srv import SetLinkState
from gz_msgs.msg import LinkState

class PumpNode(Node):
    """
    ROS2 Node to simulate a suction pump in Gazebo Harmonic.
    Attaches cube to TCP by updating cube pose to match TCP.
    """
    def __init__(self):
        super().__init__('pump_node')
        
        # Subscribe to /pump_enable topic (Bool)
        qos = QoSProfile(depth=10)
        self.sub = self.create_subscription(Bool, '/pump_enable', self.pump_callback, qos)
        
        # ROS2 client for Gazebo link state service
        self.cli = self.create_client(SetLinkState, '/world/default/set_link_state')
        while not self.cli.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('Waiting for /set_link_state service...')
        
        self.attached = False
        self.tcp_pose = None  # To store current TCP pose
        self.cube_name = 'aruco_cube::link'  # Change if your cube has different link name
        self.robot_tcp_name = 'mycobot::tcp'  # Change if your TCP link has different name

    def pump_callback(self, msg: Bool):
        """
        Called when /pump_enable topic publishes True/False
        """
        if msg.data and not self.attached:
            self.attach_cube()
        elif not msg.data and self.attached:
            self.detach_cube()

    def attach_cube(self):
        """
        Attaches the cube by setting its pose to match TCP continuously.
        """
        # For simplicity, just set cube to current TCP once
        # For smoother demo, you can loop this to follow TCP while moving
        tcp_pose = self.get_tcp_pose()
        if tcp_pose is None:
            self.get_logger().warn("TCP pose not yet available. Cannot attach cube.")
            return

        link_state = LinkState()
        link_state.name = self.cube_name
        link_state.pose.position.x = tcp_pose.position.x
        link_state.pose.position.y = tcp_pose.position.y
        link_state.pose.position.z = tcp_pose.position.z
        link_state.pose.orientation = tcp_pose.orientation

        req = SetLinkState.Request()
        req.state = link_state
        self.cli.call_async(req)
        self.attached = True
        self.get_logger().info("Cube attached to TCP.")

    def detach_cube(self):
        """
        Detaches cube. In Gazebo, just let it fall by doing nothing.
        """
        self.attached = False
        self.get_logger().info("Cube detached from TCP.")

    def get_tcp_pose(self):
        """
        Get TCP pose from Gazebo.
        Here we can use ros_gz_bridge to get /model/tf or /link/pose
        For simplicity, this is a placeholder you fill in based on your TF or topic
        """
        # You should subscribe to /tf or /model/pose and get TCP pose here
        # For demo, let's just set a fixed position above the table
        pose = Pose()
        pose.position.x = 0.5
        pose.position.y = 0.0
        pose.position.z = 0.25
        pose.orientation.w = 1.0
        return pose


def main(args=None):
    rclpy.init(args=args)
    node = PumpNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
