from aim_fsm import *
from datetime import datetime
import json
from pathlib import Path

import cv2
import numpy as np

from soccer_search_nodes import _ai_snapshot


SCAN_HEADINGS = (
    ("front_000", 0),
    ("front_right_060", 60),
    ("back_right_120", 120),
    ("back_180", 180),
    ("back_left_240", 240),
    ("front_left_300", 300),
)


def _round_or_none(value, digits=1):
    try:
        return round(float(value), digits)
    except Exception:
        return None


def _string_or_none(value):
    if value is None:
        return None
    text = str(value)
    return text or None


def _robot_pose_snapshot(robot):
    pose = getattr(robot, "pose", None)
    if pose is None:
        return {}
    return {
        "x": _round_or_none(getattr(pose, "x", None)),
        "y": _round_or_none(getattr(pose, "y", None)),
        "heading_deg": _round_or_none(getattr(pose, "theta", 0.0) * 180.0 / np.pi, 2),
    }


def _visible_world_objects(robot):
    world_map = getattr(robot, "world_map", None)
    if world_map is None:
        return []
    objects = []
    for obj in getattr(world_map, "objects", {}).values():
        if not getattr(obj, "is_visible", False):
            continue
        pose = getattr(obj, "pose", None)
        objects.append(
            {
                "id": _string_or_none(getattr(obj, "id", None)),
                "name": _string_or_none(getattr(obj, "name", None)),
                "kind": _string_or_none(obj.__class__.__name__),
                "x": _round_or_none(getattr(pose, "x", None)),
                "y": _round_or_none(getattr(pose, "y", None)),
            }
        )
    objects.sort(key=lambda item: ((item.get("name") or ""), (item.get("id") or "")))
    return objects


def _snapshot_tags(robot):
    objects, error = _ai_snapshot(robot, "ALL_TAGS")
    if error:
        return [], error
    tags = []
    for obj in objects:
        width = _round_or_none(getattr(obj, "width", None))
        height = _round_or_none(getattr(obj, "height", None))
        area = None if width is None or height is None else round(width * height, 1)
        tags.append(
            {
                "id": int(getattr(obj, "id", -1)),
                "origin_x": _round_or_none(getattr(obj, "originX", None)),
                "origin_y": _round_or_none(getattr(obj, "originY", None)),
                "width": width,
                "height": height,
                "area": area,
            }
        )
    tags.sort(key=lambda item: (-(item.get("area") or 0.0), item.get("id", -1)))
    return tags, None


def _snapshot_cargo(robot):
    objects, error = _ai_snapshot(robot, "ALL_CARGO")
    if error:
        return [], error
    cargo = []
    for obj in objects:
        width = _round_or_none(getattr(obj, "width", None))
        height = _round_or_none(getattr(obj, "height", None))
        area = None if width is None or height is None else round(width * height, 1)
        cargo.append(
            {
                "classname": _string_or_none(getattr(obj, "classname", None)),
                "origin_x": _round_or_none(getattr(obj, "originX", None)),
                "origin_y": _round_or_none(getattr(obj, "originY", None)),
                "width": width,
                "height": height,
                "area": area,
            }
        )
    cargo.sort(key=lambda item: (-(item.get("area") or 0.0), (item.get("classname") or "")))
    return cargo, None


