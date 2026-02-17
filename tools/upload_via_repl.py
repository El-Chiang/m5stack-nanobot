#!/usr/bin/env python3
"""通过 UIFlow REPL paste mode 上传单个文件到设备（不依赖 mpremote）。"""

import argparse
import base64
import os
import time

import serial


BAUD = 115200
OK_MARK = "__UPLOAD_OK__"


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--port", default="/dev/tty.usbserial-5B090280621")
    p.add_argument("local_path", help="本地文件路径")
    p.add_argument("remote_path", help="设备路径（不带冒号），例如 spirit/a.jpg")
    p.add_argument("--chunk", type=int, default=384, help="base64 分块大小")
    return p.parse_args()


def read_available(s):
    time.sleep(0.05)
    return s.read(s.in_waiting or 4096)


def ensure_repl(s):
    s.write(b"\r\n")
    buf = b""
    deadline = time.time() + 1.2
    while time.time() < deadline:
        buf += read_available(s)
        if b">>>" in buf:
            return

    # 打断 UIFlow 后台脚本
    for _ in range(14):
        s.write(b"\x03")
        time.sleep(0.18)
    s.write(b"\r\n")

    buf = b""
    deadline = time.time() + 3
    while time.time() < deadline:
        buf += read_available(s)
        if b"raw REPL; CTRL-B to exit" in buf or buf.rstrip().endswith(b">"):
            s.write(b"\x02")  # Ctrl+B -> normal repl
            time.sleep(0.3)
            buf += read_available(s)
        if b">>>" in buf:
            return

    raise RuntimeError("could not enter normal repl")


def wait_for(s, marker, timeout=8):
    buf = b""
    deadline = time.time() + timeout
    marker_b = marker.encode("utf-8")
    while time.time() < deadline:
        buf += read_available(s)
        if marker_b in buf and b">>>" in buf:
            return buf
    raise RuntimeError("timeout waiting marker=%s, got=%r" % (marker, buf[-200:]))


def to_chunks_b64(data, chunk):
    encoded = base64.b64encode(data).decode("ascii")
    return [encoded[i:i + chunk] for i in range(0, len(encoded), chunk)]


def make_script(remote_path, data, chunk):
    b64_parts = to_chunks_b64(data, chunk)
    # 逐级 mkdir，兼容没有 makedirs 的 MicroPython
    path_parts = remote_path.split("/")
    dir_parts = path_parts[:-1]

    lines = [
        "import ubinascii",
        "try:",
        "    import uos as os",
        "except ImportError:",
        "    import os",
        "_p = ''",
    ]
    for part in dir_parts:
        if not part:
            continue
        safe = part.replace("\\", "\\\\").replace("'", "\\'")
        lines += [
            "_p = _p + '/%s' if _p else '%s'" % (safe, safe),
            "try:",
            "    os.mkdir(_p)",
            "except OSError:",
            "    pass",
        ]

    safe_remote = remote_path.replace("\\", "\\\\").replace("'", "\\'")
    lines.append("_f = open('%s', 'wb')" % safe_remote)
    for part in b64_parts:
        lines.append("_f.write(ubinascii.a2b_base64(b'%s'))" % part)
    lines += [
        "_f.close()",
        "print('%s:%s:%d')" % (OK_MARK, safe_remote, len(data)),
    ]
    return "\n".join(lines) + "\n"


def exec_paste(s, code, marker):
    s.write(b"\x05")  # Ctrl+E paste mode
    time.sleep(0.2)
    _ = read_available(s)
    for line in code.split("\n"):
        s.write((line + "\r\n").encode("utf-8"))
        time.sleep(0.002)
    s.write(b"\x04")  # Ctrl+D execute
    return wait_for(s, marker)


def main():
    args = parse_args()
    with open(args.local_path, "rb") as f:
        data = f.read()

    s = serial.Serial(args.port, BAUD, timeout=0.2)
    try:
        ensure_repl(s)
        marker = "%s:%s:%d" % (OK_MARK, args.remote_path, len(data))
        code = make_script(args.remote_path, data, args.chunk)
        exec_paste(s, code, marker)
    finally:
        s.close()

    print("uploaded %s -> %s (%d bytes)" % (args.local_path, args.remote_path, len(data)))


if __name__ == "__main__":
    main()
