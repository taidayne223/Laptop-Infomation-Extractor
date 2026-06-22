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
        "source": path.name,
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
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return {"error": f"Command timed out after {timeout}s: {command[0]}"}
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
$items.ComputerSystem = Get-CimInstance Win32_ComputerSystem | Select-Object Manufacturer,Model,SystemType,PCSystemType,PCSystemTypeEx,TotalPhysicalMemory,HypervisorPresent
$items.ComputerSystemProduct = Get-CimInstance Win32_ComputerSystemProduct | Select-Object Vendor,Name,Version,IdentifyingNumber,UUID,SKUNumber
$items.BaseBoard = Get-CimInstance Win32_BaseBoard | Select-Object Manufacturer,Product,Version,SerialNumber
$items.BIOS = Get-CimInstance Win32_BIOS | Select-Object Manufacturer,SMBIOSBIOSVersion,Version,ReleaseDate,SerialNumber
$items.SystemEnclosure = Get-CimInstance Win32_SystemEnclosure | Select-Object Manufacturer,ChassisTypes,SMBIOSAssetTag,SerialNumber,Version
$items.Processor = Get-CimInstance Win32_Processor | Select-Object Name,Manufacturer,NumberOfCores,NumberOfLogicalProcessors,MaxClockSpeed,CurrentClockSpeed,L2CacheSize,L3CacheSize,SocketDesignation,VirtualizationFirmwareEnabled
$items.VideoController = Get-CimInstance Win32_VideoController | Select-Object Name,AdapterRAM,DriverVersion,VideoProcessor,VideoModeDescription,CurrentHorizontalResolution,CurrentVerticalResolution,CurrentRefreshRate,Status,PNPDeviceID
$items.PhysicalMemory = Get-CimInstance Win32_PhysicalMemory | Select-Object Manufacturer,Capacity,Speed,ConfiguredClockSpeed,PartNumber,BankLabel,DeviceLocator,FormFactor,MemoryType,SMBIOSMemoryType
$items.PhysicalMemoryArray = Get-CimInstance Win32_PhysicalMemoryArray | Select-Object MemoryDevices,MaxCapacity,MaxCapacityEx,Use
$items.DiskDrive = Get-CimInstance Win32_DiskDrive | Select-Object Model,Size,MediaType,InterfaceType,FirmwareRevision,Partitions,Status,SerialNumber,PNPDeviceID
try {
  $items.PhysicalDisks = Get-PhysicalDisk | Select-Object FriendlyName,MediaType,BusType,Size,HealthStatus,OperationalStatus,FirmwareVersion,SerialNumber,SpindleSpeed
} catch {}
$items.NetworkAdapter = Get-CimInstance Win32_NetworkAdapter | Where-Object { $_.PhysicalAdapter -eq $true -or $_.NetEnabled -eq $true } | Select-Object Name,Manufacturer,AdapterType,Speed,NetConnectionID,ServiceName,PNPDeviceID
$items.NetworkAdapterConfiguration = Get-CimInstance Win32_NetworkAdapterConfiguration | Where-Object { $_.IPEnabled -eq $true } | Select-Object Description,DHCPEnabled,DNSServerSearchOrder,IPSubnet,DefaultIPGateway
$items.SoundDevice = Get-CimInstance Win32_SoundDevice | Select-Object Name,Manufacturer,Status
$items.Camera = Get-CimInstance Win32_PnPEntity | Where-Object { $_.Class -match 'Camera|Image' -or $_.Name -match 'Camera|Webcam|IR Camera' } | Select-Object Name,Manufacturer,Status,Class
$items.BiometricAndSensors = Get-CimInstance Win32_PnPEntity | Where-Object { $_.Class -match 'Biometric|Sensor|SmartCardReader' -or $_.Name -match 'Fingerprint|IR Camera|Hello|Sensor|Accelerometer|Ambient Light' } | Select-Object Name,Manufacturer,Status,Class
$items.PnpSignedDrivers = Get-CimInstance Win32_PnPSignedDriver | Where-Object { $_.DeviceClass -match 'DISPLAY|MEDIA|CAMERA|IMAGE|NET|BLUETOOTH|BIOMETRIC|HIDCLASS|KEYBOARD|MOUSE|USB|SYSTEM' } | Select-Object DeviceName,DeviceClass,Manufacturer,DriverProviderName,DriverVersion,HardwareID,CompatibleID,DeviceID
$items.InputDevices = [ordered]@{
  Keyboard = Get-CimInstance Win32_Keyboard | Select-Object Name,Description,NumberOfFunctionKeys
  Pointing = Get-CimInstance Win32_PointingDevice | Select-Object Name,Manufacturer,PointingType,NumberOfButtons
}
$items.Security = $null
try {
  $items.Security = Get-Tpm | Select-Object TpmPresent,TpmReady,SpecVersion,ManufacturerVersion
} catch {}
$items.WindowsFirmware = [ordered]@{}
try {
  $items.WindowsFirmware.SecureBoot = Confirm-SecureBootUEFI
} catch {}
try {
  $items.WindowsFirmware.FirmwareType = (Get-ComputerInfo -Property BiosFirmwareType).BiosFirmwareType
} catch {}
$items.UsbAndThunderbolt = Get-CimInstance Win32_PnPEntity | Where-Object { $_.Name -match 'Thunderbolt|USB4|USB 4|USB 3|USB xHCI|USB Root Hub|Type-C|UCM-UCSI|USB Connector' } | Select-Object Name,Manufacturer,Status,Class
$items.PowerCapabilities = $null
try {
  $items.PowerCapabilities = (powercfg /a | Out-String).Trim()
} catch {}
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
$items.WindowsWmiMonitors = $null
try {
  $items.WindowsWmiMonitors = Get-CimInstance -Namespace root\wmi -ClassName WmiMonitorID | ForEach-Object {
    [ordered]@{
      InstanceName = $_.InstanceName
      ManufacturerName = -join ($_.ManufacturerName | Where-Object { $_ -ne 0 } | ForEach-Object { [char]$_ })
      ProductCodeID = -join ($_.ProductCodeID | Where-Object { $_ -ne 0 } | ForEach-Object { [char]$_ })
      UserFriendlyName = -join ($_.UserFriendlyName | Where-Object { $_ -ne 0 } | ForEach-Object { [char]$_ })
      SerialNumberID = -join ($_.SerialNumberID | Where-Object { $_ -ne 0 } | ForEach-Object { [char]$_ })
      Active = $_.Active
    }
  }
} catch {}
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
$items.WindowsComputerInfo = $null
try {
  $items.WindowsComputerInfo = Get-ComputerInfo | Select-Object WindowsProductName,WindowsVersion,OsHardwareAbstractionLayer,CsManufacturer,CsModel,CsSystemType,CsPCSystemType,CsProcessors,CsNumberOfLogicalProcessors,CsTotalPhysicalMemory,BiosName,BiosVersion,BiosReleaseDate,BiosFirmwareType
} catch {}
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
$items.BatteryStatic = Get-CimInstance Win32_Battery | Select-Object Name,DeviceID,Manufacturer,Chemistry,DesignVoltage,EstimatedChargeRemaining,EstimatedRunTime,BatteryStatus,Status
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
$items | ConvertTo-Json -Depth 7
"""
    return _run_json_command(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script]
    )


def _collect_macos() -> dict[str, Any]:
    raw = _run_json_command(
        [
            "system_profiler",
            "SPHardwareDataType",
            "SPDisplaysDataType",
            "SPPowerDataType",
            "SPNetworkDataType",
            "SPBluetoothDataType",
            "SPAudioDataType",
            "SPCameraDataType",
            "SPThunderboltDataType",
            "SPUSBDataType",
            "SPMemoryDataType",
            "SPNVMeDataType",
            "SPiBridgeDataType",
            "SPDiagnosticsDataType",
            "-json",
        ],
        timeout=120,
    )
    cpu = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True, check=False)
    if cpu.returncode == 0 and cpu.stdout.strip():
        raw["cpu_brand_string"] = cpu.stdout.strip()
    for key, command in {
        "hw_model": ["sysctl", "-n", "hw.model"],
        "hw_machine": ["sysctl", "-n", "hw.machine"],
        "hw_memsize": ["sysctl", "-n", "hw.memsize"],
    }.items():
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode == 0 and result.stdout.strip():
            raw[key] = result.stdout.strip()
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
        enclosure = raw.get("SystemEnclosure") or {}
        cpu = raw.get("Processor") or {}
        registry_bios = raw.get("WindowsRegistryBIOS") or {}
        registry_cpu = raw.get("WindowsRegistryCPU") or {}
        registry_display = raw.get("WindowsRegistryDisplay") or []
        display_edid = raw.get("WindowsDisplayEdid") or []
        wmi_monitors = raw.get("WindowsWmiMonitors") or []
        windows_screens = raw.get("WindowsScreens") or []
        registry_os = raw.get("WindowsRegistryOS") or {}
        computer_info = raw.get("WindowsComputerInfo") or {}
        disk_enum = raw.get("WindowsRegistryDiskEnum") or {}
        battery_report = raw.get("BatteryReport") or []
        battery_static = raw.get("BatteryStatic") or []
        dotnet_memory = raw.get("DotNetMemory") or {}
        dotnet_drives = raw.get("DotNetDrives") or []
        gpu = raw.get("VideoController") or []
        disks = raw.get("DiskDrive") or []
        physical_disks = raw.get("PhysicalDisks") or []
        network = raw.get("NetworkAdapter") or []
        audio = raw.get("SoundDevice") or []
        camera = raw.get("Camera") or []
        biometric_and_sensors = raw.get("BiometricAndSensors") or []
        input_devices = raw.get("InputDevices") or {}
        security = raw.get("Security") or {}
        firmware = raw.get("WindowsFirmware") or {}
        ports = raw.get("UsbAndThunderbolt") or []
        sku = _first(csp.get("SKUNumber"), csp.get("Version"), registry_bios.get("SystemSKU"))
        registry_model = _first(registry_bios.get("SystemProductName"))
        marketing_model = _marketing_model_from_sku(sku)
        total_memory = _format_bytes(
            _first(dotnet_memory.get("TotalPhysicalMemory"), computer_info.get("CsTotalPhysicalMemory"), cs.get("TotalPhysicalMemory"))
        )
        return {
            "manufacturer": _normalize_manufacturer(
                _first(csp.get("Vendor"), cs.get("Manufacturer"), registry_bios.get("SystemManufacturer"))
            ),
            "system_model": _first(csp.get("Name"), cs.get("Model"), registry_model),
            "marketing_model": marketing_model,
            "system_sku": sku,
            "baseboard": _first(board.get("Product"), board.get("Version"), registry_bios.get("BaseBoardProduct")),
            "chassis": _chassis_summary(enclosure, cs),
            "bios_version": _first(
                bios.get("SMBIOSBIOSVersion"),
                bios.get("Version"),
                registry_bios.get("BIOSVersion"),
                computer_info.get("BiosVersion"),
            ),
            "firmware": _firmware_summary(firmware, computer_info),
            "cpu": _cpu_summary(cpu, registry_cpu, computer_info),
            "gpu": _unique_names(_names_from_list(gpu) + _gpu_names_from_registry(registry_display)),
            "gpu_details": _gpu_summaries(gpu, registry_display, raw.get("PnpSignedDrivers")),
            "memory": total_memory,
            "memory_modules": _memory_module_summaries(raw.get("PhysicalMemory")),
            "memory_layout": _memory_layout_summary(raw.get("PhysicalMemoryArray"), raw.get("PhysicalMemory"), total_memory),
            "storage": _unique_names(
                _names_from_list(disks, key="Model")
                + _names_from_list(physical_disks, key="FriendlyName")
                + _disk_names_from_registry(disk_enum)
            ),
            "storage_details": _storage_summaries(disks, physical_disks),
            "drives": _drive_summaries(dotnet_drives),
            "display": _display_summaries_from_edid(display_edid, windows_screens, wmi_monitors),
            "battery": _battery_summaries(battery_report, raw.get("BatteryRuntimeEstimates"), battery_static),
            "network": _network_summaries(network),
            "audio": _device_summaries(audio),
            "camera": _device_summaries(camera),
            "input": _input_summaries(input_devices),
            "security": _security_summary(security, firmware),
            "ports_or_controllers": _device_summaries(ports),
            "biometric_or_sensors": _device_summaries(biometric_and_sensors),
            "device_drivers": _driver_summaries(raw.get("PnpSignedDrivers")),
            "power_capabilities": _power_capability_summary(raw.get("PowerCapabilities")),
            "local_evidence_crosscheck": _windows_evidence_crosscheck(raw),
            "os": _format_windows_os(registry_os, computer_info),
        }

    if os_name.lower() == "darwin":
        hardware_items = raw.get("SPHardwareDataType") or []
        hardware = hardware_items[0] if hardware_items else {}
        return {
            "manufacturer": "Apple",
            "system_model": _first(hardware.get("machine_name"), hardware.get("model_name")),
            "system_sku": _first(hardware.get("machine_model"), raw.get("hw_model"), raw.get("hw_machine")),
            "cpu": _first(hardware.get("chip_type"), raw.get("cpu_brand_string")),
            "gpu": _macos_gpu_names(raw.get("SPDisplaysDataType") or []),
            "memory": _first(hardware.get("physical_memory"), _format_bytes(raw.get("hw_memsize"))),
            "memory_modules": _macos_memory_summaries(raw.get("SPMemoryDataType") or []),
            "storage": _macos_storage_names([], raw.get("SPNVMeDataType") or []),
            "storage_details": _macos_storage_summaries([], raw.get("SPNVMeDataType") or []),
            "display": _macos_display_summaries(raw.get("SPDisplaysDataType") or []),
            "battery": _macos_battery_summaries(raw.get("SPPowerDataType") or []),
            "network": _macos_named_items(raw.get("SPNetworkDataType") or []),
            "bluetooth": _macos_named_items(raw.get("SPBluetoothDataType") or []),
            "audio": _macos_named_items(raw.get("SPAudioDataType") or []),
            "camera": _macos_named_items(raw.get("SPCameraDataType") or []),
            "ports_or_controllers": _macos_named_items(
                _as_list(raw.get("SPThunderboltDataType")) + _as_list(raw.get("SPUSBDataType"))
            ),
            "local_evidence_crosscheck": _macos_evidence_crosscheck(raw),
            "os": f"macOS {platform.mac_ver()[0]}" if platform.mac_ver()[0] else "macOS",
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


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


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


def _cpu_summary(cpu: Any, registry_cpu: Any, computer_info: Any) -> str | None:
    if isinstance(cpu, list):
        cpu = cpu[0] if cpu else {}
    if not isinstance(cpu, dict):
        cpu = {}
    if not isinstance(registry_cpu, dict):
        registry_cpu = {}
    if not isinstance(computer_info, dict):
        computer_info = {}
    name = _first(cpu.get("Name"), registry_cpu.get("ProcessorNameString"))
    if not name:
        processors = computer_info.get("CsProcessors")
        if isinstance(processors, list) and processors:
            first = processors[0]
            if isinstance(first, dict):
                name = _first(first.get("Name"))
    details = []
    cores = _first(cpu.get("NumberOfCores"))
    threads = _first(cpu.get("NumberOfLogicalProcessors"), computer_info.get("CsNumberOfLogicalProcessors"))
    max_clock = _format_speed_mhz(cpu.get("MaxClockSpeed"))
    if cores and threads:
        details.append(f"{cores} cores / {threads} threads")
    if max_clock:
        details.append(f"max {max_clock}")
    if details and name:
        return f"{name} ({', '.join(details)})"
    return name


def _chassis_summary(enclosure: Any, computer_system: Any) -> str | None:
    if isinstance(enclosure, list):
        enclosure = enclosure[0] if enclosure else {}
    if not isinstance(enclosure, dict):
        enclosure = {}
    if not isinstance(computer_system, dict):
        computer_system = {}

    chassis_types = enclosure.get("ChassisTypes")
    if not isinstance(chassis_types, list):
        chassis_types = [chassis_types] if chassis_types is not None else []
    names = [_chassis_type_name(value) for value in chassis_types]
    names = [name for name in names if name]
    system_type = _first(computer_system.get("SystemType"))
    pc_type = _pc_system_type_name(computer_system.get("PCSystemTypeEx") or computer_system.get("PCSystemType"))
    pieces = names + [piece for piece in (pc_type, system_type) if piece]
    return ", ".join(_unique_names(pieces)) if pieces else None


def _chassis_type_name(value: Any) -> str | None:
    try:
        code = int(value)
    except (TypeError, ValueError):
        return _first(value)
    names = {
        8: "Portable",
        9: "Laptop",
        10: "Notebook",
        14: "Sub-notebook",
        30: "Tablet",
        31: "Convertible",
        32: "Detachable",
    }
    return names.get(code, f"Chassis type {code}")


def _pc_system_type_name(value: Any) -> str | None:
    try:
        code = int(value)
    except (TypeError, ValueError):
        return _first(value)
    names = {
        1: "Desktop",
        2: "Mobile",
        3: "Workstation",
        4: "Enterprise server",
        5: "SOHO server",
        6: "Appliance PC",
        7: "Performance server",
        8: "Slate",
        9: "Maximum",
    }
    return names.get(code, f"PC system type {code}")


def _firmware_summary(firmware: Any, computer_info: Any) -> str | None:
    if not isinstance(firmware, dict):
        firmware = {}
    if not isinstance(computer_info, dict):
        computer_info = {}
    pieces = []
    firmware_type = _first(firmware.get("FirmwareType"), computer_info.get("BiosFirmwareType"))
    secure_boot = firmware.get("SecureBoot")
    if firmware_type:
        pieces.append(str(firmware_type))
    if secure_boot is not None:
        pieces.append(f"Secure Boot {'enabled' if bool(secure_boot) else 'disabled'}")
    return ", ".join(pieces) if pieces else None


def _gpu_summaries(video: Any, registry_display: Any, drivers: Any) -> list[dict[str, Any]]:
    if isinstance(video, dict):
        video = [video]
    if not isinstance(video, list):
        video = []
    driver_lookup = _driver_lookup(drivers)
    gpus: list[dict[str, Any]] = []
    for item in video:
        if not isinstance(item, dict):
            continue
        name = _first(item.get("Name"), item.get("VideoProcessor"))
        driver = _first(item.get("DriverVersion"))
        matched = _find_driver_for_name(driver_lookup, name)
        gpu = {
            "name": name,
            "video_processor": _first(item.get("VideoProcessor")),
            "adapter_ram": _format_bytes(item.get("AdapterRAM")),
            "driver_version": driver or (matched or {}).get("driver_version"),
            "current_resolution": _format_resolution(
                item.get("CurrentHorizontalResolution"), item.get("CurrentVerticalResolution")
            ),
            "refresh": _format_hz(item.get("CurrentRefreshRate")),
            "status": _first(item.get("Status")),
            "hardware_ids": _first((matched or {}).get("hardware_ids")),
        }
        gpus.append({key: val for key, val in gpu.items() if val not in (None, "", [])})

    for name in _gpu_names_from_registry(registry_display):
        if not any((gpu.get("name") or "").lower() == name.lower() for gpu in gpus):
            gpus.append({"name": name, "source": "Windows display registry"})
    return _dedupe_dicts(gpus)


def _storage_summaries(disk_drives: Any, physical_disks: Any) -> list[dict[str, Any]]:
    if isinstance(disk_drives, dict):
        disk_drives = [disk_drives]
    if isinstance(physical_disks, dict):
        physical_disks = [physical_disks]
    disk_drives = disk_drives if isinstance(disk_drives, list) else []
    physical_disks = physical_disks if isinstance(physical_disks, list) else []

    details: list[dict[str, Any]] = []
    matched_physical: set[int] = set()
    for drive in disk_drives:
        if not isinstance(drive, dict):
            continue
        model = _first(drive.get("Model"))
        match_index = _find_physical_disk_index(model, physical_disks, matched_physical)
        physical = physical_disks[match_index] if match_index is not None else {}
        if match_index is not None:
            matched_physical.add(match_index)
        detail = {
            "model": model or _first(physical.get("FriendlyName")),
            "size": _format_bytes(_first(drive.get("Size"), physical.get("Size"))),
            "media_type": _first(physical.get("MediaType"), drive.get("MediaType")),
            "bus_type": _first(physical.get("BusType"), drive.get("InterfaceType")),
            "firmware": _first(drive.get("FirmwareRevision"), physical.get("FirmwareVersion")),
            "partitions": _first(drive.get("Partitions")),
            "health": _first(physical.get("HealthStatus"), drive.get("Status")),
            "status": _first(physical.get("OperationalStatus"), drive.get("Status")),
            "spindle_speed": _first(physical.get("SpindleSpeed")),
        }
        details.append({key: val for key, val in detail.items() if val not in (None, "", [])})

    for index, physical in enumerate(physical_disks):
        if index in matched_physical or not isinstance(physical, dict):
            continue
        detail = {
            "model": _first(physical.get("FriendlyName")),
            "size": _format_bytes(physical.get("Size")),
            "media_type": _first(physical.get("MediaType")),
            "bus_type": _first(physical.get("BusType")),
            "firmware": _first(physical.get("FirmwareVersion")),
            "health": _first(physical.get("HealthStatus")),
            "status": _first(physical.get("OperationalStatus")),
        }
        details.append({key: val for key, val in detail.items() if val not in (None, "", [])})
    return _dedupe_dicts(details)


def _find_physical_disk_index(model: str | None, physical_disks: list[Any], used: set[int]) -> int | None:
    if not model:
        return None
    normalized = _normalize_device_name(model)
    for index, item in enumerate(physical_disks):
        if index in used or not isinstance(item, dict):
            continue
        friendly = _normalize_device_name(_first(item.get("FriendlyName")) or "")
        if friendly and (friendly in normalized or normalized in friendly):
            return index
    return None


def _memory_layout_summary(memory_arrays: Any, modules: Any, total_memory: Any = None) -> str | None:
    if isinstance(memory_arrays, dict):
        memory_arrays = [memory_arrays]
    if isinstance(modules, dict):
        modules = [modules]
    arrays = memory_arrays if isinstance(memory_arrays, list) else []
    module_list = modules if isinstance(modules, list) else []
    populated = len([module for module in module_list if isinstance(module, dict) and _first(module.get("Capacity"))])
    slots = None
    max_capacity = None
    for item in arrays:
        if not isinstance(item, dict):
            continue
        slots = slots or _first(item.get("MemoryDevices"))
        max_capacity = max_capacity or _memory_array_max_capacity(item)
    pieces = []
    if populated and slots:
        pieces.append(f"{populated}/{slots} slots populated")
    elif populated:
        pieces.append(f"{populated} module(s) detected")
    if total_memory:
        pieces.append(f"total {total_memory}")
    if max_capacity:
        pieces.append(f"reported max {max_capacity}")
    return ", ".join(pieces) if pieces else None


def _memory_array_max_capacity(item: dict[str, Any]) -> str | None:
    max_ex = item.get("MaxCapacityEx")
    try:
        max_ex_kb = int(max_ex)
        if max_ex_kb > 0:
            return _format_bytes(max_ex_kb * 1024)
    except (TypeError, ValueError):
        pass
    try:
        max_kb = int(item.get("MaxCapacity"))
    except (TypeError, ValueError):
        return None
    return _format_bytes(max_kb * 1024) if max_kb > 0 else None


def _display_summaries_from_edid(edid_items: Any, screen_items: Any, monitor_items: Any = None) -> list[dict[str, Any]]:
    if isinstance(edid_items, dict):
        edid_items = [edid_items]
    if isinstance(screen_items, dict):
        screen_items = [screen_items]
    if not isinstance(screen_items, list):
        screen_items = []
    if isinstance(monitor_items, dict):
        monitor_items = [monitor_items]
    if not isinstance(monitor_items, list):
        monitor_items = []

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

    for monitor in monitor_items:
        if not isinstance(monitor, dict):
            continue
        name = _first(monitor.get("UserFriendlyName"), monitor.get("ProductCodeID"), monitor.get("ManufacturerName"))
        manufacturer_id = _first(monitor.get("ManufacturerName"))
        product_code = _first(monitor.get("ProductCodeID"))
        if not name and not manufacturer_id and not product_code:
            continue
        key = "|".join(str(part or "") for part in (manufacturer_id, product_code, name))
        matching = next(
            (
                display
                for display in displays
                if str(display.get("manufacturer_id") or "").upper() == str(manufacturer_id or "").upper()
                and (
                    str(display.get("name") or "").upper() == str(name or "").upper()
                    or str(display.get("registry_hint") or "").upper() == str(product_code or "").upper()
                    or str(display.get("product_code") or "").upper() == str(product_code or "").upper()
                )
            ),
            None,
        )
        if matching:
            matching.setdefault("wmi_name", name)
            matching.setdefault("wmi_product_code", product_code)
            if "active" not in matching and monitor.get("Active") is not None:
                matching["active"] = bool(monitor.get("Active"))
            continue
        if key in seen:
            continue
        seen.add(key)
        display = {
            "name": name,
            "manufacturer_id": manufacturer_id,
            "product_code": product_code,
            "active": bool(monitor.get("Active")) if monitor.get("Active") is not None else None,
            "source": "WMI monitor ID",
        }
        displays.append({k: v for k, v in display.items() if v not in (None, "", [])})

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


def _battery_summaries(value: Any, estimates: Any = None, static_battery: Any = None) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        value = [value]
    if not isinstance(value, list):
        value = []
    if isinstance(static_battery, dict):
        static_battery = [static_battery]
    if not isinstance(static_battery, list):
        static_battery = []
    batteries: list[dict[str, Any]] = []
    static_items = [item for item in static_battery if isinstance(item, dict)]
    for item in value:
        if not isinstance(item, dict):
            continue
        static = static_items[0] if static_items else {}
        battery_data = {
            "id": _first(item.get("Id"), static.get("Name")),
            "manufacturer": _first(item.get("Manufacturer"), static.get("Manufacturer")),
            "chemistry": _first(item.get("Chemistry"), _battery_chemistry_name(static.get("Chemistry"))),
            "design_capacity": _format_mwh(item.get("DesignCapacity")),
            "full_charge_capacity": _format_mwh(item.get("FullChargeCapacity")),
            "cycle_count": _first(item.get("CycleCount")),
            "design_voltage": _format_millivolts(static.get("DesignVoltage")),
            "charge_remaining": _format_percent(static.get("EstimatedChargeRemaining")),
            "status": _first(static.get("Status")),
            "battery_status": _battery_status_name(static.get("BatteryStatus")),
        }
        if estimates and isinstance(estimates, dict):
            design_active = _parse_battery_duration(estimates.get("DesignActive"))
            full_active = _parse_battery_duration(estimates.get("FullChargeActive"))
            if design_active:
                battery_data["estimated_active_runtime_design"] = design_active
            if full_active:
                battery_data["estimated_active_runtime_full_charge"] = full_active
        batteries.append(battery_data)
    if not batteries:
        for static in static_items:
            battery_data = {
                "id": _first(static.get("Name")),
                "manufacturer": _first(static.get("Manufacturer")),
                "chemistry": _battery_chemistry_name(static.get("Chemistry")),
                "design_voltage": _format_millivolts(static.get("DesignVoltage")),
                "charge_remaining": _format_percent(static.get("EstimatedChargeRemaining")),
                "estimated_runtime": _format_minutes(static.get("EstimatedRunTime")),
                "status": _first(static.get("Status")),
                "battery_status": _battery_status_name(static.get("BatteryStatus")),
            }
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
            if name in {"sppower_battery_information", "spbattery_information"}:
                model_info = current.get("sppower_battery_model_info") if isinstance(current.get("sppower_battery_model_info"), dict) else {}
                health_info = current.get("sppower_battery_health_info") if isinstance(current.get("sppower_battery_health_info"), dict) else {}
                charge_info = current.get("sppower_battery_charge_info") if isinstance(current.get("sppower_battery_charge_info"), dict) else {}
                battery_data = {
                    "id": current.get("sppower_device_name") or model_info.get("sppower_battery_device_name"),
                    "manufacturer": current.get("sppower_battery_manufacturer") or current.get("sppower_device_name") or model_info.get("sppower_battery_device_name"),
                    "chemistry": current.get("sppower_battery_chemistry"),
                    "design_capacity": current.get("sppower_design_capacity") or current.get("sppower_battery_design_capacity"),
                    "full_charge_capacity": current.get("sppower_max_capacity") or current.get("sppower_battery_max_capacity"),
                    "cycle_count": current.get("sppower_cycle_count") or health_info.get("sppower_battery_cycle_count"),
                    "health": current.get("sppower_battery_health") or health_info.get("sppower_battery_health"),
                    "maximum_capacity": health_info.get("sppower_battery_health_maximum_capacity"),
                    "charge_remaining": _format_percent(charge_info.get("sppower_battery_state_of_charge")),
                    "charging": charge_info.get("sppower_battery_is_charging"),
                    "fully_charged": charge_info.get("sppower_battery_fully_charged"),
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


def _macos_memory_summaries(value: Any) -> list[dict[str, Any]]:
    modules: list[dict[str, Any]] = []

    def walk(item: Any) -> None:
        if isinstance(item, list):
            for child in item:
                walk(child)
            return
        if not isinstance(item, dict):
            return
        candidate = {
            "slot": _first(item.get("_name"), item.get("dimm_name"), item.get("spmemory_bank_locator")),
            "capacity": _first(item.get("dimm_size"), item.get("spmemory_size")),
            "speed": _first(item.get("dimm_speed"), item.get("spmemory_speed")),
            "memory_type": _first(item.get("dimm_type"), item.get("spmemory_type")),
            "manufacturer": _first(item.get("dimm_manufacturer"), item.get("spmemory_manufacturer")),
            "part_number": _first(item.get("dimm_part_number"), item.get("spmemory_part_number")),
        }
        if any(candidate.values()):
            modules.append({key: val for key, val in candidate.items() if val not in (None, "", [])})
        for child in item.values():
            if isinstance(child, (dict, list)):
                walk(child)

    walk(value)
    return _dedupe_dicts(modules)


def _macos_storage_names(storage: Any, nvme: Any) -> list[str]:
    return _unique_names([item.get("model") or item.get("name") or "" for item in _macos_storage_summaries(storage, nvme)])


def _macos_storage_summaries(storage: Any, nvme: Any) -> list[dict[str, Any]]:
    devices: list[dict[str, Any]] = []

    def walk(item: Any, source: str) -> None:
        if isinstance(item, list):
            for child in item:
                walk(child, source)
            return
        if not isinstance(item, dict):
            return
        candidate = {
            "name": _first(item.get("_name"), item.get("spstorage_volume_name")),
            "model": _first(item.get("sppci_model"), item.get("device_model"), item.get("spnvme_model")),
            "size": _first(item.get("size"), item.get("spstorage_physical_drive_media_size"), item.get("spnvme_capacity")),
            "media_type": _first(item.get("medium_type"), item.get("spstorage_medium_type"), item.get("spstorage_physical_drive_media_name")),
            "protocol": _first(item.get("protocol"), item.get("spnvme_link_width")),
            "file_system": _first(item.get("file_system"), item.get("spstorage_file_system")),
            "free": _first(item.get("free_space_in_bytes"), item.get("spstorage_free_space")),
            "source": source,
        }
        if any(value for key, value in candidate.items() if key != "source"):
            devices.append({key: val for key, val in candidate.items() if val not in (None, "", [])})
        for key, child in item.items():
            if source == "system_profiler NVMe" and key == "volumes":
                continue
            if isinstance(child, (dict, list)):
                walk(child, source)

    walk(storage, "system_profiler storage")
    walk(nvme, "system_profiler NVMe")
    return _dedupe_dicts(devices)


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
                "label": "[REDACTED]" if item.get("VolumeLabel") else None,
            }
        )
    return drives


def _memory_module_summaries(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        value = [value]
    if not isinstance(value, list):
        return []
    modules: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        module = {
            "manufacturer": _first(item.get("Manufacturer")),
            "capacity": _format_bytes(item.get("Capacity")),
            "speed": _format_speed_mhz(item.get("Speed")),
            "configured_speed": _format_speed_mhz(item.get("ConfiguredClockSpeed")),
            "part_number": _first(item.get("PartNumber")),
            "slot": _first(item.get("DeviceLocator"), item.get("BankLabel")),
            "form_factor": _memory_form_factor_name(item.get("FormFactor")),
            "memory_type": _memory_type_name(item.get("SMBIOSMemoryType"), item.get("MemoryType")),
        }
        modules.append({key: val for key, val in module.items() if val not in (None, "", [])})
    return modules


def _network_summaries(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        value = [value]
    if not isinstance(value, list):
        return []
    adapters: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        adapter = {
            "name": _first(item.get("Name"), item.get("NetConnectionID")),
            "manufacturer": _first(item.get("Manufacturer")),
            "type": _first(item.get("AdapterType")),
            "speed": _format_network_speed(item.get("Speed")),
            "service": _first(item.get("ServiceName")),
        }
        adapters.append({key: val for key, val in adapter.items() if val not in (None, "", [])})
    return _dedupe_dicts(adapters)


def _device_summaries(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        value = [value]
    if not isinstance(value, list):
        return []
    devices: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        device = {
            "name": _first(item.get("Name"), item.get("Description"), item.get("_name")),
            "manufacturer": _first(item.get("Manufacturer")),
            "status": _first(item.get("Status")),
            "class": _first(item.get("Class")),
        }
        devices.append({key: val for key, val in device.items() if val not in (None, "", [])})
    return _dedupe_dicts(devices)


def _input_summaries(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, dict):
        return []
    devices: list[dict[str, Any]] = []
    for group_name, items in value.items():
        if isinstance(items, dict):
            items = [items]
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            device = {
                "type": str(group_name),
                "name": _first(item.get("Name"), item.get("Description")),
                "manufacturer": _first(item.get("Manufacturer")),
                "details": _first(item.get("PointingType"), item.get("NumberOfFunctionKeys"), item.get("NumberOfButtons")),
            }
            devices.append({key: val for key, val in device.items() if val not in (None, "", [])})
    return _dedupe_dicts(devices)


def _security_summary(value: Any, firmware: Any = None) -> dict[str, Any]:
    if isinstance(value, list):
        value = value[0] if value else {}
    if not isinstance(value, dict):
        return {}
    if not isinstance(firmware, dict):
        firmware = {}
    summary = {
        "tpm_present": value.get("TpmPresent"),
        "tpm_ready": value.get("TpmReady"),
        "tpm_spec_version": _first(value.get("SpecVersion")),
        "tpm_manufacturer_version": _first(value.get("ManufacturerVersion")),
        "secure_boot": firmware.get("SecureBoot"),
    }
    return {key: val for key, val in summary.items() if val not in (None, "", [])}


def _macos_named_items(value: Any, limit: int = 24) -> list[dict[str, Any]]:
    names: list[dict[str, Any]] = []

    def walk(item: Any) -> None:
        if len(names) >= limit:
            return
        if isinstance(item, list):
            for child in item:
                walk(child)
            return
        if not isinstance(item, dict):
            return
        name = _first(
            item.get("_name"),
            item.get("sppci_model"),
            item.get("spaudio_device_name"),
            item.get("spcamera_model-id"),
            item.get("spusb_product_id"),
            item.get("spnetwork_interface"),
        )
        if name:
            entry = {"name": name}
            for source_key, target_key in (
                ("spnetwork_type", "type"),
                ("spnetwork_hardware", "hardware"),
                ("spnetwork_interface", "interface"),
                ("spaudio_coreaudio_device_transport", "transport"),
                ("spusb_vendor_name", "vendor"),
                ("spusb_speed", "speed"),
            ):
                cleaned = _first(item.get(source_key))
                if cleaned:
                    entry[target_key] = cleaned
            names.append(entry)
        for child in item.values():
            if isinstance(child, (dict, list)):
                walk(child)

    walk(value)
    return _dedupe_dicts(names)


def _dedupe_dicts(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        if not item:
            continue
        key = "|".join(str(item.get(part) or "") for part in sorted(item))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _driver_summaries(value: Any, limit: int = 40) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        value = [value]
    if not isinstance(value, list):
        return []
    drivers: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        driver = {
            "device": _first(item.get("DeviceName")),
            "class": _first(item.get("DeviceClass")),
            "manufacturer": _first(item.get("Manufacturer")),
            "provider": _first(item.get("DriverProviderName")),
            "driver_version": _first(item.get("DriverVersion")),
            "hardware_ids": _clean_hardware_ids(item.get("HardwareID")),
            "compatible_ids": _clean_hardware_ids(item.get("CompatibleID")),
        }
        clean = {key: val for key, val in driver.items() if val not in (None, "", [])}
        if clean:
            drivers.append(clean)
        if len(drivers) >= limit:
            break
    return _dedupe_dicts(drivers)


def _driver_lookup(value: Any) -> list[dict[str, Any]]:
    return _driver_summaries(value, limit=200)


def _find_driver_for_name(drivers: list[dict[str, Any]], name: str | None) -> dict[str, Any] | None:
    if not name:
        return None
    normalized_name = _normalize_device_name(name)
    for driver in drivers:
        device = _normalize_device_name(str(driver.get("device") or ""))
        if device and (device in normalized_name or normalized_name in device):
            return driver
    return None


def _clean_hardware_ids(value: Any, limit: int = 3) -> str | None:
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, list):
        values = value
    else:
        return None
    cleaned: list[str] = []
    for item in values:
        text = _first(item)
        if not text:
            continue
        text = re.sub(r"(?i)\\[0-9a-f&]{8,}.*$", "", text)
        text = text.replace("\\", " ")
        if text and text not in cleaned:
            cleaned.append(text)
        if len(cleaned) >= limit:
            break
    return "; ".join(cleaned) if cleaned else None


def _power_capability_summary(value: Any) -> str | None:
    text = _first(value)
    if not text:
        return None
    interesting = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if (
            "standby" in line.lower()
            or "hibernate" in line.lower()
            or "fast startup" in line.lower()
            or "available" in line.lower()
        ):
            interesting.append(line)
        if len(interesting) >= 8:
            break
    return "; ".join(interesting) if interesting else text[:400]


def _windows_evidence_crosscheck(raw: dict[str, Any]) -> list[dict[str, Any]]:
    cs = raw.get("ComputerSystem") or {}
    csp = raw.get("ComputerSystemProduct") or {}
    registry_bios = raw.get("WindowsRegistryBIOS") or {}
    bios = raw.get("BIOS") or {}
    cpu = raw.get("Processor") or {}
    registry_cpu = raw.get("WindowsRegistryCPU") or {}
    computer_info = raw.get("WindowsComputerInfo") or {}

    rows = [
        {
            "field": "manufacturer",
            "values": _join_unique(
                csp.get("Vendor"), cs.get("Manufacturer"), registry_bios.get("SystemManufacturer"), computer_info.get("CsManufacturer")
            ),
            "sources": "ComputerSystemProduct, ComputerSystem, Registry BIOS, Get-ComputerInfo",
        },
        {
            "field": "model",
            "values": _join_unique(
                csp.get("Name"), cs.get("Model"), registry_bios.get("SystemProductName"), computer_info.get("CsModel")
            ),
            "sources": "ComputerSystemProduct, ComputerSystem, Registry BIOS, Get-ComputerInfo",
        },
        {
            "field": "sku/version",
            "values": _join_unique(csp.get("SKUNumber"), csp.get("Version"), registry_bios.get("SystemSKU")),
            "sources": "ComputerSystemProduct, Registry BIOS",
        },
        {
            "field": "bios",
            "values": _join_unique(bios.get("SMBIOSBIOSVersion"), bios.get("Version"), registry_bios.get("BIOSVersion")),
            "sources": "Win32_BIOS, Registry BIOS",
        },
        {
            "field": "cpu",
            "values": _join_unique(cpu.get("Name"), registry_cpu.get("ProcessorNameString")),
            "sources": "Win32_Processor, Registry CPU",
        },
    ]
    return [row for row in rows if row.get("values")]


def _macos_evidence_crosscheck(raw: dict[str, Any]) -> list[dict[str, Any]]:
    hardware_items = raw.get("SPHardwareDataType") or []
    hardware = hardware_items[0] if isinstance(hardware_items, list) and hardware_items else {}
    rows = [
        {
            "field": "model",
            "values": _join_unique(hardware.get("machine_name"), hardware.get("model_name")),
            "sources": "system_profiler SPHardwareDataType",
        },
        {
            "field": "model identifier",
            "values": _join_unique(hardware.get("machine_model"), raw.get("hw_model"), raw.get("hw_machine")),
            "sources": "system_profiler, sysctl hw.model/hw.machine",
        },
        {
            "field": "cpu/chip",
            "values": _join_unique(hardware.get("chip_type"), raw.get("cpu_brand_string")),
            "sources": "system_profiler, sysctl machdep.cpu.brand_string",
        },
        {
            "field": "memory",
            "values": _join_unique(hardware.get("physical_memory"), _format_bytes(raw.get("hw_memsize"))),
            "sources": "system_profiler, sysctl hw.memsize",
        },
    ]
    return [row for row in rows if row.get("values")]


def _join_unique(*values: Any) -> str:
    cleaned: list[str] = []
    for value in values:
        text = _first(value)
        if text and text not in cleaned:
            cleaned.append(text)
    return " | ".join(cleaned)


def _normalize_device_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _memory_form_factor_name(value: Any) -> str | None:
    try:
        code = int(value)
    except (TypeError, ValueError):
        return _first(value)
    names = {
        8: "DIMM",
        12: "SODIMM",
        13: "SRIMM",
        16: "FB-DIMM",
        17: "Die",
        18: "TSOP",
        19: "Row of chips",
        20: "RIMM",
        21: "SODIMM",
        22: "SRIMM",
        23: "FB-DIMM",
    }
    return names.get(code, f"Form factor {code}")


def _memory_type_name(*values: Any) -> str | None:
    for value in values:
        try:
            code = int(value)
        except (TypeError, ValueError):
            cleaned = _first(value)
            if cleaned:
                return cleaned
            continue
        names = {
            20: "DDR",
            21: "DDR2",
            24: "DDR3",
            26: "DDR4",
            30: "LPDDR4",
            34: "DDR5",
            35: "LPDDR5",
            36: "LPDDR5X",
        }
        if code in names:
            return names[code]
    return None


def _battery_chemistry_name(value: Any) -> str | None:
    try:
        code = int(value)
    except (TypeError, ValueError):
        return _first(value)
    names = {
        1: "Other",
        2: "Unknown",
        3: "Lead Acid",
        4: "Nickel Cadmium",
        5: "Nickel Metal Hydride",
        6: "Lithium-ion",
        7: "Zinc air",
        8: "Lithium Polymer",
    }
    return names.get(code, f"Chemistry {code}")


def _battery_status_name(value: Any) -> str | None:
    try:
        code = int(value)
    except (TypeError, ValueError):
        return _first(value)
    names = {
        1: "Discharging",
        2: "AC connected",
        3: "Fully charged",
        4: "Low",
        5: "Critical",
        6: "Charging",
        7: "Charging and high",
        8: "Charging and low",
        9: "Charging and critical",
        10: "Undefined",
        11: "Partially charged",
    }
    return names.get(code, f"Battery status {code}")


def _format_millivolts(value: Any) -> str | None:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    if number <= 0:
        return None
    return f"{number / 1000:g} V"


def _format_percent(value: Any) -> str | None:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    if number < 0:
        return None
    return f"{number}%"


def _format_minutes(value: Any) -> str | None:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    if number < 0 or number >= 71582788:
        return None
    hours, minutes = divmod(number, 60)
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def _format_hz(value: Any) -> str | None:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return f"{number} Hz" if number > 0 else None


def _format_speed_mhz(value: Any) -> str | None:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return f"{number} MHz" if number > 0 else None


def _format_network_speed(value: Any) -> str | None:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    if number <= 0:
        return None
    if number >= 1_000_000_000:
        return f"{number / 1_000_000_000:g} Gbps"
    if number >= 1_000_000:
        return f"{number / 1_000_000:g} Mbps"
    return f"{number} bps"


def _format_windows_os(value: dict[str, Any], computer_info: Any = None) -> str | None:
    if not isinstance(computer_info, dict):
        computer_info = {}
    product = _first(value.get("ProductName"), value.get("EditionID"))
    version = _first(value.get("DisplayVersion"), computer_info.get("WindowsVersion"))
    build = _first(value.get("CurrentBuild"))
    ubr = _first(value.get("UBR"))
    hal = _first(computer_info.get("OsHardwareAbstractionLayer"))
    pieces = [piece for piece in (product, version, f"build {build}.{ubr}" if build and ubr else None, hal) if piece]
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
