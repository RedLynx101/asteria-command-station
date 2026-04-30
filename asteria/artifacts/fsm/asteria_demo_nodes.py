from __future__ import annotations

from math import atan2, pi, sqrt
import re

from aim_fsm import *
from aim_fsm.geometry import wrap_angle
from aim_fsm import vex

from soccer_search_nodes import (
    AIVISION_FRAME_CENTER_X,
    SEARCH_STEP_DEG,
    SEARCH_TURN_COUNT,
    _ai_snapshot,
    _best_ai_tag,
    _object_center_x,
)


BARREL_SPEC = r"^(BlueBarrel|OrangeBarrel)(?:\.[a-z]+)?$"
BARREL_NAME_RE = re.compile(BARREL_SPEC)
APRILTAG_NAME_RE = re.compile(r"^AprilTag-(\d+)(?:\.[a-z]+)?$")
BARREL_AIM_TOLERANCE_PX = 24.0
BARREL_AIM_GAIN_DEG_PER_PX = 0.20
BARREL_AIM_MAX_TURN_DEG = 16.0
BARREL_CHARGE_STEP_MM = 140.0
BARREL_CHARGE_NEAR_STEP_MM = 80.0
BARREL_CHARGE_MAX_STEPS = 6
BARREL_CHARGE_CENTER_TOLERANCE_PX = 40.0
BARREL_CHARGE_TURN_GAIN_DEG_PER_PX = 0.12
BARREL_CHARGE_MAX_TURN_DEG = 10.0
BARREL_CHARGE_MAX_CORRECTIONS = 8
BARREL_NEAR_BOTTOM_PX = 170.0
TAG_AIM_TOLERANCE_PX = 18.0
TAG_AIM_GAIN_DEG_PER_PX = 0.22
TAG_AIM_MAX_TURN_DEG = 14.0
TRACK_SCAN_REVOLUTIONS = 2
TRACK_SCAN_TURNS = SEARCH_TURN_COUNT * TRACK_SCAN_REVOLUTIONS
GALLERY_TAG_IDS = (0, 1, 2, 3, 4)


def _tag_spec(tag_id: int) -> str:
    return rf"^AprilTag-{int(tag_id)}(?:\.[a-z]+)?$"


def _visible_world_tag_candidates(robot):
    candidates = []
    for obj in robot.world_map.objects.values():
        match = APRILTAG_NAME_RE.match(getattr(obj, "name", ""))
        if not match:
            continue
        if not getattr(obj, "is_valid", True):
            continue
        if not getattr(obj, "is_visible", False):
            continue
        dx = float(getattr(obj.pose, "x", 0.0)) - float(getattr(robot.pose, "x", 0.0))
        dy = float(getattr(obj.pose, "y", 0.0)) - float(getattr(robot.pose, "y", 0.0))
        candidates.append((dx * dx + dy * dy, int(match.group(1)), obj))
    candidates.sort(key=lambda item: item[0])
    return candidates


def _visible_world_barrel_candidates(robot):
    candidates = []
    for obj in robot.world_map.objects.values():
        if not BARREL_NAME_RE.match(getattr(obj, "name", "")):
            continue
        if not getattr(obj, "is_valid", True):
            continue
        if not getattr(obj, "is_visible", False):
            continue
        dx = float(getattr(obj.pose, "x", 0.0)) - float(getattr(robot.pose, "x", 0.0))
        dy = float(getattr(obj.pose, "y", 0.0)) - float(getattr(robot.pose, "y", 0.0))
        candidates.append((dx * dx + dy * dy, obj))
    candidates.sort(key=lambda item: item[0])
    return candidates


def _best_ai_barrel(robot):
    objects, error = _ai_snapshot(robot, "ALL_CARGO")
    if error:
        return None, error
    matches = []
    for obj in objects:
        classname = str(getattr(obj, "classname", ""))
        if classname not in ("BlueBarrel", "OrangeBarrel"):
            continue
        area = float(getattr(obj, "width", 0.0)) * float(getattr(obj, "height", 0.0))
        center_error = abs(_object_center_x(obj) - AIVISION_FRAME_CENTER_X)
        matches.append((area, -center_error, obj))
    if not matches:
        return None, "no barrel visible in AI vision"
    matches.sort(key=lambda item: (item[0], item[1]), reverse=True)
    best_match = matches[0][2]
    return best_match, f"AI vision {getattr(best_match, 'classname', 'barrel')}"


def _has_any_barrel(robot):
    robot0 = getattr(robot, "robot0", None)
    if robot0 is None:
        return False, "robot0 unavailable"
    probe = getattr(robot0, "has_any_barrel", None)
    if not callable(probe):
        return False, "has_any_barrel unavailable"
    try:
        return bool(probe()), None
    except Exception as exc:
        return False, f"has_any_barrel error: {exc}"


def _best_any_ai_tag(robot):
    objects, error = _ai_snapshot(robot, "ALL_TAGS")
    if error:
        return None, None, error
    if not objects:
        return None, None, "no AprilTags visible in AI vision"
    best_match = max(
        objects,
        key=lambda obj: float(getattr(obj, "width", 0.0)) * float(getattr(obj, "height", 0.0)),
    )
    return best_match, int(getattr(best_match, "id", -1)), "AI vision AprilTag"


