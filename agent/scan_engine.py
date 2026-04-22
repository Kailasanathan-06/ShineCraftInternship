import platform
import subprocess
import concurrent.futures
import sys
import json
from unittest import result
import requests
import datetime
import socket
import psutil
import uuid
import re
from screeninfo import get_monitors
import importlib.util
import struct
import shutil
import ctypes
import os
import getpass
import time
from pathlib import Path

def get_admin_group_members():

    if platform.system() == "Windows":
        out = run_command('net localgroup administrators')
        return out

    elif platform.system() == "Linux":
        return run_command('getent group sudo')

    elif platform.system() == "Darwin":
        return run_command('dscl . read /Groups/admin GroupMembership')
    
def read_sys_file(path):
    try:
        if os.path.exists(path):
            with open(path) as f:
                return f.read().strip()
    except:
        pass
    return None

def tool_exists(tool):
    return shutil.which(tool) is not None

def safe_call(func):

    try:
        return func()

    except Exception as e:
        return {"error": str(e)}

def get_mac_basic():

    return {
        "cpu": run_command("sysctl -n machdep.cpu.brand_string"),
        "ram": run_command("sysctl -n hw.memsize"),
        "kernel": run_command("uname -r")
    }

system=platform.system()
if system == "Windows":
    import winreg
    import wmi

    def install_package(package):
        """Install a package using pip."""
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"Successfully installed {package}")
        except subprocess.CalledProcessError:
            print(f"Failed to install {package}. Try running the script as an administrator.")

def ensure_packages_installed():
    """Ensure external packages are installed."""
    required_packages = ["psutil", "requests", "screeninfo", "wmi"]
    
    for package in required_packages:
        if importlib.util.find_spec(package) is None:
            print(f"Installing missing package: {package}")
            install_package(package)

def run_command(command, timeout=4):
    try:
        result = subprocess.run(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=timeout
        )
        return result.stdout.strip()
    except:
        return None
    
def get_audio_devices():

    """
    Enterprise Audio Inventory
    Returns:
    name, manufacturer, make, model, serial_number, asset_tag
    """

    system = platform.system()
    devices = []

    asset_tag = get_serial_number()

    try:

        # ================= WINDOWS =================
        if system == "Windows":

            out = run_command(
                'powershell "Get-CimInstance Win32_SoundDevice | '
                'Select Name,Manufacturer,PNPDeviceID | ConvertTo-Json"'
            )

            if out:
                data = json.loads(out)

                if isinstance(data, dict):
                    data = [data]

                for d in data:

                    device_id = d.get("PNPDeviceID")

                    serial = None
                    if device_id and "\\" in device_id:
                        serial = device_id.split("\\")[-1]

                    devices.append({
                        "name": d.get("Name"),
                        "manufacturer": d.get("Manufacturer"),
                        "make": d.get("Manufacturer"),
                        "model": d.get("Name"),
                        "serial_number": serial,
                        "asset_tag": asset_tag
                    })

            # ⭐ fallback HID / PnP scan
            if not devices:

                out = run_command(
                    'powershell "Get-PnpDevice | '
                    'Where-Object {$_.FriendlyName -match \'audio|speaker|microphone\'} '
                    '| Select FriendlyName,Manufacturer,InstanceId | ConvertTo-Json"'
                )

                if out:
                    data = json.loads(out)

                    if isinstance(data, dict):
                        data = [data]

                    for d in data:

                        serial = None
                        if d.get("InstanceId"):
                            serial = d["InstanceId"].split("\\")[-1]

                        devices.append({
                            "name": d.get("FriendlyName"),
                            "manufacturer": d.get("Manufacturer"),
                            "make": d.get("Manufacturer"),
                            "model": d.get("FriendlyName"),
                            "serial_number": serial,
                            "asset_tag": asset_tag
                        })

        # ================= LINUX =================
        elif system == "Linux":

            out = run_command("cat /proc/asound/cards")

            if out:
                for line in out.splitlines():
                    if "[" in line:

                        name = line.split("[")[1].split("]")[0]

                        devices.append({
                            "name": name,
                            "manufacturer": None,
                            "make": None,
                            "model": name,
                            "serial_number": None,
                            "asset_tag": asset_tag
                        })

            # ⭐ fallback aplay
            if not devices:

                out = run_command("aplay -l")

                if out:
                    for line in out.splitlines():
                        if "card" in line:
                            devices.append({
                                "name": line.strip(),
                                "manufacturer": None,
                                "make": None,
                                "model": line.strip(),
                                "serial_number": None,
                                "asset_tag": asset_tag
                            })

        # ================= MAC =================
        elif system == "Darwin":

            out = run_command("system_profiler SPAudioDataType -json")

            if out:
                data = json.loads(out)

                for dev in data.get("SPAudioDataType", []):

                    name = dev.get("_name")

                    devices.append({
                        "name": name,
                        "manufacturer": dev.get("coreaudio_device_manufacturer"),
                        "make": dev.get("coreaudio_device_manufacturer"),
                        "model": name,
                        "serial_number": None,
                        "asset_tag": asset_tag
                    })

    except Exception as e:
        devices.append({"error": str(e)})

    return devices

def get_camera_devices():
    """
    Enterprise camera inventory
    Returns: Make, Model, Serial Number, Asset Tag
    Cross-platform safe
    """

    system = platform.system()
    cameras = []

    asset_tag = get_serial_number()

    try:

        # ================= WINDOWS =================
        if system == "Windows":

            out = run_command(
                'powershell "Get-CimInstance Win32_PnPEntity | '
                'Where-Object {$_.PNPClass -eq \'Camera\' -or $_.Name -match \'camera|webcam\'} '
                '| Select Name,Manufacturer,PNPDeviceID | ConvertTo-Json"'
            )

            if out:
                data = json.loads(out)

                if isinstance(data, dict):
                    data = [data]

                for cam in data:

                    device_id = cam.get("PNPDeviceID")

                    # Serial extraction attempt
                    serial = None
                    if device_id and "\\" in device_id:
                        parts = device_id.split("\\")
                        if len(parts) > 2:
                            serial = parts[-1]

                    cameras.append({
                        "name": cam.get("Name"),
                        "manufacturer": cam.get("Manufacturer"),
                        "make": cam.get("Manufacturer"),
                        "model": cam.get("Name"),
                        "serial_number": serial,
                        "asset_tag": asset_tag
                        
                    })

        # ================= LINUX =================
        elif system == "Linux":

            out = run_command("v4l2-ctl --list-devices")

            if out:
                blocks = out.split("\n\n")

                for block in blocks:
                    if "camera" in block.lower():

                        lines = block.splitlines()

                        model = lines[0].strip()

                        cameras.append({
                            "make": None,
                            "model": model,
                            "serial_number": None,
                            "asset_tag": asset_tag
                        })

            # fallback
            if not cameras:
                out = run_command("lsusb")

                if out:
                    for line in out.splitlines():
                        if "camera" in line.lower():
                            cameras.append({
                                "make": None,
                                "model": line,
                                "serial_number": None,
                                "asset_tag": asset_tag
                            })

        # ================= macOS =================
        elif system == "Darwin":

            out = run_command(
                "system_profiler SPCameraDataType -json"
            )

            if out:
                data = json.loads(out)

                for cam in data.get("SPCameraDataType", []):

                    cameras.append({
                        "make": cam.get("spcamera_vendor"),
                        "model": cam.get("_name"),
                        "serial_number": cam.get("spcamera_unique_id"),
                        "asset_tag": asset_tag
                    })

    except Exception as e:
        cameras.append({"error": str(e)})

    return cameras

def get_keyboard_devices():
    """Get keyboard devices (Make | Model | Serial | Asset Tag)."""

    system = platform.system()
    keyboards = []

    asset_tag = None
    try:
        asset_tag = get_system_info()[1]
    except:
        pass

    try:

        # ---------------- WINDOWS ----------------
        if system == "Windows":

            import wmi
            c = wmi.WMI()

            for kb in c.Win32_Keyboard():

                keyboards.append({
                    "name": getattr(kb, "Name", None),  
                    "manufacturer": getattr(kb, "Manufacturer", None),
                    "make": getattr(kb, "Manufacturer", None),
                    "model": getattr(kb, "Name", None) or getattr(kb, "Description", None),
                    "serial_number": setattr(kb, "SerialNumber", "Unavailable") if hasattr(kb, "SerialNumber") else "Unavailable",
                    "asset_tag": asset_tag
                })

        # ---------------- LINUX ----------------
        elif system == "Linux":

            try:
                out = subprocess.check_output(
                    ["lsusb"],
                    text=True
                )

                for line in out.splitlines():
                    if "keyboard" in line.lower():

                        keyboards.append({
                            "make": line.split()[-2] if len(line.split()) > 2 else None,
                            "model": line,
                            "serial_number": "Unavailable",
                            "asset_tag": asset_tag
                        })

            except:
                pass

        # ---------------- macOS ----------------
        elif system == "Darwin":

            try:
                out = subprocess.check_output(
                    ["system_profiler", "SPUSBDataType", "-json"],
                    text=True
                )

                data = json.loads(out)

                def parse_items(items):
                    for item in items:

                        name = item.get("_name", "")

                        if "keyboard" in name.lower():

                            keyboards.append({
                                "make": item.get("manufacturer"),
                                "model": name,
                                "serial_number": item.get("serial_num", "Unavailable"),
                                "asset_tag": asset_tag
                            })

                        if "_items" in item:
                            parse_items(item["_items"])

                for controller in data.get("SPUSBDataType", []):
                    if "_items" in controller:
                        parse_items(controller["_items"])

            except:
                pass

    except Exception as e:
        keyboards.append({
            "error": str(e)
        })

    return keyboards if keyboards else [{
        "make": None,
        "model": "No Keyboard Detected",
        "serial_number": None,
        "asset_tag": asset_tag
    }]

def get_mice_devices():
    """
    Enterprise Mouse Inventory
    Returns:
    name, manufacturer, make, model, serial_number, asset_tag
    """

    system = platform.system()
    mice = []

    asset_tag = get_serial_number()

    try:

        # ================= WINDOWS =================
        if system == "Windows":

            out = run_command(
                'powershell "Get-CimInstance Win32_PointingDevice | '
                'Select Name,Manufacturer,PNPDeviceID | ConvertTo-Json"'
            )

            if out:
                data = json.loads(out)

                if isinstance(data, dict):
                    data = [data]

                for m in data:

                    device_id = m.get("PNPDeviceID")

                    serial = None
                    if device_id and "\\" in device_id:
                        serial = device_id.split("\\")[-1]

                    mice.append({
                        "name": m.get("Name"),
                        "manufacturer": m.get("Manufacturer"),
                        "make": m.get("Manufacturer"),
                        "model": m.get("Name"),
                        "serial_number": serial,
                        "asset_tag": asset_tag
                    })

            # ⭐ fallback HID scan
            if not mice:

                out = run_command(
                    'powershell "Get-PnpDevice | '
                    'Where-Object {$_.FriendlyName -match \'mouse|touchpad\'} '
                    '| Select FriendlyName,Manufacturer,InstanceId | ConvertTo-Json"'
                )

                if out:
                    data = json.loads(out)

                    if isinstance(data, dict):
                        data = [data]

                    for m in data:

                        serial = None
                        if m.get("InstanceId"):
                            serial = m["InstanceId"].split("\\")[-1]

                        mice.append({
                            "name": m.get("FriendlyName"),
                            "manufacturer": m.get("Manufacturer"),
                            "make": m.get("Manufacturer"),
                            "model": m.get("FriendlyName"),
                            "serial_number": serial,
                            "asset_tag": asset_tag
                        })

        # ================= LINUX =================
        elif system == "Linux":

            out = run_command("cat /proc/bus/input/devices")

            if out:
                blocks = out.split("\n\n")

                for b in blocks:
                    if "mouse" in b.lower():

                        name = None
                        for line in b.splitlines():
                            if line.startswith("N: Name="):
                                name = line.split("=")[1].replace('"', '')
                                break

                        mice.append({
                            "name": name,
                            "manufacturer": None,
                            "make": None,
                            "model": name,
                            "serial_number": None,
                            "asset_tag": asset_tag
                        })

        # ================= MAC =================
        elif system == "Darwin":

            out = run_command("system_profiler SPUSBDataType -json")

            if out:
                data = json.loads(out)

                def parse(items):
                    for item in items:

                        name = item.get("_name", "")

                        if "mouse" in name.lower():

                            mice.append({
                                "name": name,
                                "manufacturer": item.get("manufacturer"),
                                "make": item.get("manufacturer"),
                                "model": name,
                                "serial_number": item.get("serial_num"),
                                "asset_tag": asset_tag
                            })

                        if "_items" in item:
                            parse(item["_items"])

                for ctrl in data.get("SPUSBDataType", []):
                    if "_items" in ctrl:
                        parse(ctrl["_items"])

    except Exception as e:
        mice.append({"error": str(e)})

    return mice

