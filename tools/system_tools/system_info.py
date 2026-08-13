import platform

import psutil


def get_system_info() -> str:
    cpu_percent = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()
    mem_used_gb = mem.used / (1024**3)
    mem_total_gb = mem.total / (1024**3)

    return (
        f"OS: {platform.system()} {platform.release()}\n"
        f"CPU usage: {cpu_percent}%\n"
        f"RAM: {mem.percent}% used ({mem_used_gb:.1f}GB / {mem_total_gb:.1f}GB)"
    )