class SearchForBarrel(ActionNode, ObjectSpecNode):
    """Turn in place until a barrel appears in the world map or AI vision."""

    def __init__(
        self,
        label="barrel",
        step_deg=SEARCH_STEP_DEG,
        max_turns=SEARCH_TURN_COUNT,
        turn_speed=None,
        settle_sec=0.35,
    ):
        super().__init__()
        self.label = label
        self.step_deg = float(step_deg)
        self.max_turns = int(max_turns)
        self.turn_speed = turn_speed
        self.settle_sec = float(settle_sec)
        self.turns_completed = 0
        self.found_object = None

    def start(self, event=None):
        super().start(event)
        self.turns_completed = 0
        self.found_object = None
        if self._check_visible("start"):
            return
        self._begin_turn()

    def complete(self, actuator=None):
        self.unlock_held_actuators()
        if not self.running:
            return
        self.turns_completed += 1
        self.robot.loop.call_later(self.settle_sec, self._after_turn_settle)

    def _after_turn_settle(self):
        if not self.running:
            return
        if self._check_visible(f"turn {self.turns_completed}"):
            return
        self._begin_turn()

    def _check_visible(self, phase):
        world_candidates = _visible_world_barrel_candidates(self.robot)
        if world_candidates:
            _, world_obj = world_candidates[0]
            self.found_object = world_obj
            print(f"{self.label}: found {world_obj.id or world_obj.name} in world map during {phase}")
            self.post_success()
            return True
        ai_barrel, reason = _best_ai_barrel(self.robot)
        if ai_barrel is not None:
            self.found_object = ai_barrel
            print(f"{self.label}: found {getattr(ai_barrel, 'classname', 'barrel')} in AI vision during {phase}")
            self.post_success()
            return True
        print(f"{self.label}: no visible barrel during {phase} ({reason})")
        return False

    def _begin_turn(self):
        if not self.running:
            return
        if self.turns_completed >= self.max_turns:
            print(f"{self.label}: not found after a full circle search")
            self.post_failure()
            return
        print(
            f"{self.label}: search turn {self.turns_completed + 1}/{self.max_turns} "
            f"by {self.step_deg:.1f} degrees"
        )
        self.robot.actuators["drive"].turn(self, self.step_deg * pi / 180.0, self.turn_speed)


class TurnTowardBarrelIfNeeded(ActionNode, ObjectSpecNode):
    """Aim toward the nearest visible barrel using the world map or AI centering."""

    def __init__(
        self,
        min_turn_deg=5.0,
        centered_tolerance_px=BARREL_AIM_TOLERANCE_PX,
        turn_gain_deg_per_px=BARREL_AIM_GAIN_DEG_PER_PX,
        max_turn_deg=BARREL_AIM_MAX_TURN_DEG,
        max_attempts=8,
        turn_speed=None,
        settle_sec=0.35,
    ):
        super().__init__()
        self.min_turn_deg = float(min_turn_deg)
        self.centered_tolerance_px = float(centered_tolerance_px)
        self.turn_gain_deg_per_px = float(turn_gain_deg_per_px)
        self.max_turn_deg = float(max_turn_deg)
        self.max_attempts = int(max_attempts)
        self.turn_speed = turn_speed
        self.settle_sec = float(settle_sec)
        self.attempt_index = 0
        self.angle_deg = 0.0

    def start(self, event=None):
        super().start(event)
        self.attempt_index = 0
        self._attempt_alignment()

    def complete(self, actuator=None):
        self.unlock_held_actuators()
        if not self.running:
            return
        self.robot.loop.call_later(self.settle_sec, self._attempt_alignment)

    def _attempt_alignment(self):
        if not self.running:
            return
        world_candidates = _visible_world_barrel_candidates(self.robot)
        if world_candidates:
            _, world_obj = world_candidates[0]
            dx = world_obj.pose.x - self.robot.pose.x
            dy = world_obj.pose.y - self.robot.pose.y
            angle = wrap_angle(atan2(dy, dx) - self.robot.pose.theta)
            self.angle_deg = angle * 180.0 / pi
            if abs(self.angle_deg) < self.min_turn_deg:
                print(f"aim: {world_obj.id or world_obj.name} already within {self.min_turn_deg:.1f} degrees")
                self.post_completion()
                return
            self._dispatch_turn(self.angle_deg, "world-map bearing")
            return

        ai_barrel, reason = _best_ai_barrel(self.robot)
        if ai_barrel is None:
            print(f"aim: barrel is not visible ({reason})")
            self.post_failure()
            return

        pixel_error = _object_center_x(ai_barrel) - AIVISION_FRAME_CENTER_X
        if abs(pixel_error) <= self.centered_tolerance_px:
            print(f"aim: barrel centered within {self.centered_tolerance_px:.1f} px")
            self.post_completion()
            return

        turn_deg = min(self.max_turn_deg, max(self.min_turn_deg, abs(pixel_error) * self.turn_gain_deg_per_px))
        signed_turn_deg = -turn_deg if pixel_error > 0 else turn_deg
        self._dispatch_turn(signed_turn_deg, f"AI vision pixel error {pixel_error:.1f}")

    def _dispatch_turn(self, angle_deg, reason):
        if self.attempt_index >= self.max_attempts:
            print(f"aim: barrel still not aligned after {self.max_attempts} attempts")
            self.post_failure()
            return
        self.attempt_index += 1
        self.angle_deg = float(angle_deg)
        print(f"aim: turning {self.angle_deg:.1f} degrees from {reason}")
        self.robot.actuators["drive"].turn(self, self.angle_deg * pi / 180.0, self.turn_speed)


