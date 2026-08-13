import psutil


def list_processes(limit: int = 15) -> str:
    procs = []
    for proc in psutil.process_iter(["pid", "name", "memory_info"]):
        info = proc.info
        mem = info["memory_info"].rss if info["memory_info"] else 0
        procs.append((mem, info["pid"], info["name"]))

    procs.sort(reverse=True)
    lines = [f"{pid:>6}  {name}" for _mem, pid, name in procs[:limit]]
    return "Top processes by memory:\n" + "\n".join(lines)


def kill_process(name_or_pid: str) -> str:
    target = name_or_pid.strip()
    killed = []

    for proc in psutil.process_iter(["pid", "name"]):
        info = proc.info
        is_pid_match = target.isdigit() and info["pid"] == int(target)
        is_name_match = info["name"] and info["name"].lower() == target.lower()

        if is_pid_match or is_name_match:
            try:
                proc.kill()
                killed.append(f"{info['name']} (pid {info['pid']})")
            except psutil.NoSuchProcess:
                pass

    if not killed:
        return f"No running process matched '{target}'."

    return "Killed: " + ", ".join(killed)
