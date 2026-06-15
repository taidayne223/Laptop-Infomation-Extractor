# Infomation Extractor - Laptop Deep Research Prompt

You are a senior laptop reviewer, technical researcher, and YouTube script strategist.
Use web/deep research to identify, verify, and evaluate this exact laptop as deeply as possible.

IMPORTANT LANGUAGE REQUIREMENT:
- The final research report MUST be written in Vietnamese.
- Keep common technical terms in English where natural, for example CPU, GPU, TGP, PWM, benchmark, thermal throttling, color gamut.
- Do not answer in English except for technical names, product names, benchmark names, and source titles.

Do not hallucinate. Every important factual claim must have a source URL. If a fact cannot be verified, mark it as `Chưa xác minh`.

## Laptop To Research

- Confirmed / detected laptop model: `Lenovo Yoga Pro 7 15IPH11`
- Confirmed / detected GPU variant: `NVIDIA GeForce RTX 5050 Laptop GPU`

## Extracted Clean Specs

| Field | Local extracted value |
|---|---|
| Confirmed model | Lenovo Yoga Pro 7 15IPH11 |
| Manufacturer | Lenovo |
| Marketing model | Yoga Pro 7 15IPH11 |
| Product/model code | 83SN |
| System SKU/version | LENOVO_MT_83SN_BU_idea_FM_Yoga Pro 7 15IPH11 |
| Baseboard | LNVNB161216 |
| BIOS version | TNCN37WW |
| CPU | Intel(R) Core(TM) Ultra 7 356H |
| Confirmed GPU variant | NVIDIA GeForce RTX 5050 Laptop GPU |
| Detected GPU list | Intel(R) Graphics, NVIDIA GeForce RTX 5050 Laptop GPU |
| RAM | 31.5 GB |
| Storage devices | NVMe SAMSUNG MZAL81T0, MSI DATAMAG 20Gbps |
| Display / panel | name: R241Y, manufacturer_id: ACR, product_code: 0x0521, physical_size: 53 x 30 cm (~24 in), native_or_preferred_resolution: 1920 x 1080, estimated_refresh_rate: 75 Hz, refresh_range: 48-76 Hz, horizontal_scan_range: 31-84 kHz, registry_hint: ACR0521, current_desktop_resolution: 1707 x 1067, primary: True; name: EF25QBA63.B, manufacturer_id: EDO, product_code: 0x3015, physical_size: 33 x 20 cm (~15.2 in), refresh_range: 48-165 Hz, horizontal_scan_range: 46-47 kHz, registry_hint: EDO3015 |
| Battery | id: L23N4PF1, manufacturer: ATL, chemistry: LiP, design_capacity: 84.0 Wh, full_charge_capacity: 87.0 Wh, cycle_count: 3 |
| Operating system | Windows 10 Home Single Language 25H2 build 26200.8457 |

### Local Drives

| Drive | Type | Total | Free | Label |
|---|---|---:|---:|---|
| C:\ | Fixed | 951.5 GB | 751.0 GB | Windows-SSD |
| D:\ | Fixed | 931.5 GB | 426.4 GB | MSI DATAMAG |

### Local Displays

| Name | Manufacturer ID | Product code | Physical size | Native/preferred resolution | Refresh | Current desktop resolution | Registry hint |
|---|---|---|---|---|---|---|---|
| R241Y | ACR | 0x0521 | 53 x 30 cm (~24 in) | 1920 x 1080 | 75 Hz | 1707 x 1067 | ACR0521 |
| EF25QBA63.B | EDO | 0x3015 | 33 x 20 cm (~15.2 in) |  |  |  | EDO3015 |

### Local Battery

| ID | Manufacturer | Chemistry | Design capacity | Full charge capacity | Cycle count |
|---|---|---|---|---|---|
| L23N4PF1 | ATL | LiP | 84.0 Wh | 87.0 Wh | 3 |

## Local Detection Evidence

- Detection method: `heuristic`
- Detection confidence: `74%`
- Evidence:
- Manufacturer: Lenovo
- System model: Yoga Pro 7 15IPH11
- Model/product code: 83SN
- SKU/version: LENOVO_MT_83SN_BU_idea_FM_Yoga Pro 7 15IPH11
- Baseboard: LNVNB161216
- CPU: Intel(R) Core(TM) Ultra 7 356H
- Alternatives/hints:
- Search commercial name using model/product code: 83SN
- Search commercial name using baseboard/product code: LNVNB161216
- Notes: `Local heuristic guess. Ask the cloud AI to verify the exact commercial variant.`

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