class ChargeBarrel(ActionNode, ObjectSpecNode):
    """Drive into a barrel using world-map distance when available, else AI-guided steps."""

    def __init__(
        self,
        step_mm=BARREL_CHARGE_STEP_MM,
        near_step_mm=BARREL_CHARGE_NEAR_STEP_MM,
        max_steps=BARREL_CHARGE_MAX_STEPS,
        centered_tolerance_px=BARREL_CHARGE_CENTER_TOLERANCE_PX,
        turn_gain_deg_per_px=BARREL_CHARGE_TURN_GAIN_DEG_PER_PX,
        max_turn_deg=BARREL_CHARGE_MAX_TURN_DEG,
        max_corrections=BARREL_CHARGE_MAX_CORRECTIONS,
        near_bottom_px=BARREL_NEAR_BOTTOM_PX,
        contact_margin_mm=8.0,
        robot_radius_mm=30.0,
        min_distance_mm=25.0,
        drive_speed=None,
        turn_speed=None,
        settle_sec=0.30,
    ):
        super().__init__()
        self.step_mm = float(step_mm)
        self.near_step_mm = float(near_step_mm)
        self.max_steps = int(max_steps)
        self.centered_tolerance_px = float(centered_tolerance_px)
        self.turn_gain_deg_per_px = float(turn_gain_deg_per_px)
        self.max_turn_deg = float(max_turn_deg)
        self.max_corrections = int(max_corrections)
        self.near_bottom_px = float(near_bottom_px)
        self.contact_margin_mm = float(contact_margin_mm)
        self.robot_radius_mm = float(robot_radius_mm)
        self.min_distance_mm = float(min_distance_mm)
        self.drive_speed = drive_speed
        self.turn_speed = turn_speed
        self.settle_sec = float(settle_sec)
        self.forward_steps = 0
        self.correction_steps = 0

    def start(self, event=None):
        super().start(event)
        self.forward_steps = 0
        self.correction_steps = 0
        self._continue_charge()

    def complete(self, actuator=None):
        self.unlock_held_actuators()
        if not self.running:
            return
        self.robot.loop.call_later(self.settle_sec, self._continue_charge)

    def _continue_charge(self):
        if not self.running:
            return

        has_barrel, reason = _has_any_barrel(self.robot)
        if has_barrel:
            print("barrel charge: barrel secured")
            self.post_completion()
            return

        world_candidates = _visible_world_barrel_candidates(self.robot)
        if world_candidates:
            if self.forward_steps >= self.max_steps:
                print("barrel charge: reached the maximum number of forward steps")
                self.post_failure()
                return
            _, world_obj = world_candidates[0]
            dx = float(world_obj.pose.x) - float(self.robot.pose.x)
            dy = float(world_obj.pose.y) - float(self.robot.pose.y)
            distance = sqrt(dx ** 2 + dy ** 2) - self.robot_radius_mm + self.contact_margin_mm
            drive_mm = max(self.min_distance_mm, min(self.step_mm, distance))
            self.forward_steps += 1
            print(
                f"barrel charge: world-guided step {self.forward_steps}/{self.max_steps} "
                f"by {drive_mm:.1f} mm toward {world_obj.id or world_obj.name}"
            )
            self.robot.actuators["drive"].forward(self, drive_mm, self.drive_speed)
            return

        ai_barrel, ai_reason = _best_ai_barrel(self.robot)
        if ai_barrel is None:
            print(f"barrel charge: barrel lost before contact ({ai_reason}; hold check: {reason})")
            self.post_failure()
            return

        pixel_error = _object_center_x(ai_barrel) - AIVISION_FRAME_CENTER_X
        if abs(pixel_error) > self.centered_tolerance_px:
            if self.correction_steps >= self.max_corrections:
                print("barrel charge: exceeded the maximum number of AI recenter corrections")
                self.post_failure()
                return
            self.correction_steps += 1
            turn_deg = min(self.max_turn_deg, max(4.0, abs(pixel_error) * self.turn_gain_deg_per_px))
            signed_turn_deg = -turn_deg if pixel_error > 0 else turn_deg
            print(
                f"barrel charge: correction {self.correction_steps}/{self.max_corrections} "
                f"by {signed_turn_deg:.1f} degrees from AI pixel error {pixel_error:.1f}"
            )
            self.robot.actuators["drive"].turn(self, signed_turn_deg * pi / 180.0, self.turn_speed)
            return

        if self.forward_steps >= self.max_steps:
            print("barrel charge: reached the maximum number of AI-guided forward steps")
            self.post_failure()
            return

        bottom_px = float(getattr(ai_barrel, "originY", 0.0)) + float(getattr(ai_barrel, "height", 0.0))
        drive_mm = self.near_step_mm if bottom_px >= self.near_bottom_px else self.step_mm
        self.forward_steps += 1
        print(
            f"barrel charge: AI-guided step {self.forward_steps}/{self.max_steps} "
            f"by {drive_mm:.1f} mm toward {getattr(ai_barrel, 'classname', 'barrel')}"
        )
        self.robot.actuators["drive"].forward(self, drive_mm, self.drive_speed)


