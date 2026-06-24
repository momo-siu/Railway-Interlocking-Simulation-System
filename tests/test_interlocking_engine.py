import os
import sys
import unittest
from PyQt5.QtCore import QCoreApplication

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from logic.interlocking_engine import InterlockingEngine
from simulation.device_simulator import DeviceSimulator
from utils.state_manager import StateManager


class LogCatcher:
    def __init__(self):
        self.items = []

    def __call__(self, level, message):
        self.items.append((level, message))


class InterlockingEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if QCoreApplication.instance() is None:
            cls._app = QCoreApplication([])

    def setUp(self):
        StateManager._instance = None
        self.state = StateManager()
        self.sim = DeviceSimulator()
        self.engine = InterlockingEngine(self.sim)
        self.log = LogCatcher()
        self.state.log_signal.connect(self.log)

    def test_route_precheck_occupied_block(self):
        self.state.update_track("JXG", is_occupied=True)
        self.engine.try_set_route("X", "XII", route_type="TRAIN")
        self.assertTrue(any(level == "ERROR" and "占用" in msg for level, msg in self.log.items))
        r = self.state.routes["R_X_XII"]
        self.assertFalse(r.is_active)

    def test_conflicting_route_block(self):
        self.engine.try_set_route("X", "XII", route_type="TRAIN")
        r1 = self.state.routes["R_X_XII"]
        self.assertTrue(r1.is_active)

        self.engine.try_set_route("S", "SII", route_type="TRAIN")
        self.assertTrue(any(level == "ERROR" and "敌对进路" in msg for level, msg in self.log.items))
        r2 = self.state.routes["R_S_SII"]
        self.assertFalse(r2.is_active)

    def test_three_point_sectional_release(self):
        self.engine.try_set_route("X", "XII", route_type="TRAIN")
        self.assertTrue(self.state.tracks["JXG"].is_locked)

        self.sim.set_track_occupancy("JXG", True)
        self.sim.set_track_occupancy("IIAG", True)
        self.sim.set_track_occupancy("JXG", False)

        self.assertFalse(self.state.tracks["JXG"].is_locked)


if __name__ == "__main__":
    unittest.main()
