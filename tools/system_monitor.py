"""Enhanced system monitoring tools - CPU, RAM, disk, network, battery, processes, health alerts."""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from tools.registry import register_tool

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@register_tool({
    "name": "get_system_health",
    "description": "Get a comprehensive system health report including CPU, RAM, disk, network, battery, and top processes.",
    "input_schema": {"type": "object", "properties": {}, "required": []},
})
def get_system_health() -> Dict[str, Any]:
    """Full system health snapshot."""
    try:
        import psutil

        cpu_pct = psutil.cpu_percent(interval=0.5)
        cpu_freq = psutil.cpu_freq()
        cpu_count = psutil.cpu_count()

        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()

        disk = psutil.disk_usage("/")

        net = psutil.net_io_counters()

        battery = None
        try:
            bat = psutil.sensors_battery()
            if bat:
                battery = {
                    "percent": round(bat.percent, 1),
                    "plugged_in": bat.power_plugged,
                    "time_left_minutes": int(bat.secsleft / 60) if bat.secsleft > 0 else None,
                }
        except Exception:
            pass

        # Top 5 CPU-consuming processes
        top_procs = []
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
            try:
                top_procs.append(proc.info)
            except Exception:
                pass
        top_procs.sort(key=lambda x: x.get("cpu_percent") or 0, reverse=True)
        top_procs = top_procs[:5]

        # Health alerts
        alerts = []
        if cpu_pct > 85:
            alerts.append(f"HIGH CPU: {cpu_pct}% usage")
        if mem.percent > 85:
            alerts.append(f"HIGH RAM: {mem.percent}% used ({mem.used // (1024**2)}MB / {mem.total // (1024**2)}MB)")
        if disk.percent > 90:
            alerts.append(f"DISK ALMOST FULL: {disk.percent}% used")
        if battery and not battery["plugged_in"] and battery["percent"] < 20:
            alerts.append(f"LOW BATTERY: {battery['percent']}%")

        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "cpu": {
                "percent": cpu_pct,
                "cores": cpu_count,
                "frequency_mhz": round(cpu_freq.current, 0) if cpu_freq else None,
            },
            "memory": {
                "percent": mem.percent,
                "used_mb": mem.used // (1024 ** 2),
                "total_mb": mem.total // (1024 ** 2),
                "available_mb": mem.available // (1024 ** 2),
            },
            "swap": {
                "percent": swap.percent,
                "used_mb": swap.used // (1024 ** 2),
                "total_mb": swap.total // (1024 ** 2),
            },
            "disk": {
                "percent": disk.percent,
                "used_gb": round(disk.used / (1024 ** 3), 2),
                "total_gb": round(disk.total / (1024 ** 3), 2),
                "free_gb": round(disk.free / (1024 ** 3), 2),
            },
            "network": {
                "bytes_sent_mb": round(net.bytes_sent / (1024 ** 2), 2),
                "bytes_recv_mb": round(net.bytes_recv / (1024 ** 2), 2),
                "packets_sent": net.packets_sent,
                "packets_recv": net.packets_recv,
            },
            "battery": battery,
            "top_processes": top_procs,
            "alerts": alerts,
            "alert_count": len(alerts),
        }
    except ImportError:
        return {"success": False, "error": "psutil not installed."}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@register_tool({
    "name": "get_network_info",
    "description": "Get network interfaces, IP addresses, and current connection statistics.",
    "input_schema": {"type": "object", "properties": {}, "required": []},
})
def get_network_info() -> Dict[str, Any]:
    """Get network interface information."""
    try:
        import psutil

        interfaces = []
        addrs = psutil.net_if_addrs()
        stats = psutil.net_if_stats()

        for iface_name, addr_list in addrs.items():
            iface_stat = stats.get(iface_name)
            iface_info = {
                "name": iface_name,
                "is_up": iface_stat.isup if iface_stat else False,
                "speed_mbps": iface_stat.speed if iface_stat else 0,
                "addresses": [],
            }
            for addr in addr_list:
                iface_info["addresses"].append({
                    "family": str(addr.family.name),
                    "address": addr.address,
                    "netmask": addr.netmask,
                })
            interfaces.append(iface_info)

        # Check internet connectivity
        import socket
        internet_ok = False
        try:
            socket.setdefaulttimeout(3)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
            internet_ok = True
        except Exception:
            pass

        return {
            "success": True,
            "internet_connected": internet_ok,
            "interfaces": interfaces,
        }
    except ImportError:
        return {"success": False, "error": "psutil not installed."}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@register_tool({
    "name": "get_disk_usage",
    "description": "Get disk usage for all mounted partitions.",
    "input_schema": {"type": "object", "properties": {}, "required": []},
})
def get_disk_usage() -> Dict[str, Any]:
    """Get disk usage for all partitions."""
    try:
        import psutil

        partitions = []
        for part in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(part.mountpoint)
                partitions.append({
                    "device": part.device,
                    "mountpoint": part.mountpoint,
                    "fstype": part.fstype,
                    "total_gb": round(usage.total / (1024 ** 3), 2),
                    "used_gb": round(usage.used / (1024 ** 3), 2),
                    "free_gb": round(usage.free / (1024 ** 3), 2),
                    "percent": usage.percent,
                })
            except PermissionError:
                continue

        return {"success": True, "partitions": partitions}
    except ImportError:
        return {"success": False, "error": "psutil not installed."}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@register_tool({
    "name": "check_proactive_alerts",
    "description": "Check for proactive system alerts: low disk, high CPU, low battery, stopped dev servers, and due tasks.",
    "input_schema": {"type": "object", "properties": {}, "required": []},
})
def check_proactive_alerts() -> Dict[str, Any]:
    """Run proactive health checks and return actionable alerts."""
    alerts: List[Dict[str, Any]] = []

    # System health
    try:
        import psutil

        cpu = psutil.cpu_percent(interval=0.3)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        if cpu > 85:
            alerts.append({"type": "system", "level": "warning", "message": f"CPU usage is high: {cpu}%"})
        if mem.percent > 85:
            alerts.append({"type": "system", "level": "warning", "message": f"RAM usage is high: {mem.percent}% ({mem.used // (1024**2)}MB used)"})
        if disk.percent > 90:
            alerts.append({"type": "system", "level": "critical", "message": f"Disk is almost full: {disk.percent}% used ({disk.free // (1024**3)}GB free)"})

        bat = psutil.sensors_battery()
        if bat and not bat.power_plugged and bat.percent < 20:
            alerts.append({"type": "battery", "level": "critical", "message": f"Battery low: {bat.percent:.0f}%"})
    except Exception:
        pass

    # Check common dev server ports
    import socket
    dev_ports = {3000: "React/Node", 8000: "FastAPI/Django", 8080: "Generic HTTP", 5000: "Flask", 4200: "Angular"}
    running_servers = []
    for port, name in dev_ports.items():
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.3)
                if s.connect_ex(("127.0.0.1", port)) == 0:
                    running_servers.append(f"{name} (:{port})")
        except Exception:
            pass

    if running_servers:
        alerts.append({"type": "info", "level": "info", "message": f"Running dev servers: {', '.join(running_servers)}"})

    # Check pending tasks
    try:
        from memory.manager import MemoryManager
        mm = MemoryManager()
        tasks = mm.list_tasks(status="pending")
        pending_count = tasks.get("count", 0)
        if pending_count > 0:
            alerts.append({"type": "tasks", "level": "info", "message": f"You have {pending_count} pending task(s)."})
    except Exception:
        pass

    # Check triggered reminders
    try:
        from memory.calendar_manager import CalendarManager
        cm = CalendarManager()
        triggered = cm.list_reminders(status="triggered")
        if triggered:
            alerts.append({"type": "reminder", "level": "alert", "message": f"{len(triggered)} reminder(s) need your attention."})
    except Exception:
        pass

    return {
        "success": True,
        "alert_count": len(alerts),
        "alerts": alerts,
        "running_servers": running_servers,
        "timestamp": datetime.now().isoformat(),
    }