def get_mouse_devices():

    system = platform.system()
    mice = []

    try:

        # ---------- WINDOWS ----------
        if system == "Windows":

            out = run_command(
                'powershell "Get-CimInstance Win32_PointingDevice '
                '| Select Name,Manufacturer,PNPDeviceID,DeviceInterface | ConvertTo-Json"'
            )

            if out:
                data = json.loads(out)

                if isinstance(data, dict):
                    data = [data]

                for m in data:
                    mice.append({
                        "Name": m.get("Name"),
                        "Manufacturer": m.get("Manufacturer"),
                        "Model": m.get("Name"),
                        "Make": m.get("Manufacturer"),
                        "Vendor": m.get("Manufacturer"),
                        "Device ID": m.get("PNPDeviceID")
                    })

            # ⭐ FALLBACK HID scan
            if not mice:

                out = run_command(
                    'powershell "Get-PnpDevice | '
                    'Where-Object {$_.FriendlyName -match \'mouse|touchpad\'} '
                    '| Select FriendlyName,Manufacturer,InstanceId | ConvertTo-Json"'
                )

                if out:
                    data = json.loads(out)

                    if isinstance(data, dict):
                        data = [data]

                    for m in data:
                        mice.append({
                            "Name": m.get("FriendlyName"),
                            "Manufacturer": m.get("Manufacturer"),
                            "Make": m.get("Manufacturer"),
                            "Model": m.get("FriendlyName"),
                            "Vendor": m.get("Manufacturer"),
                            "Device ID": m.get("InstanceId")
                        })

        # ---------- LINUX ----------
        elif system == "Linux":

            out = run_command("cat /proc/bus/input/devices")

            if out:
                blocks = out.split("\n\n")

                for b in blocks:
                    if "mouse" in b.lower():
                        mice.append({"Raw": b})

        # ---------- MAC ----------
        elif system == "Darwin":

            out = run_command("system_profiler SPUSBDataType")

            if out:
                for line in out.splitlines():
                    if "mouse" in line.lower():
                        mice.append({"Raw": line.strip()})

    except Exception as e:
        mice.append({"error": str(e)})

    return mice

def get_printer_devices():
    """
    Enterprise Printer Inventory
    Returns:
    name, manufacturer, make, model, serial_number, asset_tag
    """

    system = platform.system()
    printers = []

    asset_tag = get_serial_number()

    try:

        # ================= WINDOWS =================
        if system == "Windows":

            out = run_command(
                'powershell "Get-CimInstance Win32_Printer | '
                'Select Name,DriverName,PortName,PNPDeviceID | ConvertTo-Json"'
            )

            if out:
                data = json.loads(out)

                if isinstance(data, dict):
                    data = [data]

                for p in data:

                    serial = None
                    device_id = p.get("PNPDeviceID")

                    if device_id and "\\" in device_id:
                        serial = device_id.split("\\")[-1]

                    printers.append({
                        "name": p.get("Name"),
                        "manufacturer": p.get("DriverName"),
                        "make": p.get("DriverName"),
                        "model": p.get("Name"),
                        "serial_number": serial,
                        "asset_tag": asset_tag,
                        "port": p.get("PortName")
                    })

        # ================= LINUX =================
        elif system == "Linux":

            out = run_command("lpstat -p")

            if out:
                for line in out.splitlines():
                    if line.startswith("printer"):

                        name = line.split()[1]

                        printers.append({
                            "name": name,
                            "manufacturer": None,
                            "make": None,
                            "model": name,
                            "serial_number": None,
                            "asset_tag": asset_tag
                        })

            # ⭐ fallback USB printers
            if not printers:

                out = run_command("lsusb")

                if out:
                    for line in out.splitlines():
                        if "printer" in line.lower():
                            printers.append({
                                "name": line,
                                "manufacturer": None,
                                "make": None,
                                "model": line,
                                "serial_number": None,
                                "asset_tag": asset_tag
                            })

        # ================= MAC =================
        elif system == "Darwin":

            out = run_command("lpstat -p")

            if out:
                for line in out.splitlines():
                    if line.startswith("printer"):

                        name = line.split()[1]

                        printers.append({
                            "name": name,
                            "manufacturer": None,
                            "make": None,
                            "model": name,
                            "serial_number": None,
                            "asset_tag": asset_tag
                        })

    except Exception as e:
        printers.append({"error": str(e)})

    return printers

def get_product_id():
    """Get the system product ID."""
    if platform.system() == "Windows":
        try:
            
            product_id = run_command("wmic csproduct get UUID")
            if product_id:
                lines = product_id.strip().split("\n")
               
                if len(lines) > 1:
                    return lines[2].strip()  
        except Exception as e:
            print(f"Warning: Failed to get product ID using wmic: {e}")


        return platform.win32_ver()[1]
    elif platform.system() == "Linux":
        return run_command("dmidecode -s system-uuid")    
    elif platform.system() == "Darwin":
        return run_command("ioreg -l | grep IOPlatformUUID | awk '{print $4}' | sed 's/\"//g'")
    else:
        return "Unsupported OS"

def get_user_accounts():
    """Get list of user accounts."""
    users = []

    if platform.system() == "Windows":
        try:
            command = 'powershell "Get-WmiObject -Class Win32_UserAccount | Where-Object { $_.LocalAccount -eq $true } | Select-Object -ExpandProperty Name | ConvertTo-Json"'
            
            output = run_command(command)
            if output:
                users = json.loads(output)
                if isinstance(users, str):  
                    users = [users]
        except Exception as e:
            print(f"Failed to get user accounts: {e}")

    elif platform.system() == "Linux":
        try:
            command = "awk -F: '($3 >= 1000) {print $1}' /etc/passwd"
            output = run_command(command)
            if output:
                users = output.split("\n")
        except Exception as e:
            print(f"Failed to get user accounts: {e}")

    elif platform.system() == "Darwin":
        try:
            command = "dscl . list /Users | grep -v '^_'"
            output = run_command(command)
            if output:
                users = output.split("\n")
        except Exception as e:
            print(f"Failed to get user accounts: {e}")

    return users

def get_battery_info():
    system = platform.system()

    battery = psutil.sensors_battery()

    if battery is not None:
        return {
            "platform": system,
            "percent": battery.percent,
            "charging": battery.power_plugged,
            "time_left_seconds": battery.secsleft
        }

    if system == "Windows":
        try:
            output = subprocess.check_output(
                "WMIC Path Win32_Battery Get EstimatedChargeRemaining,BatteryStatus /Format:List",
                shell=True
            ).decode()

            percent = None
            charging = None

            for line in output.splitlines():
                if "EstimatedChargeRemaining" in line:
                    percent = int(line.split("=")[1])

                if "BatteryStatus" in line:
                    status = int(line.split("=")[1])
                    charging = status == 2

            return {
                "platform": system,
                "percent": percent,
                "charging": charging,
                "time_left_seconds": None
            }

        except:
            pass

    if system == "Linux":
        try:
            output = subprocess.check_output(
                ["upower", "-i", "/org/freedesktop/UPower/devices/battery_BAT0"]
            ).decode()

            percent = None
            charging = None

            for line in output.splitlines():
                if "percentage" in line:
                    percent = int(line.split(":")[1].strip().replace("%", ""))

                if "state" in line:
                    charging = "charging" in line

            return {
                "platform": system,
                "percent": percent,
                "charging": charging,
                "time_left_seconds": None
            }

        except:
            pass

    if system == "Darwin":
        try:
            output = subprocess.check_output(
                ["pmset", "-g", "batt"]
            ).decode()

            percent = int(output.split("\t")[1].split("%")[0])
            charging = "AC Power" in output

            return {
                "platform": system,
                "percent": percent,
                "charging": charging,
                "time_left_seconds": None
            }

        except:
            pass

    return {
        "platform": system,
        "error": "No battery detected"
    }

def get_private_ip():
    system = platform.system()
    hostname = socket.gethostname()

    result = {
        "platform": system,
        "hostname": hostname,
        "primary_ip": None,
        "all_ips": []
    }

    # ---------- METHOD 1 (BEST ROUTING METHOD) ----------
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))   # No real internet required
            result["primary_ip"] = s.getsockname()[0]
    except Exception:
        pass

    # ---------- METHOD 2 (COLLECT ALL INTERFACE IPS) ----------
    try:
        for interface, addrs in psutil.net_if_addrs().items():

            for addr in addrs:

                if addr.family == socket.AF_INET:

                    ip = addr.address

                    # Skip loopback
                    if ip.startswith("127."):
                        continue

                    # Skip APIPA (No DHCP assigned)
                    if ip.startswith("169.254."):
                        continue

                    result["all_ips"].append({
                        "interface": interface,
                        "ip": ip
                    })

                    # fallback primary
                    if result["primary_ip"] is None:
                        result["primary_ip"] = ip

    except Exception:
        pass

    # ---------- FINAL ----------
    if result["primary_ip"] is None:
        result["primary_ip"] = "Unavailable"

    return result

def get_network_interfaces():
    """Get network interfaces (Windows / Linux / macOS)."""

    interfaces = []
    system = platform.system()

    try:
        addrs = psutil.net_if_addrs()
        stats = psutil.net_if_stats()

        for interface_name, addr_list in addrs.items():

            mac = None
            ipv4 = None
            ipv6 = None

            for addr in addr_list:

                if addr.family == socket.AF_INET:
                    ipv4 = addr.address

                elif addr.family == socket.AF_INET6:
                    ipv6 = addr.address

                elif addr.family == psutil.AF_LINK:
                    mac = addr.address

            interface_info = {
                "platform": system,
                "name": interface_name,
                "mac_address": mac,
                "ipv4": ipv4,
                "ipv6": ipv6,
                "is_up": stats[interface_name].isup if interface_name in stats else None,
                "speed_mbps": stats[interface_name].speed if interface_name in stats else None,
                "mtu": stats[interface_name].mtu if interface_name in stats else None
            }

            interfaces.append(interface_info)

    except Exception as e:
        print(f"Network interface error: {e}")

    return interfaces

def get_bluetooth_devices():

    system = platform.system()
    devices = []
    try:

        if system == "Windows":

            devices = []

            # ⭐ METHOD 1 — PowerShell modern
            output = run_command(
                'powershell "Get-PnpDevice -Class Bluetooth | '
                'Select FriendlyName, Status | ConvertTo-Json"'
            )

            if output:
                try:
                    data = json.loads(output)
                    if isinstance(data, dict):
                        data = [data]
                    return data
                except:
                    pass

            # ⭐ METHOD 2 — WMIC fallback (VERY IMPORTANT)
            output = run_command(
                'wmic path Win32_PnPEntity where "Name like \'%Bluetooth%\'" get Name /format:csv'
            )

            if output:
                for line in output.splitlines():
                    if "Bluetooth" in line:
                        devices.append({"name": line.strip()})

            if devices:
                return devices

            # ⭐ METHOD 3 — service detection fallback
            output = run_command("sc query bthserv")

            if output:
                return [{"Bluetooth Service": "Present"}]

            return []

        elif system == "Linux":

            if not tool_exists("bluetoothctl"):
                return []

            output = run_command("bluetoothctl devices")

            if not output:
                return []

            for line in output.splitlines():
                devices.append({"device": line})

            return devices

        elif system == "Darwin":

            output = run_command(
                "system_profiler SPBluetoothDataType"
            )

            if not output:
                return []

            return [{"raw": output}]

    except:
        pass

    return []
 
def get_loopback_interface():
    """Get loopback interfaces (Windows / Linux / macOS)."""

    loopbacks = []
    system = platform.system()

    try:
        interfaces = psutil.net_if_addrs()
        stats = psutil.net_if_stats()

        for interface, addrs in interfaces.items():

            for addr in addrs:

                if addr.family == socket.AF_INET and addr.address.startswith("127."):

                    loopbacks.append({
                        "platform": system,
                        "interface": interface,
                        "ip_address": addr.address,
                        "is_up": stats[interface].isup if interface in stats else None,
                        "mtu": stats[interface].mtu if interface in stats else None
                    })

    except Exception as e:
        print(f"Loopback error: {e}")

    return loopbacks
    
