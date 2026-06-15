from __future__ import annotations

import json
import platform
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from .utils import redact_sensitive


PLACEHOLDER_VALUES = {
    "",
    "default string",
    "system product name",
    "system manufacturer",
    "to be filled by o.e.m.",
    "to be filled by oem",
    "not available",
    "none",
    "unknown",
}


def collect_system_info(input_file: Path | None = None) -> dict[str, Any]:
    if input_file:
        return parse_system_info_file(input_file)

    current = platform.system().lower()
    if current == "windows":
        raw = _collect_windows()
    elif current == "darwin":
        raw = _collect_macos()
    else:
        raw = _collect_generic()

    info = {
        "source": "live",
        "platform": platform.system(),
        "summary": _build_summary(raw, platform.system()),
        "raw": raw,
    }
    return redact_sensitive(info)


def parse_system_info_file(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    raw: dict[str, Any]

    if suffix == ".json":
        try:
            loaded = json.loads(text)
            raw = loaded if isinstance(loaded, dict) else {"items": loaded}
        except json.JSONDecodeError:
            raw = {"text": text}
    elif suffix in {".xml", ".nfo"} and text.strip().startswith("<"):
        if "BatteryReport" in text:
            try:
                root = ET.fromstring(text)
                raw = _parse_battery_report_xml(root)
            except ET.ParseError:
                raw = _parse_xml_text(text)
        else:
            raw = _parse_xml_text(text)
    else:
        raw = _parse_key_value_text(text)

    if "BatteryReport" in raw:
        summary = _build_summary(raw, "windows")
    else:
        summary = _summary_from_flattened(raw)

    info = {
        "source": str(path),
        "platform": "file",
        "summary": summary,
        "raw": raw,
    }
    return redact_sensitive(info)


def _parse_battery_report_xml(root: ET.Element) -> dict[str, Any]:
    ns_uri = ""
    if root.tag.startswith("{"):
        ns_uri = root.tag.split("}")[0][1:]
    
    ns = {"b": ns_uri} if ns_uri else {}

    def find_node(parent: ET.Element, tag: str) -> ET.Element | None:
        return parent.find(f".//b:{tag}", ns) if ns else parent.find(f".//{tag}")
        
    def find_nodes(parent: ET.Element, xpath: str) -> list[ET.Element]:
        if ns:
            parts = xpath.split("/")
            ns_xpath = "/".join(f"b:{p}" for p in parts)
            return parent.findall(ns_xpath, ns)
        return parent.findall(xpath)

    sys_info = find_node(root, "SystemInformation")
    sys_prod = {}
    bios = {}
    reg_os = {}
    if sys_info is not None:
        mfr = find_node(sys_info, "SystemManufacturer")
        prod = find_node(sys_info, "SystemProductName")
        bios_ver = find_node(sys_info, "BIOSVersion")
        os_build = find_node(sys_info, "OSBuild")
        
        sys_prod["Vendor"] = mfr.text.strip() if mfr is not None and mfr.text else None
        sys_prod["Name"] = prod.text.strip() if prod is not None and prod.text else None
        bios["SMBIOSBIOSVersion"] = bios_ver.text.strip() if bios_ver is not None and bios_ver.text else None
        reg_os["CurrentBuild"] = os_build.text.strip() if os_build is not None and os_build.text else None

    batteries = []
    bat_list = find_nodes(root, "Batteries/Battery")
    for bat_node in bat_list:
        bat = {}
        for field in ("Id", "Manufacturer", "Chemistry", "DesignCapacity", "FullChargeCapacity", "CycleCount"):
            node = find_node(bat_node, field)
            if node is not None and node.text:
                bat[field] = node.text.strip()
        batteries.append(bat)

    estimates = {}
    runtime_node = find_node(root, "RuntimeEstimates")
    if runtime_node is not None:
        design = find_node(runtime_node, "DesignCapacity")
        fcc = find_node(runtime_node, "FullChargeCapacity")
        if design is not None:
            active = find_node(design, "ActiveRuntime")
            cs = find_node(design, "ConnectedStandbyRuntime")
            estimates["DesignActive"] = active.text.strip() if active is not None and active.text else None
            estimates["DesignConnectedStandby"] = cs.text.strip() if cs is not None and cs.text else None
        if fcc is not None:
            active = find_node(fcc, "ActiveRuntime")
            cs = find_node(fcc, "ConnectedStandbyRuntime")
            estimates["FullChargeActive"] = active.text.strip() if active is not None and active.text else None
            estimates["FullChargeConnectedStandby"] = cs.text.strip() if cs is not None and cs.text else None

    return {
        "ComputerSystem": {
            "Manufacturer": sys_prod.get("Vendor"),
            "Model": sys_prod.get("Name"),
        },
        "ComputerSystemProduct": sys_prod,
        "BIOS": bios,
        "WindowsRegistryOS": reg_os,
        "BatteryReport": batteries,
        "BatteryRuntimeEstimates": estimates,
    }


def _run_json_command(command: list[str], timeout: int = 45) -> dict[str, Any]:
    result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    if result.returncode != 0:
        return {"error": result.stderr.strip() or f"Command failed: {command[0]}"}
    try:
        parsed = json.loads(result.stdout)
        return parsed if isinstance(parsed, dict) else {"items": parsed}
    except json.JSONDecodeError:
        return {"text": result.stdout.strip()}


def _collect_windows() -> dict[str, Any]:
    script = r"""
$ErrorActionPreference = 'SilentlyContinue'
$items = [ordered]@{}
$items.ComputerSystem = Get-CimInstance Win32_ComputerSystem | Select-Object Manufacturer,Model,SystemType,TotalPhysicalMemory
$items.ComputerSystemProduct = Get-CimInstance Win32_ComputerSystemProduct | Select-Object Vendor,Name,Version,IdentifyingNumber,UUID,SKUNumber
$items.BaseBoard = Get-CimInstance Win32_BaseBoard | Select-Object Manufacturer,Product,Version,SerialNumber
$items.BIOS = Get-CimInstance Win32_BIOS | Select-Object Manufacturer,SMBIOSBIOSVersion,Version,ReleaseDate,SerialNumber
$items.Processor = Get-CimInstance Win32_Processor | Select-Object Name,Manufacturer,NumberOfCores,NumberOfLogicalProcessors,MaxClockSpeed
$items.VideoController = Get-CimInstance Win32_VideoController | Select-Object Name,AdapterRAM,DriverVersion,VideoModeDescription,CurrentHorizontalResolution,CurrentVerticalResolution,CurrentRefreshRate
$items.PhysicalMemory = Get-CimInstance Win32_PhysicalMemory | Select-Object Manufacturer,Capacity,Speed,ConfiguredClockSpeed,PartNumber
$items.DiskDrive = Get-CimInstance Win32_DiskDrive | Select-Object Model,Size,MediaType,InterfaceType
$items.WindowsRegistryBIOS = Get-ItemProperty -Path 'HKLM:\HARDWARE\DESCRIPTION\System\BIOS' | Select-Object SystemManufacturer,SystemProductName,SystemSKU,BaseBoardProduct,BIOSVersion
$items.WindowsRegistryCPU = Get-ItemProperty -Path 'HKLM:\HARDWARE\DESCRIPTION\System\CentralProcessor\0' | Select-Object ProcessorNameString,VendorIdentifier
$items.WindowsRegistryDisplay = Get-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}\*' | Select-Object DriverDesc,ProviderName,MatchingDeviceId,HardwareInformation.AdapterString
$items.WindowsDisplayEdid = Get-ChildItem -Path 'HKLM:\SYSTEM\CurrentControlSet\Enum\DISPLAY' -Recurse | Where-Object { $_.PSChildName -eq 'Device Parameters' } | ForEach-Object {
  $props = Get-ItemProperty -LiteralPath $_.PSPath -Name EDID
  if ($props.EDID) {
    [ordered]@{
      RegistryPath = $_.PSPath
      EDID = @($props.EDID)
    }
  }
}
$items.WindowsScreens = $null
try {
  Add-Type -TypeDefinition '
  using System;
  using System.Runtime.InteropServices;

  public class ScreenInfo {
      [DllImport("user32.dll", CharSet = CharSet.Ansi)]
      public static extern bool EnumDisplaySettings(string deviceName, int modeNum, ref DEVMODE devMode);

      [DllImport("user32.dll", CharSet = CharSet.Ansi)]
      public static extern bool EnumDisplayDevices(string lpDevice, uint iDevNum, ref DISPLAY_DEVICE lpDisplayDevice, uint dwFlags);

      [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Ansi)]
      public struct DEVMODE {
          [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 32)]
          public string dmDeviceName;
          public short dmSpecVersion;
          public short dmDriverVersion;
          public short dmSize;
          public short dmDriverExtra;
          public int dmFields;
          public int dmPositionX;
          public int dmPositionY;
          public int dmDisplayOrientation;
          public int dmDisplayFixedOutput;
          public short dmColor;
          public short dmDuplex;
          public short dmYResolution;
          public short dmTTOption;
          public short dmCollate;
          [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 32)]
          public string dmFormName;
          public short dmLogPixels;
          public short dmBitsPerPel;
          public int dmPelsWidth;
          public int dmPelsHeight;
          public int dmDisplayFlags;
          public int dmDisplayFrequency;
      }

      [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Ansi)]
      public struct DISPLAY_DEVICE {
          [MarshalAs(UnmanagedType.U4)]
          public int cb;
          [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 32)]
          public string DeviceName;
          [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 128)]
          public string DeviceString;
          [MarshalAs(UnmanagedType.U4)]
          public int StateFlags;
          [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 128)]
          public string DeviceID;
          [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 128)]
          public string DeviceKey;
      }

      public static DEVMODE GetMode(string device) {
          DEVMODE d = new DEVMODE();
          d.dmSize = (short)Marshal.SizeOf(d);
          EnumDisplaySettings(device, -1, ref d);
          return d;
      }

      public static string GetMonitorID(string adapterName) {
          DISPLAY_DEVICE d = new DISPLAY_DEVICE();
          d.cb = Marshal.SizeOf(d);
          if (EnumDisplayDevices(adapterName, 0, ref d, 0)) {
              return d.DeviceID;
          }
          return "";
      }
  }
  '
  Add-Type -AssemblyName System.Windows.Forms
  $items.WindowsScreens = [System.Windows.Forms.Screen]::AllScreens | ForEach-Object {
    $mode = [ScreenInfo]::GetMode($_.DeviceName)
    $mon = [ScreenInfo]::GetMonitorID($_.DeviceName)
    [ordered]@{
      DeviceName = $_.DeviceName
      Primary = $_.Primary
      Width = $mode.dmPelsWidth
      Height = $mode.dmPelsHeight
      RefreshRate = $mode.dmDisplayFrequency
      MonitorID = $mon
    }
  }
} catch {}
$items.WindowsRegistryOS = Get-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion' | Select-Object ProductName,DisplayVersion,CurrentBuild,UBR,EditionID
$diskEnum = Get-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Services\disk\Enum'
$cleanDiskEnum = [ordered]@{}
foreach ($prop in $diskEnum.PSObject.Properties) {
  if ($prop.Name -match '^\d+$' -or $prop.Name -eq 'Count') {
    $cleanDiskEnum[$prop.Name] = $prop.Value
  }
}
$items.WindowsRegistryDiskEnum = $cleanDiskEnum
$items.BatteryReport = $null
$items.BatteryRuntimeEstimates = $null
try {
  $batteryPath = Join-Path $env:TEMP ("infomation-extractor-battery-" + [Guid]::NewGuid().ToString() + ".xml")
  powercfg /batteryreport /output $batteryPath /xml | Out-Null
  [xml]$batteryXml = Get-Content -LiteralPath $batteryPath
  $ns = New-Object System.Xml.XmlNamespaceManager($batteryXml.NameTable)
  $ns.AddNamespace("b", "http://schemas.microsoft.com/battery/2012")
  $batteryNodes = $batteryXml.SelectNodes("//b:Batteries/b:Battery", $ns)
  $items.BatteryReport = @($batteryNodes | ForEach-Object {
    [ordered]@{
      Id = $_.Id
      Manufacturer = $_.Manufacturer
      Chemistry = $_.Chemistry
      DesignCapacity = $_.DesignCapacity
      FullChargeCapacity = $_.FullChargeCapacity
      CycleCount = $_.CycleCount
    }
  })
  $runtimeNodes = $batteryXml.SelectSingleNode("//b:RuntimeEstimates", $ns)
  if ($runtimeNodes) {
    $items.BatteryRuntimeEstimates = [ordered]@{
      DesignActive = $runtimeNodes.DesignCapacity.ActiveRuntime
      DesignConnectedStandby = $runtimeNodes.DesignCapacity.ConnectedStandbyRuntime
      FullChargeActive = $runtimeNodes.FullChargeCapacity.ActiveRuntime
      FullChargeConnectedStandby = $runtimeNodes.FullChargeCapacity.ConnectedStandbyRuntime
    }
  }
  Remove-Item -LiteralPath $batteryPath -Force
} catch {}
$items.DotNetMemory = $null
try {
  Add-Type -AssemblyName Microsoft.VisualBasic
  $ci = New-Object Microsoft.VisualBasic.Devices.ComputerInfo
  $items.DotNetMemory = [ordered]@{
    TotalPhysicalMemory = $ci.TotalPhysicalMemory
    AvailablePhysicalMemory = $ci.AvailablePhysicalMemory
  }
} catch {}
$items.DotNetDrives = [System.IO.DriveInfo]::GetDrives() | Where-Object { $_.IsReady } | ForEach-Object {
  [ordered]@{
    Name = $_.Name
    DriveType = $_.DriveType.ToString()
    TotalSize = $_.TotalSize
    AvailableFreeSpace = $_.AvailableFreeSpace
    VolumeLabel = $_.VolumeLabel
  }
}
$items | ConvertTo-Json -Depth 5
"""
    return _run_json_command(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script]
    )