class SceneInventoryScan(StateMachineProgram):
    # A richer variant of area_context_scan that writes a machine-readable inventory
    # manifest for later host-side reasoning, not just a folder of images.
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.scan_root = None
        self.scan_run_dir = None
        self.scan_manifest_path = None
        self.scan_views = []
        self.scan_started_at = None

    class PrepareScan(StateNode):
        def start(self, event=None):
            super().start(event)
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            images_root = Path(__file__).resolve().parents[1] / "images"
            scan_root = images_root / "scene_inventory_scan"
            run_dir = scan_root / stamp
            run_dir.mkdir(parents=True, exist_ok=True)
            self.parent.scan_root = scan_root
            self.parent.scan_run_dir = run_dir
            self.parent.scan_manifest_path = scan_root / "latest_scene_inventory_scan.json"
            self.parent.scan_views = []
            self.parent.scan_started_at = datetime.now().isoformat(timespec="seconds")
            print(f"Prepared scene inventory scan directory: {run_dir}")
            self.post_completion()

    class CaptureInventoryView(StateNode):
        def __init__(self, label, heading_deg):
            super().__init__()
            self.label = label
            self.heading_deg = heading_deg

        def start(self, event=None):
            super().start(event)
            world = getattr(self.robot, "world", None)
            latest_image = getattr(world, "latest_image", None)
            raw_image = getattr(latest_image, "raw_image", None)
            if raw_image is None or self.parent.scan_run_dir is None:
                print(f"Scene inventory capture failed for {self.label}: no camera frame available.")
                self.post_failure()
                return

            image = np.array(raw_image)
            image_index = len(self.parent.scan_views)
            image_path = self.parent.scan_run_dir / f"{image_index:02d}_{self.label}.jpg"
            ok = cv2.imwrite(str(image_path), cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
            if not ok:
                print(f"Scene inventory capture failed for {self.label}: cv2.imwrite returned False.")
                self.post_failure()
                return

            ai_tags, ai_tags_error = _snapshot_tags(self.robot)
            ai_cargo, ai_cargo_error = _snapshot_cargo(self.robot)
            record = {
                "index": image_index,
                "label": self.label,
                "heading_deg": self.heading_deg,
                "path": str(image_path),
                "captured_at": datetime.now().isoformat(timespec="seconds"),
                "robot_pose": _robot_pose_snapshot(self.robot),
                "world_visible_objects": _visible_world_objects(self.robot),
                "ai_tags": ai_tags,
                "ai_cargo": ai_cargo,
            }
            if ai_tags_error or ai_cargo_error:
                record["ai_errors"] = {
                    "tags": ai_tags_error,
                    "cargo": ai_cargo_error,
                }
            self.parent.scan_views.append(record)
            print(f"Saved scene inventory view {self.label} to {image_path}")
            self.post_completion()

    class WriteManifest(StateNode):
        def start(self, event=None):
            super().start(event)
            if self.parent.scan_run_dir is None or self.parent.scan_manifest_path is None:
                print("Scene inventory manifest failed: scan directories were not prepared.")
                self.post_failure()
                return

            world_names = sorted(
                {
                    item.get("id") or item.get("name")
                    for view in self.parent.scan_views
                    for item in view.get("world_visible_objects", [])
                    if item.get("id") or item.get("name")
                }
            )
            tag_ids = sorted(
                {
                    int(item.get("id"))
                    for view in self.parent.scan_views
                    for item in view.get("ai_tags", [])
                    if item.get("id") is not None and int(item.get("id")) >= 0
                }
            )
            cargo_classes = sorted(
                {
                    item.get("classname")
                    for view in self.parent.scan_views
                    for item in view.get("ai_cargo", [])
                    if item.get("classname")
                }
            )

            manifest = {
                "kind": "scene_inventory_scan",
                "created_at": self.parent.scan_started_at,
                "run_dir": str(self.parent.scan_run_dir),
                "count": len(self.parent.scan_views),
                "aggregate": {
                    "world_visible_names": world_names,
                    "ai_tag_ids": tag_ids,
                    "ai_cargo_classes": cargo_classes,
                },
                "views": self.parent.scan_views,
                "notes": [
                    "This scan is for later host-side review and agent planning, not as a guarantee that every object classification is correct.",
                    "World-map entries and direct AI snapshots are both stored because either surface can be more useful depending on the task.",
                ],
            }

            run_manifest = self.parent.scan_run_dir / "manifest.json"
            run_manifest.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            self.parent.scan_manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            print(f"Wrote scene inventory manifest to {run_manifest}")
            print(f"Updated latest scene inventory manifest at {self.parent.scan_manifest_path}")
            self.post_completion()

    def setup(self):
        #     start: self.PrepareScan() =C=> announce
        # 
        #     announce: Say("Starting scene inventory scan") =C=> settle_front
        # 
        #     settle_front: StateNode() =T(1.0)=> capture_front
        #     capture_front: self.CaptureInventoryView("front_000", 0)
        #     capture_front =C=> turn_1
        #     capture_front =F=> failed
        # 
        #     turn_1: Turn(60) =C=> settle_front_right
        #     settle_front_right: StateNode() =T(0.8)=> capture_front_right
        #     capture_front_right: self.CaptureInventoryView("front_right_060", 60)
        #     capture_front_right =C=> turn_2
        #     capture_front_right =F=> failed
        # 
        #     turn_2: Turn(60) =C=> settle_back_right
        #     settle_back_right: StateNode() =T(0.8)=> capture_back_right
        #     capture_back_right: self.CaptureInventoryView("back_right_120", 120)
        #     capture_back_right =C=> turn_3
        #     capture_back_right =F=> failed
        # 
        #     turn_3: Turn(60) =C=> settle_back
        #     settle_back: StateNode() =T(0.8)=> capture_back
        #     capture_back: self.CaptureInventoryView("back_180", 180)
        #     capture_back =C=> turn_4
        #     capture_back =F=> failed
        # 
        #     turn_4: Turn(60) =C=> settle_back_left
        #     settle_back_left: StateNode() =T(0.8)=> capture_back_left
        #     capture_back_left: self.CaptureInventoryView("back_left_240", 240)
        #     capture_back_left =C=> turn_5
        #     capture_back_left =F=> failed
        # 
        #     turn_5: Turn(60) =C=> settle_front_left
        #     settle_front_left: StateNode() =T(0.8)=> capture_front_left
        #     capture_front_left: self.CaptureInventoryView("front_left_300", 300)
        #     capture_front_left =C=> turn_6
        #     capture_front_left =F=> failed
        # 
        #     turn_6: Turn(60) =C=> write_manifest
        # 
        #     write_manifest: self.WriteManifest()
        #     write_manifest =C=> done
        #     write_manifest =F=> failed
        # 
        #     done: Say("Scene inventory scan complete")
        #     failed: Say("Scene inventory scan failed")
        
        # Code generated by genfsm on Mon Apr 20 16:30:53 2026:
        
        start = self.PrepareScan() .set_name("start") .set_parent(self)
        announce = Say("Starting scene inventory scan") .set_name("announce") .set_parent(self)
        settle_front = StateNode() .set_name("settle_front") .set_parent(self)
        capture_front = self.CaptureInventoryView("front_000", 0) .set_name("capture_front") .set_parent(self)
        turn_1 = Turn(60) .set_name("turn_1") .set_parent(self)
        settle_front_right = StateNode() .set_name("settle_front_right") .set_parent(self)
        capture_front_right = self.CaptureInventoryView("front_right_060", 60) .set_name("capture_front_right") .set_parent(self)
        turn_2 = Turn(60) .set_name("turn_2") .set_parent(self)
        settle_back_right = StateNode() .set_name("settle_back_right") .set_parent(self)
        capture_back_right = self.CaptureInventoryView("back_right_120", 120) .set_name("capture_back_right") .set_parent(self)
        turn_3 = Turn(60) .set_name("turn_3") .set_parent(self)
        settle_back = StateNode() .set_name("settle_back") .set_parent(self)
        capture_back = self.CaptureInventoryView("back_180", 180) .set_name("capture_back") .set_parent(self)
        turn_4 = Turn(60) .set_name("turn_4") .set_parent(self)
        settle_back_left = StateNode() .set_name("settle_back_left") .set_parent(self)
        capture_back_left = self.CaptureInventoryView("back_left_240", 240) .set_name("capture_back_left") .set_parent(self)
        turn_5 = Turn(60) .set_name("turn_5") .set_parent(self)
        settle_front_left = StateNode() .set_name("settle_front_left") .set_parent(self)
        capture_front_left = self.CaptureInventoryView("front_left_300", 300) .set_name("capture_front_left") .set_parent(self)
        turn_6 = Turn(60) .set_name("turn_6") .set_parent(self)
        write_manifest = self.WriteManifest() .set_name("write_manifest") .set_parent(self)
        done = Say("Scene inventory scan complete") .set_name("done") .set_parent(self)
        failed = Say("Scene inventory scan failed") .set_name("failed") .set_parent(self)
        
        completiontrans1 = CompletionTrans() .set_name("completiontrans1")
        completiontrans1 .add_sources(start) .add_destinations(announce)
        
        completiontrans2 = CompletionTrans() .set_name("completiontrans2")
        completiontrans2 .add_sources(announce) .add_destinations(settle_front)
        
        timertrans1 = TimerTrans(1.0) .set_name("timertrans1")
        timertrans1 .add_sources(settle_front) .add_destinations(capture_front)
        
        completiontrans3 = CompletionTrans() .set_name("completiontrans3")
        completiontrans3 .add_sources(capture_front) .add_destinations(turn_1)
        
        failuretrans1 = FailureTrans() .set_name("failuretrans1")
        failuretrans1 .add_sources(capture_front) .add_destinations(failed)
        
        completiontrans4 = CompletionTrans() .set_name("completiontrans4")
        completiontrans4 .add_sources(turn_1) .add_destinations(settle_front_right)
        
        timertrans2 = TimerTrans(0.8) .set_name("timertrans2")
        timertrans2 .add_sources(settle_front_right) .add_destinations(capture_front_right)
        
        completiontrans5 = CompletionTrans() .set_name("completiontrans5")
        completiontrans5 .add_sources(capture_front_right) .add_destinations(turn_2)
        
        failuretrans2 = FailureTrans() .set_name("failuretrans2")
        failuretrans2 .add_sources(capture_front_right) .add_destinations(failed)
        
        completiontrans6 = CompletionTrans() .set_name("completiontrans6")
        completiontrans6 .add_sources(turn_2) .add_destinations(settle_back_right)
        
        timertrans3 = TimerTrans(0.8) .set_name("timertrans3")
        timertrans3 .add_sources(settle_back_right) .add_destinations(capture_back_right)
        
        completiontrans7 = CompletionTrans() .set_name("completiontrans7")
        completiontrans7 .add_sources(capture_back_right) .add_destinations(turn_3)
        
        failuretrans3 = FailureTrans() .set_name("failuretrans3")
        failuretrans3 .add_sources(capture_back_right) .add_destinations(failed)
        
        completiontrans8 = CompletionTrans() .set_name("completiontrans8")
        completiontrans8 .add_sources(turn_3) .add_destinations(settle_back)
        
        timertrans4 = TimerTrans(0.8) .set_name("timertrans4")
        timertrans4 .add_sources(settle_back) .add_destinations(capture_back)
        
        completiontrans9 = CompletionTrans() .set_name("completiontrans9")
        completiontrans9 .add_sources(capture_back) .add_destinations(turn_4)
        
        failuretrans4 = FailureTrans() .set_name("failuretrans4")
        failuretrans4 .add_sources(capture_back) .add_destinations(failed)
        
        completiontrans10 = CompletionTrans() .set_name("completiontrans10")
        completiontrans10 .add_sources(turn_4) .add_destinations(settle_back_left)
        
        timertrans5 = TimerTrans(0.8) .set_name("timertrans5")
        timertrans5 .add_sources(settle_back_left) .add_destinations(capture_back_left)
        
        completiontrans11 = CompletionTrans() .set_name("completiontrans11")
        completiontrans11 .add_sources(capture_back_left) .add_destinations(turn_5)
        
        failuretrans5 = FailureTrans() .set_name("failuretrans5")
        failuretrans5 .add_sources(capture_back_left) .add_destinations(failed)
        
        completiontrans12 = CompletionTrans() .set_name("completiontrans12")
        completiontrans12 .add_sources(turn_5) .add_destinations(settle_front_left)
        
        timertrans6 = TimerTrans(0.8) .set_name("timertrans6")
        timertrans6 .add_sources(settle_front_left) .add_destinations(capture_front_left)
        
        completiontrans13 = CompletionTrans() .set_name("completiontrans13")
        completiontrans13 .add_sources(capture_front_left) .add_destinations(turn_6)
        
        failuretrans6 = FailureTrans() .set_name("failuretrans6")
        failuretrans6 .add_sources(capture_front_left) .add_destinations(failed)
        
        completiontrans14 = CompletionTrans() .set_name("completiontrans14")
        completiontrans14 .add_sources(turn_6) .add_destinations(write_manifest)
        
        completiontrans15 = CompletionTrans() .set_name("completiontrans15")
        completiontrans15 .add_sources(write_manifest) .add_destinations(done)
        
        failuretrans7 = FailureTrans() .set_name("failuretrans7")
        failuretrans7 .add_sources(write_manifest) .add_destinations(failed)
        
        return self
