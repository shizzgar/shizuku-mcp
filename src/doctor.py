import os
import platform
from typing import Any, Dict
from src.config import config
from src.runners.rish_runner import rish_runner
from src.runners.termux_api_runner import termux_api_runner
from src.runners.subprocess_runner import run_command

async def get_system_info() -> Dict[str, Any]:
    info = {
        "android_version": None,
        "termux_api_available": await termux_api_runner._check_availability(),
        "rish_available": False,
        "rish_path": None,
        "shizuku_running": False,
        "backend": "unknown",
        "android_14_warning": False,
        "artifacts_dir_writable": os.access(config.artifacts_dir, os.W_OK),
        "server_version": "0.1.0"
    }

    try:
        rish_path = await rish_runner._find_rish()
        info["rish_available"] = True
        info["rish_path"] = rish_path
        
        # Check permissions for Android 14+ warning
        # On Android 14+, rish should not be writable by anyone other than the owner
        # Shizuku docs: "If the rish file is writable by others, it will not work on Android 14+."
        # In Termux, files are usually owned by the user.
        # We can check if it has write permission for group/others.
        stat = os.stat(rish_path)
        if stat.st_mode & 0o022: # Writable by group or others
             info["android_14_warning"] = True

        info["shizuku_running"] = await rish_runner.check_shizuku()
        
        if info["shizuku_running"]:
            # Try to get android version and backend
            rc, stdout, stderr = await rish_runner.run_rish("getprop ro.build.version.release")
            if rc == 0:
                info["android_version"] = stdout
            
            # Check backend (adb or root)
            rc, stdout, stderr = await rish_runner.run_rish("getprop rikka.shizuku.mode")
            if rc == 0:
                # 0: adb, 1: root
                info["backend"] = "adb" if stdout == "0" else "root" if stdout == "1" else "unknown"
                
    except Exception:
        pass

    return info