def get_dns_servers():
    try:
        if platform.system() == "Windows":
            result = subprocess.check_output("nslookup google.com", shell=True).decode()
            for line in result.split("\n"):
                if "Address" in line:
                    return line.split(":")[-1].strip()
        elif platform.system() == "Linux" or platform.system() == "Darwin":  

            try:
                with open("/etc/resolv.conf") as f:
                    for line in f:
                        if line.startswith("nameserver"):
                            return line.split()[1]
            except:
                pass
    except:
        return "Unavailable"

def get_security_status():
    """Get Antivirus / Security status (Windows / Linux / macOS)."""

    system = platform.system()

    result = {
        "platform": system,
        "antivirus": None,
        "realtime_protection": None,
        "version": None,
        "firewall": None
    }

    try:

        # ---------------- WINDOWS ----------------
        if system == "Windows":

            command = [
                "powershell",
                "-Command",
                "Get-MpComputerStatus | "
                "Select AntivirusEnabled, RealTimeProtectionEnabled, AMProductVersion | ConvertTo-Json"
            ]

            output = subprocess.check_output(command, text=True)

            if output.strip():
                data = json.loads(output)

                result["antivirus"] = data.get("AntivirusEnabled")
                result["realtime_protection"] = data.get("RealTimeProtectionEnabled")
                result["version"] = data.get("AMProductVersion")

        # ---------------- LINUX ----------------
        elif system == "Linux":

            # Firewall status (ufw)
            try:
                fw = subprocess.check_output(
                    ["ufw", "status"],
                    text=True
                )
                result["firewall"] = "active" in fw.lower()
            except:
                result["firewall"] = None

            # SELinux status
            try:
                se = read_sys_file("/sys/class/dmi/id/sys_vendor") or "Unavailable"
                result["antivirus"] = f"SELinux ({se})"
            except:
                pass

        # ---------------- macOS ----------------
        elif system == "Darwin":

            # Firewall status
            try:
                fw = subprocess.check_output(
                    ["/usr/libexec/ApplicationFirewall/socketfilterfw", "--getglobalstate"],
                    text=True
                )
                result["firewall"] = "enabled" in fw.lower()
            except:
                pass

            # SIP Status
            try:
                sip = subprocess.check_output(
                    ["csrutil", "status"],
                    text=True
                )
                result["antivirus"] = "SIP " + sip.strip()
            except:
                pass

    except Exception as e:
        print("Security status error:", e)

    return result

def get_dhcp_server():
    system = platform.system()

    result = {
        "platform": system,
        "dhcp_servers": []
    }

    try:

        # ---------------- WINDOWS ----------------
        if system == "Windows":

            output = subprocess.check_output(
                ["ipconfig", "/all"],
                text=True,
                errors="ignore"
            )

            for line in output.splitlines():
                if "DHCP Server" in line:
                    ip = line.split(":")[-1].strip()

                    if ip and ip not in result["dhcp_servers"]:
                        result["dhcp_servers"].append(ip)

        # ---------------- LINUX ----------------
        elif system == "Linux":

            try:
                output = subprocess.check_output(
                    ["nmcli", "-t", "dev", "show"],
                    text=True
                )

                for line in output.splitlines():
                    if "DHCP4.OPTION" in line and "dhcp_server_identifier" in line:
                        ip = line.split("=")[-1].strip()

                        if ip not in result["dhcp_servers"]:
                            result["dhcp_servers"].append(ip)

            except:
                pass

            # fallback → parse /var/lib/dhcp
            try:
                output = subprocess.check_output(
                    ["grep", "-r", "dhcp-server-identifier", "/var/lib"],
                    text=True,
                    stderr=subprocess.DEVNULL
                )

                for part in output.split():
                    if part.count(".") == 3:
                        if part not in result["dhcp_servers"]:
                            result["dhcp_servers"].append(part)

            except:
                pass

        # ---------------- macOS ----------------
        elif system == "Darwin":

            try:
                output = subprocess.check_output(
                    ["ipconfig", "getpacket", "en0"],
                    text=True
                )

                for line in output.splitlines():
                    if "server_identifier" in line:
                        ip = line.split("=")[-1].strip()

                        if ip not in result["dhcp_servers"]:
                            result["dhcp_servers"].append(ip)

            except:
                pass

    except Exception as e:
        print("DHCP detection error:", e)

    if not result["dhcp_servers"]:
        result["dhcp_servers"] = "Unavailable"

    return result

# def get_hard_disk_info():

#     system = platform.system()
#     disks = []

#     try:

#         # ---------- WINDOWS ----------
#         if system == "Windows":

#             out = run_command(
#                 'powershell "Get-WmiObject Win32_DiskDrive | '
#                 'Select Model,Manufacturer,SerialNumber,Size | ConvertTo-Json"'
#             )

#             if out:
#                 data = json.loads(out)

#                 if isinstance(data, dict):
#                     data = [data]

#                 for d in data:
#                     disks.append({
#                         "Model": d.get("Model"),
#                         "Manufacturer": d.get("Manufacturer"),
#                         "Serial Number": d.get("SerialNumber"),
#                         "Size GB": round(int(d.get("Size", 0))/(1024**3),2)
#                     })

#         # ---------- LINUX ----------
#         elif system == "Linux":

#             out = run_command("lsblk -d -o NAME,MODEL,SERIAL,VENDOR,SIZE -J")

#             if out:
#                 data = json.loads(out)

#                 for d in data.get("blockdevices", []):
#                     disks.append({
#                         "Name": d.get("name"),
#                         "Model": d.get("model"),
#                         "Manufacturer": d.get("vendor"),
#                         "Serial Number": d.get("serial"),
#                         "Size": d.get("size")
#                     })

#         # ---------- MAC ----------
#         elif system == "Darwin":

#             out = run_command("system_profiler SPStorageDataType -json")

#             if out:
#                 data = json.loads(out)

#                 for item in data.get("SPStorageDataType", []):
#                     disks.append({
#                         "Model": item.get("_name"),
#                         "Serial Number": item.get("serial_num"),
#                         "Manufacturer": item.get("vendor"),
#                         "Size": item.get("size_in_bytes")
#                     })

#     except Exception as e:
#         disks.append({"error": str(e)})

#     return disks

def get_disk_health():
    """Get disk health (Windows / Linux / macOS)."""

    system = platform.system()
    disks = []

    try:

        # ---------------- WINDOWS ----------------
        if system == "Windows":

            cmd = [
                "powershell",
                "-Command",
                "Get-PhysicalDisk | "
                "Select FriendlyName, MediaType, HealthStatus, Size | ConvertTo-Json"
            ]

            output = subprocess.check_output(cmd, text=True)

            if output.strip():
                data = json.loads(output)

                if isinstance(data, dict):
                    data = [data]

                for d in data:
                    disks.append({
                        "platform": system,
                        "name": d.get("FriendlyName"),
                        "type": d.get("MediaType"),
                        "health": d.get("HealthStatus"),
                        "size_gb": round(int(d.get("Size", 0)) / (1024**3), 2)
                    })

        # ---------------- LINUX ----------------
        elif system == "Linux":

            output = subprocess.check_output(
                ["lsblk", "-d", "-o", "NAME,ROTA,SIZE,MODEL", "-J"],
                text=True
            )

            data = json.loads(output)

            for d in data.get("blockdevices", []):
                disks.append({
                    "platform": system,
                    "name": d.get("name"),
                    "type": "HDD" if d.get("rota") == True else "SSD",
                    "health": "Unknown",
                    "size": d.get("size"),
                    "model": d.get("model")
                })

        # ---------------- macOS ----------------
        elif system == "Darwin":

            output = subprocess.check_output(
                ["diskutil", "list", "-plist"],
                text=True
            )

            # macOS plist → treat simple parsing
            raw = subprocess.check_output(
                ["diskutil", "info", "-all"],
                text=True
            )

            current_disk = None

            for line in raw.splitlines():

                if "Device Identifier" in line:
                    current_disk = line.split(":")[-1].strip()

                if "Solid State" in line and current_disk:
                    disks.append({
                        "platform": system,
                        "name": current_disk,
                        "type": "SSD" if "Yes" in line else "HDD",
                        "health": "Unknown"
                    })
                    current_disk = None

    except Exception as e:
        print("Disk health error:", e)

    return disks

def get_usb_devices():

    system = platform.system()
    devices = []

    try:

        if system == "Windows":

            output = run_command(
                'powershell "Get-PnpDevice -Class USB | '
                'Select FriendlyName, Status | ConvertTo-Json"'
            )

            if not output:
                return []

            data = json.loads(output)

            if isinstance(data, dict):
                data = [data]

            return data

        elif system == "Linux":

            if not tool_exists("lsusb"):
                return []

            output = run_command("lsusb")

            if not output:
                return []

            for line in output.splitlines():
                devices.append({"device": line})

            return devices

        elif system == "Darwin":

            output = run_command("system_profiler SPUSBDataType")

            if not output:
                return []

            return [{"raw": output}]

    except:
        pass

    return []

def get_firewall_status():
    """Get firewall status (Windows / Linux / macOS)."""

    system = platform.system()

    result = {
        "platform": system,
        "profiles": []
    }

    try:

        # ---------------- WINDOWS ----------------
        if system == "Windows":

            cmd = [
                "powershell",
                "-Command",
                "Get-NetFirewallProfile | "
                "Select Name, Enabled | ConvertTo-Json"
            ]

            output = subprocess.check_output(cmd, text=True)

            if output.strip():
                data = json.loads(output)

                if isinstance(data, dict):
                    data = [data]

                for p in data:
                    result["profiles"].append({
                        "profile": p.get("Name"),
                        "enabled": p.get("Enabled")
                    })

        # ---------------- LINUX ----------------
        elif system == "Linux":

            if tool_exists("ufw"):
                status=run_command("ufw status")

            # Try UFW first (Ubuntu / Kali etc.)
            try:
                ufw = subprocess.check_output(
                    ["ufw", "status"],
                    text=True
                )

                result["profiles"].append({
                    "profile": "ufw",
                    "enabled": "active" in ufw.lower()
                })

            except:
                pass

            # Fallback → firewalld
            try:
                fw = subprocess.check_output(
                    ["firewall-cmd", "--state"],
                    text=True
                ).strip()

                result["profiles"].append({
                    "profile": "firewalld",
                    "enabled": fw == "running"
                })

            except:
                pass

        # ---------------- macOS ----------------
        elif system == "Darwin":

            try:
                fw = subprocess.check_output(
                    ["/usr/libexec/ApplicationFirewall/socketfilterfw", "--getglobalstate"],
                    text=True
                )

                result["profiles"].append({
                    "profile": "ApplicationFirewall",
                    "enabled": "enabled" in fw.lower()
                })

            except:
                pass

    except Exception as e:
        print("Firewall detection error:", e)

    if not result["profiles"]:
        result["profiles"] = "Unavailable"

    return result
    
def parse_edid_for_model(edid):
    """
    Parse EDID bytes and return structured monitor info.
    Works for EDID 1.3+ descriptor format.
    """

    result = {
        "model": "Unknown Monitor",
        "manufacturer": None,
        "product_id": None,
        "week": None,
        "year": None
    }

    try:
        if not edid or not isinstance(edid, (bytes, bytearray)):
            return result

        edid = bytearray(edid)

        # ---------- Manufacture Date ----------
        if len(edid) >= 18:
            result["week"] = edid[16]
            result["year"] = 1990 + edid[17]

        # ---------- Descriptor Scan ----------
        for i in range(4):
            offset = 54 + (i * 18)

            if len(edid) < offset + 18:
                continue

            # Proper display name descriptor check
            if (
                edid[offset] == 0x00 and
                edid[offset + 1] == 0x00 and
                edid[offset + 2] == 0x00 and
                edid[offset + 3] == 0xFC
            ):
                raw = edid[offset + 5: offset + 18]

                name = raw.split(b'\x0a')[0].split(b'\x00')[0]

                try:
                    name = name.decode("ascii", errors="ignore").strip()
                except:
                    name = ""

                if name:
                    result["model"] = name
                    return result

        # ---------- Manufacturer Decode ----------
        if len(edid) >= 12:

            mfg_raw = (edid[8] << 8) | edid[9]

            letters = []
            for shift in (10, 5, 0):
                val = (mfg_raw >> shift) & 0x1F
                if 1 <= val <= 26:
                    letters.append(chr(val + 64))

            manufacturer = "".join(letters)

            product_id = (edid[11] << 8) | edid[10]

            manufacturer_map = {
                "ACI": "Asus",
                "ACR": "Acer",
                "AOC": "AOC",
                "AUO": "AU Optronics",
                "DEL": "Dell",
                "HPN": "HP",
                "HWP": "HP",
                "LEN": "Lenovo",
                "LGD": "LG Display",
                "LPL": "LG Philips",
                "NEC": "NEC",
                "SAM": "Samsung",
                "SEC": "Samsung",
                "SHP": "Sharp",
                "SNY": "Sony",
                "VSC": "ViewSonic"
            }

            manufacturer_full = manufacturer_map.get(manufacturer, manufacturer)
            serial = None

            if len(edid) >= 20:
                serial = struct.unpack("<I", edid[12:16])[0]

            result["serial_number"] = serial
            result["manufacturer"] = manufacturer_full
            result["product_id"] = product_id
            result["model"] = f"{manufacturer_full} Monitor"

        return result

    except Exception as e:
        print("EDID parsing error:", e)
        return result

