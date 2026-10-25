import sys

# Windows: nếu pandas/truststore được import trước torch thì torch lỗi
# "WinError 1114 ... c10.dll" (xung đột bản MSVC runtime). Nạp trước msvcp140.dll của hệ thống để tránh.
if sys.platform == 'win32':
    import ctypes
    ctypes.WinDLL('msvcp140.dll')

def main() -> None:
    print("Hello from bank-faqs!")
