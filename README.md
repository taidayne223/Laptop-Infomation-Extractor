# Infomation Extractor

Infomation Extractor reads laptop hardware/system details on Windows or macOS and exports one Markdown prompt file. Upload that single file to ChatGPT, Gemini, Claude, or another cloud AI with web/deep-research access.

The simplest workflow does not use API keys, billing, cloud connectors, or local model setup.

## Quick Start

Windows:

```powershell
.\make_prompt.bat
```

macOS:

- Cách nhanh nhất: Double-click (nhấp đúp chuột) vào file `make_prompt_macos.command` ở thư mục chính.
- Hoặc dùng terminal:
```bash
bash scripts/make_prompt_macos.sh
```

The generated prompt is saved in:

```text
outputs/
```

After export, the script opens the prompt file automatically.

## What The Prompt Contains

- Detected laptop model and product/SKU codes.
- CPU, GPU, RAM, storage, OS, BIOS/baseboard where available.
- A clean local spec snapshot, without bulky raw PowerShell/.NET objects.
- A Vietnamese deep-research instruction for cloud AI.
- Required output sections for specs, pros/cons, competitor comparison, YouTube review plan, benchmark checklist, infographic/data tables, fact-check table, and sources.

## Useful Options

Force a model name:

```powershell
.\make_prompt.bat --model-name "Lenovo Yoga Pro 7 15IPH11"
```

Force a GPU variant:

```powershell
.\make_prompt.bat --gpu "NVIDIA GeForce RTX 5050 Laptop GPU"
```

Create the prompt without opening it:

```powershell
.\make_prompt.bat --no-open
```

Use an exported system-info file instead of the current machine:

```powershell
.\make_prompt.bat --system-info-file "C:\path\to\system-info.txt"
```

## Cross-Platform Notes

- Windows launcher: [make_prompt.bat](make_prompt.bat)
- macOS launcher (Double-click): [make_prompt_macos.command](make_prompt_macos.command)
- macOS launcher (Shell script): [scripts/make_prompt_macos.sh](scripts/make_prompt_macos.sh)
- Python entrypoint still works:

```bash
python -m infomation_extractor
```

## Privacy

Serial numbers, UUIDs, and service tags are redacted before being written into the prompt file. Review the generated file before uploading if the laptop contains sensitive organization-specific details.