def get_edids_windows():
    """Extract all monitor EDIDs from Windows registry (professional version)."""

    if platform.system() != "Windows":
        return []

    edids = []
    seen = set()

    registry_roots = [
        r"SYSTEM\CurrentControlSet\Enum\DISPLAY",
        r"SYSTEM\ControlSet001\Enum\MONITOR"
    ]

    try:
        for root in registry_roots:

            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, root) as root_key:

                    i = 0
                    while True:
                        try:
                            vendor_key_name = winreg.EnumKey(root_key, i)
                            vendor_path = f"{root}\\{vendor_key_name}"

                            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, vendor_path) as vendor_key:

                                j = 0
                                while True:
                                    try:
                                        instance_name = winreg.EnumKey(vendor_key, j)
                                        params_path = f"{vendor_path}\\{instance_name}\\Device Parameters"

                                        try:
                                            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, params_path) as params_key:
                                                edid = winreg.QueryValueEx(params_key, "EDID")[0]

                                                if not isinstance(edid, (bytes, bytearray)):
                                                    edid = bytes(edid)

                                                fingerprint = hash(edid)

                                                if fingerprint not in seen:
                                                    seen.add(fingerprint)

                                                    edids.append({
                                                        "registry_root": root,
                                                        "vendor_id": vendor_key_name,
                                                        "instance_id": instance_name,
                                                        "edid": edid
                                                    })

                                        except FileNotFoundError:
                                            pass

                                        j += 1

                                    except OSError:
                                        break

                            i += 1

                        except OSError:
                            break

            except FileNotFoundError:
                continue

        return edids

    except Exception as e:
        print("Windows EDID extraction error:", e)
        return []

def get_monitor_details():
    """
    Universal Monitor Detection
    Windows / Linux / macOS
    Enterprise structured output
    """

    system = platform.system()
    monitors = []

    asset_tag = get_serial_number()

    try:

        # ================= WINDOWS =================
        if system == "Windows":

            try:
                edids = get_edids_windows()
            except:
                edids = []

            parsed = []

            for item in edids:
                parsed.append(parse_edid_for_model(item["edid"]))

            basic = []
            try:
                basic = list(get_monitors())
            except:
                pass

            for i, m in enumerate(basic):

                info = parsed[i] if i < len(parsed) else {}

                monitors.append({
                    "name": info.get("name"),
                    "manufacturer": info.get("manufacturer"),
                    "model": info.get("model"),
                    "serial_number": info.get("serial_number"),
                    "resolution": f"{m.width}x{m.height}",
                    "primary": (m.x == 0 and m.y == 0),
                    "asset_tag": asset_tag
                })

        # ================= LINUX =================
        elif system == "Linux":

            out = run_command("xrandr --query")

            if out:
                for line in out.splitlines():

                    if " connected" in line:

                        parts = line.split()

                        name = parts[0]
                        res = next((p for p in parts if "x" in p), None)

                        monitors.append({
                            "name": name,
                            "manufacturer": None,
                            "model": name,
                            "serial_number": None,
                            "resolution": res,
                            "primary": "primary" in line,
                            "asset_tag": asset_tag
                        })

        # ================= MAC =================
        elif system == "Darwin":

            out = run_command("system_profiler SPDisplaysDataType -json")

            if out:
                data = json.loads(out)

                for gpu in data.get("SPDisplaysDataType", []):

                    for d in gpu.get("spdisplays_ndrvs", []):

                        monitors.append({
                            "name": d.get("_name"),
                            "manufacturer": None,
                            "model": d.get("_name"),
                            "serial_number": None,
                            "resolution": d.get("spdisplays_resolution"),
                            "primary": True,
                            "asset_tag": asset_tag
                        })

    except Exception as e:
        monitors.append({"error": str(e)})

    return monitors if monitors else [{"error": "No monitor detected"}]

def get_system_accounts():

    system = platform.system()
    accounts = []

    try:

        # -------- WINDOWS --------
        if system == "Windows":

            out = run_command(
                'powershell "Get-WmiObject Win32_UserAccount | '
                'Select Name,Domain,SID,Disabled,Description,LocalAccount | ConvertTo-Json"'
            )

            if out:
                data = json.loads(out)

                if isinstance(data, dict):
                    data = [data]

                for u in data:
                    accounts.append({
                        "Computer Name": socket.gethostname(),
                        "Account Name": u.get("Name"),
                        "Domain": u.get("Domain"),
                        "Description": u.get("Description"),
                        "Status": "Disabled" if u.get("Disabled") else "Enabled",
                        "SID": u.get("SID")
                    })

        # -------- LINUX --------
        elif system == "Linux":

            out = run_command("getent passwd")

            for line in out.splitlines():
                parts = line.split(":")
                accounts.append({
                    "Computer Name": socket.gethostname(),
                    "Account Name": parts[0],
                    "Domain": "Local",
                    "Description": parts[4],
                    "Status": "Enabled",
                    "SID": parts[2]
                })

        # -------- MAC --------
        elif system == "Darwin":

            out = run_command("dscl . list /Users UniqueID")

            for line in out.splitlines():
                parts = line.split()
                accounts.append({
                    "Computer Name": socket.gethostname(),
                    "Account Name": parts[0],
                    "Domain": "Local",
                    "Description": "",
                    "Status": "Enabled",
                    "SID": parts[1]
                })

    except:
        pass

    return accounts

def get_system_info():
    try:
        if platform.system() == "Windows":
            manufacturer = subprocess.check_output(
                "wmic computersystem get manufacturer",
                shell=True
            ).decode().split("\n")[1].strip()

            model = subprocess.check_output(
                "wmic computersystem get model",
                shell=True
            ).decode().split("\n")[1].strip()

            serial_number = subprocess.check_output(
                "wmic bios get serialnumber",
                shell=True
            ).decode().split("\n")[1].strip()
        elif platform.system() == "Linux":

            manufacturer = (
                read_sys_file("/sys/class/dmi/id/sys_vendor")
                or read_sys_file("/sys/devices/virtual/dmi/id/sys_vendor")
                or "Unavailable"
            )

            serial_number = (
                read_sys_file("/sys/class/dmi/id/product_serial")
                or read_sys_file("/etc/machine-id")
                or run_command("dmidecode -s system-serial-number")
                or "Unavailable"
            )

        elif platform.system() == "Darwin": 
            manufacturer = "Apple"
            serial_number = run_command("ioreg -l | grep IOPlatformSerialNumber").split('"')[3].strip()
        return manufacturer, serial_number
    except:
        return "Unavailable", "Unavailable"

def get_geo_location():
    """Get geolocation info using public IP (cross-platform safe)."""

    result = {
        "public_ip": None,
        "country": None,
        "region": None,
        "city": None,
        "isp": None,
        "latitude": None,
        "longitude": None
    }

    apis = [
        "https://ipinfo.io/json",
        "https://ipapi.co/json/",
        "https://ipwho.is/"
    ]

    for url in apis:

        try:
            r = requests.get(url, timeout=3)

            if r.status_code != 200:
                continue

            data = r.json()

            # -------- ipinfo --------
            if "ipinfo" in url:
                result["public_ip"] = data.get("ip")
                result["country"] = data.get("country")
                result["region"] = data.get("region")
                result["city"] = data.get("city")
                result["isp"] = data.get("org")

                if "loc" in data:
                    lat, lon = data["loc"].split(",")
                    result["latitude"] = lat
                    result["longitude"] = lon

                break

            # -------- ipapi --------
            elif "ipapi" in url:
                result["public_ip"] = data.get("ip")
                result["country"] = data.get("country_name")
                result["region"] = data.get("region")
                result["city"] = data.get("city")
                result["isp"] = data.get("org")
                result["latitude"] = data.get("latitude")
                result["longitude"] = data.get("longitude")

                break

            # -------- ipwhois --------
            elif "ipwho" in url:
                result["public_ip"] = data.get("ip")
                result["country"] = data.get("country")
                result["region"] = data.get("region")
                result["city"] = data.get("city")
                result["isp"] = data.get("connection", {}).get("isp")
                result["latitude"] = data.get("latitude")
                result["longitude"] = data.get("longitude")

                break

        except Exception:
            continue

    # final fallback
    for k in result:
        if result[k] is None:
            result[k] = "Unavailable"

    return result

def get_network_info():
    """Get full network interface information (professional version)."""

    system = platform.system()

    result = {
        "platform": system,
        "interfaces": []
    }

    try:
        addrs = psutil.net_if_addrs()
        stats = psutil.net_if_stats()

        for interface_name, addr_list in addrs.items():

            interface_obj = {
                "name": interface_name,
                "mac": None,
                "ipv4": [],
                "ipv6": [],
                "is_up": None,
                "speed_mbps": None,
                "mtu": None
            }

            # -------- Addresses --------
            for addr in addr_list:

                if addr.family == socket.AF_INET:
                    interface_obj["ipv4"].append(addr.address)

                elif addr.family == socket.AF_INET6:
                    interface_obj["ipv6"].append(addr.address)

                elif addr.family == psutil.AF_LINK:
                    interface_obj["mac"] = addr.address

            # -------- Stats --------
            if interface_name in stats:
                interface_obj["is_up"] = stats[interface_name].isup
                interface_obj["speed_mbps"] = stats[interface_name].speed
                interface_obj["mtu"] = stats[interface_name].mtu

            result["interfaces"].append(interface_obj)

    except Exception as e:
        print("Network info error:", e)

    return result

def get_serial_number():
    """Get the system serial number safely."""
    try:
        if platform.system() == "Windows":
            result = run_command(
                'powershell -Command "(Get-CimInstance Win32_BIOS).SerialNumber"'
            )
            if result:
                return result.strip()
            return "Unavailable"
        elif platform.system() == "Linux":
            result = (
                read_sys_file("/sys/class/dmi/id/product_serial")
                or run_command("dmidecode -s system-serial-number")
                or read_sys_file("/etc/machine-id")
            )
            return result if result else "Unavailable"
        elif platform.system() == "Darwin":
            result = run_command(
                "ioreg -l | grep IOPlatformSerialNumber | awk '{print $4}' | sed 's/\"//g'"
            )
            if result:
                return result.strip()
            return "Unavailable"
        return "Unsupported OS"
    except Exception as e:
        print("Serial number extraction error:", e)
        return "Unavailable"

def get_product_name():
    """Get the system product name."""
    if platform.system() == "Windows":
        try:
            command = 'powershell "Get-WmiObject -Class Win32_ComputerSystem | Select-Object -ExpandProperty Model"'
            return run_command(command) or "Unknown"
        except Exception as e:
            print(f"Failed to get product name: {e}")

    elif platform.system() == "Linux":
        try:
            return run_command("dmidecode -s system-product-name") or "Unknown"
        except Exception as e:
            print(f"Failed to get product name: {e}")

    elif platform.system() == "Darwin":
        try:
            return run_command("sysctl -n hw.model") or "Unknown"
        except Exception as e:
            print(f"Failed to get product name: {e}")

    return "Unsupported OS"

def get_bios_info():
    """Get BIOS information."""
    if platform.system() == "Windows":
        try:
            command = 'powershell "Get-WmiObject -Class Win32_BIOS | Select-Object -Property SMBIOSBIOSVersion, Manufacturer, ReleaseDate | ConvertTo-Json"'
            output = run_command(command)
            if output:
                bios_data = json.loads(output)
                date = bios_data.get("ReleaseDate", "Unknown")
                if date and len(date) >= 8:
                    date = f"{date[:4]}-{date[4:6]}-{date[6:8]}"
                return {
                    "Version": bios_data.get("SMBIOSBIOSVersion", "Unknown"),
                    "Manufacturer": bios_data.get("Manufacturer", "Unknown"),
                    "Date": date
                }
        except Exception as e:
            print(f"Failed to get BIOS info: {e}")

    elif platform.system() == "Linux":
        try:
            version = run_command("dmidecode -s bios-version")
            manufacturer = run_command("dmidecode -s bios-vendor")
            date = run_command("dmidecode -s bios-release-date")
            return {
                "Version": version if version else "Unknown",
                "Manufacturer": manufacturer if manufacturer else "Unknown",
                "Date": date if date else "Unknown"
            }
        except Exception as e:
            print(f"Failed to get BIOS info: {e}")

    elif platform.system() == "Darwin":
        try:
            version = run_command("system_profiler SPHardwareDataType | grep 'Boot ROM Version' | awk -F: '{print $2}'").strip()
            return {
                "Version": version if version else "Unknown",
                "Manufacturer": "Apple",
                "Date": "N/A"
            }
        except Exception as e:
            print(f"Failed to get BIOS info: {e}")

    return {
        "Version": "Unsupported OS",
        "Manufacturer": "Unsupported OS",
        "Date": "Unsupported OS"
    }

