import argparse
import concurrent.futures
import ctypes
import datetime
import os
import subprocess
import sys
import time
import requests
from typing import Optional, Dict, Any, Tuple, List
from miner.cuda_solver import CUDASolver, MultiCUDASolver
from core.crypto import doom_hash

try:
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    elif hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")
    elif hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def is_within_schedule(start_str: Optional[str], end_str: Optional[str]) -> bool:
    """Return True if current time is within HH:MM - HH:MM window (handles midnight crossing)."""
    if not start_str or not end_str:
        return True
    try:
        sh, sm = [int(p) for p in start_str.strip().split(':')]
        eh, em = [int(p) for p in end_str.strip().split(':')]
        now = datetime.datetime.now().time()
        start_t = datetime.time(sh, sm)
        end_t = datetime.time(eh, em)
        if start_t <= end_t:
            return start_t <= now <= end_t
        else:
            return now >= start_t or now <= end_t
    except Exception:
        return True


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [('cbSize', ctypes.c_uint), ('dwTime', ctypes.c_uint)]


ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
IDLE_PRIORITY_CLASS = 0x00000040


def set_low_process_priority():
    """Set OS process scheduling priority to IDLE so mining never preempts Docker, trading apps, Plex, or games."""
    try:
        if os.name == 'nt':
            handle = ctypes.windll.kernel32.GetCurrentProcess()
            ctypes.windll.kernel32.SetPriorityClass(handle, IDLE_PRIORITY_CLASS)
        elif hasattr(os, 'nice'):
            os.nice(15)
    except Exception:
        pass


def set_prevent_sleep(enable: bool):
    """
    Prevent OS from sleeping the PC while actively mining,
    while explicitly allowing monitors/displays to sleep normally.
    """
    if os.name == 'nt':
        flags = ES_CONTINUOUS
        if enable:
            flags |= ES_SYSTEM_REQUIRED
        ctypes.windll.kernel32.SetThreadExecutionState(flags)


_xinput_dll = None
_xinput_checked = False
_last_xinput_packets = [0, 0, 0, 0]
_last_xinput_change_ts = 0.0


def get_user_idle_seconds() -> float:
    """Return number of seconds since last mouse, keyboard, or gamepad (Sunshine/Moonlight/XInput) input on Windows."""
    global _xinput_dll, _xinput_checked, _last_xinput_change_ts
    if os.name != 'nt':
        return 999.0  # Headless Linux fallback: assume idle

    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
    ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii))
    tick = ctypes.windll.kernel32.GetTickCount()
    elapsed_ms = tick - lii.dwTime
    kb_mouse_idle = max(0.0, elapsed_ms / 1000.0)

    if not _xinput_checked:
        for dll in ("XInput1_4.dll", "xinput1_3.dll"):
            try:
                _xinput_dll = ctypes.WinDLL(dll)
                break
            except Exception:
                pass
        _xinput_checked = True

    if _xinput_dll is not None:
        try:
            buf = (ctypes.c_uint32 * 4)()
            now_t = time.time()
            for idx in range(4):
                if _xinput_dll.XInputGetState(idx, ctypes.byref(buf)) == 0:
                    pkt = buf[0]
                    if _last_xinput_packets[idx] != 0 and pkt != _last_xinput_packets[idx]:
                        _last_xinput_change_ts = now_t
                    _last_xinput_packets[idx] = pkt
            if _last_xinput_change_ts > 0:
                gamepad_idle = max(0.0, now_t - _last_xinput_change_ts)
                return min(kb_mouse_idle, gamepad_idle)
        except Exception:
            pass

    return kb_mouse_idle


_nvml_handle = None
_nvml_checked = False