class SearchForAprilTag(ActionNode, ObjectSpecNode):
    """Turn in place through a full sweep until a specific AprilTag is visible."""

    def __init__(
        self,
        tag_id,
        label=None,
        step_deg=SEARCH_STEP_DEG,
        max_turns=SEARCH_TURN_COUNT,
        turn_speed=None,
        settle_sec=0.45,
    ):
        super().__init__()
        self.tag_id = int(tag_id)
        self.label = label or f"AprilTag {self.tag_id}"
        self.step_deg = float(step_deg)
        self.max_turns = int(max_turns)
        self.turn_speed = turn_speed
        self.settle_sec = float(settle_sec)
        self.turns_completed = 0
        self.found_object = None

    def start(self, event=None):
        super().start(event)
        self.turns_completed = 0
        self.found_object = None
        if self._check_visible("start"):
            return
        self._begin_turn()

    def complete(self, actuator=None):
        self.unlock_held_actuators()
        if not self.running:
            return
        self.turns_completed += 1
        self.robot.loop.call_later(self.settle_sec, self._after_turn_settle)

    def _after_turn_settle(self):
        if not self.running:
            return
        if self._check_visible(f"turn {self.turns_completed}"):
            return
        self._begin_turn()

    def _check_visible(self, phase):
        world_obj = self.get_object_from_spec(_tag_spec(self.tag_id))
        if world_obj is not None and getattr(world_obj, "is_visible", False):
            self.found_object = world_obj
            print(f"{self.label}: found {world_obj.id or world_obj.name} in world map during {phase}")
            self.post_success()
            return True
        ai_tag, reason = _best_ai_tag(self.robot, self.tag_id)
        if ai_tag is not None:
            self.found_object = ai_tag
            print(f"{self.label}: found tag {self.tag_id} in AI vision during {phase}")
            self.post_success()
            return True
        print(f"{self.label}: no visible tag during {phase} ({reason})")
        return False

    def _begin_turn(self):
        if not self.running:
            return
        if self.turns_completed >= self.max_turns:
            print(f"{self.label}: not found after the allotted scan")
            self.post_failure()
            return
        print(
            f"{self.label}: search turn {self.turns_completed + 1}/{self.max_turns} "
            f"by {self.step_deg:.1f} degrees"
        )
        self.robot.actuators["drive"].turn(self, self.step_deg * pi / 180.0, self.turn_speed)


class TurnTowardAprilTagIfNeeded(ActionNode, ObjectSpecNode):
    """Aim toward a specific AprilTag using world-map or AI centering."""

    def __init__(
        self,
        tag_id,
        min_turn_deg=5.0,
        centered_tolerance_px=TAG_AIM_TOLERANCE_PX,
        turn_gain_deg_per_px=TAG_AIM_GAIN_DEG_PER_PX,
        max_turn_deg=TAG_AIM_MAX_TURN_DEG,
        max_attempts=8,
        turn_speed=None,
        settle_sec=0.35,
    ):
        super().__init__()
        self.tag_id = int(tag_id)
        self.min_turn_deg = float(min_turn_deg)
        self.centered_tolerance_px = float(centered_tolerance_px)
        self.turn_gain_deg_per_px = float(turn_gain_deg_per_px)
        self.max_turn_deg = float(max_turn_deg)
        self.max_attempts = int(max_attempts)
        self.turn_speed = turn_speed
        self.settle_sec = float(settle_sec)
        self.attempt_index = 0
        self.angle_deg = 0.0

    def start(self, event=None):
        super().start(event)
        self.attempt_index = 0
        self._attempt_alignment()

    def complete(self, actuator=None):
        self.unlock_held_actuators()
        if not self.running:
            return
        self.robot.loop.call_later(self.settle_sec, self._attempt_alignment)

    def _attempt_alignment(self):
        if not self.running:
            return
        world_obj = self.get_object_from_spec(_tag_spec(self.tag_id))
        if world_obj is not None and getattr(world_obj, "is_visible", False):
            dx = world_obj.pose.x - self.robot.pose.x
            dy = world_obj.pose.y - self.robot.pose.y
            angle = wrap_angle(atan2(dy, dx) - self.robot.pose.theta)
            self.angle_deg = angle * 180.0 / pi
            if abs(self.angle_deg) < self.min_turn_deg:
                print(f"aim: AprilTag {self.tag_id} already within {self.min_turn_deg:.1f} degrees")
                self.post_completion()
                return
            self._dispatch_turn(self.angle_deg, "world-map bearing")
            return

        ai_tag, reason = _best_ai_tag(self.robot, self.tag_id)
        if ai_tag is None:
            print(f"aim: AprilTag {self.tag_id} is not visible ({reason})")
            self.post_failure()
            return

        pixel_error = _object_center_x(ai_tag) - AIVISION_FRAME_CENTER_X
        if abs(pixel_error) <= self.centered_tolerance_px:
            print(f"aim: AprilTag {self.tag_id} centered within {self.centered_tolerance_px:.1f} px")
            self.post_completion()
            return

        turn_deg = min(self.max_turn_deg, max(self.min_turn_deg, abs(pixel_error) * self.turn_gain_deg_per_px))
        signed_turn_deg = -turn_deg if pixel_error > 0 else turn_deg
        self._dispatch_turn(signed_turn_deg, f"AI vision pixel error {pixel_error:.1f}")

    def _dispatch_turn(self, angle_deg, reason):
        if self.attempt_index >= self.max_attempts:
            print(f"aim: AprilTag {self.tag_id} still not aligned after {self.max_attempts} attempts")
            self.post_failure()
            return
        self.attempt_index += 1
        self.angle_deg = float(angle_deg)
        print(f"aim: turning {self.angle_deg:.1f} degrees from {reason}")
        self.robot.actuators["drive"].turn(self, self.angle_deg * pi / 180.0, self.turn_speed)


