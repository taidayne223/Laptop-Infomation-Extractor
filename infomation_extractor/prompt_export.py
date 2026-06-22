from __future__ import annotations

from pathlib import Path
from typing import Any

from .model_inference import ModelGuess
from .utils import ensure_dir, now_stamp, redact_sensitive, slugify, to_json


def write_cloud_research_prompt(
    output_dir: Path,
    model_name: str,
    system_info: dict[str, Any],
    guess: ModelGuess,
) -> Path:
    ensure_dir(output_dir)
    gpu = (system_info.get("confirmed") or {}).get("gpu")
    name = model_name if not gpu else f"{model_name}-{gpu}"
    path = output_dir / f"{now_stamp()}-{slugify(name)}-infomation-extractor-prompt.md"
    path.write_text(build_cloud_research_prompt(model_name, system_info, guess), encoding="utf-8")
    return path


def build_cloud_research_prompt(model_name: str, system_info: dict[str, Any], guess: ModelGuess) -> str:
    summary = system_info.get("summary") or {}
    confirmed = system_info.get("confirmed") or {}
    gpu = confirmed.get("gpu") or ", ".join(summary.get("gpu") or []) or "Not confirmed"
    snapshot = build_clean_snapshot(system_info)
    evidence_json = build_structured_evidence_json(system_info)

    return f"""# Infomation Extractor - Laptop Deep Research Prompt

You are a senior laptop reviewer, technical researcher, and YouTube script strategist.
Use web/deep research to identify, verify, and evaluate this exact laptop as deeply as possible.

IMPORTANT LANGUAGE REQUIREMENT & TERMINOLOGY TRANSLATION:
- The final research report MUST be written in Vietnamese.
- All titles, subtitles, headings, and lists must be generated in Vietnamese. Do not use English names for sections (e.g. use "Bàn phím, bàn di chuột, webcam và loa" instead of "Keyboard, Touchpad, Webcam, Speakers"; use "Cổng kết nối, khả năng nâng cấp và sửa chữa" instead of "Ports, Upgradeability, Repairability"; use "Thời lượng pin & Sạc" instead of "Battery Life & Charging", etc.).
- Translate hardware terms, feedback adjectives, and user concerns into natural, easy-to-understand Vietnamese rather than leaving them in English jargon (except for proper names like CPU, GPU, RAM, BIOS, Windows, SSD, TGP, TDP, HDMI, USB-C, Wi-Fi, etc.). For example:
  + "spongy/soft keyboard" -> "phím bấm hơi lún/nhão/mềm"
  + "key travel" -> "hành trình phím"
  + "feedback" -> "phản hồi/độ nảy phím"
  + "clickpad/touchpad tracking" -> "độ nhạy/khả năng tracking của bàn rê"
  + "palm rejection" -> "khả năng chống tì đè lòng bàn tay"
  + "upgradeability" -> "khả năng nâng cấp"
  + "common issues" -> "các lỗi thường gặp/vấn đề phổ biến"
  + "pros & cons" -> "Ưu điểm & Nhược điểm"
  + "B-roll" -> "Cảnh quay phụ họa (B-roll)"
  + "takeaways" -> "Điểm nhấn rút ra"
  + "display deep dive" -> "Đánh giá chi tiết màn hình"
  + "performance deep dive" -> "Đánh giá chi tiết hiệu năng"
  + "thermal throttling" -> "giảm hiệu năng do quá nhiệt / hạ xung nhiệt"
- For all other hardware descriptions, try to write in a clear, easy-to-understand language for non-technical users, avoiding raw English jargon.
- Do not answer in English except for technical names, product names, benchmark names, and source titles.

Do not hallucinate. Every important factual claim must have a source URL. If a fact cannot be verified, mark it as `Chưa xác minh`.

## Laptop To Research

- Confirmed / detected laptop model: `{model_name}`
- Confirmed / detected GPU variant: `{gpu}`

## Extracted Clean Specs

{snapshot}

## Structured Local Evidence - Sanitized JSON

Use this machine-readable local evidence to verify the exact variant. It has been privacy-redacted before export. Prefer the clean specs table for quick reading, then use this JSON appendix to resolve ambiguity about RAM modules, display panel clues, battery data, network/audio/camera devices, ports/controllers, BIOS, OS build, and other local hardware evidence.

```json
{evidence_json}
```

## Local Detection Evidence

- Detection method: `{guess.method}`
- Detection confidence: `{guess.confidence:.0%}`
- Evidence:
{format_list(guess.evidence)}
- Alternatives/hints:
{format_list(guess.alternatives)}
- Notes: `{guess.notes or "None"}`

Use the extracted specs above as the local evidence. Do not ask the user for another system-information file unless the exact variant cannot be verified from web sources.

## Research Mission

Your job is to create a professional, source-backed laptop review/research dossier for a YouTube creator.

First, verify the exact commercial model and variant using the local product code, SKU, CPU, GPU, BIOS/baseboard, and official sources. If the exact regional SKU is ambiguous, explain the ambiguity and list the most likely matching variants.

Search and use sources in this priority order:

1. Official manufacturer product page, support page, PSREF/spec sheet, manuals, BIOS/driver page.
2. Professional reviews and databases: Notebookcheck, LaptopMedia, UltrabookReview, PCMag, Tom's Hardware, The Verge, Windows Central, RTINGS, TechRadar, PCWorld, KitGuru, Hardware Canucks, Jarrod'sTech or similar.
3. Store listings only for real-world configuration and pricing context.
4. Reddit/forums/community posts only for common complaints and owner reports. Label them as weaker evidence.
5. YouTube video reviews only when the reviewer is identifiable and the claim can be attributed.

## Required Output Structure

Your output report must be organized into the following 6 comprehensive chapters. Avoid generating tiny, fragmented sections. Write in a flowing, cohesive review style (văn phong phân tích chuyên sâu, mạch lạc, kết nối chặt chẽ giữa các ý, tránh viết rời rạc từng mục nhỏ cụt lủn).

# CHƯƠNG 1: TỔNG QUAN & NHẬN DIỆN MẪU MÁY CHÍNH XÁC
1. Tóm tắt đánh giá cốt lõi:
   - Đánh giá tổng quan về laptop trong 1-2 đoạn văn mạch lạc, nêu rõ định vị thị trường, đối tượng nên mua và đối tượng nên tránh.
   - 5 điểm nhấn quan trọng rút ra phục vụ cho kịch bản review.
2. Xác nhận & Nhận diện phiên bản:
   - Tên thương mại chính thức, SKU khu vực.
   - Đối chiếu bằng chứng từ hệ thống cục bộ so với thông tin trực tuyến để tăng độ tin cậy.
   - Những chi tiết cấu hình còn mơ hồ cần kiểm tra thực tế thêm trên máy.
3. Bảng thông số kỹ thuật đầy đủ:
   - Tạo bảng Markdown sạch sẽ gồm: CPU, GPU (kèm điện năng giới hạn/TGP nếu có), RAM (loại, tốc độ, dung lượng, khả năng nâng cấp), Ổ cứng (model, chuẩn kết nối, khe cắm nâng cấp), Màn hình (kích thước, độ phân giải, loại panel, tần số quét, độ sáng, độ bao phủ màu, PWM), Dung lượng pin & Công suất bộ sạc, Cân nặng & Kích thước, Cổng kết nối, Wi-Fi/Bluetooth, Webcam/Mic/Loa, Bàn phím/Touchpad, Hệ điều hành kèm phần mềm đi kèm.

# CHƯƠNG 2: THIẾT KẾ, PHẦN CỨNG VÀ TRẢI NGHIỆM VẬT LÝ VẬN HÀNH
1. Thiết kế & Chất lượng hoàn thiện:
   - Phân tích chi tiết vật liệu chế tạo, độ cứng cáp của khung sườn, độ linh hoạt của bản lề, độ võng (flex) của nắp máy và bệ phím.
   - Tính cơ động, thiết kế thẩm mỹ và gợi ý các cảnh quay phụ họa (B-roll) ấn tượng.
2. Trải nghiệm nhập liệu và Ngoại vi (Bàn phím, Bàn di chuột, Webcam, Loa):
   - Cảm giác gõ phím thực tế (hành trình phím, độ nảy, tiếng ồn), độ nhạy của bàn di chuột (touchpad/clickpad).
   - Chất lượng webcam (độ phân giải/hình ảnh), microphone và hệ thống loa.
3. Cổng kết nối & Khả năng nâng cấp, sửa chữa:
   - Sơ đồ bố trí các cổng kết nối.
   - Khả năng nâng cấp RAM (hàn chết hay có khe cắm), số khe cắm SSD, loại card Wi-Fi.
   - Cách tháo nắp đáy và nhận định sơ bộ về độ phức tạp của hệ thống tản nhiệt/linh kiện bên trong.

# CHƯƠNG 3: MÀN HÌNH & HIỆU NĂNG CHUYÊN SÂU
1. Phân tích màn hình chuyên sâu:
   - Phân tích chi tiết độ phân giải, tỷ lệ khung hình, tần số quét, độ sáng thực tế, độ phủ màu (sRGB, DCI-P3, AdobeRGB), độ tương phản, thời gian phản hồi và sự hiện diện của hiện tượng nhấp nháy màn hình (PWM/flicker).
   - Đánh giá mức độ phù hợp cho từng tác vụ: văn phòng, học tập, lập trình, thiết kế đồ họa, dựng video, chơi game.
   - Ưu điểm và Nhược điểm của màn hình và các lưu ý khi kiểm tra màn hình thực tế.
2. Hiệu năng & Tản nhiệt chuyên sâu:
   - Đánh giá hiệu năng CPU và GPU trong các tác vụ văn phòng và đồ họa nặng/chơi game.
   - Điện năng tiêu thụ thực tế (TDP/TGP), hiện tượng giảm hiệu năng do quá nhiệt (thermal throttling), tiếng ồn quạt và các chế độ điều phối năng lượng.
   - Tổng hợp kết quả chấm điểm hiệu năng (benchmark) thực tế từ các nguồn đánh giá uy tín (Notebookcheck, UltrabookReview, v.v.), bắt buộc đính kèm URL nguồn Gợi ý các bài test hiệu năng mà reviewer nên tự thực hiện trên máy.

# CHƯƠNG 4: PIN & ĐÁNH GIÁ THỰC TẾ TỪ CỘNG ĐỒNG
1. Thời lượng Pin & Công nghệ sạc:
   - Dung lượng pin, kết quả test thực tế từ các bài đánh giá uy tín dưới các kịch bản sử dụng khác nhau (lướt web, xem video, làm việc nặng).
   - Tốc độ sạc, các yếu tố ảnh hưởng trực tiếp đến thời lượng pin thực tế.
2. Lỗi vặt và Phản hồi từ cộng đồng:
   - Tổng hợp các lỗi hoặc phàn nàn phổ biến từ người dùng trên Reddit, diễn đàn công nghệ về Driver, BIOS, màn hình xanh, quạt kêu to, sụt pin nhanh hoặc quá nhiệt.
   - Đánh giá mức độ nghiêm trọng và độ tin cậy của các phản hồi này.

# CHƯƠNG 5: SO SÁNH ĐỐI THỦ & TƯ VẤN MUA SẮM SẮC BÉN
1. Bảng so sánh 5-8 đối thủ cùng phân khúc:
   - Lập bảng so sánh chi tiết gồm các cột: Tên máy, CPU/GPU, Màn hình, Dung lượng pin, Trọng lượng, Khả năng nâng cấp, Giá tham khảo.
   - Phân tích rõ lý do nên chọn đối thủ thay vì máy này và ngược lại.
2. Bảng Ưu điểm & Nhược điểm:
   - Tạo bảng so sánh ưu/nhược điểm đối sánh trực quan, súc tích và có tính thuyết phục cao.
3. Tư vấn mua sắm & Định giá:
   - Khoảng giá tốt/tệ để mua máy.
   - Phiên bản cấu hình tối ưu nhất nên mua và phiên bản cấu hình cần tránh.
   - Các lưu ý khi mua máy cũ hoặc hàng tân trang (refurbished) (nếu có).

# CHƯƠNG 6: GÓI TÀI NGUYÊN CHO CREATOR VÀ NGUỒN THAM KHẢO
1. Gói hỗ trợ làm video YouTube:
   - Đề xuất 10 ý tưởng tiêu đề, 10 câu giật tít hình thu nhỏ (thumbnail), 5 câu mở đầu video thu hút (hooks).
   - Dàn ý kịch bản chi tiết, danh sách cảnh quay phụ họa (B-roll) cần thực hiện.
   - Các câu hỏi từ khán giả mà kịch bản nên giải đáp trực tiếp.
2. Bộ thông tin đồ họa (Infographic):
   - Thiết kế sẵn nội dung dạng bảng Markdown để có thể dễ dàng sao chép và dán vào Canva/Figma/Sheets (gồm thông tin cấu hình, bảng so sánh hiệu năng/pin, ma trận đối thủ).
3. Bảng đối chiếu thông tin (Fact-Check):
   - Tạo bảng đối chiếu: Tuyên bố thông tin | URL nguồn dẫn chứng | Loại nguồn | Độ tin cậy (Cao/Trung bình/Thấp) | Ghi chú.
4. Danh sách nguồn tham khảo chi tiết:
   - Phân nhóm nguồn rõ ràng (Official, Professional, Store, Community, Video reviews) kèm tiêu đề bài viết và liên kết URL đầy đủ.

## Quality Rules

- Bắt buộc viết dưới dạng văn phong phân tích chuyên sâu, mạch lạc, kết nối chặt chẽ giữa các ý (Cohesive narrative). Tránh liệt kê các gạch đầu dòng rời rạc mà không có phân tích đi kèm.
- Luôn ưu tiên thông tin chính xác của đúng phiên bản (variant) phần cứng đang được quét, tránh nhầm lẫn thông số với các phiên bản khác trong cùng dòng máy.
- Không tự bịa đặt số liệu benchmark hay URL nguồn. Nếu thông tin không thể xác minh, ghi rõ là "Chưa xác minh".
- Cân bằng tốt giữa phân tích kỹ thuật chuyên sâu dành cho người yêu công nghệ và giải thích trực quan, dễ hiểu dành cho người dùng phổ thông.
- Đảm bảo đầu ra có giá trị sử dụng cao như một tài liệu nghiên cứu kịch bản sản xuất video chuyên nghiệp.
"""


