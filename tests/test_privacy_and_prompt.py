from __future__ import annotations

import json
import re
import unittest

from infomation_extractor.model_inference import ModelGuess
from infomation_extractor.prompt_export import build_cloud_research_prompt
from infomation_extractor.utils import redact_sensitive


class PrivacyAndPromptTests(unittest.TestCase):
    def test_redacts_common_personal_identifiers(self) -> None:
        sample = {
            "ComputerName": "Alice-Laptop",
            "VolumeLabel": "Alice Work",
            "RegistryPath": r"HKEY_LOCAL_MACHINE\SYSTEM\DISPLAY\ABC",
            "MAC Address": "AA:BB:CC:DD:EE:FF",
            "IPv4 Addresses": ["192.168.1.22"],
            "Current Network": "Alice Home Wi-Fi",
            "note": (
                "/Users/alice/Desktop/report.json "
                r"C:\Users\bob\Desktop\file.txt "
                "123e4567-e89b-12d3-a456-426614174000 "
                "me@example.com "
                "10.0.0.5 "
                "11-22-33-44-55-66"
            ),
        }

        redacted = redact_sensitive(sample)
        rendered = json.dumps(redacted)

        self.assertNotIn("Alice-Laptop", rendered)
        self.assertNotIn("Alice Work", rendered)
        self.assertNotIn("alice", rendered)
        self.assertNotIn("bob", rendered)
        self.assertNotIn("me@example.com", rendered)
        self.assertNotIn("AA:BB:CC:DD:EE:FF", rendered)
        self.assertNotIn("192.168.1.22", rendered)
        self.assertNotIn("Alice Home Wi-Fi", rendered)
        self.assertIn("[REDACTED]", rendered)
        self.assertIn("[REDACTED_EMAIL]", rendered)
        self.assertIn("[REDACTED_IP]", rendered)
        self.assertIn("[REDACTED_MAC]", rendered)

    def test_prompt_contains_sanitized_structured_local_evidence(self) -> None:
        system_info = {
            "source": "/Users/alice/Desktop/system.json",
            "platform": "file",
            "summary": {
                "manufacturer": "Example",
                "system_model": "ExampleBook 14",
                "cpu": "Example CPU",
                "gpu": ["Example GPU"],
                "memory": "16.0 GB",
                "memory_modules": [{"capacity": "16.0 GB", "speed": "6400 MHz"}],
                "network": [{"name": "Example Wi-Fi 7 Adapter"}],
                "audio": [{"name": "Example Speakers"}],
                "camera": [{"name": "Example IR Camera"}],
                "ports_or_controllers": [{"name": "USB4 Host Router"}],
                "battery": [{"design_capacity": "70.0 Wh"}],
            },
            "raw": {
                "ComputerName": "Alice-Laptop",
                "note": "/Users/alice/Desktop/system.json",
            },
        }
        guess = ModelGuess(
            model_name="Example ExampleBook 14",
            confidence=0.74,
            method="test",
            evidence=["System model: ExampleBook 14"],
        )

        prompt = build_cloud_research_prompt("Example ExampleBook 14", system_info, guess)

        self.assertIn("Structured Local Evidence - Sanitized JSON", prompt)
        self.assertIn("Local RAM Modules", prompt)
        self.assertIn("Local Network / Wi-Fi", prompt)
        self.assertIn("Local Ports / Controllers", prompt)
        self.assertNotIn("Alice-Laptop", prompt)
        self.assertNotRegex(prompt, re.compile(r"/Users/alice", re.IGNORECASE))
        self.assertIn("/Users/[REDACTED]/Desktop/system.json", prompt)


if __name__ == "__main__":
    unittest.main()
