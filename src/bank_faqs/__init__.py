import os
import sys

# Windows 11 có sẵn onnxruntime.dll (bản cũ) trong System32, bị nạp nhầm thay cho bản trong venv
# -> crash khi import qdrant_client/fastembed. Nạp trước DLL của venv để tránh xung đột.
if sys.platform == 'win32':
    import ctypes
    import importlib.util

    _spec = importlib.util.find_spec('onnxruntime')
    if _spec and _spec.origin:
        _dll = os.path.join(os.path.dirname(_spec.origin), 'capi', 'onnxruntime.dll')
        if os.path.exists(_dll):
            ctypes.WinDLL(_dll)

def main() -> None:
    print("Hello from bank-faqs!")