def get_os_info():
    """Professional OS information collector (Windows / Linux / macOS)."""

    system = platform.system()
    

    result = {
        "platform": system,
        "os_name": None,
        "os_version": None,
        "kernel_version": None,
        "build": None,
        "architecture": platform.machine(),
        "bitness": platform.architecture()[0],
        "hostname": socket.gethostname(),
        "fqdn": socket.getfqdn(),
        "user": None,
        "boot_time": None,
        "uptime_seconds": None,
        "system_type": platform.machine() + "-based PC"
    }

    try:
        # ---------- Boot Time ----------
        boot = psutil.boot_time()
        result["boot_time"] = datetime.datetime.fromtimestamp(boot).isoformat()
        result["uptime_seconds"] = int(datetime.datetime.now().timestamp() - boot)
    except:
        pass

    try:
        result["user"] = get_logged_in_user()
    except:
        pass

    # ---------- WINDOWS ----------
    if system == "Windows":
        result["os_name"] = platform.system()
        result["registered_to"] = os.environ.get("USERNAME")
        result["os_version"] = platform.version()
        result["domain_name"] = socket.getfqdn()
        result["kernel_version"] = platform.release()
        result["build"] = platform.win32_ver()[1]
        result["service_pack"]=platform.win32_ver()[2]
        

        try:
            result["product_id"] = get_product_id()
        except:
            result["product_id"] = None

    # ---------- LINUX ----------
    elif system == "Linux":

        try:
            import distro
            result["os_name"] = distro.name(pretty=True)
            result["os_version"] = distro.version()
        except:
            result["os_name"] = "Linux"

        result["kernel_version"] = platform.release()

    # ---------- macOS ----------
    elif system == "Darwin":

        mac_ver = platform.mac_ver()

        result["os_name"] = "macOS"
        result["os_version"] = mac_ver[0]
        result["kernel_version"] = platform.release()

    return result

def get_vendor_warranty_info():

    manufacturer, serial = get_system_info()

    result = {
        "Vendor Name": manufacturer,
        "Serial Number": serial,
        "Purchase Cost": None,
        "Asset Created Date": None,
        "Warranty Expiry Date": None,
        "Warranty Status": None
    }

    try:

        # ---------- DELL ----------
        if "Dell" in manufacturer:

            url = f"https://api.dell.com/support/v2/assetinfo/warranty/tags.json?svctags={serial}"

            r = requests.get(url, timeout=5)

            if r.status_code == 200:

                data = r.json()

                ent = data["GetAssetWarrantyResponse"]["GetAssetWarrantyResult"]["Response"]["DellAsset"]

                result["Warranty Expiry Date"] = ent["Warranties"]["Warranty"][0]["EndDate"]
                result["Asset Created Date"] = ent["ShipDate"]
                result["Warranty Status"] = "Active"

        # ---------- HP ----------
        elif "HP" in manufacturer:

            url = f"https://support.hp.com/us-en/check-warranty?serialnumber={serial}"

            r = requests.get(url, timeout=5)

            if r.status_code == 200:
                result["Warranty Status"] = "Fetched (HP page response)"

        # ---------- LENOVO ----------
        elif "Lenovo" in manufacturer:

            url = f"https://pcsupport.lenovo.com/us/en/api/v4/mse/getproducts?productId={serial}"

            r = requests.get(url, timeout=5)

            if r.status_code == 200:
                result["Warranty Status"] = "Fetched (Lenovo API response)"

    except Exception as e:
        result["error"] = str(e)

    return result

def get_rdp_group_members():

    system = platform.system()

    result = {
        "rdp_group_users": None,
        "active_rdp_sessions": None
    }

    try:

        if system == "Windows":

            # -------- GROUP MEMBERS --------
            group = run_command(
                'powershell "Get-LocalGroupMember -Group \'Remote Desktop Users\' '
                '| Select Name,ObjectClass | ConvertTo-Json"'
            )

            if group:
                result["rdp_group_users"] = json.loads(group)

            # -------- ADMIN USERS (CAN ALSO RDP) --------
            admin = run_command(
                'powershell "Get-LocalGroupMember -Group Administrators '
                '| Select Name,ObjectClass | ConvertTo-Json"'
            )

            result["admin_users"] = json.loads(admin) if admin else None

            # -------- ACTIVE RDP SESSIONS --------
            sessions = run_command("query user")

            result["active_rdp_sessions"] = sessions

        elif system == "Linux":

            result["rdp_group_users"] = run_command("getent group xrdp")

        elif system == "Darwin":

            result["rdp_group_users"] = run_command(
                "dscl . read /Groups/com.apple.access_screensharing GroupMembership"
            )

    except Exception as e:
        result["error"] = str(e)

    return result

def get_cpu_info():
    """Get CPU information."""
    cpu_info = {}
    if platform.system() == "Windows":
        try:
            command = 'powershell "Get-WmiObject Win32_Processor | Select Manufacturer, Name, ProcessorId, NumberOfCores, NumberOfLogicalProcessors, MaxClockSpeed | ConvertTo-Json"'
            output = run_command(command)

            if output:

                cpu = json.loads(output)

                if isinstance(cpu, list):
                    cpu = cpu[0]

                cpu_info = {
                    "Manufacturer": cpu.get("Manufacturer"),
                    "Model": cpu.get("Name"),
                    "Serial Number": cpu.get("ProcessorId"),
                    "Architecture": platform.machine(),
                    "Cores": cpu.get("NumberOfCores"),
                    "Logical Processors": cpu.get("NumberOfLogicalProcessors"),
                    "Processor Speed (MHz)": cpu.get("MaxClockSpeed")
                }

        except Exception as e:
            cpu_info["Error"] = str(e)
    elif platform.system() == "Linux":

        vendor = run_command("lscpu | grep 'Vendor ID'")
        model = run_command("lscpu | grep 'Model name'")

        cpu_info["Manufacturer"] = vendor.split(":")[1].strip() if vendor else "Unknown"
        cpu_info["Model"] = model.split(":")[1].strip() if model else "Unknown"
        cpu_info["Architecture"] = platform.machine()

        cores = run_command("nproc")
        cpu_info["Cores"] = int(cores) if cores else None

    elif platform.system() == "Darwin":
        cpu_info["Manufacturer"] = "Apple"
        cpu_info["Model"] = run_command('sysctl -n machdep.cpu.brand_string').strip()
        cpu_info["Serial Number"] = "N/A"
        cpu_info["Architecture"] = platform.machine()
        cpu_info["Cores"] = int(run_command('sysctl -n hw.ncpu').strip())
        cpu_info["Logical Processors"] = int(run_command('sysctl -n hw.ncpu').strip())
        cpu_info["Processor Speed (GHz)"] = run_command('sysctl -n hw.cpufrequency_max').strip() + " MHz"
    return cpu_info

def get_gpu_info():
    """Cross-platform GPU detection (Windows / Linux / macOS)."""

    system = platform.system()
    gpus = []

    try:

        # ---------------- WINDOWS ----------------
        if system == "Windows":

            try:
                import wmi
                c = wmi.WMI()

                for gpu in c.Win32_VideoController():
                    gpus.append({
                        "platform": system,
                        "name": gpu.Name,
                        "driver_version": gpu.DriverVersion,
                        "video_processor": gpu.VideoProcessor,
                        "vram_mb": int(gpu.AdapterRAM / (1024*1024)) if gpu.AdapterRAM else None
                    })

            except:
                pass

            # fallback → WMIC
            if not gpus:
                try:
                    out = subprocess.check_output(
                        ["wmic", "path", "win32_VideoController", "get", "name"],
                        text=True
                    )

                    for line in out.splitlines()[1:]:
                        name = line.strip()
                        if name:
                            gpus.append({
                                "platform": system,
                                "name": name
                            })
                except:
                    pass

        # ---------------- LINUX ----------------
        elif system == "Linux":
            if tool_exists("ufw"):
                status = run_command("ufw status")

            try:
                out = subprocess.check_output(
                    ["lspci", "-mm"],
                    text=True
                )

                for line in out.splitlines():
                    if "VGA" in line or "3D" in line:
                        gpus.append({
                            "platform": system,
                            "name": line
                        })
            except:
                pass

        # ---------------- macOS ----------------
        elif system == "Darwin":

            try:
                out = subprocess.check_output(
                    ["system_profiler", "SPDisplaysDataType", "-json"],
                    text=True
                )

                data = json.loads(out)

                for gpu in data.get("SPDisplaysDataType", []):
                    gpus.append({
                        "platform": system,
                        "name": gpu.get("sppci_model"),
                        "vendor": gpu.get("spdisplays_vendor"),
                        "vram": gpu.get("spdisplays_vram")
                    })
            except:
                pass

    except Exception as e:
        gpus.append({"error": str(e)})

    return gpus if gpus else [{"error": "No GPU detected"}]

def get_ram_info():
    """Get RAM information including total capacity and hardware details when available."""
    ram = psutil.virtual_memory()
    ram_info = {
        "total": f"{round(ram.total / (1024 ** 3), 2)} GB",
        "available": f"{round(ram.available / (1024 ** 3), 2)} GB",
        "percent_used": f"{ram.percent}%",
        "details": []
    }

    if platform.system() == "Windows":
        try:
            command = 'powershell "Get-CimInstance Win32_PhysicalMemory | Select BankLabel,Manufacturer,SerialNumber,Capacity,Speed,DeviceLocator | ConvertTo-Json"'            
            output = run_command(command)

            if output:
                ram_chips = json.loads(output)

                # If only one RAM stick exists, PowerShell returns dict not list
                if isinstance(ram_chips, dict):
                    ram_chips = [ram_chips]

                for chip in ram_chips:
                    ram_info["details"].append({
                        "Slot": chip.get("BankLabel", "Unknown"),
                        "Manufacturer": chip.get("Manufacturer", "Unknown"),
                        "Part Number": chip.get("PartNumber", "Unknown"),
                        "Serial Number": chip.get("SerialNumber", "Unknown"),
                        "Capacity (GB)": round(int(chip.get("Capacity", 0)) / (1024**3), 2),
                        "Model_name": chip.get("PartNumber", "Unknown").strip()[:20],  # Attempt to extract model from part number
                        "Frequency MHz": chip.get("Speed"),
                        "Port / Slot": chip.get("DeviceLocator"),
                    })

        except Exception as e:
            ram_info["error"] = str(e)

    elif platform.system() == "Linux":
        try:
            command = ["dmidecode", "--type", "memory"]

            output = subprocess.check_output(
                command,
                text=True,
                stderr=subprocess.STDOUT
            )

            memory_devices = []
            current_device = None

            for line in output.splitlines():

                line = line.strip()

                if line.startswith("Memory Device"):
                    if current_device:
                        memory_devices.append(current_device)
                    current_device = {}

                elif current_device is not None and ":" in line:
                    key, value = line.split(":", 1)
                    current_device[key.strip()] = value.strip()

            if current_device:
                memory_devices.append(current_device)

            ram_info["details"] = memory_devices

        except subprocess.CalledProcessError:
            ram_info["error"] = "Root privileges required for detailed RAM info (dmidecode)"

        except FileNotFoundError:
            ram_info["error"] = "dmidecode not installed"

        except Exception as e:
            ram_info["error"] = f"RAM scan failed: {str(e)}"

    elif platform.system() == "Darwin":  # macOS
        try:
            # Get basic RAM information using system_profiler
            command = 'system_profiler SPMemoryDataType'
            output = subprocess.check_output(command, shell=True, text=True)
            
            # Process the output
            memory_details = []
            current_dimm = {}
            
            for line in output.splitlines():
                line = line.strip()
                if line.startswith("BANK") or line.startswith("DIMM"):
                    if current_dimm:
                        memory_details.append(current_dimm)
                    current_dimm = {"slot": line}
                elif current_dimm and ":" in line:
                    key, value = line.split(":", 1)
                    current_dimm[key.strip()] = value.strip()
            
            # Add the last DIMM
            if current_dimm:
                memory_details.append(current_dimm)
                
            ram_info["details"] = memory_details
            
        except Exception as e:
            ram_info["error"] = f"Failed to get RAM details: {str(e)}"
    
    return ram_info