def _collect_macos() -> dict[str, Any]:
    raw = _run_json_command(["system_profiler", "SPHardwareDataType", "SPDisplaysDataType", "SPPowerDataType", "-json"])
    cpu = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True, check=False)
    if cpu.returncode == 0 and cpu.stdout.strip():
        raw["cpu_brand_string"] = cpu.stdout.strip()
    return raw


def _collect_generic() -> dict[str, Any]:
    return {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "node": platform.node(),
    }


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if text.lower() in PLACEHOLDER_VALUES:
        return None
    return text


def _first(*values: Any) -> str | None:
    for value in values:
        cleaned = _clean(value)
        if cleaned:
            return cleaned
    return None


def _build_summary(raw: dict[str, Any], os_name: str) -> dict[str, Any]:
    if os_name.lower() == "windows":
        cs = raw.get("ComputerSystem") or {}
        csp = raw.get("ComputerSystemProduct") or {}
        board = raw.get("BaseBoard") or {}
        bios = raw.get("BIOS") or {}
        cpu = raw.get("Processor") or {}
        registry_bios = raw.get("WindowsRegistryBIOS") or {}
        registry_cpu = raw.get("WindowsRegistryCPU") or {}
        registry_display = raw.get("WindowsRegistryDisplay") or []
        display_edid = raw.get("WindowsDisplayEdid") or []
        windows_screens = raw.get("WindowsScreens") or []
        registry_os = raw.get("WindowsRegistryOS") or {}
        disk_enum = raw.get("WindowsRegistryDiskEnum") or {}
        battery_report = raw.get("BatteryReport") or []
        dotnet_memory = raw.get("DotNetMemory") or {}
        dotnet_drives = raw.get("DotNetDrives") or []
        gpu = raw.get("VideoController") or []
        disks = raw.get("DiskDrive") or []
        sku = _first(csp.get("SKUNumber"), csp.get("Version"), registry_bios.get("SystemSKU"))
        registry_model = _first(registry_bios.get("SystemProductName"))
        marketing_model = _marketing_model_from_sku(sku)
        return {
            "manufacturer": _normalize_manufacturer(
                _first(csp.get("Vendor"), cs.get("Manufacturer"), registry_bios.get("SystemManufacturer"))
            ),
            "system_model": _first(csp.get("Name"), cs.get("Model"), registry_model),
            "marketing_model": marketing_model,
            "system_sku": sku,
            "baseboard": _first(board.get("Product"), board.get("Version"), registry_bios.get("BaseBoardProduct")),
            "bios_version": _first(
                bios.get("SMBIOSBIOSVersion"), bios.get("Version"), registry_bios.get("BIOSVersion")
            ),
            "cpu": _first(cpu.get("Name"), registry_cpu.get("ProcessorNameString")),
            "gpu": _unique_names(_names_from_list(gpu) + _gpu_names_from_registry(registry_display)),
            "memory": _format_bytes(_first(dotnet_memory.get("TotalPhysicalMemory"))),
            "storage": _unique_names(_names_from_list(disks, key="Model") + _disk_names_from_registry(disk_enum)),
            "drives": _drive_summaries(dotnet_drives),
            "display": _display_summaries_from_edid(display_edid, windows_screens),
            "battery": _battery_summaries(battery_report, raw.get("BatteryRuntimeEstimates")),
            "os": _format_windows_os(registry_os),
        }

    if os_name.lower() == "darwin":
        hardware_items = raw.get("SPHardwareDataType") or []
        hardware = hardware_items[0] if hardware_items else {}
        return {
            "manufacturer": "Apple",
            "system_model": _first(hardware.get("machine_name"), hardware.get("model_name")),
            "system_sku": _first(hardware.get("machine_model")),
            "cpu": _first(hardware.get("chip_type"), raw.get("cpu_brand_string")),
            "gpu": _macos_gpu_names(raw.get("SPDisplaysDataType") or []),
            "memory": _first(hardware.get("physical_memory")),
            "display": _macos_display_summaries(raw.get("SPDisplaysDataType") or []),
            "battery": _macos_battery_summaries(raw.get("SPPowerDataType") or []),
        }

    return {
        "manufacturer": None,
        "system_model": raw.get("platform"),
        "system_sku": raw.get("machine"),
        "cpu": raw.get("processor"),
        "gpu": [],
        "display": [],
        "battery": [],
    }


