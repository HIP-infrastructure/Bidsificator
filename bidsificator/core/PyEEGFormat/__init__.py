# Platform-specific wrapper imports with exact Python version matching
import platform
import os
import sys

# Auto-detect available wrappers based on current platform and Python version
_current_dir = os.path.dirname(__file__)
_python_version = f"{sys.version_info.major}{sys.version_info.minor}"  # e.g., "312"
_os_name = platform.system()
_machine = platform.machine()

# Determine wrapper file name based on platform and Python version
wrapper_name = None
wrapper_file = None

if _os_name == "Linux" and "x86_64" in _machine.lower():
    wrapper_name = "wrapperlinux"
    wrapper_file = f"wrapperlinux.cpython-{_python_version}-x86_64-linux-gnu.so"
elif _os_name == "Darwin" and "arm" in _machine.lower():
    wrapper_name = "wrappermacarm"
    wrapper_file = f"wrappermacarm.cpython-{_python_version}-darwin.so"
elif _os_name == "Windows":
    wrapper_name = "wrapperwinamd64"
    wrapper_file = f"wrapperwinamd64.cp{_python_version}-win_amd64.pyd"

# Import the wrapper if it exists, otherwise raise ImportError
if wrapper_name and wrapper_file and os.path.exists(os.path.join(_current_dir, wrapper_file)):
    exec(f"from . import {wrapper_name}")
else:
    available_files = [f for f in os.listdir(_current_dir) if f.endswith(('.so', '.pyd'))]
    raise ImportError(f"No wrapper available for {_os_name} {_machine} Python {_python_version}. Available: {available_files}")