class DriveToObject(Forward, ObjectSpecNode):
    """Drive straight into a visible/known object using its current world pose."""

    def __init__(self, object_spec, contact_margin_mm=8.0, robot_radius_mm=30.0, min_distance_mm=10.0, drive_speed=None):
        super().__init__(0.0, drive_speed)
        self.object_spec = object_spec
        self.contact_margin_mm = float(contact_margin_mm)
        self.robot_radius_mm = float(robot_radius_mm)
        self.min_distance_mm = float(min_distance_mm)

    def start(self, event=None):
        if isinstance(event, DataEvent):
            spec = event.data
        else:
            spec = self.object_spec
        obj = self.get_object_from_spec(spec)
        if obj is None:
            StateNode.start(self, event)
            self.post_failure()
            return
        dx = float(obj.pose.x) - float(self.robot.pose.x)
        dy = float(obj.pose.y) - float(self.robot.pose.y)
        distance = sqrt(dx ** 2 + dy ** 2) - self.robot_radius_mm + self.contact_margin_mm
        self.distance_mm = max(self.min_distance_mm, distance)
        print(f"drive: advancing {self.distance_mm:.1f} mm toward {obj.id or obj.name}")
        Forward.start(self, event)


class DriveNearAprilTag(Forward, ObjectSpecNode):
    """Drive toward a specific AprilTag while stopping at a configurable stand-off distance."""

    def __init__(
        self,
        tag_id,
        label=None,
        standoff_mm=220.0,
        min_drive_mm=40.0,
        max_drive_mm=450.0,
        drive_speed=None,
    ):
        super().__init__(0.0, drive_speed)
        self.tag_id = int(tag_id)
        self.label = label or f"AprilTag {self.tag_id}"
        self.standoff_mm = float(standoff_mm)
        self.min_drive_mm = float(min_drive_mm)
        self.max_drive_mm = float(max_drive_mm)

    def start(self, event=None):
        obj = self.get_object_from_spec(_tag_spec(self.tag_id))
        if obj is None or not getattr(obj, "is_visible", False):
            StateNode.start(self, event)
            print(f"drive: {self.label} is not visible in the world map for the approach step")
            self.post_failure()
            return

        dx = float(obj.pose.x) - float(self.robot.pose.x)
        dy = float(obj.pose.y) - float(self.robot.pose.y)
        distance_mm = sqrt(dx ** 2 + dy ** 2)
        if distance_mm <= self.standoff_mm:
            StateNode.start(self, event)
            print(f"drive: already within the {self.standoff_mm:.1f} mm stand-off for {obj.id or obj.name}")
            self.post_completion()
            return

        drive_mm = min(self.max_drive_mm, max(self.min_drive_mm, distance_mm - self.standoff_mm))
        self.distance_mm = drive_mm
        print(
            f"drive: advancing {self.distance_mm:.1f} mm toward {obj.id or obj.name} "
            f"with a {self.standoff_mm:.1f} mm stand-off"
        )
        Forward.start(self, event)


class ApproachSpecificAprilTag(StateNode):
    """Search for, center on, and stop at a stand-off distance from one specific AprilTag."""

    def __init__(self, tag_id, label=None, max_scan_turns=TRACK_SCAN_TURNS, standoff_mm=220.0):
        self.tag_id = int(tag_id)
        self.label = label or f"AprilTag {self.tag_id}"
        self.max_scan_turns = int(max_scan_turns)
        self.standoff_mm = float(standoff_mm)
        super().__init__()

    def setup(self):
        search = SearchForAprilTag(
            self.tag_id,
            label=self.label,
            max_turns=self.max_scan_turns,
        ).set_name("search").set_parent(self)
        aim = TurnTowardAprilTagIfNeeded(self.tag_id, 5.0, max_attempts=6).set_name("aim").set_parent(self)
        drive = DriveNearAprilTag(
            self.tag_id,
            label=self.label,
            standoff_mm=self.standoff_mm,
        ).set_name("drive").set_parent(self)
        arrived = Say(f"I am in front of {self.label}").set_name("arrived").set_parent(self)
        missing = Say(f"I could not find {self.label}").set_name("missing").set_parent(self)
        misaligned = Say(f"I found {self.label} but could not line up").set_name("misaligned").set_parent(self)
        unsafe_range = (
            Say(f"I found {self.label} but could not get a safe range fix")
            .set_name("unsafe_range")
            .set_parent(self)
        )
        parentcompletes1 = ParentCompletes().set_name("parentcompletes1").set_parent(self)
        parentfails1 = ParentFails().set_name("parentfails1").set_parent(self)

        successtrans1 = SuccessTrans().set_name("successtrans1")
        successtrans1.add_sources(search).add_destinations(aim)

        failuretrans1 = FailureTrans().set_name("failuretrans1")
        failuretrans1.add_sources(search).add_destinations(missing)

        completiontrans1 = CompletionTrans().set_name("completiontrans1")
        completiontrans1.add_sources(aim).add_destinations(drive)

        failuretrans2 = FailureTrans().set_name("failuretrans2")
        failuretrans2.add_sources(aim).add_destinations(misaligned)

        completiontrans2 = CompletionTrans().set_name("completiontrans2")
        completiontrans2.add_sources(drive).add_destinations(arrived)

        failuretrans3 = FailureTrans().set_name("failuretrans3")
        failuretrans3.add_sources(drive).add_destinations(unsafe_range)

        completiontrans3 = CompletionTrans().set_name("completiontrans3")
        completiontrans3.add_sources(arrived).add_destinations(parentcompletes1)

        completiontrans4 = CompletionTrans().set_name("completiontrans4")
        completiontrans4.add_sources(missing).add_destinations(parentfails1)

        completiontrans5 = CompletionTrans().set_name("completiontrans5")
        completiontrans5.add_sources(misaligned).add_destinations(parentfails1)

        completiontrans6 = CompletionTrans().set_name("completiontrans6")
        completiontrans6.add_sources(unsafe_range).add_destinations(parentfails1)

        return self