def _names_from_list(value: Any, key: str = "Name") -> list[str]:
    if isinstance(value, dict):
        value = [value]
    names: list[str] = []
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                name = _clean(item.get(key))
                if name and name not in names:
                    names.append(name)
    return names


def _gpu_names_from_registry(value: Any) -> list[str]:
    if isinstance(value, dict):
        value = [value]
    names: list[str] = []
    if not isinstance(value, list):
        return names

    for item in value:
        if not isinstance(item, dict):
            continue
        candidates = [
            item.get("HardwareInformation.AdapterString"),
            item.get("DriverDesc"),
        ]
        for candidate in candidates:
            if isinstance(candidate, list):
                for entry in candidate:
                    _append_clean_name(names, entry)
            else:
                _append_clean_name(names, candidate)
    return names


def _macos_gpu_names(value: Any) -> list[str]:
    if isinstance(value, dict):
        value = [value]
    names: list[str] = []
    if not isinstance(value, list):
        return names

    for item in value:
        if not isinstance(item, dict):
            continue
        for key in ("sppci_model", "spdisplays_vendor", "_name"):
            _append_clean_name(names, item.get(key))
    return names


def _display_summaries_from_edid(edid_items: Any, screen_items: Any) -> list[dict[str, Any]]:
    if isinstance(edid_items, dict):
        edid_items = [edid_items]
    if isinstance(screen_items, dict):
        screen_items = [screen_items]
    if not isinstance(screen_items, list):
        screen_items = []

    displays: list[dict[str, Any]] = []
    seen: set[str] = set()
    if isinstance(edid_items, list):
        for item in edid_items:
            if not isinstance(item, dict):
                continue
            parsed = _parse_edid(item.get("EDID") or [], item.get("RegistryPath"))
            if not parsed:
                continue
            key = "|".join(str(parsed.get(part) or "") for part in ("manufacturer_id", "product_code", "name"))
            if key in seen:
                continue
            seen.add(key)
            displays.append(parsed)

    def _get_monitor_model(monitor_id: str | None) -> str | None:
        if not monitor_id:
            return None
        parts = [p for p in monitor_id.split("\\") if p]
        if len(parts) >= 2:
            return parts[1].upper()
        return None

    matched_indices: set[int] = set()
    for screen in screen_items:
        if not isinstance(screen, dict):
            continue
        
        matched_index = -1
        screen_mon_model = _get_monitor_model(screen.get("MonitorID"))
        
        if screen_mon_model:
            for i, edid in enumerate(displays):
                edid_model = edid.get("registry_hint", "").upper()
                if edid_model == screen_mon_model and i not in matched_indices:
                    matched_index = i
                    break
        
        if matched_index == -1:
            for i in range(len(displays)):
                if i not in matched_indices:
                    matched_index = i
                    break

        current_resolution = _format_resolution(screen.get("Width"), screen.get("Height"))
        refresh_rate = screen.get("RefreshRate")
        refresh_str = f"{refresh_rate} Hz" if refresh_rate and refresh_rate > 0 else None

        if matched_index != -1 and matched_index < len(displays):
            matched_indices.add(matched_index)
            displays[matched_index]["current_desktop_resolution"] = current_resolution
            displays[matched_index]["primary"] = bool(screen.get("Primary"))
            if refresh_str:
                displays[matched_index]["active_refresh_rate"] = refresh_str
                if "estimated_refresh_rate" not in displays[matched_index]:
                    displays[matched_index]["estimated_refresh_rate"] = refresh_str
            if "native_or_preferred_resolution" not in displays[matched_index] and current_resolution:
                displays[matched_index]["native_or_preferred_resolution"] = current_resolution
        else:
            disp_info = {
                "name": screen.get("DeviceName") or f"Display {len(displays) + 1}",
                "current_desktop_resolution": current_resolution,
                "primary": bool(screen.get("Primary")),
            }
            if refresh_str:
                disp_info["active_refresh_rate"] = refresh_str
                disp_info["estimated_refresh_rate"] = refresh_str
            if current_resolution:
                disp_info["native_or_preferred_resolution"] = current_resolution
            displays.append(disp_info)

    return displays