def run_command(command):
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return result.stdout.strip()

def get_disk_info():
    """
    Enterprise Hard Disk Inventory
    Returns:
        physical_disks -> actual SSD/HDD/NVMe devices
        partitions -> logical volumes
    """
    system = platform.system()

    disk_data = {
        "physical_disks": [],
        "partitions": []
    }

    try:
        # ==========================================
        # WINDOWS
        # ==========================================
        if system == "Windows":
            out = run_command(
                'powershell "Get-CimInstance Win32_DiskDrive | '
                'Select Model,Manufacturer,SerialNumber,Size,MediaType | ConvertTo-Json"'
            )

            if out:
                data = json.loads(out)

                if isinstance(data, dict):
                    data = [data]

                for d in data:
                    size = d.get("Size")

                    disk_data["physical_disks"].append({
                        "Manufacturer": d.get("Manufacturer") or d.get("Model"),
                        "Model": d.get("Model"),
                        "Serial Number": d.get("SerialNumber"),
                        "Media Type": d.get("MediaType"),
                        "Size GB": round(int(size)/(1024**3), 2) if size else None
                    })

        # ==========================================
        # LINUX
        # ==========================================
        elif system == "Linux":
            out = run_command("lsblk -d -o NAME,MODEL,SERIAL,VENDOR,SIZE,ROTA -J")

            if out:
                data = json.loads(out)

                for d in data.get("blockdevices", []):
                    disk_data["physical_disks"].append({
                        "Manufacturer": d.get("vendor"),
                        "Model": d.get("model"),
                        "Serial Number": d.get("serial"),
                        "Media Type": "HDD" if d.get("rota") else "SSD",
                        "Size": d.get("size")
                    })

        # ==========================================
        # MAC
        # ==========================================
        elif system == "Darwin":
            out = run_command("system_profiler SPStorageDataType -json")

            if out:
                data = json.loads(out)

                for d in data.get("SPStorageDataType", []):
                    disk_data["physical_disks"].append({
                        "Manufacturer": d.get("vendor"),
                        "Model": d.get("_name"),
                        "Serial Number": d.get("serial_num"),
                        "Media Type": "SSD",
                        "Size GB": round(int(d.get("size_in_bytes", 0))/(1024**3), 2)
                    })

        # ==========================================
        # PARTITIONS (ALL OS)
        # ==========================================
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)

                disk_data["partitions"].append({
                    "Device ID": partition.device,
                    "Mount Point": partition.mountpoint,
                    "File System": partition.fstype,
                    "Free Space GB": round(usage.free / (1024 ** 3), 2),
                    "Total Size GB": round(usage.total / (1024 ** 3), 2)
                })

            except PermissionError:
                continue

    except Exception as e:
        disk_data["error"] = str(e)

    return disk_data

def get_motherboard_info():
    """Cross-platform motherboard / baseboard detection."""

    system = platform.system()

    result = {
        "platform": system,
        "manufacturer": None,
        "product": None,
        "serial": None,
        "version": None,
        "bios_vendor": None,
        "bios_version": None
    }

    try:

        # ---------------- WINDOWS ----------------
        if system == "Windows":

            try:
                cmd = [
                    "powershell",
                    "-Command",
                    "Get-CimInstance Win32_BaseBoard | "
                    "Select Manufacturer, Product, SerialNumber, Version | ConvertTo-Json"
                ]

                out = subprocess.check_output(cmd, text=True)

                if out.strip():
                    data = json.loads(out)

                    result["manufacturer"] = data.get("Manufacturer")
                    result["product"] = data.get("Product")
                    result["serial"] = data.get("SerialNumber")
                    result["version"] = data.get("Version")

            except:
                pass

            # BIOS
            try:
                cmd = [
                    "powershell",
                    "-Command",
                    "Get-CimInstance Win32_BIOS | "
                    "Select Manufacturer, SMBIOSBIOSVersion | ConvertTo-Json"
                ]

                out = subprocess.check_output(cmd, text=True)

                if out.strip():
                    bios = json.loads(out)

                    result["bios_vendor"] = bios.get("Manufacturer")
                    result["bios_version"] = bios.get("SMBIOSBIOSVersion")

            except:
                pass

        # ---------------- LINUX ----------------
        elif system == "Linux":

            result["manufacturer"] = (
                read_sys_file("/sys/class/dmi/id/board_vendor")
                or "Unavailable"
            )

            result["product"] = (
                read_sys_file("/sys/class/dmi/id/board_name")
                or "Unavailable"
            )

            result["version"] = (
                read_sys_file("/sys/class/dmi/id/board_version")
                or "Unavailable"
            )

            result["serial"] = (
                read_sys_file("/sys/class/dmi/id/board_serial")
                or "Unavailable"
            )
        # ---------------- macOS ----------------
        elif system == "Darwin":

            try:
                out = subprocess.check_output(
                    ["system_profiler", "SPHardwareDataType", "-json"],
                    text=True
                )

                data = json.loads(out)

                hw = data.get("SPHardwareDataType", [{}])[0]

                result["manufacturer"] = "Apple"
                result["product"] = hw.get("machine_model")
                result["serial"] = hw.get("serial_number")

            except:
                pass

    except Exception as e:
        print("Motherboard detection error:", e)

    return result

def get_network_info():
    """Professional network interface collector."""

    system = platform.system()

    interfaces = []
    addrs = psutil.net_if_addrs()
    stats = psutil.net_if_stats()

    for interface, addr_list in addrs.items():

        mac = None
        ipv4 = []
        ipv6 = []

        for addr in addr_list:

            if addr.family == socket.AF_INET:
                ipv4.append(addr.address)

            elif addr.family == socket.AF_INET6:
                ipv6.append(addr.address)

            elif addr.family == psutil.AF_LINK:
                mac = addr.address

        iface_obj = {
            "platform": system,
            "nic_name": interface,
            "mac_address": mac,
            "ipv4": ipv4,
            "ipv6": ipv6,
            "connection_status": (
                "Up" if interface in stats and stats[interface].isup else "Down"
            ),
            "speed_mbps": (
                stats[interface].speed if interface in stats else None
            ),
            "mtu": (
                stats[interface].mtu if interface in stats else None
            )
        }

        interfaces.append(iface_obj)

    return interfaces

def get_public_ip():
    """Get public IP (IPv4 / IPv6) with fallback APIs."""

    result = {
        "ipv4": None,
        "ipv6": None,
        "provider": None,
        "latency_ms": None
    }

    apis = [
        ("https://api.ipify.org?format=json", "ipify"),
        ("https://ip.seeip.org/jsonip?", "seeip"),
        ("https://ifconfig.me/all.json", "ifconfig")
    ]

    for url, provider in apis:
        try:
            start = time.time()

            r = requests.get(url, timeout=3)

            latency = int((time.time() - start) * 1000)

            if r.status_code != 200:
                continue

            data = r.json()

            # ipify / seeip
            ip = data.get("ip") or data.get("ip_addr")

            # ifconfig.me
            if not ip:
                ip = data.get("ip_addr")

            if ip:
                if ":" in ip:
                    result["ipv6"] = ip
                else:
                    result["ipv4"] = ip

                result["provider"] = provider
                result["latency_ms"] = latency

                break

        except Exception:
            continue

    # final normalization
    for k in result:
        if result[k] is None:
            result[k] = "Unavailable"

    return result

def get_logged_in_user():
    """Get current logged-in username (cross-platform safe)."""

    try:
        # BEST universal method
        user = getpass.getuser()

        if user:
            return user

    except:
        pass

    try:
        # fallback environment
        if platform.system() == "Windows":
            return os.environ.get("USERNAME")

        else:
            return os.environ.get("USER")

    except:
        pass

    return "Unavailable"

try:
    import winreg
except:
    winreg = None


def get_installed_software():
    """Cross-platform installed software inventory."""

    system = platform.system()
    software = []
    seen = set()

    hostname = socket.gethostname()

    # ---------------- WINDOWS ----------------
    if system == "Windows" and winreg:

        registry_roots = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall")
        ]

        for hive, path in registry_roots:
            try:
                with winreg.OpenKey(hive, path) as key:

                    for i in range(winreg.QueryInfoKey(key)[0]):

                        try:
                            subname = winreg.EnumKey(key, i)

                            with winreg.OpenKey(key, subname) as subkey:

                                try:
                                    name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                                except:
                                    continue

                                if name in seen:
                                    continue

                                seen.add(name)

                                def q(v):
                                    try:
                                        return winreg.QueryValueEx(subkey, v)[0]
                                    except:
                                        return None

                                software.append({
                                    "platform": system,
                                    "computer": hostname,
                                    "name": name,
                                    "version": q("DisplayVersion"),
                                    "publisher": q("Publisher"),
                                    "install_date": q("InstallDate"),
                                    "install_location": q("InstallLocation"),
                                    "uninstall_string": q("UninstallString")
                                })

                        except:
                            continue

            except:
                continue

    # ---------------- LINUX ----------------
    elif system == "Linux":

        try:
            out = subprocess.check_output(
                ["dpkg-query", "-W", "-f=${Package}\t${Version}\n"],
                text=True
            )

            for line in out.splitlines():
                name, version = line.split("\t")

                software.append({
                    "platform": system,
                    "computer": hostname,
                    "name": name,
                    "version": version
                })

        except:
            pass

    # ---------------- macOS ----------------
    elif system == "Darwin":

        try:
            out = subprocess.check_output(
                ["system_profiler", "SPApplicationsDataType", "-json"],
                text=True
            )

            import json
            data = json.loads(out)

            apps = data.get("SPApplicationsDataType", [])

            for app in apps:
                software.append({
                    "platform": system,
                    "computer": hostname,
                    "name": app.get("_name"),
                    "version": app.get("version"),
                    "location": app.get("path")
                })

        except:
            pass

    return software

def get_windows_updates():
    """Get installed Windows Updates (KB patches)."""

    system = platform.system()

    result = {
        "platform": system,
        "updates": []
    }

    if system != "Windows":
        result["updates"] = "Not Supported"
        return result

    try:

        # ---------- PRIMARY METHOD (PowerShell CIM) ----------
        cmd = [
            "powershell",
            "-Command",
            "Get-HotFix | Select HotFixID, Description, InstalledOn | ConvertTo-Json"
        ]

        out = subprocess.check_output(cmd, text=True)

        if out.strip():
            data = json.loads(out)

            if isinstance(data, dict):
                data = [data]

            for u in data:
                result["updates"].append({
                    "kb": u.get("HotFixID"),
                    "description": u.get("Description"),
                    "installed_on": str(u.get("InstalledOn"))
                })

    except Exception:
        pass

    # ---------- FALLBACK METHOD (WMIC) ----------
    if not result["updates"]:
        try:
            out = subprocess.check_output(
                ["wmic", "qfe", "get", "HotFixID,InstalledOn"],
                text=True
            )

            for line in out.splitlines()[1:]:
                parts = line.split()

                if parts:
                    result["updates"].append({
                        "kb": parts[0],
                        "installed_on": parts[-1] if len(parts) > 1 else None
                    })

        except:
            pass

    return result

def _decode_product_state(state):
    """Decode Windows SecurityCenter productState."""
    try:
        state = int(state)

        enabled = bool(state & 0x1000)
        updated = bool(state & 0x10)

        return {
            "enabled": enabled,
            "definitions_up_to_date": updated
        }
    except:
        return {
            "enabled": None,
            "definitions_up_to_date": None
        }

def get_antivirus():
    """Cross-platform antivirus detection."""

    system = platform.system()

    result = {
        "platform": system,
        "products": []
    }

    try:

        # ---------------- WINDOWS ----------------
        if system == "Windows":

            cmd = [
                "powershell",
                "-Command",
                "Get-CimInstance -Namespace root/SecurityCenter2 "
                "-ClassName AntiVirusProduct | "
                "Select displayName,productState | ConvertTo-Json"
            ]

            out = subprocess.check_output(cmd, text=True)

            if out.strip():
                data = json.loads(out)

                if isinstance(data, dict):
                    data = [data]

                for av in data:
                    decoded = _decode_product_state(av.get("productState"))

                    result["products"].append({
                        "name": av.get("displayName"),
                        "enabled": decoded["enabled"],
                        "definitions_up_to_date": decoded["definitions_up_to_date"]
                    })

        # ---------------- LINUX ----------------
        elif system == "Linux":

            try:
                out = subprocess.check_output(["clamscan", "--version"], text=True)

                result["products"].append({
                    "name": "ClamAV",
                    "version": out.strip()
                })

            except:
                pass

        # ---------------- macOS ----------------
        elif system == "Darwin":

            # macOS normally uses XProtect
            result["products"].append({
                "name": "Apple XProtect",
                "enabled": True
            })

    except Exception as e:
        result["products"].append({
            "error": str(e)
        })

    if not result["products"]:
        result["products"] = "No antivirus detected"

    return result