class GalleryStop(StateNode):
    """Search for, center, and announce one specific AprilTag, then continue."""

    def __init__(self, tag_id):
        self.tag_id = int(tag_id)
        super().__init__()

    def setup(self):
        intro = Say(f"Looking for AprilTag {self.tag_id}").set_name("intro").set_parent(self)
        search = SearchForAprilTag(self.tag_id).set_name("search").set_parent(self)
        aim = TurnTowardAprilTagIfNeeded(self.tag_id, 5.0, max_attempts=6).set_name("aim").set_parent(self)
        found = Say(f"Here is AprilTag {self.tag_id}").set_name("found").set_parent(self)
        missing = Say(f"I could not find AprilTag {self.tag_id}").set_name("missing").set_parent(self)
        misaligned = (
            Say(f"I found AprilTag {self.tag_id} but could not center it")
            .set_name("misaligned")
            .set_parent(self)
        )
        parentcompletes1 = ParentCompletes().set_name("parentcompletes1").set_parent(self)

        completiontrans1 = CompletionTrans().set_name("completiontrans1")
        completiontrans1.add_sources(intro).add_destinations(search)

        successtrans1 = SuccessTrans().set_name("successtrans1")
        successtrans1.add_sources(search).add_destinations(aim)

        failuretrans1 = FailureTrans().set_name("failuretrans1")
        failuretrans1.add_sources(search).add_destinations(missing)

        completiontrans2 = CompletionTrans().set_name("completiontrans2")
        completiontrans2.add_sources(aim).add_destinations(found)

        failuretrans2 = FailureTrans().set_name("failuretrans2")
        failuretrans2.add_sources(aim).add_destinations(misaligned)

        completiontrans3 = CompletionTrans().set_name("completiontrans3")
        completiontrans3.add_sources(found).add_destinations(parentcompletes1)

        completiontrans4 = CompletionTrans().set_name("completiontrans4")
        completiontrans4.add_sources(missing).add_destinations(parentcompletes1)

        completiontrans5 = CompletionTrans().set_name("completiontrans5")
        completiontrans5.add_sources(misaligned).add_destinations(parentcompletes1)

        return self


class ChargeAndKickBarrel(StateNode):
    def setup(self):
        search = SearchForBarrel().set_name("search").set_parent(self)
        aim = TurnTowardBarrelIfNeeded(5.0).set_name("aim").set_parent(self)
        charge = ChargeBarrel().set_name("charge").set_parent(self)
        settle = StateNode().set_name("settle").set_parent(self)
        kick = Kick(vex.KickType.HARD).set_name("kick").set_parent(self)
        announce_missing = Say("I could not find a barrel").set_name("announce_missing").set_parent(self)
        announce_aim_failed = Say("I found a barrel but could not line up").set_name("announce_aim_failed").set_parent(self)
        announce_charge_failed = (
            Say("I got mad but could not reach the barrel")
            .set_name("announce_charge_failed")
            .set_parent(self)
        )
        celebrate = Say("Take that, barrel").set_name("celebrate").set_parent(self)
        announce_kick_failed = Say("I reached the barrel but could not kick it").set_name("announce_kick_failed").set_parent(self)
        parentcompletes1 = ParentCompletes().set_name("parentcompletes1").set_parent(self)
        parentfails1 = ParentFails().set_name("parentfails1").set_parent(self)

        successtrans1 = SuccessTrans().set_name("successtrans1")
        successtrans1.add_sources(search).add_destinations(aim)

        failuretrans1 = FailureTrans().set_name("failuretrans1")
        failuretrans1.add_sources(search).add_destinations(announce_missing)

        completiontrans1 = CompletionTrans().set_name("completiontrans1")
        completiontrans1.add_sources(aim).add_destinations(charge)

        failuretrans2 = FailureTrans().set_name("failuretrans2")
        failuretrans2.add_sources(aim).add_destinations(announce_aim_failed)

        completiontrans2 = CompletionTrans().set_name("completiontrans2")
        completiontrans2.add_sources(charge).add_destinations(settle)

        failuretrans3 = FailureTrans().set_name("failuretrans3")
        failuretrans3.add_sources(charge).add_destinations(announce_charge_failed)

        timertrans1 = TimerTrans(0.2).set_name("timertrans1")
        timertrans1.add_sources(settle).add_destinations(kick)

        completiontrans3 = CompletionTrans().set_name("completiontrans3")
        completiontrans3.add_sources(kick).add_destinations(celebrate)

        failuretrans4 = FailureTrans().set_name("failuretrans4")
        failuretrans4.add_sources(kick).add_destinations(announce_kick_failed)

        completiontrans4 = CompletionTrans().set_name("completiontrans4")
        completiontrans4.add_sources(celebrate).add_destinations(parentcompletes1)

        completiontrans5 = CompletionTrans().set_name("completiontrans5")
        completiontrans5.add_sources(announce_missing).add_destinations(parentfails1)

        completiontrans6 = CompletionTrans().set_name("completiontrans6")
        completiontrans6.add_sources(announce_aim_failed).add_destinations(parentfails1)

        completiontrans7 = CompletionTrans().set_name("completiontrans7")
        completiontrans7.add_sources(announce_charge_failed).add_destinations(parentfails1)

        completiontrans8 = CompletionTrans().set_name("completiontrans8")
        completiontrans8.add_sources(announce_kick_failed).add_destinations(parentfails1)

        return self