def format_list(items: list[str]) -> str:
    if not items:
        return "- None"
    return "\n".join(f"- {item}" for item in items)


def build_clean_snapshot(system_info: dict[str, Any]) -> str:
    summary = system_info.get("summary") or {}
    confirmed = system_info.get("confirmed") or {}
    fields = [
        ("Confirmed model", confirmed.get("model_name")),
        ("Manufacturer", summary.get("manufacturer")),
        ("Marketing model", summary.get("marketing_model")),
        ("Product/model code", summary.get("system_model")),
        ("System SKU/version", summary.get("system_sku")),
        ("Baseboard", summary.get("baseboard")),
        ("BIOS version", summary.get("bios_version")),
        ("CPU", summary.get("cpu")),
        ("Confirmed GPU variant", confirmed.get("gpu")),
        ("Detected GPU list", join_values(summary.get("gpu"))),
        ("RAM", summary.get("memory")),
        ("RAM modules", summarize_dict_list(summary.get("memory_modules"))),
        ("Storage devices", join_values(summary.get("storage"))),
        ("Network / Wi-Fi", summarize_dict_list(summary.get("network"))),
        ("Bluetooth", summarize_dict_list(summary.get("bluetooth"))),
        ("Audio", summarize_dict_list(summary.get("audio"))),
        ("Camera / webcam", summarize_dict_list(summary.get("camera"))),
        ("Input devices", summarize_dict_list(summary.get("input"))),
        ("Security", summarize_dict(summary.get("security"))),
        ("Ports / controllers", summarize_dict_list(summary.get("ports_or_controllers"))),
        ("Display / panel", summarize_dict_list(summary.get("display"))),
        ("Battery", summarize_dict_list(summary.get("battery"))),
        ("Operating system", summary.get("os")),
    ]

    lines = ["| Field | Local extracted value |", "|---|---|"]
    for label, value in fields:
        lines.append(f"| {label} | {escape_table(value or 'Unknown')} |")

    drives = summary.get("drives") or []
    if drives:
        lines.extend(["", "### Local Drives", "", "| Drive | Type | Total | Free | Label |", "|---|---|---:|---:|---|"])
        for drive in drives:
            if not isinstance(drive, dict):
                continue
            lines.append(
                "| {name} | {type} | {total} | {free} | {label} |".format(
                    name=escape_table(drive.get("name") or ""),
                    type=escape_table(drive.get("type") or ""),
                    total=escape_table(drive.get("total") or ""),
                    free=escape_table(drive.get("free") or ""),
                    label=escape_table(drive.get("label") or ""),
                )
            )

    displays = summary.get("display") or []
    if displays:
        append_dict_table(
            lines,
            "Local Displays",
            displays,
            [
                ("Name", "name"),
                ("Manufacturer ID", "manufacturer_id"),
                ("Product code", "product_code"),
                ("Physical size", "physical_size"),
                ("Native/preferred resolution", "native_or_preferred_resolution"),
                ("Current resolution", "current_desktop_resolution"),
                ("Refresh", "estimated_refresh_rate"),
                ("Active refresh", "active_refresh_rate"),
                ("Display Type", "display_type"),
                ("Main", "main"),
                ("Registry hint", "registry_hint"),
            ],
        )

    memory_modules = summary.get("memory_modules") or []
    if memory_modules:
        append_dict_table(
            lines,
            "Local RAM Modules",
            memory_modules,
            [
                ("Manufacturer", "manufacturer"),
                ("Capacity", "capacity"),
                ("Speed", "speed"),
                ("Configured speed", "configured_speed"),
                ("Part number", "part_number"),
            ],
        )

    batteries = summary.get("battery") or []
    if batteries:
        append_dict_table(
            lines,
            "Local Battery",
            batteries,
            [
                ("ID / Device Name", "id"),
                ("Manufacturer", "manufacturer"),
                ("Chemistry", "chemistry"),
                ("Design capacity", "design_capacity"),
                ("Full charge/Max capacity", "full_charge_capacity"),
                ("Cycle count", "cycle_count"),
                ("Health / State", "health"),
                ("Est. Active Runtime (Design)", "estimated_active_runtime_design"),
                ("Est. Active Runtime (Full)", "estimated_active_runtime_full_charge"),
                ("Charger Wattage", "charger_wattage"),
            ],
        )

    for heading, key, columns in (
        (
            "Local Network / Wi-Fi",
            "network",
            [
                ("Name", "name"),
                ("Manufacturer", "manufacturer"),
                ("Type", "type"),
                ("Speed", "speed"),
                ("Hardware", "hardware"),
                ("Interface", "interface"),
            ],
        ),
        (
            "Local Bluetooth",
            "bluetooth",
            [
                ("Name", "name"),
                ("Type", "type"),
                ("Hardware", "hardware"),
                ("Interface", "interface"),
            ],
        ),
        (
            "Local Audio",
            "audio",
            [
                ("Name", "name"),
                ("Manufacturer", "manufacturer"),
                ("Transport", "transport"),
                ("Status", "status"),
                ("Class", "class"),
            ],
        ),
        (
            "Local Camera / Webcam",
            "camera",
            [
                ("Name", "name"),
                ("Manufacturer", "manufacturer"),
                ("Status", "status"),
                ("Class", "class"),
            ],
        ),
        (
            "Local Input Devices",
            "input",
            [
                ("Type", "type"),
                ("Name", "name"),
                ("Manufacturer", "manufacturer"),
                ("Details", "details"),
            ],
        ),
        (
            "Local Ports / Controllers",
            "ports_or_controllers",
            [
                ("Name", "name"),
                ("Manufacturer/Vendor", "manufacturer"),
                ("Vendor", "vendor"),
                ("Speed", "speed"),
                ("Status", "status"),
                ("Class", "class"),
            ],
        ),
    ):
        rows = summary.get(key) or []
        if rows:
            append_dict_table(lines, heading, rows, columns)

    return "\n".join(lines)


