from PyQt5.QtCore import QObject
from utils.state_manager import StateManager
from utils.models import RouteStage, SignalAspect, SwitchPosition
from simulation.device_simulator import DeviceSimulator
from typing import Dict, Optional, Set

class InterlockingEngine(QObject):
    def __init__(self, simulator: DeviceSimulator):
        super().__init__()
        self.state_manager = StateManager()
        self.simulator = simulator
        self._active_route_ids: Set[str] = set()
        self._route_track_ever_occupied: Dict[str, Set[str]] = {}
        self._guide_lock_enabled = False

        self.state_manager.state_changed.connect(self._on_state_changed)

    def try_set_route(self, start: str, end: str, route_type: Optional[str] = None) -> bool:
        if route_type is None:
            route_type = "SHUNTING" if start.startswith("D") else "TRAIN"

        route = self.state_manager.find_route(start, end, route_type=route_type)
        if not route:
            candidates = self.state_manager.list_routes_from_start(start, route_type=route_type)
            ends = sorted({r.end_signal for r in candidates})
            if ends:
                self.state_manager.log(
                    f"办理失败：未定义进路 {start} -> {end}（{route_type}），可选终端：{' / '.join(ends)}",
                    "ERROR",
                )
            else:
                any_type = self.state_manager.list_routes_from_start(start, route_type=None)
                if any_type:
                    types = sorted({r.type for r in any_type})
                    self.state_manager.log(
                        f"办理失败：未定义进路 {start} -> {end}（{route_type}），该始端无此类型进路，可用类型：{' / '.join(types)}",
                        "ERROR",
                    )
                else:
                    self.state_manager.log(f"办理失败：未定义进路 {start} -> {end}（{route_type}）", "ERROR")
            return False

        if self._guide_lock_enabled:
            self.state_manager.log("办理失败：引导总锁有效，禁止办理列车/调车进路", "ERROR")
            return False

        if route.is_active:
            self.state_manager.log(f"办理失败：进路已在办理/锁闭 {route.id}", "ERROR")
            return False

        for conflict_id in route.conflicting_routes:
            cr = self.state_manager.routes.get(conflict_id)
            if cr and cr.is_active:
                self.state_manager.log(f"办理失败：敌对进路占用 {conflict_id}", "ERROR")
                return False

        start_sig = self.state_manager.signals.get(route.start_signal)
        if not start_sig:
            self.state_manager.log(f"办理失败：始端信号机不存在 {route.start_signal}", "ERROR")
            return False

        # 规则：办理进路前置校验
        # 1）进路区段+接近区段空闲、无分路不良未确认、无封锁/故障
        track_ids = list(dict.fromkeys(route.approach_tracks + route.path_tracks + route.departure_tracks))
        for tid in track_ids:
            tk = self.state_manager.tracks.get(tid)
            if not tk:
                self.state_manager.log(f"办理失败：区段不存在 {tid}", "ERROR")
                return False
            if tk.is_blocked or tk.is_fault:
                self.state_manager.log(f"办理失败：区段封锁/故障 {tid}", "ERROR")
                return False
            if tk.is_shunt_failure:
                self.state_manager.log(f"办理失败：区段分路不良未确认 {tid}", "ERROR")
                return False
            if tk.is_occupied:
                self.state_manager.log(f"办理失败：区段占用 {tid}", "ERROR")
                return False
            if tk.is_locked:
                self.state_manager.log(f"办理失败：区段已锁闭 {tid}", "ERROR")
                return False

        # 2）道岔无进路锁/单锁/封锁/故障，位置满足进路规定定位/反位，防护道岔满足要求
        all_required_switches: Dict[str, SwitchPosition] = {}
        all_required_switches.update(route.path_switches)
        all_required_switches.update(route.flank_switches)
        switch_condition_items = []
        for swid, required_pos in all_required_switches.items():
            sw = self.state_manager.switches.get(swid)
            if not sw:
                self.state_manager.log(f"办理失败：道岔不存在 {swid}#", "ERROR")
                return False
            if sw.is_blocked or sw.is_fault:
                self.state_manager.log(f"办理失败：道岔封锁/故障 {swid}#", "ERROR")
                return False
            if sw.is_locked or sw.is_individual_locked:
                self.state_manager.log(f"办理失败：道岔锁闭/单锁 {swid}#", "ERROR")
                return False
            if sw.position == SwitchPosition.MOVING:
                self.state_manager.log(f"办理失败：道岔转换中 {swid}#", "ERROR")
                return False

            suffix = "（防护）" if swid in route.flank_switches else ""
            if sw.position == required_pos:
                switch_condition_items.append(f"{swid}#{suffix}={required_pos.value}(已到位)")
            else:
                switch_condition_items.append(f"{swid}#{suffix}={required_pos.value}(待转换)")

        # 3）灯丝完好、信号可用
        if start_sig.is_filament_fault or start_sig.is_fault or start_sig.is_blocked:
            self.state_manager.log(f"办理失败：始端信号机故障/封锁/断丝 {route.start_signal}", "ERROR")
            return False

        self.state_manager.log(f"进路征用：{route.id} {route.start_signal} -> {route.end_signal}")
        if switch_condition_items:
            self.state_manager.log(f"道岔条件：{'，'.join(switch_condition_items)}")
        self.state_manager.update_route(route.id, stage=RouteStage.SELECTED, is_active=True)
        self._active_route_ids.add(route.id)
        self._route_track_ever_occupied[route.id] = set()

        # 阶段1：选排进路，转换不符合位置的道岔（联锁层只下发指令）
        for swid, required_pos in all_required_switches.items():
            sw = self.state_manager.switches[swid]
            if sw.position != required_pos:
                self.simulator.move_switch(swid, required_pos)

        self._try_finish_route_setting(route.id)
        return True

    def cancel_route(self, start_signal: Optional[str] = None):
        for rid in list(self._active_route_ids):
            rt = self.state_manager.routes.get(rid)
            if not rt:
                continue
            if start_signal and rt.start_signal != start_signal:
                continue
            self._cancel_route_if_allowed(rid)

    def manual_unlock(self):
        for rid in list(self._active_route_ids):
            rt = self.state_manager.routes.get(rid)
            if not rt:
                continue

            any_occupied = any(self.state_manager.tracks[tid].is_occupied for tid in rt.path_tracks if tid in self.state_manager.tracks)
            if not any_occupied and rt.stage == RouteStage.PRELOCKED:
                continue

            if rt.type == "TRAIN" and rt.start_signal in ("X", "S"):
                seconds = 180
            else:
                seconds = 30

            self.state_manager.log(f"总人解：启动倒计时 {seconds}s（{rid}）")
            self.state_manager.update_route(rid, stage=RouteStage.RELEASING, manual_unlock_required=True, manual_unlock_remaining_s=seconds)
            self.simulator.start_manual_unlock_countdown(rid, seconds)

    def switch_single_operate(self, swid: str, target_pos: SwitchPosition):
        if self._guide_lock_enabled:
            self.state_manager.log("单操失败：引导总锁有效", "ERROR")
            return

        sw = self.state_manager.switches.get(swid)
        if not sw:
            self.state_manager.log(f"单操失败：道岔不存在 {swid}#", "ERROR")
            return

        if sw.is_locked or sw.is_individual_locked:
            self.state_manager.log(f"单操失败：道岔锁闭/单锁 {swid}#", "ERROR")
            return

        self.simulator.move_switch(swid, target_pos)

    def simulate_track_occupancy(self, track_id: str, is_occupied: bool):
        self.simulator.set_track_occupancy(track_id, is_occupied)

    def guide_control(self, start_signal: str):
        if not self._guide_lock_enabled:
            self.state_manager.log("引导失败：未投入引导总锁", "ERROR")
            return
        self.state_manager.log(f"引导：开放引导信号 {start_signal}")
        self.simulator.set_signal_aspect(start_signal, SignalAspect.GUIDE)

    def set_guide_lock(self, enabled: bool):
        self._guide_lock_enabled = enabled
        if enabled:
            self.state_manager.log("引导总锁：投入", "SUCCESS")
        else:
            self.state_manager.log("引导总锁：解除", "SUCCESS")

    def fault_section_unlock(self, track_id: str):
        tk = self.state_manager.tracks.get(track_id)
        if not tk:
            self.state_manager.log(f"区故解失败：区段不存在 {track_id}", "ERROR")
            return
        if not tk.is_fault:
            self.state_manager.log(f"区故解失败：区段无故障 {track_id}", "ERROR")
            return
        if tk.is_occupied:
            self.state_manager.log(f"区故解失败：区段占用 {track_id}", "ERROR")
            return
        if not tk.is_locked:
            self.state_manager.log(f"区故解失败：区段未锁闭 {track_id}", "ERROR")
            return
        self.state_manager.update_track(track_id, is_locked=False)
        self.state_manager.log(f"区故解：已解锁区段 {track_id}", "SUCCESS")

    def _try_finish_route_setting(self, route_id: str):
        rt = self.state_manager.routes.get(route_id)
        if not rt or not rt.is_active:
            return
        if rt.stage != RouteStage.SELECTED:
            return

        required_switches: Dict[str, SwitchPosition] = {}
        required_switches.update(rt.path_switches)
        required_switches.update(rt.flank_switches)

        for swid, required_pos in required_switches.items():
            sw = self.state_manager.switches.get(swid)
            if not sw:
                return
            if sw.position != required_pos:
                return
            if sw.last_move_failed:
                self.state_manager.log(f"进路办理失败：道岔 {swid}# 转换失败", "ERROR")
                self._force_release_route(route_id)
                return

        self.state_manager.update_route(route_id, stage=RouteStage.PRELOCKED)

        # 阶段2：进路锁闭（预先锁闭）
        for tid in rt.path_tracks + rt.approach_tracks + rt.departure_tracks:
            if tid in self.state_manager.tracks:
                self.state_manager.update_track(tid, is_locked=True)
        for swid in required_switches.keys():
            if swid in self.state_manager.switches:
                self.state_manager.update_switch(swid, is_locked=True)

        self.state_manager.log(f"进路预先锁闭完成：{route_id}", "SUCCESS")
        locked_tracks = list(dict.fromkeys(
            tid
            for tid in (rt.path_tracks + rt.approach_tracks + rt.departure_tracks)
            if tid in self.state_manager.tracks and self.state_manager.tracks[tid].is_locked
        ))
        locked_switches = [f"{swid}#" for swid in required_switches.keys() if swid in self.state_manager.switches and self.state_manager.switches[swid].is_locked]
        if locked_tracks or locked_switches:
            self.state_manager.log(f"锁闭设备：区段[{', '.join(locked_tracks)}] 道岔[{', '.join(locked_switches)}]")

        # 阶段3：开放信号（按配置点灯）
        self.simulator.set_signal_aspect(rt.start_signal, rt.start_aspect)
        self.state_manager.update_route(route_id, stage=RouteStage.OPENED)
        self.state_manager.log(f"信号开放：{rt.start_signal}（{rt.start_aspect.value}）", "SUCCESS")

    def _cancel_route_if_allowed(self, route_id: str):
        rt = self.state_manager.routes.get(route_id)
        if not rt:
            return

        # 规则：取消进路仅限预先锁闭，且接近区段无车、整条进路空闲、信号关闭
        if rt.stage not in (RouteStage.SELECTED, RouteStage.PRELOCKED):
            self.state_manager.log(f"总取消失败：进路已压入/开放后不可直接取消 {route_id}", "ERROR")
            return

        for tid in rt.approach_tracks + rt.path_tracks + rt.departure_tracks:
            tk = self.state_manager.tracks.get(tid)
            if tk and tk.is_occupied:
                self.state_manager.log(f"总取消失败：区段占用 {tid}（{route_id}）", "ERROR")
                return

        self.simulator.set_signal_aspect(rt.start_signal, SignalAspect.STOP)
        self._force_release_route(route_id)
        self.state_manager.log(f"总取消完成：{route_id}", "SUCCESS")

    def _force_release_route(self, route_id: str):
        rt = self.state_manager.routes.get(route_id)
        if not rt:
            return

        self._active_route_ids.discard(route_id)
        self._route_track_ever_occupied.pop(route_id, None)

        required_switches: Dict[str, SwitchPosition] = {}
        required_switches.update(rt.path_switches)
        required_switches.update(rt.flank_switches)

        for tid in rt.approach_tracks + rt.path_tracks + rt.departure_tracks:
            if tid in self.state_manager.tracks:
                self.state_manager.update_track(tid, is_locked=False)
        for swid in required_switches.keys():
            if swid in self.state_manager.switches:
                self.state_manager.update_switch(swid, is_locked=False)

        self.state_manager.update_route(
            route_id,
            stage=RouteStage.RELEASED,
            is_active=False,
            manual_unlock_required=False,
            manual_unlock_remaining_s=0,
        )

    def _on_state_changed(self, device_id: str, state: object):
        if device_id in self._active_route_ids:
            rt = self.state_manager.routes.get(device_id)
            if not rt:
                return
            if rt.manual_unlock_required and rt.manual_unlock_remaining_s == 0:
                self._try_release_after_manual_unlock(device_id)
            return

        if device_id in self.state_manager.switches:
            for rid in list(self._active_route_ids):
                self._try_finish_route_setting(rid)
            return

        if device_id in self.state_manager.tracks:
            self._handle_track_change(device_id)

    def _handle_track_change(self, track_id: str):
        for rid in list(self._active_route_ids):
            rt = self.state_manager.routes.get(rid)
            if not rt:
                continue
            if track_id not in rt.path_tracks:
                continue

            tk = self.state_manager.tracks.get(track_id)
            if not tk:
                continue

            if tk.is_occupied:
                self._route_track_ever_occupied.setdefault(rid, set()).add(track_id)

                # 规则：列车压入进路第一区段，信号自动关闭
                if rt.stage == RouteStage.OPENED and rt.path_tracks and track_id == rt.path_tracks[0]:
                    self.simulator.set_signal_aspect(rt.start_signal, SignalAspect.STOP)
                    self.state_manager.update_route(rid, stage=RouteStage.APPROACH_LOCKED)
                    self.state_manager.log(f"压入关闭：{rt.start_signal}", "SUCCESS")

            self._try_segment_release(rid)
            if rt.manual_unlock_required and rt.manual_unlock_remaining_s == 0:
                self._try_release_after_manual_unlock(rid)

    def _try_segment_release(self, route_id: str):
        rt = self.state_manager.routes.get(route_id)
        if not rt:
            return
        if rt.stage not in (RouteStage.OPENED, RouteStage.APPROACH_LOCKED, RouteStage.RELEASING):
            return

        ever = self._route_track_ever_occupied.get(route_id, set())
        tracks = rt.path_tracks
        if not tracks:
            return

        for i, tid in enumerate(tracks[:-1]):
            curr = self.state_manager.tracks.get(tid)
            nxt = self.state_manager.tracks.get(tracks[i + 1])
            if not curr or not nxt:
                continue
            if tid in ever and tracks[i + 1] in ever and (not curr.is_occupied) and curr.is_locked:
                # 规则：正常分段解锁（三点检查机制）
                self.state_manager.update_track(tid, is_locked=False)
                self.state_manager.log(f"分段解锁：{tid}（{route_id}）", "SUCCESS")

        last_tid = tracks[-1]
        last_tk = self.state_manager.tracks.get(last_tid)
        if not last_tk:
            return
        if last_tid in ever and (not last_tk.is_occupied):
            if all((not self.state_manager.tracks[t].is_occupied) for t in tracks if t in self.state_manager.tracks):
                self._force_release_route(route_id)
                self.state_manager.log(f"进路解锁完成：{route_id}", "SUCCESS")

    def _try_release_after_manual_unlock(self, route_id: str):
        rt = self.state_manager.routes.get(route_id)
        if not rt:
            return
        if any(self.state_manager.tracks[tid].is_occupied for tid in rt.path_tracks if tid in self.state_manager.tracks):
            return
        self._force_release_route(route_id)
        self.state_manager.log(f"人解完成：{route_id}", "SUCCESS")