class FollowAnyAprilTag(StateNode):
    def __init__(self, max_search_turns=TRACK_SCAN_TURNS, step_deg=SEARCH_STEP_DEG):
        self.max_search_turns = int(max_search_turns)
        self.step_deg = float(step_deg)
        self.tracked_tag_id = None
        self.tracked_tag_name = None
        super().__init__()

    class SearchForTrackedTag(ActionNode, ObjectSpecNode):
        def __init__(self, step_deg=SEARCH_STEP_DEG, max_turns=TRACK_SCAN_TURNS, turn_speed=None, settle_sec=0.45):
            super().__init__()
            self.step_deg = float(step_deg)
            self.max_turns = int(max_turns)
            self.turn_speed = turn_speed
            self.settle_sec = float(settle_sec)
            self.turns_completed = 0

        def start(self, event=None):
            super().start(event)
            self.turns_completed = 0
            if self._check_visible("start"):
                return
            self._begin_turn()

        def complete(self, actuator=None):
            self.unlock_held_actuators()
            if not self.running:
                return
            self.turns_completed += 1
            self.robot.loop.call_later(self.settle_sec, self._after_turn_settle)

        def _after_turn_settle(self):
            if not self.running:
                return
            if self._check_visible(f"turn {self.turns_completed}"):
                return
            self._begin_turn()

        def _check_visible(self, phase):
            tag_id = getattr(self.parent, "tracked_tag_id", None)
            if tag_id is not None:
                world_obj = self.get_object_from_spec(_tag_spec(tag_id))
                if world_obj is not None and getattr(world_obj, "is_visible", False):
                    self.parent.tracked_tag_name = world_obj.id or world_obj.name
                    print(f"follow tag: reacquired AprilTag {tag_id} in world map during {phase}")
                    self.post_success()
                    return True
                ai_tag, reason = _best_ai_tag(self.robot, tag_id)
                if ai_tag is not None:
                    self.parent.tracked_tag_name = f"AprilTag-{tag_id}"
                    print(f"follow tag: reacquired AprilTag {tag_id} in AI vision during {phase}")
                    self.post_success()
                    return True
                print(f"follow tag: tag {tag_id} not visible during {phase} ({reason})")
                return False

            world_candidates = _visible_world_tag_candidates(self.robot)
            if world_candidates:
                _, tag_id, world_obj = world_candidates[0]
                self.parent.tracked_tag_id = tag_id
                self.parent.tracked_tag_name = world_obj.id or world_obj.name
                print(f"follow tag: acquired AprilTag {tag_id} from world map during {phase}")
                self.post_success()
                return True

            ai_tag, tag_id, reason = _best_any_ai_tag(self.robot)
            if ai_tag is not None and tag_id is not None and tag_id >= 0:
                self.parent.tracked_tag_id = tag_id
                self.parent.tracked_tag_name = f"AprilTag-{tag_id}"
                print(f"follow tag: acquired AprilTag {tag_id} from AI vision during {phase}")
                self.post_success()
                return True

            print(f"follow tag: no visible AprilTag during {phase} ({reason})")
            return False

        def _begin_turn(self):
            if not self.running:
                return
            if self.turns_completed >= self.max_turns:
                print("follow tag: gave up after the full reacquisition scan")
                self.post_failure()
                return
            print(
                f"follow tag: search turn {self.turns_completed + 1}/{self.max_turns} "
                f"by {self.step_deg:.1f} degrees"
            )
            self.robot.actuators["drive"].turn(self, self.step_deg * pi / 180.0, self.turn_speed)

    class AimTrackedTag(ActionNode, ObjectSpecNode):
        def __init__(
            self,
            min_turn_deg=5.0,
            centered_tolerance_px=TAG_AIM_TOLERANCE_PX,
            turn_gain_deg_per_px=TAG_AIM_GAIN_DEG_PER_PX,
            max_turn_deg=TAG_AIM_MAX_TURN_DEG,
            max_attempts=8,
            turn_speed=None,
            settle_sec=0.35,
        ):
            super().__init__()
            self.min_turn_deg = float(min_turn_deg)
            self.centered_tolerance_px = float(centered_tolerance_px)
            self.turn_gain_deg_per_px = float(turn_gain_deg_per_px)
            self.max_turn_deg = float(max_turn_deg)
            self.max_attempts = int(max_attempts)
            self.turn_speed = turn_speed
            self.settle_sec = float(settle_sec)
            self.attempt_index = 0
            self.angle_deg = 0.0

        def start(self, event=None):
            super().start(event)
            self.attempt_index = 0
            self._attempt_alignment()

        def complete(self, actuator=None):
            self.unlock_held_actuators()
            if not self.running:
                return
            self.robot.loop.call_later(self.settle_sec, self._attempt_alignment)

        def _attempt_alignment(self):
            if not self.running:
                return
            tag_id = getattr(self.parent, "tracked_tag_id", None)
            if tag_id is None:
                self.post_failure()
                return

            world_obj = self.get_object_from_spec(_tag_spec(tag_id))
            if world_obj is not None and getattr(world_obj, "is_visible", False):
                dx = world_obj.pose.x - self.robot.pose.x
                dy = world_obj.pose.y - self.robot.pose.y
                angle = wrap_angle(atan2(dy, dx) - self.robot.pose.theta)
                self.angle_deg = angle * 180.0 / pi
                if abs(self.angle_deg) < self.min_turn_deg:
                    print(f"follow tag: AprilTag {tag_id} already centered by world-map bearing")
                    self.post_completion()
                    return
                self._dispatch_turn(self.angle_deg, f"world-map AprilTag {tag_id}")
                return

            ai_tag, reason = _best_ai_tag(self.robot, tag_id)
            if ai_tag is None:
                print(f"follow tag: lost AprilTag {tag_id} during aim ({reason})")
                self.post_failure()
                return

            pixel_error = _object_center_x(ai_tag) - AIVISION_FRAME_CENTER_X
            if abs(pixel_error) <= self.centered_tolerance_px:
                print(f"follow tag: AprilTag {tag_id} centered in AI vision")
                self.post_completion()
                return

            turn_deg = min(self.max_turn_deg, max(self.min_turn_deg, abs(pixel_error) * self.turn_gain_deg_per_px))
            signed_turn_deg = -turn_deg if pixel_error > 0 else turn_deg
            self._dispatch_turn(signed_turn_deg, f"AI vision pixel error {pixel_error:.1f}")

        def _dispatch_turn(self, angle_deg, reason):
            if self.attempt_index >= self.max_attempts:
                print(f"follow tag: could not finish centering after {self.max_attempts} attempts")
                self.post_failure()
                return
            self.attempt_index += 1
            self.angle_deg = float(angle_deg)
            print(f"follow tag: turning {self.angle_deg:.1f} degrees from {reason}")
            self.robot.actuators["drive"].turn(self, self.angle_deg * pi / 180.0, self.turn_speed)

    def setup(self):
        acquire = (
            self.SearchForTrackedTag(step_deg=self.step_deg, max_turns=self.max_search_turns)
            .set_name("acquire")
            .set_parent(self)
        )
        announce = Say("Tracking the tag").set_name("announce").set_parent(self)
        track = self.AimTrackedTag(5.0).set_name("track").set_parent(self)
        wait = StateNode().set_name("wait").set_parent(self)
        reacquire = (
            self.SearchForTrackedTag(step_deg=self.step_deg, max_turns=self.max_search_turns)
            .set_name("reacquire")
            .set_parent(self)
        )
        give_up = Say("I couldn't find the tag after two full circles").set_name("give_up").set_parent(self)
        parentfails1 = ParentFails().set_name("parentfails1").set_parent(self)

        successtrans1 = SuccessTrans().set_name("successtrans1")
        successtrans1.add_sources(acquire).add_destinations(announce)

        failuretrans1 = FailureTrans().set_name("failuretrans1")
        failuretrans1.add_sources(acquire).add_destinations(give_up)

        completiontrans1 = CompletionTrans().set_name("completiontrans1")
        completiontrans1.add_sources(announce).add_destinations(wait)

        timertrans1 = TimerTrans(0.2).set_name("timertrans1")
        timertrans1.add_sources(wait).add_destinations(track)

        completiontrans2 = CompletionTrans().set_name("completiontrans2")
        completiontrans2.add_sources(track).add_destinations(wait)

        failuretrans2 = FailureTrans().set_name("failuretrans2")
        failuretrans2.add_sources(track).add_destinations(reacquire)

        successtrans2 = SuccessTrans().set_name("successtrans2")
        successtrans2.add_sources(reacquire).add_destinations(wait)

        failuretrans3 = FailureTrans().set_name("failuretrans3")
        failuretrans3.add_sources(reacquire).add_destinations(give_up)

        completiontrans3 = CompletionTrans().set_name("completiontrans3")
        completiontrans3.add_sources(give_up).add_destinations(parentfails1)

        return self