def _parse_edid(raw_edid: Any, registry_path: Any = None) -> dict[str, Any] | None:
    if not isinstance(raw_edid, list) or len(raw_edid) < 128:
        return None
    try:
        edid = [int(byte) & 0xFF for byte in raw_edid]
    except (TypeError, ValueError):
        return None

    manufacturer_id = _edid_manufacturer_id(edid[8], edid[9])
    product_code = f"0x{edid[10] | (edid[11] << 8):04X}"
    width_cm = edid[21] or None
    height_cm = edid[22] or None
    diagonal = _display_diagonal(width_cm, height_cm)
    name = _edid_descriptor_text(edid, 0xFC)
    ascii_name = _edid_descriptor_text(edid, 0xFE)
    timing = _best_edid_timing(edid)
    range_limits = _edid_range_limits(edid)

    display: dict[str, Any] = {
        "name": name or ascii_name or manufacturer_id,
        "manufacturer_id": manufacturer_id,
        "product_code": product_code,
        "physical_size": _format_physical_size(width_cm, height_cm, diagonal),
    }
    if timing:
        display["native_or_preferred_resolution"] = timing.get("resolution")
        display["estimated_refresh_rate"] = timing.get("refresh_rate")
    if range_limits:
        display["refresh_range"] = range_limits.get("vertical")
        display["horizontal_scan_range"] = range_limits.get("horizontal")
    if registry_path:
        display["registry_hint"] = _display_registry_hint(str(registry_path))
    return {key: value for key, value in display.items() if value not in (None, "", [])}


