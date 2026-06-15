# Infomation Extractor - Laptop Deep Research Prompt

You are a senior laptop reviewer, technical researcher, and YouTube script strategist.
Use web/deep research to identify, verify, and evaluate this exact laptop as deeply as possible.

IMPORTANT LANGUAGE REQUIREMENT:
- The final research report MUST be written in Vietnamese.
- Keep common technical terms in English where natural, for example CPU, GPU, TGP, PWM, benchmark, thermal throttling, color gamut.
- Do not answer in English except for technical names, product names, benchmark names, and source titles.

Do not hallucinate. Every important factual claim must have a source URL. If a fact cannot be verified, mark it as `Chưa xác minh`.

## Laptop To Research

- Confirmed / detected laptop model: `"1.0" encoding="utf-8"?>`
- Confirmed / detected GPU variant: `Not confirmed`

## Extracted Clean Specs

| Field | Local extracted value |
|---|---|
| Confirmed model | "1.0" encoding="utf-8"?> |
| Manufacturer | Unknown |
| Marketing model | Unknown |
| Product/model code | Unknown |
| System SKU/version | "1.0" encoding="utf-8"?> |
| Baseboard | Unknown |
| BIOS version | Unknown |
| CPU | Unknown |
| Confirmed GPU variant | Unknown |
| Detected GPU list | Unknown |
| RAM | Unknown |
| Storage devices | Unknown |
| Display / panel | Unknown |
| Battery | Unknown |
| Operating system | Unknown |

## Local Detection Evidence

- Detection method: `heuristic`
- Detection confidence: `35%`
- Evidence:
- SKU/version: "1.0" encoding="utf-8"?>
- Alternatives/hints:
- None
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
