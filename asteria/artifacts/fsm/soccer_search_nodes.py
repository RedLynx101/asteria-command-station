from __future__ import annotations

from math import atan2, pi
import re

from aim_fsm import *
from aim_fsm.geometry import wrap_angle
from aim_fsm import vex


BALL_SPEC = r"^(Ball|SportsBall)(?:\.[a-z]+)?$"
TAG0_SPEC = r"^AprilTag-0(?:\.[a-z]+)?$"
SEARCH_STEP_DEG = 30.0
SEARCH_TURN_COUNT = 12
AIVISION_FRAME_CENTER_X = 160.0
HELD_BALL_MIN_CX = 105.0
HELD_BALL_MAX_CX = 215.0
HELD_BALL_MIN_Y = 135.0
TAG0_ID = 0
TAG0_AIM_TOLERANCE_PX = 18.0
TAG0_AIM_GAIN_DEG_PER_PX = 0.22
TAG0_AIM_MAX_TURN_DEG = 14.0


def _ai_snapshot(robot, descriptor_attr):
    robot0 = getattr(robot, "robot0", None)
    if robot0 is None:
        return None, "robot0 unavailable"
    aiv = getattr(robot0, "aiv", None)
    if aiv is None:
        return None, "AI vision unavailable"
    descriptor = getattr(aiv, descriptor_attr, None)
    take_snapshot = getattr(aiv, "take_snapshot", None)
    if descriptor is None or not callable(take_snapshot):
        return None, f"AI vision {descriptor_attr} snapshot unavailable"
    try:
        return list(take_snapshot(descriptor)), None
    except Exception as exc:
        return None, f"AI snapshot error: {exc}"


def _best_ai_tag(robot, tag_id=TAG0_ID):
    objects, error = _ai_snapshot(robot, "ALL_TAGS")
    if error:
        return None, error
    matches = []
    for obj in objects:
        try:
            obj_id = int(getattr(obj, "id", -1))
        except Exception:
            obj_id = -1
        if obj_id != int(tag_id):
            continue
        matches.append(obj)
    if not matches:
        return None, f"AprilTag {tag_id} not visible in AI vision"
    best_match = max(
        matches,
        key=lambda obj: float(getattr(obj, "width", 0.0)) * float(getattr(obj, "height", 0.0)),
    )
    return best_match, f"AI vision AprilTag {tag_id}"


def _object_center_x(obj):
    return float(getattr(obj, "originX", 0.0)) + float(getattr(obj, "width", 0.0)) / 2.0


class SearchForVisibleObject(ActionNode, ObjectSpecNode):
    """Turn in place through a full sweep until a visible world-map match appears."""

    def __init__(
        self,
        object_spec,
        label,
        step_deg=SEARCH_STEP_DEG,
        max_turns=SEARCH_TURN_COUNT,
        turn_speed=None,
        settle_sec=0.35,
    ):
        super().__init__()
        self.object_spec = object_spec
        self.label = label
        self.step_deg = float(step_deg)
        self.max_turns = int(max_turns)
        self.turn_speed = turn_speed
        self.settle_sec = float(settle_sec)
        self.turns_completed = 0
        self.found_object = None

    def start(self, event=None):
        super().start(event)
        if self.object_spec is None:
            self.post_failure()
            return
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
        obj = self.get_object_from_spec(self.object_spec)
        if obj is None:
            print(f"{self.label}: no match visible during {phase}")
            return False
        if not getattr(obj, "is_visible", False):
            print(f"{self.label}: matched {obj.id or obj.name}, but it is not visible during {phase}")
            return False
        self.found_object = obj
        print(f"{self.label}: found {obj.id or obj.name} during {phase}")
        self.post_success()
        return True

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


class SearchForAprilTag0(ActionNode, ObjectSpecNode):
    """Turn in place through a full sweep until AprilTag 0 is visible in either surface."""

    def __init__(
        self,
        step_deg=SEARCH_STEP_DEG,
        max_turns=SEARCH_TURN_COUNT,
        turn_speed=None,
        settle_sec=0.45,
    ):
        super().__init__()
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
        world_obj = self.get_object_from_spec(TAG0_SPEC)
        if world_obj is not None and getattr(world_obj, "is_visible", False):
            self.found_object = world_obj
            print(f"AprilTag 0: found {world_obj.id or world_obj.name} in world map during {phase}")
            self.post_success()
            return True
        ai_tag, reason = _best_ai_tag(self.robot, TAG0_ID)
        if ai_tag is not None:
            self.found_object = ai_tag
            print(f"AprilTag 0: found tag {getattr(ai_tag, 'id', TAG0_ID)} in AI vision during {phase}")
            self.post_success()
            return True
        print(f"AprilTag 0: no visible tag during {phase} ({reason})")
        return False

    def _begin_turn(self):
        if not self.running:
            return
        if self.turns_completed >= self.max_turns:
            print("AprilTag 0: not found after a full circle search")
            self.post_failure()
            return
        print(
            f"AprilTag 0: search turn {self.turns_completed + 1}/{self.max_turns} "
            f"by {self.step_deg:.1f} degrees"
        )
        self.robot.actuators["drive"].turn(self, self.step_deg * pi / 180.0, self.turn_speed)


