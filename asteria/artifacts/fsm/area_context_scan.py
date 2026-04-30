from aim_fsm import *
from datetime import datetime
import json
from pathlib import Path

import cv2
import numpy as np


class AreaContextScan(StateMachineProgram):
    # Rotates through four headings, saves each view to the Asteria image artifacts area,
    # and writes a manifest that later host-side tooling can inspect without guessing paths.
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
            scan_root = images_root / "area_context_scan"
            run_dir = scan_root / stamp
            run_dir.mkdir(parents=True, exist_ok=True)
            self.parent.scan_root = scan_root
            self.parent.scan_run_dir = run_dir
            self.parent.scan_manifest_path = scan_root / "latest_area_context_scan.json"
            self.parent.scan_views = []
            self.parent.scan_started_at = datetime.now().isoformat(timespec="seconds")
            print(f"Prepared area context scan directory: {run_dir}")
            self.post_completion()

    class CaptureView(StateNode):
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
                print(f"Area context capture failed for {self.label}: no camera frame available.")
                self.post_failure()
                return

            image = np.array(raw_image)
            image_index = len(self.parent.scan_views)
            image_path = self.parent.scan_run_dir / f"{image_index:02d}_{self.label}.jpg"
            ok = cv2.imwrite(str(image_path), cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
            if not ok:
                print(f"Area context capture failed for {self.label}: cv2.imwrite returned False.")
                self.post_failure()
                return

            record = {
                "index": image_index,
                "label": self.label,
                "heading_deg": self.heading_deg,
                "path": str(image_path),
                "captured_at": datetime.now().isoformat(timespec="seconds"),
            }
            self.parent.scan_views.append(record)
            print(f"Saved area context view {self.label} to {image_path}")
            self.post_completion()

    class WriteManifest(StateNode):
        def start(self, event=None):
            super().start(event)
            if self.parent.scan_run_dir is None or self.parent.scan_manifest_path is None:
                print("Area context manifest failed: scan directories were not prepared.")
                self.post_failure()
                return

            manifest = {
                "kind": "area_context_scan",
                "created_at": self.parent.scan_started_at,
                "run_dir": str(self.parent.scan_run_dir),
                "count": len(self.parent.scan_views),
                "views": self.parent.scan_views,
                "notes": [
                    "The robot captured four headings while rotating 90 degrees counterclockwise between views.",
                    "The host-side agent can inspect these saved images later without requiring the FSM to stay active.",
                ],
            }

            run_manifest = self.parent.scan_run_dir / "manifest.json"
            run_manifest.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            self.parent.scan_manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            print(f"Wrote area context manifest to {run_manifest}")
            print(f"Updated latest area context manifest at {self.parent.scan_manifest_path}")
            self.post_completion()

    def setup(self):
        #     start: self.PrepareScan() =C=> announce
        # 
        #     announce: Say("Starting area context scan") =C=> settle_front
        # 
        #     settle_front: StateNode() =T(1.0)=> capture_front
        #     capture_front: self.CaptureView("front_000", 0)
        #     capture_front =C=> turn_1
        #     capture_front =F=> failed
        # 
        #     turn_1: Turn(90) =C=> settle_left
        #     settle_left: StateNode() =T(0.8)=> capture_left
        #     capture_left: self.CaptureView("left_090", 90)
        #     capture_left =C=> turn_2
        #     capture_left =F=> failed
        # 
        #     turn_2: Turn(90) =C=> settle_back
        #     settle_back: StateNode() =T(0.8)=> capture_back
        #     capture_back: self.CaptureView("back_180", 180)
        #     capture_back =C=> turn_3
        #     capture_back =F=> failed
        # 
        #     turn_3: Turn(90) =C=> settle_right
        #     settle_right: StateNode() =T(0.8)=> capture_right
        #     capture_right: self.CaptureView("right_270", 270)
        #     capture_right =C=> turn_4
        #     capture_right =F=> failed
        # 
        #     turn_4: Turn(90) =C=> write_manifest
        # 
        #     write_manifest: self.WriteManifest()
        #     write_manifest =C=> done
        #     write_manifest =F=> failed
        # 
        #     done: Say("Area context scan complete")
        #     failed: Say("Area context scan failed")
        
        # Code generated by genfsm on Wed Apr 15 18:49:54 2026:
        
        start = self.PrepareScan() .set_name("start") .set_parent(self)
        announce = Say("Starting area context scan") .set_name("announce") .set_parent(self)
        settle_front = StateNode() .set_name("settle_front") .set_parent(self)
        capture_front = self.CaptureView("front_000", 0) .set_name("capture_front") .set_parent(self)
        turn_1 = Turn(90) .set_name("turn_1") .set_parent(self)
        settle_left = StateNode() .set_name("settle_left") .set_parent(self)
        capture_left = self.CaptureView("left_090", 90) .set_name("capture_left") .set_parent(self)
        turn_2 = Turn(90) .set_name("turn_2") .set_parent(self)
        settle_back = StateNode() .set_name("settle_back") .set_parent(self)
        capture_back = self.CaptureView("back_180", 180) .set_name("capture_back") .set_parent(self)
        turn_3 = Turn(90) .set_name("turn_3") .set_parent(self)
        settle_right = StateNode() .set_name("settle_right") .set_parent(self)
        capture_right = self.CaptureView("right_270", 270) .set_name("capture_right") .set_parent(self)
        turn_4 = Turn(90) .set_name("turn_4") .set_parent(self)
        write_manifest = self.WriteManifest() .set_name("write_manifest") .set_parent(self)
        done = Say("Area context scan complete") .set_name("done") .set_parent(self)
        failed = Say("Area context scan failed") .set_name("failed") .set_parent(self)
        
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
        completiontrans4 .add_sources(turn_1) .add_destinations(settle_left)
        
        timertrans2 = TimerTrans(0.8) .set_name("timertrans2")
        timertrans2 .add_sources(settle_left) .add_destinations(capture_left)
        
        completiontrans5 = CompletionTrans() .set_name("completiontrans5")
        completiontrans5 .add_sources(capture_left) .add_destinations(turn_2)
        
        failuretrans2 = FailureTrans() .set_name("failuretrans2")
        failuretrans2 .add_sources(capture_left) .add_destinations(failed)
        
        completiontrans6 = CompletionTrans() .set_name("completiontrans6")
        completiontrans6 .add_sources(turn_2) .add_destinations(settle_back)
        
        timertrans3 = TimerTrans(0.8) .set_name("timertrans3")
        timertrans3 .add_sources(settle_back) .add_destinations(capture_back)
        
        completiontrans7 = CompletionTrans() .set_name("completiontrans7")
        completiontrans7 .add_sources(capture_back) .add_destinations(turn_3)
        
        failuretrans3 = FailureTrans() .set_name("failuretrans3")
        failuretrans3 .add_sources(capture_back) .add_destinations(failed)
        
        completiontrans8 = CompletionTrans() .set_name("completiontrans8")
        completiontrans8 .add_sources(turn_3) .add_destinations(settle_right)
        
        timertrans4 = TimerTrans(0.8) .set_name("timertrans4")
        timertrans4 .add_sources(settle_right) .add_destinations(capture_right)
        
        completiontrans9 = CompletionTrans() .set_name("completiontrans9")
        completiontrans9 .add_sources(capture_right) .add_destinations(turn_4)
        
        failuretrans4 = FailureTrans() .set_name("failuretrans4")
        failuretrans4 .add_sources(capture_right) .add_destinations(failed)
        
        completiontrans10 = CompletionTrans() .set_name("completiontrans10")
        completiontrans10 .add_sources(turn_4) .add_destinations(write_manifest)
        
        completiontrans11 = CompletionTrans() .set_name("completiontrans11")
        completiontrans11 .add_sources(write_manifest) .add_destinations(done)
        
        failuretrans5 = FailureTrans() .set_name("failuretrans5")
        failuretrans5 .add_sources(write_manifest) .add_destinations(failed)
        
        return self
