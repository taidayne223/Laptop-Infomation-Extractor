from __future__ import annotations

import argparse
import os
import platform
import subprocess
import sys
from pathlib import Path

from .model_inference import infer_model
from .prompt_export import write_cloud_research_prompt
from .system_info import collect_system_info
from .utils import ensure_dir, to_json


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root_dir = Path.cwd()

    print("Collecting laptop information...")
    system_info = collect_system_info(Path(args.system_info_file) if args.system_info_file else None)
    guess = infer_model(system_info, provider=None)

    model_name = (args.model_name or guess.model_name).strip()
    if not model_name:
        print('Could not detect a model name. Re-run with --model-name "Full laptop model".')
        return 1

    gpu = choose_gpu(system_info, args.gpu)
    system_info.setdefault("confirmed", {})["model_name"] = model_name
    if gpu:
        system_info.setdefault("confirmed", {})["gpu"] = gpu

    output_dir = ensure_dir(Path(args.output_dir) if args.output_dir else root_dir / "Noi luu File ket qua")
    path = write_cloud_research_prompt(output_dir, model_name, system_info, guess)

    print("")
    print("Infomation Extractor prompt exported.")
    print(f"Model: {model_name}")
    if gpu:
        print(f"GPU:   {gpu}")
    print(f"File:  {path}")

    if args.print_system_info:
        print("")
        print(to_json(system_info))

    if not args.no_open:
        open_output_file(path)
        open_containing_directory(path.parent)

    print("")
    print("Upload or paste this single file into ChatGPT, Gemini, Claude, or another AI with web/deep-research access.")
    return 0


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="infomation-extractor",
        description="Extract laptop information and export one cloud-AI deep-research prompt file.",
    )
    parser.add_argument("--model-name", help="Override the detected laptop model name.")
    parser.add_argument("--gpu", help="Override the detected GPU variant, e.g. 'NVIDIA RTX 4060 Laptop GPU'.")
    parser.add_argument("--system-info-file", help="Read system information from a text/json/xml/nfo file.")
    parser.add_argument("--output-dir", help="Directory for generated prompt files. Defaults to Noi luu File ket qua/.")
    parser.add_argument("--no-open", action="store_true", help="Do not open the generated prompt file.")
    parser.add_argument("--print-system-info", action="store_true", help="Print sanitized system info JSON.")
    parser.add_argument(
        "--export-prompt",
        action="store_true",
        help="Compatibility flag. Prompt export is now the default behavior.",
    )
    return parser.parse_args(argv)


def choose_gpu(system_info: dict, gpu_override: str | None) -> str | None:
    if gpu_override is not None:
        cleaned = gpu_override.strip()
        return None if cleaned.lower() in {"", "none", "no", "skip"} else cleaned

    detected = system_info.get("summary", {}).get("gpu") or []
    if isinstance(detected, str):
        detected = [detected]
    detected = [str(item).strip() for item in detected if str(item).strip()]
    return suggest_dedicated_gpu(detected) or (", ".join(detected) if detected else None)


def suggest_dedicated_gpu(gpus: list[str]) -> str | None:
    dedicated_markers = (
        "nvidia",
        "geforce",
        "rtx",
        "gtx",
        "radeon rx",
        "arc a",
        "arc pro",
    )
    integrated_markers = (
        "intel(r) graphics",
        "intel graphics",
        "uhd graphics",
        "iris xe",
        "radeon graphics",
    )
    for gpu in gpus:
        lowered = gpu.lower()
        if any(marker in lowered for marker in dedicated_markers):
            return gpu
    for gpu in gpus:
        lowered = gpu.lower()
        if not any(marker in lowered for marker in integrated_markers):
            return gpu
    return None


def open_output_file(path: Path) -> None:
    try:
        current_os = platform.system().lower()
        if current_os == "windows":
            try:
                os.startfile(str(path))  # type: ignore[attr-defined]
            except OSError:
                subprocess.Popen(["notepad.exe", str(path)])
        elif current_os == "darwin":
            subprocess.run(["open", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path)], check=False)
        print("Opened the generated prompt file.")
    except Exception as exc:
        print(f"Could not auto-open the prompt file: {exc}")


def open_containing_directory(path: Path) -> None:
    try:
        current_os = platform.system().lower()
        if current_os == "windows":
            try:
                os.startfile(str(path))  # type: ignore[attr-defined]
            except OSError:
                subprocess.Popen(["explorer.exe", str(path)])
        elif current_os == "darwin":
            subprocess.run(["open", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path)], check=False)
        print("Opened the output folder.")
    except Exception as exc:
        print(f"Could not auto-open the output folder: {exc}")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