class TurnTowardIfNeeded(TurnToward):
    def __init__(self, object_spec=None, min_turn_deg=5.0):
        super().__init__(object_spec)
        self.min_turn_deg = min_turn_deg

    def start(self, event=None):
        if isinstance(event, DataEvent):
            spec = event.data
        else:
            spec = self.object_spec
        StateNode.start(self, event)
        if spec is None:
            self.post_failure()
            return
        obj = self.get_object_from_spec(spec)
        if obj is None:
            self.post_failure()
            return
        dx = obj.pose.x - self.robot.pose.x
        dy = obj.pose.y - self.robot.pose.y
        angle = wrap_angle(atan2(dy, dx) - self.robot.pose.theta)
        self.angle_deg = angle * 180.0 / pi
        if abs(self.angle_deg) < self.min_turn_deg:
            print(f"aim: {obj.id or obj.name} already within {self.min_turn_deg:.1f} degrees")
            self.post_completion()
            return
        self.robot.actuators["drive"].turn(self, angle, self.turn_speed)


class TurnTowardAprilTag0IfNeeded(ActionNode, ObjectSpecNode):
    """Aim toward AprilTag 0, preferring the world map but falling back to direct AI centering."""

    def __init__(
        self,
        min_turn_deg=5.0,
        centered_tolerance_px=TAG0_AIM_TOLERANCE_PX,
        turn_gain_deg_per_px=TAG0_AIM_GAIN_DEG_PER_PX,
        max_turn_deg=TAG0_AIM_MAX_TURN_DEG,
        max_attempts=8,
        turn_speed=None,
        settle_sec=0.35,
        retry_sec=0.25,
    ):
        super().__init__()
        self.min_turn_deg = float(min_turn_deg)
        self.centered_tolerance_px = float(centered_tolerance_px)
        self.turn_gain_deg_per_px = float(turn_gain_deg_per_px)
        self.max_turn_deg = float(max_turn_deg)
        self.max_attempts = int(max_attempts)
        self.turn_speed = turn_speed
        self.settle_sec = float(settle_sec)
        self.retry_sec = float(retry_sec)
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

        world_obj = self.get_object_from_spec(TAG0_SPEC)
        if world_obj is not None and getattr(world_obj, "is_visible", False):
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

        ai_tag, reason = _best_ai_tag(self.robot, TAG0_ID)
        if ai_tag is None:
            if self.attempt_index >= self.max_attempts:
                print(f"aim: could not reacquire AprilTag 0 ({reason})")
                self.post_failure()
                return
            self.attempt_index += 1
            print(f"aim: waiting for AprilTag 0 visibility ({reason})")
            self.robot.loop.call_later(self.retry_sec, self._attempt_alignment)
            return

        pixel_error = _object_center_x(ai_tag) - AIVISION_FRAME_CENTER_X
        if abs(pixel_error) <= self.centered_tolerance_px:
            print(f"aim: AprilTag 0 centered in AI vision within {self.centered_tolerance_px:.1f} px")
            self.post_completion()
            return

        turn_deg = min(self.max_turn_deg, max(self.min_turn_deg, abs(pixel_error) * self.turn_gain_deg_per_px))
        signed_turn_deg = -turn_deg if pixel_error > 0 else turn_deg
        self._dispatch_turn(signed_turn_deg, f"AI vision pixel error {pixel_error:.1f}")

    def _dispatch_turn(self, angle_deg, reason):
        if self.attempt_index >= self.max_attempts:
            print(f"aim: AprilTag 0 still not aligned after {self.max_attempts} attempts")
            self.post_failure()
            return
        self.attempt_index += 1
        self.angle_deg = float(angle_deg)
        print(f"aim: turning {self.angle_deg:.1f} degrees from {reason}")
        self.robot.actuators["drive"].turn(self, self.angle_deg * pi / 180.0, self.turn_speed)