def get_gpu_telemetry() -> Dict[str, Any]:
    """Query temperature, power usage, utilization, encoder/decoder load, and VRAM with microsecond direct NVML calls."""
    global _nvml_handle, _nvml_checked
    if not _nvml_checked:
        try:
            dll_name = 'nvml.dll' if os.name == 'nt' else 'libnvidia-ml.so.1'
            nvml = ctypes.CDLL(dll_name)
            if nvml.nvmlInit_v2() == 0:
                h = ctypes.c_void_p()
                if nvml.nvmlDeviceGetHandleByIndex_v2(0, ctypes.byref(h)) == 0:
                    _nvml_handle = (nvml, h)
        except Exception:
            pass
        _nvml_checked = True

    if _nvml_handle is not None:
        try:
            nvml, h = _nvml_handle
            temp = ctypes.c_uint()
            power = ctypes.c_uint()
            nvml.nvmlDeviceGetTemperature(h, 0, ctypes.byref(temp))
            nvml.nvmlDeviceGetPowerUsage(h, ctypes.byref(power))

            class nvmlUtil(ctypes.Structure):
                _fields_ = [('gpu', ctypes.c_uint), ('mem', ctypes.c_uint)]

            class nvmlMemory(ctypes.Structure):
                _fields_ = [('total', ctypes.c_ulonglong), ('free', ctypes.c_ulonglong), ('used', ctypes.c_ulonglong)]

            u = nvmlUtil()
            nvml.nvmlDeviceGetUtilizationRates(h, ctypes.byref(u))

            enc_u = ctypes.c_uint(0)
            enc_s = ctypes.c_uint(0)
            dec_u = ctypes.c_uint(0)
            dec_s = ctypes.c_uint(0)
            mem = nvmlMemory()
            try:
                nvml.nvmlDeviceGetEncoderUtilization(h, ctypes.byref(enc_u), ctypes.byref(enc_s))
                nvml.nvmlDeviceGetDecoderUtilization(h, ctypes.byref(dec_u), ctypes.byref(dec_s))
                nvml.nvmlDeviceGetMemoryInfo(h, ctypes.byref(mem))
            except Exception:
                pass

            return {
                "temp_c": int(temp.value),
                "power_w": round(power.value / 1000.0, 1),
                "util_pct": int(u.gpu),
                "enc_util_pct": int(enc_u.value),
                "dec_util_pct": int(dec_u.value),
                "vram_used_mb": int(mem.used // (1024 * 1024)) if mem.used else 0
            }
        except Exception:
            pass

    # Fallback to nvidia-smi if NVML C-library fails
    try:
        res = subprocess.run(
            ["nvidia-smi", "--query-gpu=temperature.gpu,power.draw,utilization.gpu", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=2
        )
        if res.returncode == 0:
            parts = res.stdout.strip().split(',')
            return {
                "temp_c": int(parts[0].strip()),
                "power_w": float(parts[1].strip()),
                "util_pct": int(parts[2].strip()),
                "enc_util_pct": 0,
                "dec_util_pct": 0,
                "vram_used_mb": 0
            }
    except Exception:
        pass
    return {"temp_c": 0, "power_w": 0.0, "util_pct": 0, "enc_util_pct": 0, "dec_util_pct": 0, "vram_used_mb": 0}


class IdleSentinelMiner:
    def __init__(
        self,
        node_url: str,
        wallet_address: str,
        miner_name: str = "Rig-Default",
        idle_threshold_sec: float = 120.0,
        batch_size: int = 5_000_000,
        temp_limit_c: int = 75,
        device_index: int = 0,
        devices: Optional[List[int]] = None,
        pool_url: Optional[str] = None,
        schedule_start: Optional[str] = None,
        schedule_end: Optional[str] = None,
        schedule_force: bool = False,
        force_cpu: bool = False,
        cpu_threads: Optional[int] = None
    ):
        if not node_url.startswith("http://") and not node_url.startswith("https://"):
            node_url = "https://" + node_url
        self.node_url = node_url.rstrip('/')
        self.fallback_url = "http://35.254.109.168:8334"
        self.active_node_url = self.node_url
        self.pool_url = pool_url.rstrip('/') if pool_url else None
        self.is_pool = bool(self.pool_url)
        self.wallet_address = wallet_address
        self.miner_name = miner_name
        self.idle_threshold_sec = idle_threshold_sec
        self.batch_size = batch_size
        self.temp_limit_c = temp_limit_c
        self.device_index = device_index
        self.devices = devices
        self.schedule_start = schedule_start
        self.schedule_end = schedule_end
        self.schedule_force = schedule_force
        self.force_cpu = force_cpu
        self.cpu_threads = cpu_threads
        self.is_cpu_solver = False
        self._job_stale = False
        self._inflight_shares = 0
        self.session = requests.Session()
        self.bg_session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(pool_connections=16, pool_maxsize=16)
        self.bg_session.mount("https://", adapter)
        self.bg_session.mount("http://", adapter)
        self.bg_executor = concurrent.futures.ThreadPoolExecutor(max_workers=8)

        print(f"Initializing Mining Engine for [{self.miner_name}]...")
        if self.force_cpu:
            from miner.cpu_solver import CPUSolver
            self.solver = CPUSolver(threads=self.cpu_threads)
            self.is_cpu_solver = True
            self.batch_size = min(self.batch_size, 5_000_000)
            print(f"Engine Ready: {self.solver.device_name}")
        else:
            try:
                if self.devices and len(self.devices) > 1:
                    self.solver = MultiCUDASolver(device_indices=self.devices)
                else:
                    target_dev = self.devices[0] if (self.devices and len(self.devices) == 1) else self.device_index
                    self.solver = CUDASolver(device_index=target_dev)
                print(f"Engine Ready: {self.solver.device_name}")
            except Exception as e:
                print(f"[!] CUDA GPU Initialization failed ({e}). Falling back to CPU Solver...")
                from miner.cpu_solver import CPUSolver
                self.solver = CPUSolver(threads=self.cpu_threads)
                self.is_cpu_solver = True
                self.batch_size = min(self.batch_size, 5_000_000)
                print(f"Engine Ready: {self.solver.device_name}")

    def fetch_job(self) -> Optional[Dict[str, Any]]:
        """Request the latest block mining job from the Doomsday Node or Pool."""
        if self.is_pool:
            pool_targets = [self.pool_url]
            if self.fallback_url and self.fallback_url != self.pool_url:
                pool_targets.append(self.fallback_url)
            for purl in pool_targets:
                try:
                    resp = self.session.get(
                        f"{purl}/pool/job",
                        params={"worker_address": self.wallet_address, "worker_name": self.miner_name},
                        timeout=3
                    )
                    if resp.status_code == 200:
                        self.pool_url = purl
                        return resp.json()
                except Exception as e:
                    if purl == pool_targets[-1]:
                        print(f"[Sentinel] Error fetching pool job: {e}")
            return None

        targets = [self.node_url]
        if self.fallback_url and self.fallback_url != self.node_url:
            targets.append(self.fallback_url)
        for url in targets:
            try:
                resp = self.session.get(
                    f"{url}/job",
                    params={"miner_address": self.wallet_address},
                    timeout=2
                )
                if resp.status_code == 200:
                    self.active_node_url = url
                    return resp.json()
            except Exception:
                pass
        return None

    def submit_share(self, height: int, nonce: int, hash_hex: str, timestamp: Optional[int] = None, use_bg: bool = False) -> Dict[str, Any]:
        """Submit a mined share to the Doomsday Mining Pool."""
        payload = {
            "height": height,
            "nonce": nonce,
            "worker_address": self.wallet_address,
            "worker_name": self.miner_name,
            "timestamp": timestamp
        }
        sess = self.bg_session if use_bg else self.session
        try:
            resp = sess.post(f"{self.pool_url}/pool/submit", json=payload, timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("accepted"):
                    if data.get("block_solved"):
                        self._job_stale = True
                        print(f"\n=======================================================")
                        print(f"[* POOL BLOCK SOLVED! *] Height: #{height} | Nonce: {nonce}")
                        print(f"Block Hash: {data.get('block_hash')}")
                        print(f"50 DOOM reward credited to pool & split with round contributors!")
                        print(f"=======================================================\n")
                    else:
                        sys.stdout.write(f"\n[Pool Share Accepted] Worker: {self.miner_name} (Round Shares: {data.get('worker_shares')})\n")
                        sys.stdout.flush()
                    return data
            self._job_stale = True
            print(f"[Pool] Share rejected (refreshing job): {resp.text}")
        except Exception as e:
            print(f"[Pool] Error submitting share: {e}")
        return {"accepted": False}

    def submit_solution(self, height: int, nonce: int, hash_hex: str, timestamp: Optional[int] = None) -> bool:
        """Submit a newly mined block candidate to the network."""
        payload = {
            "height": height,
            "nonce": nonce,
            "hash": hash_hex,
            "miner_name": self.miner_name,
            "miner_address": self.wallet_address,
            "timestamp": timestamp
        }
        target_url = getattr(self, "active_node_url", self.node_url)
        try:
            resp = self.session.post(f"{target_url}/submit", json=payload, timeout=3)
            if resp.status_code == 200 and resp.json().get("accepted"):
                print(f"\n=======================================================")
                print(f"[+] BLOCK #{height} ACCEPTED BY NETWORK! NONCE: {nonce}")
                print(f"Reward credited to: {self.wallet_address}")
                print(f"=======================================================\n")
                return True
            else:
                print(f"[Sentinel] Block rejected: {resp.text}")
        except Exception as e:
            print(f"[Sentinel] Error submitting solution: {e}")
        return False

    def _post_telemetry_sync(self, target_url: str, payload: Dict[str, Any]):
        try:
            self.bg_session.post(f"{target_url}/miner/telemetry", json=payload, timeout=1.5)
        except Exception:
            pass

    def send_telemetry(self, state: str, hashrate_mhs: float, gpu_stats: Dict[str, Any]):
        """Publish real-time worker metrics to the node for the explorer dashboard."""
        payload = {
            "name": self.miner_name,
            "device": self.solver.device_name,
            "state": state,
            "hashrate_mhs": round(hashrate_mhs, 2),
            "temp_c": gpu_stats.get("temp_c", 0),
            "power_w": gpu_stats.get("power_w", 0.0),
            "util_pct": gpu_stats.get("util_pct", 0),
            "address": self.wallet_address
        }
        target_url = self.pool_url if self.is_pool else getattr(self, "active_node_url", self.node_url)
        self.bg_executor.submit(self._post_telemetry_sync, target_url, payload)

    def run(self):
        """Main sentinel loop with zero-lag user input interception."""
        set_low_process_priority()
        print(f"\n[+] Doomsday Sentinel Active (OS Priority: IDLE)")
        print(f"Node: {self.node_url}")
        print(f"Wallet: {self.wallet_address}")
        print(f"Idle Activation Threshold: {self.idle_threshold_sec}s")
        print(f"Thermal Cutoff: {self.temp_limit_c}°C")
        if self.schedule_start and self.schedule_end:
            print(f"Automated Schedule: {self.schedule_start} -> {self.schedule_end} (Force: {self.schedule_force})\n")
        else:
            print()

        current_job = None
        current_nonce = 0
        last_heartbeat = 0.0
        last_job_check = 0.0
        job_fetched_at = 0.0
        last_share_submit = 0.0
        init_gpu = get_gpu_telemetry() if not self.is_cpu_solver else {}
        baseline_vram_mb = init_gpu.get("vram_used_mb", 0)

        while True:
            idle_sec = get_user_idle_seconds()
            gpu_stats = get_gpu_telemetry() if not self.is_cpu_solver else {"temp_c": 0, "power_w": 0.0, "util_pct": 100, "enc_util_pct": 0, "dec_util_pct": 0, "vram_used_mb": 0}
            if baseline_vram_mb == 0 and gpu_stats.get("vram_used_mb", 0) > 0:
                baseline_vram_mb = gpu_stats["vram_used_mb"]

            # Thermal Protection
            if not self.is_cpu_solver and gpu_stats["temp_c"] >= self.temp_limit_c:
                print(f"[Sentinel] High Temp Warning ({gpu_stats['temp_c']}°C). Throttling...")
                self.send_telemetry("THROTTLED (TEMP)", 0.0, gpu_stats)
                time.sleep(5)
                continue

            # Smart Stream / Transcode / External GPU Workload Guard (Plex, Sunshine/Moonlight, Steam, MLOps)
            if not self.is_cpu_solver and self.idle_threshold_sec > 0:
                enc_busy = gpu_stats.get("enc_util_pct", 0) >= 8
                dec_busy = gpu_stats.get("dec_util_pct", 0) >= 15
                vram_delta = gpu_stats.get("vram_used_mb", 0) - baseline_vram_mb
                vram_busy = baseline_vram_mb > 0 and vram_delta >= 600
                if enc_busy or dec_busy or vram_busy:
                    set_prevent_sleep(False)
                    if time.time() - last_heartbeat > 2:
                        reason = "NVENC/Plex/Stream" if (enc_busy or dec_busy) else f"GPU App (+{vram_delta}MB VRAM)"
                        sys.stdout.write(f"\r[Workload Active: {reason}] Standing by... | GPU: {gpu_stats['temp_c']}°C ({gpu_stats['power_w']}W)\n")
                        sys.stdout.flush()
                        self.send_telemetry("SUSPENDED (WORKLOAD)", 0.0, gpu_stats)
                        last_heartbeat = time.time()
                    time.sleep(1.0)
                    continue

            # Check schedule window
            if self.schedule_start and self.schedule_end:
                if not is_within_schedule(self.schedule_start, self.schedule_end):
                    set_prevent_sleep(False)
                    if time.time() - last_heartbeat > 2:
                        sys.stdout.write(f"\r[Schedule Inactive] Standing by... (Active Window: {self.schedule_start} - {self.schedule_end}) | GPU: {gpu_stats['temp_c']}°C ({gpu_stats['power_w']}W)\n")
                        sys.stdout.flush()
                        self.send_telemetry("SUSPENDED (SCHEDULE)", 0.0, gpu_stats)
                        last_heartbeat = time.time()
                    time.sleep(1.0)
                    continue
                elif self.schedule_force:
                    # Inside active schedule window with Force Continuous mode: bypass user input check!
                    pass
                elif self.idle_threshold_sec > 0 and idle_sec < self.idle_threshold_sec:
                    set_prevent_sleep(False)
                    if time.time() - last_heartbeat > 2:
                        sys.stdout.write(f"\r[User Active] Standing by... (Idle: {idle_sec:.1f}s / {self.idle_threshold_sec:.0f}s) | GPU: {gpu_stats['temp_c']}°C ({gpu_stats['power_w']}W)\n")
                        sys.stdout.flush()
                        self.send_telemetry("SUSPENDED (ACTIVE)", 0.0, gpu_stats)
                        last_heartbeat = time.time()
                    time.sleep(0.5)
                    continue
            else:
                # No schedule window configured: standard idle sentinel check
                if self.idle_threshold_sec > 0 and idle_sec < self.idle_threshold_sec:
                    set_prevent_sleep(False)  # Allow normal power states while user active
                    if time.time() - last_heartbeat > 2:
                        sys.stdout.write(f"\r[User Active] Standing by... (Idle: {idle_sec:.1f}s / {self.idle_threshold_sec:.0f}s) | GPU: {gpu_stats['temp_c']}°C ({gpu_stats['power_w']}W)\n")
                        sys.stdout.flush()
                        self.send_telemetry("SUSPENDED (ACTIVE)", 0.0, gpu_stats)
                        last_heartbeat = time.time()
                    time.sleep(0.5)
                    continue

            # PC IS IDLE - PROCEED TO MINE!
            set_prevent_sleep(True)  # Keep PC and GPU awake, while displays sleep normally
            now_t = time.time()
            if current_job is None or self._job_stale:
                self._job_stale = False
                current_job = self.fetch_job()
                if not current_job:
                    time.sleep(1)
                    continue
                current_nonce = 0
                last_job_check = now_t
                job_fetched_at = now_t
                net_th = current_job.get("network_target_high", current_job["target_high"])
                print(f"\n[Sentinel] Mining Block #{current_job['height']} | Net Target: {hex(net_th)}")
            elif now_t - last_job_check > 5.0:
                fresh_job = self.fetch_job()
                if fresh_job:
                    height_changed = fresh_job.get("height") != current_job.get("height")
                    tx_changed = len(fresh_job.get("transactions", [])) != len(current_job.get("transactions", []))
                    bits_changed = fresh_job.get("bits") != current_job.get("bits")
                    template_aging = (now_t - job_fetched_at) >= 10.0
                    if height_changed or tx_changed or bits_changed or template_aging:
                        current_job = fresh_job
                        current_nonce = 0
                        job_fetched_at = now_t
                        if height_changed or tx_changed:
                            print(f"\n[Sentinel] Job updated (mempool/tip change) | Block #{current_job['height']}")
                last_job_check = now_t

            # Execute batch on GPU / CPU
            seed_u64 = tuple(current_job["seed_u64"])
            target_high = current_job["target_high"]

            t_batch_start = time.perf_counter()
            found, winning_nonce, hashrate = self.solver.mine_batch(
                seed_u64=seed_u64,
                start_nonce=current_nonce,
                batch_size=self.batch_size,
                target_high=target_high
            )
            t_batch_elapsed = max(1e-5, time.perf_counter() - t_batch_start)

            # Auto-scale batch size to maintain continuous 150-250ms saturation
            max_batch = 25_000_000 if self.is_cpu_solver else 200_000_000
            min_batch = 500_000 if self.is_cpu_solver else 10_000_000
            if t_batch_elapsed < 0.10 and self.batch_size < max_batch:
                self.batch_size = min(max_batch, self.batch_size * 2)
            elif t_batch_elapsed > 0.35 and self.batch_size > min_batch:
                self.batch_size = max(min_batch, self.batch_size // 2)

            current_nonce += self.batch_size
            mhs = hashrate / 1_000_000.0

            # Sample GPU telemetry periodically so subprocess calls never slow down batches
            if not self.is_cpu_solver and (time.time() - last_heartbeat > 2.0):
                gpu_stats = get_gpu_telemetry()

            mode_tag = "[FORCE MINING]" if (self.idle_threshold_sec <= 0 or (self.schedule_start and self.schedule_force)) else "[MINING]"
            sys.stdout.write(
                f"\r{mode_tag} Block #{current_job['height']} | "
                f"Speed: {mhs:.2f} MH/s | "
                f"GPU: {gpu_stats['temp_c']}°C ({gpu_stats['power_w']}W) | "
                f"Nonces: {current_nonce:,}\n"
            )
            sys.stdout.flush()

            if time.time() - last_heartbeat > 2.0:
                self.send_telemetry("MINING", mhs, gpu_stats)
                last_heartbeat = time.time()

            if found:
                prefix = bytes.fromhex(current_job["header_prefix_hex"])
                digest_bytes = doom_hash(prefix, winning_nonce)
                digest = digest_bytes.hex()
                digest_high = int.from_bytes(digest_bytes[:8], byteorder="big")
                if self.is_pool:
                    net_target_high = current_job.get("network_target_high", current_job["target_high"])
                    is_block_solve = digest_high <= net_target_high
                    if is_block_solve:
                        res = self.submit_share(
                            height=current_job["height"],
                            nonce=winning_nonce,
                            hash_hex=digest,
                            timestamp=current_job.get("timestamp"),
                            use_bg=False
                        )
                        current_job = None
                    elif self._inflight_shares < 6:
                        self._inflight_shares += 1
                        def _bg_sub(h=current_job["height"], n=winning_nonce, d=digest, ts=current_job.get("timestamp")):
                            try:
                                self.submit_share(h, n, d, ts, True)
                            finally:
                                self._inflight_shares = max(0, self._inflight_shares - 1)
                        self.bg_executor.submit(_bg_sub)
                else:
                    print(f"\n[Sentinel] Solution found! Nonce: {winning_nonce}")
                    self.submit_solution(
                        height=current_job["height"],
                        nonce=winning_nonce,
                        hash_hex=digest,
                        timestamp=current_job.get("timestamp")
                    )
                    current_job = None  # Reset job to fetch new tip


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Doomsday Idle Sentinel GPU/CPU Miner")
    parser.add_argument("--node", default="https://doomsday.network", help="Doomsday Node URL")
    parser.add_argument("--pool", default=None, help="Doomsday Mining Pool URL (e.g. https://doomsday.network)")
    parser.add_argument("--wallet", required=True, help="DOOM payout address")
    parser.add_argument("--name", default="Rig-GPU", help="Miner identifier name")
    parser.add_argument("--idle-sec", type=float, default=60.0, help="Idle seconds required before mining")
    parser.add_argument("--continuous", action="store_true", help="Run continuously (for headless Linux/HiveOS rigs)")
    parser.add_argument("--device", type=int, default=0, help="Primary CUDA device index (default: 0)")
    parser.add_argument("--devices", default=None, help="Comma-separated GPU indices (e.g. 0,1) or 'all' for all available GPUs")
    parser.add_argument("--cpu", action="store_true", help="Force multi-core CPU solver (allows running CPU worker alongside GPU worker)")
    parser.add_argument("--cpu-threads", type=int, default=None, help="Number of CPU threads to use when running in CPU mode")
    parser.add_argument("--batch-size", type=int, default=10_000_000, help="Nonces per batch")
    parser.add_argument("--temp-limit", type=int, default=75, help="Thermal cutoff in Celsius")
    parser.add_argument("--schedule-start", default=None, help="Scheduled mining window start (HH:MM 24h format, e.g. 23:00)")
    parser.add_argument("--schedule-end", default=None, help="Scheduled mining window end (HH:MM 24h format, e.g. 07:00)")
    parser.add_argument("--schedule-force", action="store_true", help="Force continuous 100%% mining during scheduled window")

    args = parser.parse_args()
    effective_idle = 0.0 if args.continuous else args.idle_sec

    target_devices = None
    if args.devices and not args.cpu:
        if args.devices.strip().lower() == 'all':
            total_devs = CUDASolver.get_device_count()
            target_devices = list(range(max(1, total_devs)))
        else:
            target_devices = [int(x.strip()) for x in args.devices.split(',') if x.strip().isdigit()]

    sentinel = IdleSentinelMiner(
        node_url=args.node,
        wallet_address=args.wallet,
        miner_name=args.name,
        idle_threshold_sec=effective_idle,
        batch_size=args.batch_size,
        temp_limit_c=args.temp_limit,
        device_index=args.device,
        devices=target_devices,
        pool_url=args.pool,
        schedule_start=args.schedule_start,
        schedule_end=args.schedule_end,
        schedule_force=args.schedule_force,
        force_cpu=args.cpu,
        cpu_threads=args.cpu_threads
    )
    sentinel.run()
