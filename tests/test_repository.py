import ast
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative_path):
    return (ROOT / relative_path).read_text(
        encoding="utf-8"
    )


class RepositoryTests(unittest.TestCase):
    def test_worker_sources_parse(self):
        for relative_path in (
            "workers/arena-curling-worker",
            "workers/arena-volleyball-worker",
            "workers/srt-worker.py",
        ):
            ast.parse(
                read(relative_path),
                filename=relative_path,
            )

    def test_camera_mappings_are_complete(self):
        volleyball = read(
            "workers/arena-volleyball-worker"
        )
        curling = read(
            "workers/arena-curling-worker"
        )

        for number in range(1, 7):
            self.assertIn(
                f'"source_path": "volleyball{number}"',
                volleyball,
            )
            self.assertIn(
                f'"target_key": "URL{number}"',
                volleyball,
            )
            self.assertIn(
                f'"field_id": {number}',
                volleyball,
            )

        for number, field_id in ((1, 7), (2, 8)):
            self.assertIn(
                f'"source_path": "curling{number}"',
                curling,
            )
            self.assertIn(
                f'"target_key": "URL{field_id}"',
                curling,
            )
            self.assertIn(
                f'"field_id": {field_id}',
                curling,
            )

    def test_camera_workers_use_protected_configuration(self):
        for relative_path in (
            "workers/arena-curling-worker",
            "workers/arena-volleyball-worker",
        ):
            text = read(relative_path)
            self.assertRegex(
                text,
                r'Path\(\s*"/etc/arena76/'
                r'rtmp-targets\.env"\s*\)',
            )
            self.assertIn(
                "ARENA_RTMP_PREVIEW_ENDPOINT_BASE",
                text,
            )
            self.assertIn(
                "ARENA_RTMP_PREVIEW_UPLOAD_TOKEN",
                text,
            )
            self.assertNotIn("https://CHANGE_ME", text)
            self.assertNotIn(
                "CHANGE_ME_PRIVATE_VALUE",
                text,
            )

    def test_srt_worker_uses_systemd_credentials(self):
        text = read("workers/srt-worker.py")
        self.assertIn("CREDENTIALS_DIRECTORY", text)
        self.assertIn('values.get("SRT_ENDPOINT")', text)
        self.assertIn('values.get("SRT_USER")', text)
        self.assertIn('values.get("SRT_PASSWORD")', text)
        self.assertIn("sanitize(err)", text)
        self.assertNotIn("uri=srt://CHANGE_ME", text)

    def test_direct_route_has_no_quoted_systemd_regex(self):
        unit = read(
            "systemd/arena-mediamtx-direct-route.service"
        )
        helper = read("scripts/direct-route.sh")

        self.assertNotIn("/bin/sh -c", unit)
        self.assertIn(
            "EnvironmentFile=/etc/arena76/direct-route.env",
            unit,
        )
        self.assertIn(
            "ExecStart=/usr/local/lib/arena76/"
            "direct-route.sh start",
            unit,
        )
        self.assertIn("ip -4 rule", helper)
        self.assertIn("lookup main", helper)

    def test_current_units_have_baseline_hardening(self):
        required = {
            "NoNewPrivileges=true",
            "PrivateTmp=true",
            "ProtectSystem=strict",
            "ProtectHome=true",
            "ProtectKernelTunables=true",
            "ProtectKernelModules=true",
            "ProtectControlGroups=true",
            "RestrictSUIDSGID=true",
            "LockPersonality=true",
            "SystemCallArchitectures=native",
        }

        for relative_path in (
            "systemd/mediamtx.service",
            "systemd/arena-curling@.service",
            "systemd/arena-volleyball@.service",
            "systemd/arena-srt@.service",
        ):
            text = read(relative_path)
            for directive in required:
                self.assertIn(
                    directive,
                    text,
                    msg=f"{directive} missing from {relative_path}",
                )

    def test_mediamtx_example_has_eight_camera_paths(self):
        text = read("mediamtx/mediamtx.yml.example")

        for name in (
            *(f"volleyball{number}" for number in range(1, 7)),
            "curling1",
            "curling2",
        ):
            self.assertEqual(
                len(re.findall(
                    rf"^  {re.escape(name)}:$",
                    text,
                    flags=re.MULTILINE,
                )),
                1,
            )

        self.assertIn("apiAddress: 127.0.0.1:9997", text)
        self.assertIn("metricsAddress: 127.0.0.1:9998", text)

    def test_examples_contain_placeholders_only(self):
        expected = {
            "ARENA_RTMP_PREVIEW_ENDPOINT_BASE",
            "ARENA_RTMP_PREVIEW_UPLOAD_TOKEN",
        }
        preview = read(
            "config/preview-upload.env.example"
        )
        keys = {
            line.split("=", 1)[0]
            for line in preview.splitlines()
            if "=" in line
        }
        self.assertEqual(keys, expected)

        private_url_pattern = re.compile(
            r"(?:rtsp|rtmp|srt)://"
            r"(?!127\.0\.0\.1|CHANGE_ME|rtmp\.example\.invalid)"
        )

        for path in (ROOT / "config").rglob("*.example"):
            self.assertIsNone(
                private_url_pattern.search(
                    path.read_text(encoding="utf-8")
                ),
                msg=f"unexpected media URL in {path}",
            )

    def test_no_generated_or_backup_files_are_required(self):
        required_files = {
            "workers/arena-curling-worker",
            "workers/arena-volleyball-worker",
            "workers/srt-worker.py",
            "scripts/direct-route.sh",
            "systemd/arena-curling@.service",
            "systemd/arena-volleyball@.service",
            "systemd/arena-srt@.service",
            "systemd/mediamtx.service",
        }

        for relative_path in required_files:
            self.assertTrue((ROOT / relative_path).is_file())

    def test_validator_scopes_systemd_diagnostics(self):
        text = read("scripts/validate.sh")

        self.assertIn("PROJECT_VERIFY_OUTPUT", text)
        for unit_name in (
            "arena-curling@",
            "arena-mediamtx-direct-route",
            "arena-srt@",
            "arena-volleyball@",
            "mediamtx",
        ):
            self.assertIn(unit_name, text)

        self.assertIn(
            'printf \'%s\\n\' "${PROJECT_VERIFY_OUTPUT}"',
            text,
        )


if __name__ == "__main__":
    unittest.main()