class RequireHeldBall(StateNode):
    def __init__(self, attempts=4, retry_sec=0.25):
        super().__init__()
        self.attempts = int(attempts)
        self.retry_sec = float(retry_sec)
        self.attempt_index = 0

    def start(self, event=None):
        super().start(event)
        self.attempt_index = 0
        self._check_or_retry()

    def _check_or_retry(self):
        if not self.running:
            return
        secured, reason = self._is_soccer_ball_secured()
        if secured:
            print(f"ball hold check: soccer ball is secured ({reason})")
            self.post_success()
            return
        self.attempt_index += 1
        if self.attempt_index >= self.attempts:
            print(f"ball hold check: robot is not holding the soccer ball ({reason})")
            self.post_failure()
            return
        print(
            f"ball hold check: attempt {self.attempt_index}/{self.attempts} did not confirm hold "
            f"({reason}); retrying"
        )
        self.robot.loop.call_later(self.retry_sec, self._check_or_retry)

    def _is_soccer_ball_secured(self):
        held = getattr(self.robot, "holding", None)
        held_name = getattr(held, "name", "")
        if re.match(BALL_SPEC, held_name):
            return True, f"world map says {held_name}"

        robot0 = getattr(self.robot, "robot0", None)
        if robot0 is None:
            return False, "robot0 unavailable"

        try:
            if robot0.has_ball():
                return True, "robot0.has_ball()"
        except Exception as exc:
            return False, f"has_ball error: {exc}"

        aiv = getattr(robot0, "aiv", None)
        all_aiobjs = getattr(aiv, "ALL_AIOBJS", None)
        take_snapshot = getattr(aiv, "take_snapshot", None)
        if aiv is None or all_aiobjs is None or not callable(take_snapshot):
            return False, "AI vision snapshot unavailable"

        try:
            ai_objects = list(take_snapshot(all_aiobjs))
        except Exception as exc:
            return False, f"AI snapshot error: {exc}"

        best_match = None
        best_score = None
        for obj in ai_objects:
            classname = getattr(obj, "classname", "")
            if classname not in ("Ball", "SportsBall"):
                continue
            cx = float(getattr(obj, "originX", 0.0)) + float(getattr(obj, "width", 0.0)) / 2.0
            origin_y = float(getattr(obj, "originY", 0.0))
            if not (HELD_BALL_MIN_CX <= cx <= HELD_BALL_MAX_CX and origin_y >= HELD_BALL_MIN_Y):
                continue
            score = abs(cx - 160.0) + max(0.0, HELD_BALL_MIN_Y - origin_y)
            if best_score is None or score < best_score:
                best_score = score
                best_match = obj

        if best_match is not None:
            return True, f"AI vision centered {best_match.classname}"

        return False, "no centered held-ball detection"


class AcquireSoccerBall(StateNode):
    def setup(self):
        search_ball = SearchForVisibleObject(BALL_SPEC, "soccer ball").set_name("search_ball").set_parent(self)
        pickup_ball = PickUp(BALL_SPEC).set_name("pickup_ball").set_parent(self)
        settle_after_pickup = StateNode().set_name("settle_after_pickup").set_parent(self)
        verify_ball = RequireHeldBall().set_name("verify_ball").set_parent(self)
        announce_missing_ball = (
            Say("I could not find the soccer ball after a full circle")
            .set_name("announce_missing_ball")
            .set_parent(self)
        )
        announce_pickup_failed = (
            Say("I could not drive in and touch the soccer ball")
            .set_name("announce_pickup_failed")
            .set_parent(self)
        )
        announce_verify_failed = (
            Say("I touched the soccer ball but did not secure it")
            .set_name("announce_verify_failed")
            .set_parent(self)
        )
        parentcompletes1 = ParentCompletes().set_name("parentcompletes1").set_parent(self)
        parentfails1 = ParentFails().set_name("parentfails1").set_parent(self)

        successtrans1 = SuccessTrans().set_name("successtrans1")
        successtrans1.add_sources(search_ball).add_destinations(pickup_ball)

        failuretrans1 = FailureTrans().set_name("failuretrans1")
        failuretrans1.add_sources(search_ball).add_destinations(announce_missing_ball)

        completiontrans1 = CompletionTrans().set_name("completiontrans1")
        completiontrans1.add_sources(pickup_ball).add_destinations(settle_after_pickup)

        failuretrans2 = FailureTrans().set_name("failuretrans2")
        failuretrans2.add_sources(pickup_ball).add_destinations(announce_pickup_failed)

        timertrans1 = TimerTrans(0.4).set_name("timertrans1")
        timertrans1.add_sources(settle_after_pickup).add_destinations(verify_ball)

        successtrans2 = SuccessTrans().set_name("successtrans2")
        successtrans2.add_sources(verify_ball).add_destinations(parentcompletes1)

        failuretrans3 = FailureTrans().set_name("failuretrans3")
        failuretrans3.add_sources(verify_ball).add_destinations(announce_verify_failed)

        completiontrans2 = CompletionTrans().set_name("completiontrans2")
        completiontrans2.add_sources(announce_missing_ball).add_destinations(parentfails1)

        completiontrans3 = CompletionTrans().set_name("completiontrans3")
        completiontrans3.add_sources(announce_pickup_failed).add_destinations(parentfails1)

        completiontrans4 = CompletionTrans().set_name("completiontrans4")
        completiontrans4.add_sources(announce_verify_failed).add_destinations(parentfails1)

        return self