def get_computer_type():

    system = platform.system()

    try:
        if system == "Windows":
            out = run_command('powershell "(Get-CimInstance Win32_SystemEnclosure).ChassisTypes"')
            if out:
                if "9" in out or "10" in out:
                    return "Laptop"
                else:
                    return "Desktop"

        elif system == "Linux":
            val = read_sys_file("/sys/class/dmi/id/chassis_type")
            if val == "9":
                return "Laptop"
            return "Desktop"

        elif system == "Darwin":
            return "Laptop"

    except:
        pass

    return "Unknown"

def get_registered_owner():

    system = platform.system()

    try:

        if system == "Windows":
            return run_command(
                'powershell "(Get-ItemProperty '
                '\'HKLM:\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\').RegisteredOwner"'
            )

        elif system == "Linux":
            return run_command("whoami")

        elif system == "Darwin":
            return run_command("stat -f '%Su' /dev/console")

    except:
        pass

    return "Unavailable"

def get_domain_info():

    system = platform.system()

    try:

        if system == "Windows":

            out = run_command(
                'powershell "(Get-CimInstance Win32_ComputerSystem).Domain"'
            )

            role = run_command(
                'powershell "(Get-CimInstance Win32_ComputerSystem).DomainRole"'
            )

            return {
                "domain_name": out,
                "domain_role": role
            }

        elif system == "Linux":

            realm = run_command("realm list")

            return {
                "domain_name": realm
            }

        elif system == "Darwin":

            return {
                "domain_name": run_command("dsconfigad -show")
            }

    except:
        pass

    return {}

def get_system_accounts_desc():

    system = platform.system()
    result = []

    try:

        if system == "Windows":

            out = run_command(
                'powershell "Get-WmiObject Win32_UserAccount | '
                'Select Name,Description | ConvertTo-Json"'
            )

            if out:
                data = json.loads(out)

                if isinstance(data, dict):
                    data = [data]

                for u in data:
                    result.append({
                        "account": u.get("Name"),
                        "description": u.get("Description")
                    })

        elif system == "Linux":

            out = run_command("getent passwd")

            for line in out.splitlines():
                p = line.split(":")
                result.append({
                    "account": p[0],
                    "description": p[4]
                })

        elif system == "Darwin":

            out = run_command("dscl . list /Users RealName")

            for line in out.splitlines():
                result.append({"raw": line})

    except:
        pass

    return result

def get_system_accounts_status():

    system = platform.system()
    result = []

    try:

        if system == "Windows":

            out = run_command(
                'powershell "Get-WmiObject Win32_UserAccount | '
                'Select Name,Disabled | ConvertTo-Json"'
            )

            if out:
                data = json.loads(out)

                if isinstance(data, dict):
                    data = [data]

                for u in data:
                    result.append({
                        "account": u.get("Name"),
                        "status": "Disabled" if u.get("Disabled") else "Enabled"
                    })

        elif system == "Linux":

            out = run_command("passwd -S -a")

            if out:
                for line in out.splitlines():
                    result.append({"raw": line})

        elif system == "Darwin":

            result.append({"status": "macOS account status limited"})

    except:
        pass

    return result

def get_system_accounts_sids():

    system = platform.system()
    result = []

    try:

        if system == "Windows":

            out = run_command(
                'powershell "Get-WmiObject Win32_UserAccount | '
                'Select Name,SID | ConvertTo-Json"'
            )

            if out:
                data = json.loads(out)

                if isinstance(data, dict):
                    data = [data]

                for u in data:
                    result.append({
                        "account": u.get("Name"),
                        "sid": u.get("SID")
                    })

        elif system == "Linux":

            out = run_command("getent passwd")

            for line in out.splitlines():
                p = line.split(":")
                result.append({
                    "account": p[0],
                    "uid": p[2]
                })

        elif system == "Darwin":

            out = run_command("dscl . list /Users UniqueID")

            for line in out.splitlines():
                result.append({"raw": line})

    except:
        pass

    return result

def get_headset_devices():

    system = platform.system()
    devices = []
    asset_tag = get_serial_number()

    try:

        if system == "Windows":

            out = run_command(
                'powershell "Get-CimInstance Win32_SoundDevice | '
                'Where-Object {$_.Name -match \'headset|headphone|earphone\'} '
                '| Select Name,Manufacturer,PNPDeviceID | ConvertTo-Json"'
            )

            if out:
                data = json.loads(out)

                if isinstance(data, dict):
                    data = [data]

                for d in data:

                    serial = None
                    if d.get("PNPDeviceID"):
                        serial = d["PNPDeviceID"].split("\\")[-1]

                    devices.append({
                        "name": d.get("Name"),
                        "manufacturer": d.get("Manufacturer"),
                        "serial_number": serial,
                        "asset_tag": asset_tag
                    })

        elif system == "Linux":

            out = run_command("pactl list short sinks")

            if out:
                for line in out.splitlines():
                    if "head" in line.lower():
                        devices.append({"raw": line})

        elif system == "Darwin":

            out = run_command("system_profiler SPAudioDataType")

            if out:
                for line in out.splitlines():
                    if "head" in line.lower():
                        devices.append({"raw": line})

    except:
        pass

    return devices

def logical_drives():
    """
    Enterprise Logical Drive Inventory
    Windows / Linux / macOS
    """

    system = platform.system()
    drives = []

    try:

        # ================= WINDOWS =================
        if system == "Windows":

            out = run_command(
                'powershell "Get-CimInstance Win32_LogicalDisk | '
                'Select DeviceID,VolumeName,FileSystem,FreeSpace,Size | ConvertTo-Json"'
            )

            if out:
                data = json.loads(out)

                if isinstance(data, dict):
                    data = [data]

                for d in data:
                    drives.append({
                        "device_id": d.get("DeviceID"),
                        "volume_name": d.get("VolumeName"),
                        "file_system": d.get("FileSystem"),
                        "free_space_gb": round(int(d.get("FreeSpace", 0))/(1024**3),2) if d.get("FreeSpace") else None,
                        "total_size_gb": round(int(d.get("Size", 0))/(1024**3),2) if d.get("Size") else None
                    })

        # ================= LINUX =================
        elif system == "Linux":

            partitions = psutil.disk_partitions()

            for p in partitions:

                try:
                    usage = psutil.disk_usage(p.mountpoint)
                except:
                    continue

                drives.append({
                    "device_id": p.device,
                    "volume_name": p.mountpoint,
                    "file_system": p.fstype,
                    "free_space_gb": round(usage.free/(1024**3),2),
                    "total_size_gb": round(usage.total/(1024**3),2)
                })

        # ================= MAC =================
        elif system == "Darwin":

            out = run_command("diskutil list -plist")

            if out:
                data = json.loads(out)

                for disk in data.get("AllDisksAndPartitions", []):

                    if "MountPoint" in disk:

                        try:
                            usage = psutil.disk_usage(disk["MountPoint"])
                        except:
                            continue

                        drives.append({
                            "device_id": disk.get("DeviceIdentifier"),
                            "volume_name": disk.get("VolumeName"),
                            "file_system": disk.get("Content"),
                            "free_space_gb": round(usage.free/(1024**3),2),
                            "total_size_gb": round(usage.total/(1024**3),2)
                        })

    except Exception as e:
        drives.append({"error": str(e)})

    return drives

def get_computer_system_snapshot():

    return {
        "scan_timestamp": datetime.datetime.now().isoformat(),

        "Computer system": {
            "Name": socket.gethostname(),
            "service tag": get_system_info()[1],
            "manufacturer": get_system_info()[0],
            "model": get_product_name(),
            "serial_number": get_serial_number(),
            "asset_tag": get_system_info(),
            "logged_in_user": get_logged_in_user(),
            "Bios": get_bios_info(),
            "ram": get_ram_info(),
            "cpu manufacturer": get_cpu_info().get("Manufacturer"),
            "computer_type": get_computer_type(),
        },

        "Operating System":{
            "System type": get_os_info().get("os_name"),
            "OS Version": get_os_info().get("os_version"),
            "CPU model": get_cpu_info().get("Model"),
            "build number": get_os_info().get("build"),
            "service pack": get_os_info().get("service_pack"),
            "product_id": get_os_info().get("product_id"),
            "registered_to": get_registered_owner(),
            "user_accounts": get_user_accounts(),
            "domain": get_domain_info(),

        },

        "site information":{
            "site name": socket.gethostname(),
            "country": get_geo_location().get("country"),
            "city": get_geo_location().get("city"),
            "location": "",
            "asset tag": get_system_info()[1]  
        },

        "vendor and warrenty":{
            "vendor name": get_vendor_warranty_info().get("Vendor Name"),
            "purchase_cost": get_vendor_warranty_info().get("Purchase Cost"),
            "asset_created_date": get_vendor_warranty_info().get("Asset Created Date"),
            "warranty_expiry_date": get_vendor_warranty_info().get("Warranty Expiry Date"),
            "purchase_date": get_vendor_warranty_info().get("Purchase Date"),   
        },

        "Geo Location": {
            "country": get_geo_location().get("country"),
            "region": get_geo_location().get("region"),
            "city": get_geo_location().get("city"),
            "ISP provider": get_geo_location().get("isp"),
        },

        "IP address": {
            "public_ip": get_public_ip(),
            "private_ip": get_private_ip(),
            "DNS Servers": get_dns_servers(),
            "dhcp server": get_dhcp_server(),
        },

        "Antivirus":get_antivirus(),
        "Admin Group Members": get_admin_group_members(),


        # "RDP Group Members": get_rdp_group_members(),
        # "System Accounts": get_system_accounts(),
        # "os": get_os_info(),
        # "computer_type": get_computer_type(),
        # "cpu": get_cpu_info(),

        # "network": {
        #     "private_ip": get_private_ip(),
        #     "public_ip": get_public_ip(),
        #     "interfaces": get_network_info(),
        #     "dhcp": get_dhcp_server(),
        #     "firewall": get_firewall_status(),
        #     "geo": get_geo_location()
        # },

        # "security": {
        #     "antivirus": get_antivirus(),
        #     "updates": get_windows_updates()
        # },

    }

