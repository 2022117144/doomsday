import ctypes
import hashlib
import os
import shutil
import struct
import subprocess
import tempfile
import time
from typing import Optional, Tuple, Union
from core.crypto import doom_hash, bits_to_target

CPU_C_SOURCE = r"""
#include <stdint.h>
#include <stdlib.h>

#if defined(_WIN32)
#include <windows.h>
#define EXPORT __declspec(dllexport)
#else
#include <pthread.h>
#define EXPORT __attribute__((visibility("default")))
#endif

static inline uint32_t rotr32(uint32_t x, int n) {
    return (x >> n) | (x << (32 - n));
}

static inline uint64_t rotl64(uint64_t x, int n) {
    return (x << n) | (x >> (64 - n));
}

static inline uint32_t bswap32(uint32_t x) {
    return ((x & 0x000000FFU) << 24) |
           ((x & 0x0000FF00U) << 8)  |
           ((x & 0x00FF0000U) >> 8)  |
           ((x & 0xFF000000U) >> 24);
}

static const uint32_t K[64] = {
    0x428a2f98U, 0x71374491U, 0xb5c0fbcfU, 0xe9b5dba5U, 0x3956c25bU, 0x59f111f1U, 0x923f82a4U, 0xab1c5ed5U,
    0xd807aa98U, 0x12835b01U, 0x243185beU, 0x550c7dc3U, 0x72be5d74U, 0x80deb1feU, 0x9bdc06a7U, 0xc19bf174U,
    0xe49b69c1U, 0xefbe4786U, 0x0fc19dc6U, 0x240ca1ccU, 0x2de92c6fU, 0x4a7484aaU, 0x5cb0a9dcU, 0x76f988daU,
    0x983e5152U, 0xa831c66dU, 0xb00327c8U, 0xbf597fc7U, 0xc6e00bf3U, 0xd5a79147U, 0x06ca6351U, 0x14292967U,
    0x27b70a85U, 0x2e1b2138U, 0x4d2c6dfcU, 0x53380d13U, 0x650a7354U, 0x766a0abbU, 0x81c2c92eU, 0x92722c85U,
    0xa2bfe8a1U, 0xa81a664bU, 0xc24b8b70U, 0xc76c51a3U, 0xd192e819U, 0xd6990624U, 0xf40e3585U, 0x106aa070U,
    0x19a4c116U, 0x1e376c08U, 0x2748774cU, 0x34b0bcb5U, 0x391c0cb3U, 0x4ed8aa4aU, 0x5b9cca4fU, 0x682e6ff3U,
    0x748f82eeU, 0x78a5636fU, 0x84c87814U, 0x8cc70208U, 0x90befffaU, 0xa4506cebU, 0xbef9a3f7U, 0xc67178f2U
};

static const uint32_t WK2[64] = {
    0xc28a2f98U, 0x71374491U, 0xb5c0fbcfU, 0xe9b5dba5U, 0x3956c25bU, 0x59f111f1U, 0x923f82a4U, 0xab1c5ed5U,
    0xd807aa98U, 0x12835b01U, 0x243185beU, 0x550c7dc3U, 0x72be5d74U, 0x80deb1feU, 0x9bdc06a7U, 0xc19bf374U,
    0x649b69c1U, 0xf0fe4786U, 0x0fe1edc6U, 0x240cf254U, 0x4fe9346fU, 0x6cc984beU, 0x61b9411eU, 0x16f988faU,
    0xf2c65152U, 0xa88e5a6dU, 0xb019fc65U, 0xb9d99ec7U, 0x9a1231c3U, 0xe70eeaa0U, 0xfdb1232bU, 0xc7353eb0U,
    0x3069bad5U, 0xcb976d5fU, 0x5a0f118fU, 0xdc1eeefdU, 0x0a35b689U, 0xde0b7a04U, 0x58f4ca9dU, 0xe15d5b16U,
    0x007f3e86U, 0x37088980U, 0xa507ea32U, 0x6fab9537U, 0x17406110U, 0x0d8cd6f1U, 0xcdaa3b6dU, 0xc0bbbe37U,
    0x83613bdaU, 0xdb48a363U, 0x0b02e931U, 0x6fd15ca7U, 0x521afacaU, 0x31338431U, 0x6ed41a95U, 0x6d437890U,
    0xc39c91f2U, 0x9eccabbdU, 0xb5c9a0e6U, 0x532fb63cU, 0xd2c741c6U, 0x07237ea3U, 0xa4954b68U, 0x4c191d76U
};

static inline uint64_t doom_hash_high64(uint64_t s0, uint64_t s1, uint64_t s2, uint64_t s3, uint64_t nonce) {
    uint64_t w[8];
    w[0] = s0;
    w[1] = s1;
    w[2] = s2;
    w[3] = s3;
    w[4] = nonce;
    w[5] = nonce ^ 0x5555555555555555ULL;
    w[6] = nonce ^ 0xAAAAAAAAAAAAAAAAULL;
    w[7] = 0x9E3779B97F4A7C15ULL;

    for (int r = 0; r < 8; r++) {
        for (int i = 0; i < 8; i++) {
            int next_idx = (i + 1) & 7;
            int prev_idx = (i + 7) & 7;
            uint64_t val = w[i] ^ w[next_idx];
            uint64_t rot = rotl64(val, 17);
            w[i] = rot * 0x9E3779B97F4A7C15ULL + w[prev_idx] + (uint64_t)r;
        }
    }

    uint32_t W[64];
    for (int i = 0; i < 8; i++) {
        W[i * 2]     = bswap32((uint32_t)w[i]);
        W[i * 2 + 1] = bswap32((uint32_t)(w[i] >> 32));
    }
    for (int i = 16; i < 64; i++) {
        uint32_t sig0 = rotr32(W[i-15], 7) ^ rotr32(W[i-15], 18) ^ (W[i-15] >> 3);
        uint32_t sig1 = rotr32(W[i-2], 17) ^ rotr32(W[i-2], 19) ^ (W[i-2] >> 10);
        W[i] = W[i-16] + sig0 + W[i-7] + sig1;
    }

    uint32_t a = 0x6a09e667U, b = 0xbb67ae85U, c = 0x3c6ef372U, d = 0xa54ff53aU;
    uint32_t e = 0x510e527fU, f = 0x9b05688cU, g = 0x1f83d9abU, h = 0x5be0cd19U;

    for (int i = 0; i < 64; i++) {
        uint32_t S1 = rotr32(e, 6) ^ rotr32(e, 11) ^ rotr32(e, 25);
        uint32_t ch = (e & f) ^ ((~e) & g);
        uint32_t temp1 = h + S1 + ch + K[i] + W[i];
        uint32_t S0 = rotr32(a, 2) ^ rotr32(a, 13) ^ rotr32(a, 22);
        uint32_t maj = (a & b) ^ (a & c) ^ (b & c);
        uint32_t temp2 = S0 + maj;
        h = g; g = f; f = e; e = d + temp1;
        d = c; c = b; b = a; a = temp1 + temp2;
    }

    uint32_t st0 = 0x6a09e667U + a, st1 = 0xbb67ae85U + b, st2 = 0x3c6ef372U + c, st3 = 0xa54ff53aU + d;
    uint32_t st4 = 0x510e527fU + e, st5 = 0x9b05688cU + f, st6 = 0x1f83d9abU + g, st7 = 0x5be0cd19U + h;

    a = st0; b = st1; c = st2; d = st3;
    e = st4; f = st5; g = st6; h = st7;

    for (int i = 0; i < 64; i++) {
        uint32_t S1 = rotr32(e, 6) ^ rotr32(e, 11) ^ rotr32(e, 25);
        uint32_t ch = (e & f) ^ ((~e) & g);
        uint32_t temp1 = h + S1 + ch + WK2[i];
        uint32_t S0 = rotr32(a, 2) ^ rotr32(a, 13) ^ rotr32(a, 22);
        uint32_t maj = (a & b) ^ (a & c) ^ (b & c);
        uint32_t temp2 = S0 + maj;
        h = g; g = f; f = e; e = d + temp1;
        d = c; c = b; b = a; a = temp1 + temp2;
    }

    return ((uint64_t)(st0 + a) << 32) | (uint64_t)(st1 + b);
}

typedef struct {
    uint64_t s0, s1, s2, s3;
    uint64_t start_nonce;
    uint64_t count;
    uint64_t best_hash;
    uint64_t winning_nonce;
} WorkerArg;

#if defined(_WIN32)
static DWORD WINAPI worker_thread(LPVOID param) {
#else
static void* worker_thread(void* param) {
#endif
    WorkerArg* arg = (WorkerArg*)param;
    uint64_t s0 = arg->s0, s1 = arg->s1, s2 = arg->s2, s3 = arg->s3;
    uint64_t best = arg->best_hash;
    uint64_t win_nonce = 0;
    uint64_t end = arg->start_nonce + arg->count;

    for (uint64_t n = arg->start_nonce; n < end; n++) {
        uint64_t h = doom_hash_high64(s0, s1, s2, s3, n);
        if (h < best) {
            best = h;
            win_nonce = n;
        }
    }
    arg->best_hash = best;
    arg->winning_nonce = win_nonce;
    return 0;
}

EXPORT int doom_cpu_mine_batch(
    uint64_t s0, uint64_t s1, uint64_t s2, uint64_t s3,
    uint64_t start_nonce,
    uint64_t batch_size,
    uint64_t target_high,
    int num_threads,
    uint64_t* out_winning_nonce,
    uint64_t* out_best_hash
) {
    if (num_threads < 1) num_threads = 1;
    if (num_threads > 64) num_threads = 64;

    WorkerArg args[64];
    uint64_t per_thread = batch_size / (uint64_t)num_threads;
    uint64_t rem = batch_size % (uint64_t)num_threads;

#if defined(_WIN32)
    HANDLE threads[64];
#else
    pthread_t threads[64];
#endif

    uint64_t cur = start_nonce;
    for (int t = 0; t < num_threads; t++) {
        uint64_t cnt = per_thread + (t == num_threads - 1 ? rem : 0);
        args[t].s0 = s0;
        args[t].s1 = s1;
        args[t].s2 = s2;
        args[t].s3 = s3;
        args[t].start_nonce = cur;
        args[t].count = cnt;
        args[t].best_hash = target_high;
        args[t].winning_nonce = 0;
        cur += cnt;

#if defined(_WIN32)
        threads[t] = CreateThread(NULL, 0, worker_thread, &args[t], 0, NULL);
#else
        pthread_create(&threads[t], NULL, worker_thread, &args[t]);
#endif
    }

    uint64_t global_best = target_high;
    uint64_t global_nonce = 0;
    int found = 0;

    for (int t = 0; t < num_threads; t++) {
#if defined(_WIN32)
        WaitForSingleObject(threads[t], INFINITE);
        CloseHandle(threads[t]);
#else
        pthread_join(threads[t], NULL);
#endif
        if (args[t].best_hash < global_best) {
            global_best = args[t].best_hash;
            global_nonce = args[t].winning_nonce;
            found = 1;
        }
    }

    *out_winning_nonce = global_nonce;
    *out_best_hash = global_best;
    return found;
}
"""