def _edid_manufacturer_id(first: int, second: int) -> str:
    value = (first << 8) | second
    chars = [
        chr(((value >> 10) & 0x1F) + 64),
        chr(((value >> 5) & 0x1F) + 64),
        chr((value & 0x1F) + 64),
    ]
    return "".join(chars).strip("@")


def _edid_descriptor_text(edid: list[int], descriptor_type: int) -> str | None:
    for offset in (54, 72, 90, 108):
        block = edid[offset : offset + 18]
        if len(block) < 18:
            continue
        if block[0] == 0 and block[1] == 0 and block[3] == descriptor_type:
            text = bytes(block[5:18]).decode("ascii", errors="ignore").replace("\x00", "").strip()
            text = " ".join(text.split())
            if text:
                return text
    return None


def _best_edid_timing(edid: list[int]) -> dict[str, str] | None:
    candidates: list[dict[str, Any]] = []
    for offset in (54, 72, 90, 108):
        timing = _parse_detailed_timing(edid[offset : offset + 18])
        if timing:
            candidates.append(timing)

    extension_count = edid[126] if len(edid) > 126 else 0
    for extension_index in range(extension_count):
        start = 128 * (extension_index + 1)
        extension = edid[start : start + 128]
        if len(extension) < 128:
            continue
        if extension[0] == 0x02:
            dtd_start = extension[2]
            if 4 <= dtd_start < 127:
                for offset in range(start + dtd_start, start + 127, 18):
                    timing = _parse_detailed_timing(edid[offset : offset + 18])
                    if timing:
                        candidates.append(timing)

    if not candidates:
        return None
    best = max(candidates, key=lambda item: item.get("pixels", 0))
    return {
        "resolution": best["resolution"],
        "refresh_rate": best["refresh_rate"],
    }