def append_dict_table(
    lines: list[str],
    heading: str,
    rows: Any,
    columns: list[tuple[str, str]],
) -> None:
    if isinstance(rows, dict):
        rows = [rows]
    if not isinstance(rows, list):
        return

    lines.extend(["", f"### {heading}", ""])
    lines.append("| " + " | ".join(label for label, _key in columns) + " |")
    lines.append("|" + "|".join("---" for _label, _key in columns) + "|")
    for row in rows:
        if not isinstance(row, dict):
            continue
        values = [escape_table(row.get(key) or "") for _label, key in columns]
        lines.append("| " + " | ".join(values) + " |")


def summarize_dict_list(value: Any) -> str:
    if isinstance(value, dict):
        value = [value]
    if not isinstance(value, list):
        return ""

    parts: list[str] = []
    for item in value:
        if isinstance(item, dict):
            readable = ", ".join(f"{key}: {val}" for key, val in item.items() if val not in (None, "", []))
            if readable:
                parts.append(readable)
        elif item:
            parts.append(str(item))
    return "; ".join(parts)


def summarize_dict(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    return ", ".join(f"{key}: {val}" for key, val in value.items() if val not in (None, "", []))


def join_values(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value if str(item).strip())
    if value is None:
        return ""
    return str(value)


def escape_table(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def build_structured_evidence_json(system_info: dict[str, Any]) -> str:
    return to_json(redact_sensitive(system_info))
