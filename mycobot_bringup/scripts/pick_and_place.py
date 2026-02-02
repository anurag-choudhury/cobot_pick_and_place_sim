#!/usr/bin/env python3
import math
import subprocess
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient

from geometry_msgs.msg import PoseStamped, PoseArray

from tf2_ros import Buffer, TransformListener
from tf2_geometry_msgs import do_transform_pose_stamped

from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import (
    Constraints,
    PositionConstraint,
    OrientationConstraint,
    JointConstraint,
    MotionPlanRequest,
    PlanningOptions,
)
from shape_msgs.msg import SolidPrimitive


def pose_str(ps: PoseStamped, name="") -> str:
    p = ps.pose.position
    q = ps.pose.orientation
    pref = f"{name}: " if name else ""
    return (f"{pref}frame='{ps.header.frame_id}' "
            f"pos=({p.x:.3f},{p.y:.3f},{p.z:.3f}) "
            f"quat=({q.x:.3f},{q.y:.3f},{q.z:.3f},{q.w:.3f})")


def quat_normalize(q):
    x, y, z, w = q
    n = math.sqrt(x*x + y*y + z*z + w*w)
    if n < 1e-12:
        return (0.0, 0.0, 0.0, 1.0)
    return (x/n, y/n, z/n, w/n)