def _parse_detailed_timing(block: list[int]) -> dict[str, Any] | None:
    if len(block) < 18:
        return None
    pixel_clock_10khz = block[0] | (block[1] << 8)
    if pixel_clock_10khz <= 0:
        return None
    h_active = block[2] | ((block[4] & 0xF0) << 4)
    h_blank = block[3] | ((block[4] & 0x0F) << 8)
    v_active = block[5] | ((block[7] & 0xF0) << 4)
    v_blank = block[6] | ((block[7] & 0x0F) << 8)
    if h_active <= 0 or v_active <= 0:
        return None
    total_pixels = (h_active + h_blank) * (v_active + v_blank)
    refresh = None
    if total_pixels > 0:
        refresh = round((pixel_clock_10khz * 10000) / total_pixels, 1)
    return {
        "resolution": f"{h_active} x {v_active}",
        "refresh_rate": f"{refresh:g} Hz" if refresh else None,
        "pixels": h_active * v_active,
    }


def _edid_range_limits(edid: list[int]) -> dict[str, str] | None:
    for offset in (54, 72, 90, 108):
        block = edid[offset : offset + 18]
        if len(block) < 18:
            continue
        if block[0] == 0 and block[1] == 0 and block[3] == 0xFD:
            return {
                "vertical": f"{block[5]}-{block[6]} Hz",
                "horizontal": f"{block[7]}-{block[8]} kHz",
            }
    return None


def _display_diagonal(width_cm: int | None, height_cm: int | None) -> float | None:
    if not width_cm or not height_cm:
        return None
    return round(((width_cm**2 + height_cm**2) ** 0.5) / 2.54, 1)


def _format_physical_size(width_cm: int | None, height_cm: int | None, diagonal: float | None) -> str | None:
    if not width_cm or not height_cm:
        return None
    size = f"{width_cm} x {height_cm} cm"
    if diagonal:
        size += f" (~{diagonal:g} in)"
    return size


def _display_registry_hint(path: str) -> str | None:
    marker = "\\DISPLAY\\"
    if marker not in path:
        return None
    tail = path.split(marker, 1)[1]
    return tail.split("\\", 1)[0]


def _format_resolution(width: Any, height: Any) -> str | None:
    try:
        return f"{int(width)} x {int(height)}"
    except (TypeError, ValueError):
        return None