class ShootHeldBallAtTag0(StateNode):
    def setup(self):
        check_ball = RequireHeldBall().set_name("check_ball").set_parent(self)
        search_tag = SearchForAprilTag0().set_name("search_tag").set_parent(self)
        aim_tag = TurnTowardAprilTag0IfNeeded(5.0).set_name("aim_tag").set_parent(self)
        settle_before_kick = StateNode().set_name("settle_before_kick").set_parent(self)
        kick_ball = Kick(vex.KickType.HARD).set_name("kick_ball").set_parent(self)
        announce_no_ball = Say("I am not holding the soccer ball").set_name("announce_no_ball").set_parent(self)
        announce_missing_tag = (
            Say("I could not find AprilTag 0 after a full circle")
            .set_name("announce_missing_tag")
            .set_parent(self)
        )
        announce_aim_failed = (
            Say("I could not aim at AprilTag 0")
            .set_name("announce_aim_failed")
            .set_parent(self)
        )
        announce_kick_failed = (
            Say("I could not kick the ball")
            .set_name("announce_kick_failed")
            .set_parent(self)
        )
        parentcompletes1 = ParentCompletes().set_name("parentcompletes1").set_parent(self)
        parentfails1 = ParentFails().set_name("parentfails1").set_parent(self)

        successtrans1 = SuccessTrans().set_name("successtrans1")
        successtrans1.add_sources(check_ball).add_destinations(search_tag)

        failuretrans1 = FailureTrans().set_name("failuretrans1")
        failuretrans1.add_sources(check_ball).add_destinations(announce_no_ball)

        successtrans2 = SuccessTrans().set_name("successtrans2")
        successtrans2.add_sources(search_tag).add_destinations(aim_tag)

        failuretrans2 = FailureTrans().set_name("failuretrans2")
        failuretrans2.add_sources(search_tag).add_destinations(announce_missing_tag)

        completiontrans1 = CompletionTrans().set_name("completiontrans1")
        completiontrans1.add_sources(aim_tag).add_destinations(settle_before_kick)

        failuretrans3 = FailureTrans().set_name("failuretrans3")
        failuretrans3.add_sources(aim_tag).add_destinations(announce_aim_failed)

        timertrans1 = TimerTrans(0.2).set_name("timertrans1")
        timertrans1.add_sources(settle_before_kick).add_destinations(kick_ball)

        completiontrans2 = CompletionTrans().set_name("completiontrans2")
        completiontrans2.add_sources(kick_ball).add_destinations(parentcompletes1)

        failuretrans4 = FailureTrans().set_name("failuretrans4")
        failuretrans4.add_sources(kick_ball).add_destinations(announce_kick_failed)

        completiontrans3 = CompletionTrans().set_name("completiontrans3")
        completiontrans3.add_sources(announce_no_ball).add_destinations(parentfails1)

        completiontrans4 = CompletionTrans().set_name("completiontrans4")
        completiontrans4.add_sources(announce_missing_tag).add_destinations(parentfails1)

        completiontrans5 = CompletionTrans().set_name("completiontrans5")
        completiontrans5.add_sources(announce_aim_failed).add_destinations(parentfails1)

        completiontrans6 = CompletionTrans().set_name("completiontrans6")
        completiontrans6.add_sources(announce_kick_failed).add_destinations(parentfails1)

        return self