class CPUSolver:
    """
    High-performance multi-threaded native C CPU miner with pure-Python fallback.
    Automatically JIT-compiles a native SIMD/multi-core C library when gcc or clang is available.
    """
    def __init__(self, threads: Optional[int] = None):
        self.threads = threads or max(1, os.cpu_count() or 4)
        self.lib = self._load_or_compile_native()
        if self.lib is not None:
            self.device_name = f"Native C Multi-Core CPU ({self.threads} Threads)"
        else:
            self.device_name = "CPU Reference Solver"

    def _load_or_compile_native(self):
        local_dir = os.path.dirname(os.path.abspath(__file__))
        src_hash = hashlib.sha256(CPU_C_SOURCE.encode("utf-8")).hexdigest()[:10]
        ext = ".dll" if os.name == "nt" else ".so"
        lib_path = os.path.join(local_dir, f"cpu_doomhash_{src_hash}{ext}")

        if not os.path.exists(lib_path):
            compiler = shutil.which("clang") or shutil.which("gcc")
            if not compiler:
                return None
            c_file = os.path.join(tempfile.gettempdir(), f"cpu_doomhash_{src_hash}.c")
            try:
                with open(c_file, "w", encoding="utf-8") as f:
                    f.write(CPU_C_SOURCE)
                if os.name == "nt":
                    cmd = [compiler, "-O3", "-shared", c_file, "-o", lib_path]
                else:
                    cmd = [compiler, "-O3", "-march=native", "-fPIC", "-pthread", "-shared", c_file, "-o", lib_path]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                if res.returncode != 0:
                    cmd = [compiler, "-O3", "-shared", c_file, "-o", lib_path]
                    if os.name != "nt":
                        cmd.extend(["-fPIC", "-pthread"])
                    subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            except Exception:
                return None
            finally:
                if os.path.exists(c_file):
                    try:
                        os.remove(c_file)
                    except Exception:
                        pass

        if os.path.exists(lib_path):
            try:
                lib = ctypes.CDLL(lib_path)
                lib.doom_cpu_mine_batch.argtypes = [
                    ctypes.c_uint64, ctypes.c_uint64, ctypes.c_uint64, ctypes.c_uint64,
                    ctypes.c_uint64, ctypes.c_uint64, ctypes.c_uint64, ctypes.c_int,
                    ctypes.POINTER(ctypes.c_uint64), ctypes.POINTER(ctypes.c_uint64)
                ]
                lib.doom_cpu_mine_batch.restype = ctypes.c_int
                return lib
            except Exception:
                return None
        return None

    def mine_batch(
        self,
        header_prefix: Optional[bytes] = None,
        start_nonce: int = 0,
        batch_size: int = 100_000,
        target: Optional[int] = None,
        *,
        seed_u64: Optional[Tuple[int, int, int, int]] = None,
        target_high: Optional[int] = None
    ) -> Tuple[bool, int, float]:
        if seed_u64 is None:
            if header_prefix is None:
                raise ValueError("Either seed_u64 or header_prefix must be provided")
            seed_bytes = hashlib.sha256(header_prefix).digest()
            seed_u64 = struct.unpack("<4Q", seed_bytes)

        if target_high is None:
            if target is None:
                raise ValueError("Either target_high or target must be provided")
            target_high = (target >> 192) & 0xFFFFFFFFFFFFFFFF if target > (1 << 64) else target

        if self.lib is not None:
            out_nonce = ctypes.c_uint64(0)
            out_best = ctypes.c_uint64(target_high)
            t0 = time.perf_counter()
            found_int = self.lib.doom_cpu_mine_batch(
                seed_u64[0], seed_u64[1], seed_u64[2], seed_u64[3],
                start_nonce,
                batch_size,
                target_high,
                self.threads,
                ctypes.byref(out_nonce),
                ctypes.byref(out_best)
            )
            t1 = time.perf_counter()
            elapsed = max(1e-6, t1 - t0)
            return bool(found_int), int(out_nonce.value), batch_size / elapsed

        # Pure Python fallback
        t0 = time.perf_counter()
        end_nonce = start_nonce + batch_size
        if header_prefix is not None and target is not None:
            for nonce in range(start_nonce, end_nonce):
                digest = doom_hash(header_prefix, nonce)
                if int.from_bytes(digest, byteorder="big") < target:
                    t1 = time.perf_counter()
                    elapsed = max(1e-6, t1 - t0)
                    return True, nonce, (nonce - start_nonce + 1) / elapsed
        else:
            s0, s1, s2, s3 = seed_u64
            for nonce in range(start_nonce, end_nonce):
                w = [
                    s0, s1, s2, s3,
                    nonce & 0xFFFFFFFFFFFFFFFF,
                    (nonce ^ 0x5555555555555555) & 0xFFFFFFFFFFFFFFFF,
                    (nonce ^ 0xAAAAAAAAAAAAAAAA) & 0xFFFFFFFFFFFFFFFF,
                    0x9E3779B97F4A7C15
                ]
                for r in range(8):
                    for i in range(8):
                        val = (w[i] ^ w[(i + 1) & 7]) & 0xFFFFFFFFFFFFFFFF
                        rot = ((val << 17) | (val >> 47)) & 0xFFFFFFFFFFFFFFFF
                        w[i] = (rot * 0x9E3779B97F4A7C15 + w[(i + 7) & 7] + r) & 0xFFFFFFFFFFFFFFFF
                digest = hashlib.sha256(struct.pack("<8Q", *w)).digest()
                if struct.unpack(">Q", digest[:8])[0] < target_high:
                    t1 = time.perf_counter()
                    elapsed = max(1e-6, t1 - t0)
                    return True, nonce, (nonce - start_nonce + 1) / elapsed

        t1 = time.perf_counter()
        elapsed = max(1e-6, t1 - t0)
        return False, 0, batch_size / elapsed