def _battery_summaries(value: Any, estimates: Any = None) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        value = [value]
    if not isinstance(value, list):
        return []
    batteries: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        battery_data = {
            "id": item.get("Id"),
            "manufacturer": item.get("Manufacturer"),
            "chemistry": item.get("Chemistry"),
            "design_capacity": _format_mwh(item.get("DesignCapacity")),
            "full_charge_capacity": _format_mwh(item.get("FullChargeCapacity")),
            "cycle_count": _first(item.get("CycleCount")),
        }
        if estimates and isinstance(estimates, dict):
            design_active = _parse_battery_duration(estimates.get("DesignActive"))
            full_active = _parse_battery_duration(estimates.get("FullChargeActive"))
            if design_active:
                battery_data["estimated_active_runtime_design"] = design_active
            if full_active:
                battery_data["estimated_active_runtime_full_charge"] = full_active
        batteries.append(battery_data)
    return [{key: val for key, val in battery.items() if val not in (None, "", [])} for battery in batteries]


def _parse_battery_duration(duration_str: Any) -> str | None:
    if not duration_str:
        return None
    val = str(duration_str).strip()
    if not val.startswith("PT"):
        return val
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", val)
    if not match:
        return val
    h, m, s = match.groups()
    parts = []
    if h:
        parts.append(f"{h}h")
    if m:
        parts.append(f"{m}m")
    if s and not h:
        parts.append(f"{s}s")
    return " ".join(parts) if parts else "0m"


