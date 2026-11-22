#!/usr/bin/env python3
"""Check the FP5 reference memory map against its board and DTS settings."""

from pathlib import Path
import re
import tomllib


ROOT = Path(__file__).resolve().parents[1]


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)


def number(value: str | int) -> int:
    return int(str(value), 0)


def main() -> None:
    with (ROOT / "UniXNU-FP5/memory.toml").open("rb") as stream:
        memory = tomllib.load(stream)
    with (ROOT / "UniXNU-FP5/board.toml").open("rb") as stream:
        board = tomllib.load(stream)

    dram = memory["dram"]
    base, size = number(dram["base"]), number(dram["size"])
    if number(dram["end_inclusive"]) != base + size - 1:
        fail("dram.end_inclusive does not match dram.base + dram.size")
    if number(board["payload"]["dram_size"]) != size:
        fail("board.toml payload.dram_size differs from memory.toml")
    bringup = memory["bringup"]
    if number(board["payload"]["adt"]["owned_memory_size"]) != number(
        bringup["darwinboot_owned_memory_size"]
    ):
        fail("board ADT memory window differs from memory.toml bring-up policy")
    owned = number(bringup["darwinboot_owned_memory_size"])
    if owned <= 0 or owned > size:
        fail("DarwinBoot owned-memory window is outside available DRAM")

    intervals: list[tuple[int, int, str]] = []
    for item in memory.get("fixed_reservation", []):
        start, length = number(item["base"]), number(item["size"])
        end = start + length
        if length <= 0 or start < base or end > base + size:
            fail(f"fixed reservation {item['name']} is outside DRAM")
        intervals.append((start, end, item["name"]))
    intervals.sort()
    for left, right in zip(intervals, intervals[1:]):
        if left[1] > right[0]:
            fail(f"fixed reservations overlap: {left[2]} and {right[2]}")

    dts = (ROOT / "UniXNU-FP5/dts/FP5.dts").read_text()
    match = re.search(
        r"memory@([0-9a-fA-F]+)\s*\{[^}]*reg\s*=\s*<\s*0\s*"
        r"(0x[0-9a-fA-F]+)\s+(0x[0-9a-fA-F]+)\s+0\s*>",
        dts,
        re.S,
    )
    if not match:
        fail("could not parse the 64-bit memory reg from FP5.dts")
    if int(match.group(1), 16) != base or number(match.group(2)) != base:
        fail("FP5.dts memory node address differs from memory.toml")
    dts_size = (number(match.group(3)) << 32)
    if dts_size != size:
        fail("FP5.dts memory node size differs from memory.toml")

    expected_disabled = {"cpu_l1", "cpu_l2", "cpu_l3", "cpu_b0", "cpu_b1", "cpu_b2", "cpu_b3"}
    disabled = set(re.findall(r"&([A-Za-z0-9_]+)\s*\{\s*status\s*=\s*\"disabled\";", dts))
    if bringup["enabled_cpus"] == 1 and not expected_disabled.issubset(disabled):
        fail("single-CPU bring-up policy does not disable every secondary CPU")

    print(
        "PASS: FP5 reference map is internally consistent "
        f"(DRAM 0x{base:x}-0x{base + size - 1:x}, "
        f"{len(intervals)} fixed reservations, {bringup['enabled_cpus']} CPU)"
    )


if __name__ == "__main__":
    main()