# 1. Executive Summary
- This laptop in one paragraph.
- Market positioning.
- Who should buy it.
- Who should avoid it.
- 5 key takeaways for a YouTube review.

# 2. Exact Model Identification
- Confirmed commercial name.
- Regional names/SKUs.
- Local machine evidence vs online evidence.
- Confidence level.
- What still needs physical verification on the unit.

# 3. Full Specification Table
Create a clean table with:
- CPU
- GPU and power limit/TGP if available
- RAM type/speed/capacity/upgradeability
- Storage model/interface/slots
- Display size/resolution/panel type/refresh rate/brightness/color gamut/PWM
- Battery capacity
- Charger wattage
- Weight/dimensions
- Ports
- Wi-Fi/Bluetooth
- Webcam/mic/speakers
- Keyboard/touchpad
- OS and bundled software

# 4. Design & Build Quality
- Materials, chassis rigidity, hinge, lid flex, keyboard deck flex.
- Portability and visual identity.
- B-roll shots worth filming.

# 5. Display Deep Dive
- Resolution, aspect ratio, refresh rate, brightness, color coverage, contrast, response time, PWM/flicker.
- Suitability for office, school, coding, color work, video editing, gaming.
- Display pros/cons and testing notes.

# 6. Performance Deep Dive
- CPU performance.
- GPU performance.
- Sustained performance.
- SSD/storage performance.
- Thermals.
- Fan noise.
- Power modes.
- Benchmarks from sources, with URLs.
- Suggested tests I should run myself.

# 7. Battery Life & Charging
- Battery capacity.
- Real-world battery results from reviews.
- Charging speed.
- What affects runtime.
- Practical expectation for creator/student/office use.

# 8. Keyboard, Touchpad, Webcam, Speakers
- Review observations.
- What to test on camera.
- Strengths and weaknesses.

# 9. Ports, Upgradeability, Repairability
- Port map.
- RAM upgradeability.
- SSD slots.
- Wi-Fi card.
- Bottom cover access.
- Thermal system observations if available.

# 10. Common Issues & Owner Complaints
- Confirmed review complaints.
- Owner/community complaints.
- Driver/BIOS/thermal/fan/display/battery issues.
- Severity and confidence rating for each issue.

# 11. Pros & Cons
Create a sharp pros/cons table. Each item must be backed by source or local evidence.

# 12. Competitor Comparison
Compare against 5-8 relevant competitors in the same class. Include:
- Model
- CPU/GPU
- Display
- Battery
- Weight
- Upgradeability
- Typical price
- Why choose it over this laptop
- Why choose this laptop instead

# 13. Value & Buying Advice
- Good price range.
- Bad price range.
- Best configuration to buy.
- Configurations to avoid.
- Used/refurbished buying notes if relevant.

# 14. YouTube Review Package
Give me:
- 10 title ideas.
- 10 thumbnail text ideas.
- 5 opening hooks.
- Full video outline.
- B-roll checklist.
- Benchmarks/tests checklist.
- Talking points for each chapter.
- Suggested verdict.
- Audience questions to answer in the video.

# 15. Infographic / Information Graphics Pack
Create chart-ready content:
- Spec card layout.
- Pros/cons visual card.
- Performance comparison table.
- Battery comparison table.
- Competitor matrix.
- Upgradeability diagram description.
- Port map description.
- Suggested icons and labels.
- Data tables in Markdown that can be pasted into Canva/Figma/Sheets.
- Short captions for each graphic.

# 16. Fact Check Table
Create a table:
- Claim
- Source URL
- Source type
- Confidence: High / Medium / Low
- Notes

# 17. Sources
Group sources by:
- Official
- Professional reviews
- Store listings
- Community/forum
- Video reviews

## Quality Rules

- Prefer exact variant data over generic model-family data.
- Never mix results from a different GPU/CPU variant without warning.
- If sources disagree, explain the conflict.
- Do not invent benchmark numbers.
- Do not invent source URLs.
- Use clear Vietnamese explanations for normal viewers, but include enough technical depth for enthusiasts.
- Make the output useful as both a written review brief and a YouTube production plan.