def get_computer_details():
    """Collect all computer details (cross-platform safe)."""

    # geo = get_geo_location()
    # system_info = get_system_info()
    # private_ip = get_private_ip()
    # public_ip = get_public_ip()
    # serial=get_serial_number()
    disk_info = get_disk_info()

    drives = logical_drives()

    logical_drive_info = drives[0] if drives else {}

    computer_system = get_computer_system_snapshot()

    return {
        "Asset Details": {

            "ComputerDetails": computer_system,

            },

            "processor":{
                "Manufacturer": get_cpu_info().get("Manufacturer"),
                "Model": get_cpu_info().get("Model"),
                "Serial Number": get_cpu_info().get("Serial Number"),
                "Architecture": get_cpu_info().get("Architecture"),
                "logical_processors": get_cpu_info().get("Logical Processors"),
                "Processor Speed (MHz)": get_cpu_info().get("Processor Speed (MHz)"),
                "cores": get_cpu_info().get("Cores"),
            },

#             "Hard Disk Details": {
#                 "Manufacturer": disk_info["physical_disks"][0].get("Manufacturer") if disk_info["physical_disks"] else None,
#                 "Model": disk_info["physical_disks"][0].get("Model") if disk_info["physical_disks"] else None,
#                 "Serial Number": disk_info["physical_disks"][0].get("Serial Number") if disk_info["physical_disks"] else None,
#                 "Size gb": disk_info["physical_disks"][0].get("Size GB") if disk_info["physical_disks"] else None,
# },

#             "logical devices":{
#                 "device_id": logical_drive_info.get("device_id"),
#                 "volume_name": logical_drive_info.get("volume_name"),
#                 "file_system": logical_drive_info.get("file_system"),
#                 "free_space_gb": logical_drive_info.get("free_space_gb"),
#                 "total_size_gb": logical_drive_info.get("total_size_gb"),
#             },

            "Hard Disk Details": disk_info["physical_disks"],
            "Disk Partitions": disk_info["partitions"],


            "RAM Details": {
                "Manufacturer": get_ram_info().get("details")[0].get("Manufacturer") if get_ram_info().get("details") else None,
                "capacity_gb": get_ram_info().get("total"),
                "serial number": get_ram_info().get("details")[0].get("Serial Number") if get_ram_info().get("details") else None,
                "frequency_mhz": get_ram_info().get("details")[0].get("Frequency MHz") if get_ram_info().get("details") else None,
                "port_slot": get_ram_info().get("details")[0].get("Port / Slot") if get_ram_info().get("details") else None,
            },

            "Montitor Details": {
                "name": get_monitor_details()[0].get("name") if get_monitor_details() else None,
                "manufacturer": get_monitor_details()[0].get("manufacturer") if get_monitor_details() else None,
                "model": get_monitor_details()[0].get("model") if get_monitor_details() else None,
                "serial_number": get_monitor_details()[0].get("serial_number") if get_monitor_details() else None,
            },

            "system accounts": {
                "computer_name": socket.gethostname(),
                "accounts names": get_system_accounts(),
                "descriptions": get_system_accounts_desc(),
                "status": get_system_accounts_status(),
                "sids": get_system_accounts_sids(),
            },

            "Peripheral Devices": {
                "mouse": get_mouse_devices(),
                "keyboard": get_keyboard_devices(),
                "audio": get_audio_devices(),
                "headset": get_headset_devices(),
                "webcam": get_camera_devices(),
                "printers": get_printer_devices(),
            },

            "components": {
                "motherboard": get_motherboard_info(),
                "cpu": get_cpu_info(),
                "gpu": get_gpu_info(),
            },

            "network": {
                "private_ip": get_private_ip(),
                "public_ip": get_public_ip(),
                "interfaces": get_network_info(),
                "dhcp": get_dhcp_server(),
                "firewall": get_firewall_status(),
                "geo": get_geo_location()
            },

            "installed_software_list": get_installed_software(),

            "installed_updates": get_windows_updates(),
            

            # "Geo Location": {
            #     "Country": geo.get("country"),
            #     "Region": geo.get("region"),
            #     "City": geo.get("city"),
            #     "ISP Provider": geo.get("isp"),
            # },

            # "IP Address": {
            #     "Public IP": public_ip,
            #     "Private IP": private_ip,
            #     "Bluetooth Devices": get_bluetooth_devices(),
            #     "Network Interfaces": get_network_interfaces(),
            #     "Loopback Interfaces": get_loopback_interface(),
            #     "DNS Servers": get_dns_servers(),
            #     "DHCP Server": get_dhcp_server(),
            # },

            # "Mouse Devices": get_mouse_devices(),
            # "Vendor & Warranty Information": get_vendor_warranty_info(),
            # "Battery": get_battery_info(),
            # "Motherboard": get_motherboard_info(),
            # "GPU Information": safe_call(get_gpu_info),
            # "Processor": safe_call(get_cpu_info),
            # "Hard Disks": safe_call(get_hard_disk_info),
            # "Disk Health": safe_call(get_disk_health),
            # "USB Devices": safe_call(get_usb_devices),
            # "Logical Drives": safe_call(get_disk_info),
            # "Monitors": safe_call(get_monitor_details),
            # "User Accounts": get_user_accounts(),
            # "Network Adapters": safe_call(get_network_info),
            # "Audio Devices": safe_call(get_audio_devices),
            # "Web Camera Devices": safe_call(get_camera_devices),
            # "Keyboard Devices": safe_call(get_keyboard_devices),
            # "Firewall Status": safe_call(get_firewall_status),
            # "Mice Devices": safe_call(get_mice_devices),
            # "Printer Devices": safe_call(get_printer_devices),
            # "Antivirus": safe_call(get_antivirus),
            # "Windows Updates": safe_call(get_windows_updates),
            # "Windows Defender": safe_call(get_security_status),
            # "Installed Software": safe_call(get_installed_software),
        }

import concurrent.futures

def get_computer_return_data():
    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
        f_drives = executor.submit(logical_drives)
        f_comp_sys = executor.submit(get_computer_system_snapshot)
        f_disk_info = executor.submit(get_disk_info)
        f_sys_info = executor.submit(get_system_info)
        f_cpu_info = executor.submit(get_cpu_info)
        f_ram_info = executor.submit(get_ram_info)
        f_os_info = executor.submit(get_os_info)
        f_geo = executor.submit(get_geo_location)
        f_monitor = executor.submit(get_monitor_details)
        
        f_product_name = executor.submit(get_product_name)
        f_serial_num = executor.submit(get_serial_number)
        f_logged_in_user = executor.submit(get_logged_in_user)
        f_bios = executor.submit(get_bios_info)
        f_comp_type = executor.submit(get_computer_type)
        
        f_reg_owner = executor.submit(get_registered_owner)
        f_user_accounts = executor.submit(get_user_accounts)
        f_domain = executor.submit(get_domain_info)
        
        f_vendor = executor.submit(get_vendor_warranty_info)
        
        f_public_ip = executor.submit(get_public_ip)
        f_private_ip = executor.submit(get_private_ip)
        f_dns = executor.submit(get_dns_servers)
        f_dhcp = executor.submit(get_dhcp_server)
        
        f_antivirus = executor.submit(get_antivirus)
        f_admin_groups = executor.submit(get_admin_group_members)
        
        f_sys_accounts = executor.submit(get_system_accounts)
        f_sys_accounts_desc = executor.submit(get_system_accounts_desc)
        f_sys_accounts_status = executor.submit(get_system_accounts_status)
        f_sys_accounts_sids = executor.submit(get_system_accounts_sids)
        
        f_mouse = executor.submit(get_mouse_devices)
        f_keyboard = executor.submit(get_keyboard_devices)
        f_audio = executor.submit(get_audio_devices)
        f_headset = executor.submit(get_headset_devices)
        f_webcam = executor.submit(get_camera_devices)
        f_printers = executor.submit(get_printer_devices)
        
        f_mobo = executor.submit(get_motherboard_info)
        f_gpu = executor.submit(get_gpu_info)
        
        f_network = executor.submit(get_network_info)
        f_firewall = executor.submit(get_firewall_status)
        
        f_software = executor.submit(get_installed_software)
        f_updates = executor.submit(get_windows_updates)

        drives = f_drives.result() or []
        computer_system = f_comp_sys.result() or {}
        disk_info = f_disk_info.result() or {}
        sys_info = f_sys_info.result() or ["", ""]
        if len(sys_info) < 2: sys_info = ["", ""]
        cpu_info = f_cpu_info.result() or {}
        ram_info = f_ram_info.result() or {}
        os_info = f_os_info.result() or {}
        geo = f_geo.result() or {}
        monitor = f_monitor.result()
        vendor = f_vendor.result() or {}

        ram_details = ram_info.get("details", [])
        if not ram_details: ram_details = [{}]
            
        monitor_details = monitor[0] if monitor else {}

        return {
            "scan_timestamp": datetime.datetime.now().isoformat(),

            "Computer system": {
                "Name": socket.gethostname(),
                "service tag": sys_info[1] if len(sys_info) > 1 else None,
                "manufacturer": sys_info[0] if len(sys_info) > 0 else None,
                "model": f_product_name.result(),
                "serial_number": f_serial_num.result(),
                "asset_tag": sys_info,
                "logged_in_user": f_logged_in_user.result(),
                "Bios": f_bios.result(),
                "ram": ram_info,
                "cpu manufacturer": cpu_info.get("Manufacturer"),
                "computer_type": f_comp_type.result(),
            },

            "Operating System":{
                "System type": os_info.get("os_name"),
                "OS Version": os_info.get("os_version"),
                "CPU model": cpu_info.get("Model"),
                "build number": os_info.get("build"),
                "service pack": os_info.get("service_pack"),
                "product_id": os_info.get("product_id"),
                "registered_to": f_reg_owner.result(),
                "user_accounts": f_user_accounts.result(),
                "domain": f_domain.result(),
            },

            "site information":{
                "site name": socket.gethostname(),
                "country": geo.get("country"),
                "city": geo.get("city"),
                "location": "",
                "asset tag": sys_info[1] if len(sys_info) > 1 else None
            },

            "vendor and warrenty":{
                "vendor name": vendor.get("Vendor Name"),
                "purchase_cost": vendor.get("Purchase Cost"),
                "asset_created_date": vendor.get("Asset Created Date"),
                "warranty_expiry_date": vendor.get("Warranty Expiry Date"),
                "purchase_date": vendor.get("Purchase Date"),   
            },

            "Geo Location": {
                "country": geo.get("country"),
                "region": geo.get("region"),
                "city": geo.get("city"),
                "ISP provider": geo.get("isp"),
            },

            "IP address": {
                "public_ip": f_public_ip.result(),
                "private_ip": f_private_ip.result(),
                "DNS Servers": f_dns.result(),
                "dhcp server": f_dhcp.result(),
            },

            "Antivirus": f_antivirus.result(),
            "Admin Group Members": f_admin_groups.result(),

            "Asset Details": {
                "ComputerDetails": computer_system,
            },

            "processor":{
                "Manufacturer": cpu_info.get("Manufacturer"),
                "Model": cpu_info.get("Model"),
                "Serial Number": cpu_info.get("Serial Number"),
                "Architecture": cpu_info.get("Architecture"),
                "logical_processors": cpu_info.get("Logical Processors"),
                "Processor Speed (MHz)": cpu_info.get("Processor Speed (MHz)"),
                "cores": cpu_info.get("Cores"),
            },

            "Hard Disk Details": disk_info.get("physical_disks", []),
            "Disk Partitions": disk_info.get("partitions", []),

            "RAM Details": {
                "Manufacturer": ram_details[0].get("Manufacturer"),
                "capacity_gb": ram_info.get("total"),
                "serial number": ram_details[0].get("Serial Number"),
                "frequency_mhz": ram_details[0].get("Frequency MHz"),
                "port_slot": ram_details[0].get("Port / Slot"),
            },

            "Montitor Details": {
                "name": monitor_details.get("name"),
                "manufacturer": monitor_details.get("manufacturer"),
                "model": monitor_details.get("model"),
                "serial_number": monitor_details.get("serial_number"),
            },

            "system accounts": {
                "computer_name": socket.gethostname(),
                "accounts names": f_sys_accounts.result(),
                "descriptions": f_sys_accounts_desc.result(),
                "status": f_sys_accounts_status.result(),
                "sids": f_sys_accounts_sids.result(),
            },

            "Peripheral Devices": {
                "mouse": f_mouse.result(),
                "keyboard": f_keyboard.result(),
                "audio": f_audio.result(),
                "headset": f_headset.result(),
                "webcam": f_webcam.result(),
                "printers": f_printers.result(),
            },

            "components": {
                "motherboard": f_mobo.result(),
                "cpu": cpu_info,
                "gpu": f_gpu.result(),
            },

            "network": {
                "private_ip": f_private_ip.result(),
                "public_ip": f_public_ip.result(),
                "interfaces": f_network.result(),
                "dhcp": f_dhcp.result(),
                "firewall": f_firewall.result(),
                "geo": geo
            },

            "installed_software_list": f_software.result(),

            "installed_updates": f_updates.result(),
        }

def run_full_scan():
    """Run full system scan and return comprehensive JSON report."""

    try:
        snapshot = get_computer_return_data()
        return snapshot

    except Exception as e:
        return {"error": str(e)}

def save_system_json(data):
    """Save system info JSON in cross-platform Documents folder"""

    try:

        system = platform.system()
        hostname = socket.gethostname()

        # ---------- DOCUMENTS FOLDER ----------
        if system == "Windows":
            documents_folder = os.path.join(os.environ["USERPROFILE"], "Documents")

        elif system == "Linux" or system == "Darwin":
            documents_folder = os.path.join(Path.home(), "Documents")

        else:
            documents_folder = Path.home()

        # ---------- CREATE FOLDER ----------
        folder_path = os.path.join(documents_folder, "System_Info_Collector")
        os.makedirs(folder_path, exist_ok=True)

        # ---------- FILE NAME ----------
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{hostname}_{system}_{timestamp}.json"

        file_path = os.path.join(folder_path, filename)

        # ---------- SAVE JSON ----------
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

        print("\n✅ JSON SAVED SUCCESSFULLY")
        print(f"📁 Path: {file_path}")

    except Exception as e:
        print("❌ JSON SAVE ERROR:", e)
# 
# -------- Example MAIN --------
def main():

    print("Collecting system data...")

    data = get_computer_details()   # FULL DATA

    save_system_json(data)          # PASS DATA HERE

if __name__ == "__main__":
    main()