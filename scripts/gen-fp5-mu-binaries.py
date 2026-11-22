#!/usr/bin/env python3
"""Generate Mu-Silicium binary INFs for the FP5 from an extract-fp5-xbl-uefi.py inventory.

The output contains proprietary Qualcomm/Fairphone code: keep it local, never commit
or upload it. Layout matches Mu-Silicium's Binaries/<device>/ tree so fp5Pkg can
reference it as ``Binaries-fp5/QcomPkg/Drivers/<Dir>/<Inf>.inf``.
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

# (Mu directory, INF base name, FFS UI name in the stock FV)
DRIVERS = [
    ("EnvDxe", "EnvDxe", "EnvDxe"),
    ("SmemDxe", "SmemDxe", "SmemDxe"),
    ("DALSYSDxe", "DALSYSDxe", "DALSys"),
    ("HWIODxe", "HWIODxe", "HWIODxeDriver"),
    ("ChipInfoDxe", "ChipInfoDxe", "ChipInfo"),
    ("PlatformInfoDxe", "PlatformInfoDxe", "PlatformInfoDxeDriver"),
    ("HALIOMMUDxe", "HALIOMMUDxe", "HALIOMMU"),
    ("ULogDxe", "ULogDxe", "ULogDxe"),
    ("CmdDbDxe", "CmdDbDxe", "CmdDbDxe"),
    ("PwrUtilsDxe", "PwrUtilsDxe", "PwrUtilsDxe"),
    ("NpaDxe", "NpaDxe", "NpaDxe"),
    ("RpmhDxe", "RpmhDxe", "RpmhDxe"),
    ("VcsDxe", "VcsDxe", "VcsDxe"),
    ("ClockDxe", "ClockDxe", "ClockDxe"),
    ("ICBDxe", "ICBDxe", "ICBDxe"),
    ("ShmBridgeDxe", "ShmBridgeDxeLA", "ShmBridgeDxeLA"),
    ("TzDxe", "ScmDxeLA", "ScmDxeLA"),
    ("TzDxe", "TzDxeLA", "TzDxeLA"),
    ("TLMMDxe", "TLMMDxe", "DALTLMM"),
    ("SPMIDxe", "SPMIDxe", "SPMI"),
    ("I2CDxe", "I2CDxe", "I2C"),
    ("PmicDxe", "PmicDxeLa", "PmicDxe"),
    ("SdccDxe", "SdccDxe", "SdccDxe"),
    ("UFSDxe", "UFSDxe", "UFSDxe"),
    ("DDRInfoDxe", "DDRInfoDxe", "DDRInfoDxe"),
    ("FeatureEnablerDxe", "FeatureEnablerDxe", "FeatureEnablerDxe"),
    ("DisplayDxe", "DisplayDxe", "DisplayDxe"),
    ("CPRDxe", "CPRDxe", "CPRDxe"),
    ("PILProxyDxe", "PILProxyDxe", "PILProxyDxe"),
    ("PILDxe", "PILDxe", "PILDxe"),
    ("IPCCDxe", "IPCCDxe", "IPCCDxe"),
    ("GLinkDxe", "GLinkDxe", "GlinkDxe"),
    ("SPIDxe", "SPIDxe", "SPI"),
    ("PmicGlinkDxe", "PmicGlinkDxe", "PmicGlinkDxe"),
    ("UsbPwrCtrlDxe", "UsbPwrCtrlDxe", "UsbPwrCtrlDxe"),
    ("QcomChargerDxe", "QcomChargerDxeLA", "QcomChargerDxeLA"),
    ("ChargerExDxe", "ChargerExDxe", "ChargerExDxe"),
    ("UsbfnDwc3Dxe", "UsbfnDwc3Dxe", "UsbfnDwc3Dxe"),
    ("XhciPciEmulationDxe", "XhciPciEmulationDxe", "XhciPciEmulation"),
    ("XhciDxe", "XhciDxe", "XhciDxe"),
    ("UsbMsdDxe", "UsbMsdDxe", "UsbMsdDxe"),
    ("UsbDeviceDxe", "UsbDeviceDxe", "UsbDeviceDxe"),
    ("UsbConfigDxe", "UsbConfigDxe", "UsbConfigDxe"),
    ("UsbInitDxe", "UsbInitDxe", "UsbInitDxe"),
    ("ButtonsDxe", "ButtonsDxe", "ButtonsDxe"),
    ("TsensDxe", "TsensDxe", "TsensDxe"),
    ("LimitsDxe", "LimitsDxe", "LimitsDxe"),
    ("GpiDxe", "GpiDxe", "GpiDxe"),
    ("UCDxe", "UCDxe", "UCDxe"),
    ("RNGDxe", "RngDxe", "RngDxe"),
]

RAW_FILES = ["SecParti.cfg", "uefipil.cfg", "QcomChargerCfg.cfg", "BATTERY.PROVISION"]


def inf_text(base, guid, has_depex):
    lines = ["[Defines]",
             "  INF_VERSION                    = 0x0001001B",
             f"  BASE_NAME                      = {base}",
             f"  FILE_GUID                      = {guid.upper()}",
             "  MODULE_TYPE                    = DXE_DRIVER",
             "  VERSION_STRING                 = 1.0",
             "",
             "[Binaries.AARCH64]"]
    if has_depex:
        lines.append(f"  DXE_DEPEX|{base}.depex|*")
    lines.append(f"  PE32|{base}.efi|*")
    lines += ["", "[Depex]", "  TRUE", ""] if has_depex else [""]
    return "\r\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("inventory", help="inventory.json from extract-fp5-xbl-uefi.py")
    ap.add_argument("-o", "--out", required=True, help="output root, e.g. Mu-Silicium/Binaries-fp5")
    a = ap.parse_args()
    inv_path = Path(a.inventory)
    inv = json.loads(inv_path.read_text())
    files_dir = inv_path.parent / "files"
    by_name = {}
    for f in inv["files"]:
        if f.get("name"):
            by_name.setdefault(f["name"], []).append(f)
    out = Path(a.out)
    missing = []
    manifest = {"source_sha256": inv["source_sha256"], "drivers": [], "raw": []}
    for mu_dir, base, ui in DRIVERS:
        cands = [f for f in by_name.get(ui, []) if f["type"] == "DRIVER"]
        if len(cands) != 1:
            missing.append(ui)
            continue
        f = cands[0]
        efi = [b for b in f["blobs"] if b.endswith(".efi")]
        dep = [b for b in f["blobs"] if b.endswith(".depex")]
        if len(efi) != 1:
            missing.append(ui)
            continue
        d = out / "QcomPkg" / "Drivers" / mu_dir
        d.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(files_dir / efi[0], d / f"{base}.efi")
        if dep:
            shutil.copyfile(files_dir / dep[0], d / f"{base}.depex")
        (d / f"{base}.inf").write_bytes(inf_text(base, f["guid"], bool(dep)).encode())
        manifest["drivers"].append({"inf": f"QcomPkg/Drivers/{mu_dir}/{base}.inf", "ui": ui,
                                    "guid": f["guid"], "depex": bool(dep)})
    raw = out / "RawFiles"
    raw.mkdir(parents=True, exist_ok=True)
    for name in RAW_FILES:
        cands = [f for f in by_name.get(name, []) if f["type"] == "FREEFORM"]
        if len(cands) != 1 or len(cands[0]["blobs"]) != 1:
            missing.append(name)
            continue
        shutil.copyfile(files_dir / cands[0]["blobs"][0], raw / name)
        manifest["raw"].append({"name": name, "guid": cands[0]["guid"]})
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print(f"drivers: {len(manifest['drivers'])}  raw: {len(manifest['raw'])}  -> {out}")
    if missing:
        sys.exit(f"missing in inventory: {', '.join(missing)}")


if __name__ == "__main__":
    main()
