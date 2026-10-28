"""Windows DPAPI encryption scoped to the current Windows sign-in."""

import ctypes
from ctypes import wintypes
import json
import os
import uuid


class Blob(ctypes.Structure):
    _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_ubyte))]


def protect(data, decrypt=False):
    if os.name != "nt":
        raise RuntimeError("Windows encryption required")
    buffer = ctypes.create_string_buffer(data)
    incoming = Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    outgoing = Blob()
    crypt = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    function = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    function.argtypes = [
        ctypes.POINTER(Blob),
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(Blob),
    ]
    function.restype = wintypes.BOOL
    if not function(ctypes.byref(incoming), None, None, None, None, 1, ctypes.byref(outgoing)):
        raise RuntimeError("Windows could not protect or read the connection")
    try:
        return ctypes.string_at(outgoing.data, outgoing.size)
    finally:
        kernel.LocalFree(outgoing.data)


def load(root):
    return json.loads(protect((root / ".private" / "connection.bin").read_bytes(), decrypt=True))


def save(root, record):
    directory = root / ".private"
    directory.mkdir(exist_ok=True)
    temporary = directory / "connection.tmp"
    with temporary.open("wb") as output:
        output.write(protect(json.dumps(record).encode()))
        output.flush()
        os.fsync(output.fileno())
    temporary.replace(directory / "connection.bin")


def create(root, key, secret):
    if (root / "live_state.json").exists() or (root / ".private" / "connection.bin").exists():
        raise RuntimeError("Existing connection/state requires migration; do not overwrite")
    record = {
        "key": key,
        "secret": secret,
        "installation": uuid.uuid4().hex[:12],
        "initialized": False,
    }
    save(root, record)
    return record