def _macos_display_summaries(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        value = [value]
    if not isinstance(value, list):
        return []
        
    displays: list[dict[str, Any]] = []
    seen: set[str] = set()
    
    gpu_list = []
    for item in value:
        if isinstance(item, dict):
            if "_items" in item:
                gpu_list.extend(item["_items"])
            else:
                gpu_list.append(item)
        elif isinstance(item, list):
            gpu_list.extend(item)
            
    for gpu_item in gpu_list:
        if not isinstance(gpu_item, dict):
            continue
            
        ndrvs = gpu_item.get("spdisplays_ndrvs")
        if isinstance(ndrvs, dict):
            ndrvs = [ndrvs]
        if not isinstance(ndrvs, list):
            ndrvs = [gpu_item]
            
        for display_item in ndrvs:
            if not isinstance(display_item, dict):
                continue
            resolution = _first(
                display_item.get("spdisplays_resolution"),
                display_item.get("_spdisplays_resolution"),
                display_item.get("spdisplays_pixels"),
                display_item.get("_spdisplays_pixels")
            )
            if not resolution and display_item is gpu_item:
                continue
                
            name = _first(
                display_item.get("_name"),
                display_item.get("spdisplays_display_name"),
                display_item.get("sppci_model")
            )
            if not name:
                continue
                
            display_type = _first(
                display_item.get("spdisplays_display_type"),
                display_item.get("spdisplays_connection_type")
            )
            main = display_item.get("spdisplays_main") or display_item.get("spdisplays_main_display")
            
            key = f"{name}|{resolution}"
            if key in seen:
                continue
            seen.add(key)
            
            disp = {
                "name": name,
                "native_or_preferred_resolution": resolution,
                "display_type": display_type,
                "main": main
            }
            displays.append({k: v for k, v in disp.items() if v not in (None, "", [])})
            
    return displays


def _macos_battery_summaries(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        value = [value]
    if not isinstance(value, list):
        return []
    
    batteries: list[dict[str, Any]] = []
    charger_info: dict[str, Any] = {}
    
    items_to_process = list(value)
    while items_to_process:
        current = items_to_process.pop(0)
        if isinstance(current, dict):
            if "_items" in current:
                items_to_process.extend(current["_items"])
            
            name = current.get("_name")
            if name == "sppower_battery_information":
                battery_data = {
                    "id": current.get("sppower_device_name"),
                    "manufacturer": current.get("sppower_battery_manufacturer") or current.get("sppower_device_name"),
                    "chemistry": current.get("sppower_battery_chemistry"),
                    "design_capacity": current.get("sppower_design_capacity") or current.get("sppower_battery_design_capacity"),
                    "full_charge_capacity": current.get("sppower_max_capacity") or current.get("sppower_battery_max_capacity"),
                    "cycle_count": current.get("sppower_cycle_count"),
                    "health": current.get("sppower_battery_health") or current.get("sppower_battery_health_info", {}).get("sppower_battery_health"),
                }
                
                for cap_key in ("design_capacity", "full_charge_capacity"):
                    val = battery_data[cap_key]
                    if val is not None and str(val).isdigit():
                        battery_data[cap_key] = f"{val} mAh"
                        
                batteries.append({k: v for k, v in battery_data.items() if v not in (None, "", [])})
            elif name == "sppower_ac_charger_information":
                charger_info = {
                    "charger_connected": current.get("sppower_battery_charger_connected"),
                    "charger_wattage": current.get("sppower_ac_charger_watts"),
                }
        elif isinstance(current, list):
            items_to_process.extend(current)
            
    if charger_info and batteries:
        for battery in batteries:
            if "charger_wattage" in charger_info and charger_info["charger_wattage"]:
                battery["charger_wattage"] = f"{charger_info['charger_wattage']} W"
            if "charger_connected" in charger_info and charger_info["charger_connected"]:
                battery["charger_connected"] = charger_info["charger_connected"]
                
    if not batteries and charger_info:
        summary = {}
        if "charger_wattage" in charger_info and charger_info["charger_wattage"]:
            summary["charger_wattage"] = f"{charger_info['charger_wattage']} W"
        return [summary] if summary else []
        
    return batteries


def _append_clean_name(names: list[str], value: Any) -> None:
    name = _clean(value)
    if name and name not in names:
        names.append(name)


def _unique_names(values: list[str]) -> list[str]:
    names: list[str] = []
    for value in values:
        _append_clean_name(names, value)
    return names


def _disk_names_from_registry(value: Any) -> list[str]:
    if not isinstance(value, dict):
        return []
    names: list[str] = []
    for key, raw in value.items():
        if not str(key).isdigit():
            continue
        text = str(raw).replace("\\", " ")
        text = text.replace("&Ven_", " ").replace("&Prod_", " ")
        text = text.replace("Disk", " ").replace("SCSI", " ").replace("NVMe", "NVMe ")
        parts = [part for part in text.split() if part and not part.startswith(("5&", "6&", "0&"))]
        readable = " ".join(parts[:6]).replace("_", " ").strip()
        if readable:
            _append_clean_name(names, readable)
    return names


def _drive_summaries(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        value = [value]
    if not isinstance(value, list):
        return []
    drives: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        drives.append(
            {
                "name": item.get("Name"),
                "type": item.get("DriveType"),
                "total": _format_bytes(item.get("TotalSize")),
                "free": _format_bytes(item.get("AvailableFreeSpace")),
                "label": item.get("VolumeLabel"),
            }
        )
    return drives


def _format_windows_os(value: dict[str, Any]) -> str | None:
    product = _first(value.get("ProductName"), value.get("EditionID"))
    version = _first(value.get("DisplayVersion"))
    build = _first(value.get("CurrentBuild"))
    ubr = _first(value.get("UBR"))
    pieces = [piece for piece in (product, version, f"build {build}.{ubr}" if build and ubr else None) if piece]
    return " ".join(pieces) if pieces else None


def _format_bytes(value: Any) -> str | None:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    units = ["B", "KB", "MB", "GB", "TB"]
    amount = float(number)
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            return f"{amount:.1f} {unit}" if unit != "B" else f"{int(amount)} B"
        amount /= 1024
    return None


def _format_mwh(value: Any) -> str | None:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return f"{number / 1000:.1f} Wh"


def _normalize_manufacturer(value: str | None) -> str | None:
    if not value:
        return value
    aliases = {
        "LENOVO": "Lenovo",
        "ASUSTEK COMPUTER INC.": "ASUS",
        "ASUSTEK COMPUTER INC": "ASUS",
        "HP": "HP",
        "HEWLETT-PACKARD": "HP",
        "DELL INC.": "Dell",
        "APPLE INC.": "Apple",
    }
    return aliases.get(value.strip().upper(), value.strip())


def _marketing_model_from_sku(value: str | None) -> str | None:
    if not value:
        return None
    text = value.strip()
    if "_FM_" in text:
        text = text.split("_FM_", 1)[1]
    text = text.replace("_", " ").strip()
    return _clean(text)


def _parse_key_value_text(text: str) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        separator = ":" if ":" in line else "=" if "=" in line else None
        if not separator:
            continue
        key, value = line.split(separator, 1)
        key = key.strip()
        value = value.strip()
        if key and value:
            values[key] = value
    return values or {"text": text[:10000]}


def _parse_xml_text(text: str) -> dict[str, Any]:
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return {"text": text[:10000]}

    values: dict[str, Any] = {}
    for elem in root.iter():
        name = elem.attrib.get("name") or elem.attrib.get("Name") or elem.tag
        value = (elem.text or "").strip()
        if value:
            values[name] = value
    return values


def _summary_from_flattened(raw: dict[str, Any]) -> dict[str, Any]:
    lowered = {str(key).lower(): value for key, value in raw.items()}

    def find(*names: str) -> Any:
        for name in names:
            if name.lower() in lowered:
                return lowered[name.lower()]
        for key, value in lowered.items():
            if any(name.lower() in key for name in names):
                return value
        return None

    return {
        "manufacturer": _first(find("system manufacturer", "manufacturer", "vendor")),
        "system_model": _first(find("system model", "model", "product name", "name")),
        "system_sku": _first(find("system sku", "sku", "version")),
        "baseboard": _first(find("baseboard product", "base board product", "board product")),
        "bios_version": _first(find("bios version", "smbiosbiosversion")),
        "cpu": _first(find("processor", "cpu")),
        "gpu": _first(find("display", "video", "gpu")),
    }