class ViewPickPlace(Node):
    def __init__(self):
        super().__init__("view_pick_place")

        # ---- core params ----
        self.declare_parameter("planning_frame", "base_link")
        self.declare_parameter("move_group", "arm")
        self.declare_parameter("ee_link", "tcp")

        # ---- pick params ----
        self.declare_parameter("pick_offset_z", 0.1)   # lift to "top" (base Z)
        self.declare_parameter("pos_box_size", 0.2)    # constraint box size
        self.declare_parameter("ori_tol_deg", 15.0)     # orientation tolerance

        # ---- VIEW joint pose ----
        self.declare_parameter(
            "view_joint_names",
            ["link1_to_link2", "link2_to_link3", "link3_to_link4",
             "link4_to_link5", "link5_to_link6", "link6_to_link6_flange"]
        )
        self.declare_parameter("view_joint_deg", [0.0, 41.0, -26.0, -65.0, 0.0, 0.0])

        # ---- PLACE pose ----
        self.declare_parameter("place_x", 0.25)
        self.declare_parameter("place_y", 0.15)
        self.declare_parameter("place_z", 0.25)
        self.declare_parameter("place_qx", 0.0)
        self.declare_parameter("place_qy", 1.0)
        self.declare_parameter("place_qz", 0.0)
        self.declare_parameter("place_qw", 1.0)

        # ---- Gazebo topics ----
        self.declare_parameter("attach_topic", "/cube/attach")
        self.declare_parameter("detach_topic", "/cube/detach")

        self.planning_frame = self.get_parameter("planning_frame").value
        self.group = self.get_parameter("move_group").value
        self.ee_link = self.get_parameter("ee_link").value

        self.pick_offset_z = float(self.get_parameter("pick_offset_z").value)
        self.pos_box_size = float(self.get_parameter("pos_box_size").value)
        self.ori_tol = math.radians(float(self.get_parameter("ori_tol_deg").value))

        self.view_joint_names = list(self.get_parameter("view_joint_names").value)
        self.view_joint_deg = list(self.get_parameter("view_joint_deg").value)

        self.attach_topic = str(self.get_parameter("attach_topic").value)
        self.detach_topic = str(self.get_parameter("detach_topic").value)

        if self.planning_frame.strip() == "world":
            self.get_logger().warn("planning_frame='world' passed, forcing 'base_link'.")
            self.planning_frame = "base_link"

        # ---- place pose ----
        self.place_pose = PoseStamped()
        self.place_pose.header.frame_id = self.planning_frame
        self.place_pose.pose.position.x = float(self.get_parameter("place_x").value)
        self.place_pose.pose.position.y = float(self.get_parameter("place_y").value)
        self.place_pose.pose.position.z = float(self.get_parameter("place_z").value)
        self.place_pose.pose.orientation.x = float(self.get_parameter("place_qx").value)
        self.place_pose.pose.orientation.y = float(self.get_parameter("place_qy").value)
        self.place_pose.pose.orientation.z = float(self.get_parameter("place_qz").value)
        self.place_pose.pose.orientation.w = float(self.get_parameter("place_qw").value)

        self.get_logger().info(f"Config: group='{self.group}', planning_frame='{self.planning_frame}', ee_link='{self.ee_link}'")
        self.get_logger().info(pose_str(self.place_pose, "PLACE"))

        # TF
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        # MoveIt action client
        self.move_client = ActionClient(self, MoveGroup, "/move_action")

        # ArUco subscription
        self.latest_pose_cam = None
        self.create_subscription(PoseArray, "/aruco_poses", self.cb_aruco, 10)

        # State
        self.phase = "VIEW"   # VIEW -> WAIT_ARUCO -> PICK_SENT -> PLACE_SENT -> DONE
        self.busy = False
        self.sent_pick = False

        self.timer = self.create_timer(0.5, self.loop)
        self.get_logger().info("Starting: will go to VIEW pose first.")

    # ---------------- ArUco ----------------
    def cb_aruco(self, msg: PoseArray):
        if not msg.poses:
            return
        ps = PoseStamped()
        ps.header = msg.header
        ps.pose = msg.poses[0]
        self.latest_pose_cam = ps

        if self.phase == "WAIT_ARUCO" and (not self.sent_pick) and (not self.busy):
            self.send_pick_once()

    def transform_to_base(self, pose_cam: PoseStamped) -> PoseStamped:
        tf = self.tf_buffer.lookup_transform(
            self.planning_frame,
            pose_cam.header.frame_id,
            rclpy.time.Time()
        )
        out = do_transform_pose_stamped(pose_cam, tf)
        out.header.frame_id = self.planning_frame
        return out

    def normalize_orientation(self, ps: PoseStamped) -> PoseStamped:
        q = (ps.pose.orientation.x, ps.pose.orientation.y, ps.pose.orientation.z, ps.pose.orientation.w)
        qn = quat_normalize(q)
        out = PoseStamped()
        out.header = ps.header
        out.pose = ps.pose
        out.pose.orientation.x = qn[0]
        out.pose.orientation.y = qn[1]
        out.pose.orientation.z = qn[2]
        out.pose.orientation.w = qn[3]
        return out

    # ---------------- MoveIt constraints ----------------
    def build_pose_constraints(self, target: PoseStamped) -> Constraints:
        c = Constraints()

        pc = PositionConstraint()
        pc.header.frame_id = target.header.frame_id
        pc.link_name = self.ee_link
        pc.weight = 1.0

        box = SolidPrimitive()
        box.type = SolidPrimitive.BOX
        box.dimensions = [self.pos_box_size, self.pos_box_size, self.pos_box_size]
        pc.constraint_region.primitives.append(box)
        pc.constraint_region.primitive_poses.append(target.pose)

        oc = OrientationConstraint()
        oc.header.frame_id = target.header.frame_id
        oc.link_name = self.ee_link
        oc.orientation = target.pose.orientation
        oc.absolute_x_axis_tolerance = self.ori_tol
        oc.absolute_y_axis_tolerance = self.ori_tol
        oc.absolute_z_axis_tolerance = self.ori_tol
        oc.weight = 1.0

        c.position_constraints.append(pc)
        c.orientation_constraints.append(oc)
        return c

    def make_goal_pose(self, target: PoseStamped) -> MoveGroup.Goal:
        req = MotionPlanRequest()
        req.group_name = self.group
        req.num_planning_attempts = 8
        req.allowed_planning_time = 8.0
        req.max_velocity_scaling_factor = 0.2
        req.max_acceleration_scaling_factor = 0.2
        req.goal_constraints.append(self.build_pose_constraints(target))

        goal = MoveGroup.Goal()
        goal.request = req
        goal.planning_options = PlanningOptions()
        goal.planning_options.plan_only = False
        goal.planning_options.replan = True
        goal.planning_options.replan_attempts = 2
        return goal

    def make_goal_view_joints(self) -> MoveGroup.Goal:
        req = MotionPlanRequest()
        req.group_name = self.group
        req.num_planning_attempts = 8
        req.allowed_planning_time = 8.0
        req.max_velocity_scaling_factor = 0.2
        req.max_acceleration_scaling_factor = 0.2

        c = Constraints()
        for name, deg in zip(self.view_joint_names, self.view_joint_deg):
            jc = JointConstraint()
            jc.joint_name = name
            jc.position = math.radians(float(deg))
            jc.tolerance_above = math.radians(2.0)
            jc.tolerance_below = math.radians(2.0)
            jc.weight = 1.0
            c.joint_constraints.append(jc)

        req.goal_constraints.append(c)

        goal = MoveGroup.Goal()
        goal.request = req
        goal.planning_options = PlanningOptions()
        goal.planning_options.plan_only = False
        goal.planning_options.replan = True
        goal.planning_options.replan_attempts = 2
        return goal

    # ---------------- Gazebo attach/detach ----------------
    def gz_empty(self, topic: str):
        cmd = f'gz topic -t {topic} -m gz.msgs.Empty -p ""'
        try:
            subprocess.run(["bash", "-lc", cmd], check=True)
            self.get_logger().info(f"GZ: published Empty to {topic}")
        except Exception as e:
            self.get_logger().error(f"GZ publish failed to {topic}: {e}")


    def attach(self):
        self.get_logger().info("GRIPPER: CLOSE -> attach")
        self.gz_empty(self.attach_topic)

    def detach(self):
        self.get_logger().info("GRIPPER: OPEN -> detach")
        self.gz_empty(self.detach_topic)

    # ---------------- Action send ----------------
    def send_goal(self, goal_msg: MoveGroup.Goal, tag: str):
        if self.busy:
            return
        if not self.move_client.wait_for_server(timeout_sec=10.0):
            self.get_logger().error("/move_action not available")
            return

        self.busy = True
        self.get_logger().info(f"[{tag}] Sending goal...")
        fut = self.move_client.send_goal_async(goal_msg)
        fut.add_done_callback(lambda f, t=tag: self.on_goal_response(f, t))

    def on_goal_response(self, future, tag: str):
        gh = future.result()
        if gh is None or not gh.accepted:
            self.get_logger().error(f"[{tag}] Goal rejected")
            self.busy = False
            return
        self.get_logger().info(f"[{tag}] Accepted, waiting result...")
        rf = gh.get_result_async()
        rf.add_done_callback(lambda f, t=tag: self.on_result(f, t))

    def on_result(self, future, tag: str):
        res = future.result()
        code = res.result.error_code.val

        if code == 1:
            self.get_logger().info(f"[{tag}] SUCCESS")
        else:
            self.get_logger().error(f"[{tag}] FAILED (MoveItErrorCodes={code})")

        self.busy = False

        if tag == "VIEW" and code == 1:
            self.phase = "WAIT_ARUCO"
            self.get_logger().info("Now waiting for ArUco...")
            return

        if tag == "PICK":
            if code == 1:
                self.attach()  # attach immediately after pick
                self.phase = "PLACE_SENT"
                self.send_goal(self.make_goal_pose(self.place_pose), "PLACE")
            else:
                self.phase = "DONE"
            return

        if tag == "PLACE":
            if code == 1:
                self.detach()  # detach after place
            self.phase = "DONE"
            self.get_logger().info("DONE.")
            return

    # ---------------- main loop ----------------
    def loop(self):
        if self.phase == "VIEW" and (not self.busy):
            self.send_goal(self.make_goal_view_joints(), "VIEW")

    def send_pick_once(self):
        if self.latest_pose_cam is None:
            return
        try:
            marker_base = self.transform_to_base(self.latest_pose_cam)
        except Exception as e:
            self.get_logger().warn(f"TF not ready: {e}")
            return

        # Build target pose (same as your working pick)
        target = PoseStamped()
        target.header.frame_id = self.planning_frame
        target.header.stamp = marker_base.header.stamp
        target.pose = marker_base.pose

        # Position: marker position + small base Z lift
        target.pose.position.z += self.pick_offset_z

        # Normalize quaternion only (keep your logic)
        target = self.normalize_orientation(target)

        self.get_logger().info(pose_str(marker_base, "MARKER_BASE"))
        self.get_logger().info(pose_str(target, "PICK_TARGET"))

        self.sent_pick = True
        self.phase = "PICK_SENT"
        self.send_goal(self.make_goal_pose(target), "PICK")


def main():
    rclpy.init()
    node = ViewPickPlace()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
