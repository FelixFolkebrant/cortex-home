import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


PROVISION_HOST = Path(__file__).parents[1] / "provision-host"


class ProvisioningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = PROVISION_HOST.read_text()

    def test_media_policy_uses_the_validated_coordinator_origin(self):
        self.assertIn(
            'coordinator_origin="$coordinator_url/"',
            self.script,
        )
        self.assertIn(
            '"AudioCaptureAllowedUrls": ["%s"]',
            self.script,
        )
        self.assertIn(
            '"OverrideSecurityRestrictionsOnInsecureOrigin": ["%s"]',
            self.script,
        )
        self.assertEqual(
            self.script.count('"$coordinator_origin"'),
            2,
        )

    def test_media_policy_does_not_grant_video_or_wildcard_access(self):
        policy_template = self.script[
            self.script.index("AudioCaptureAllowedUrls") :
            self.script.index(
                "> /var/snap/chromium/current/policies/managed/"
                "cortex-home-media.json"
            )
        ]

        self.assertNotIn("VideoCapture", policy_template)
        self.assertNotIn("*", policy_template)
        self.assertNotIn("MediaStream", policy_template)

    def test_focused_media_provision_uses_existing_exact_origin(self):
        focused_script = (
            PROVISION_HOST.parent / "provision-media-host"
        ).read_text()

        self.assertIn(
            "coordinator_url_file=/etc/cortex-endpoint/coordinator-url",
            focused_script,
        )
        self.assertIn('coordinator_origin="$coordinator_url/"', focused_script)
        self.assertIn('"AudioCaptureAllowedUrls"', focused_script)
        self.assertIn(
            '"OverrideSecurityRestrictionsOnInsecureOrigin"',
            focused_script,
        )
        self.assertIn("systemctl restart lightdm.service", focused_script)
        self.assertNotIn("VideoCaptureAllowedUrls", focused_script)
        self.assertNotIn('["*"]', focused_script)
        self.assertNotIn("netplan", focused_script)

    def test_qualification_playback_is_limited_to_the_kiosk_audio_session(self):
        files = PROVISION_HOST.parent / "files"
        helper = (
            files / "cortex-speech-qualification-playback"
        ).read_text()
        capture = (
            files / "cortex-speech-qualification-capture"
        ).read_text()
        sudoers = (
            files / "cortex-speech-qualification-playback.sudoers"
        ).read_text()

        self.assertIn('if [ "$#" -ne 0 ]', helper)
        self.assertIn('pulse_socket="$runtime_dir/pulse/native"', helper)
        self.assertIn(
            "sink_name=$(/usr/local/bin/cortex-endpoint-audio-route)",
            helper,
        )
        self.assertIn("--device=\"$sink_name\"", helper)
        self.assertIn("/bin/cat |", helper)
        self.assertEqual(
            sudoers,
            "imac ALL=(cortex-endpoint) NOPASSWD: "
            '/usr/local/bin/cortex-speech-qualification-playback ""\n'
            "imac ALL=(cortex-endpoint) NOPASSWD: "
            '/usr/local/bin/cortex-speech-qualification-capture ""\n',
        )
        self.assertIn('if [ "$#" -ne 0 ]', capture)
        self.assertIn("--device=plughw:S330", capture)
        self.assertIn("--format=S16_LE", capture)
        self.assertIn("--rate=16000", capture)
        self.assertIn("--channels=1", capture)
        self.assertIn("--duration=15", capture)
        self.assertIn("--file-type=wav", capture)

    def test_output_route_selects_only_the_pci_analog_sink(self):
        files = PROVISION_HOST.parent / "files"
        route = (files / "cortex-endpoint-audio-route").read_text()
        session = (files / "cortex-endpoint-session").read_text()
        raspotify = (files / "cortex-raspotify").read_text()

        self.assertIn(
            "/^alsa_output\\.pci-.*\\.analog-stereo$/",
            route,
        )
        self.assertIn('if [ "$#" -ne 1 ]', route)
        self.assertIn('/usr/bin/pactl set-default-sink "$1"', route)
        self.assertIn('/usr/bin/pactl set-sink-mute "$1" 0', route)
        self.assertNotIn("set-sink-volume", route)
        self.assertNotIn("alsa_output.usb", route)
        self.assertIn(
            "/usr/local/bin/cortex-endpoint-audio-route >/dev/null",
            session,
        )
        self.assertIn(
            "LIBRESPOT_DEVICE=$(/usr/local/bin/cortex-endpoint-audio-route)",
            raspotify,
        )

    def test_focused_media_provision_restores_the_room_mixer_baseline(self):
        focused_script = (
            PROVISION_HOST.parent / "provision-media-host"
        ).read_text()

        self.assertIn("amixer -c 0 sset Master 80% unmute", self.script)
        self.assertIn("amixer -c 0 sset Master 80% unmute", focused_script)
        self.assertIn("amixer -c 0 sset Speaker mute", focused_script)
        self.assertIn(
            "amixer -c 0 sset Headphone 60% unmute",
            focused_script,
        )
        self.assertIn("alsactl store 0", focused_script)
        self.assertLess(
            focused_script.index("systemctl restart raspotify.service"),
            focused_script.index("amixer -c 0 sset Master 80% unmute"),
        )
        self.assertLess(
            self.script.index("systemctl restart raspotify.service"),
            self.script.index("amixer -c 0 sset Master 80% unmute"),
        )

    def test_openbox_binds_fixed_headphone_volume_steps(self):
        files = PROVISION_HOST.parent / "files"
        helper = (files / "cortex-endpoint-headphone-volume").read_text()
        openbox = ET.parse(files / "openbox-rc.xml")
        namespace = {"openbox": "http://openbox.org/3.4/rc"}
        bindings = {
            binding.attrib["key"]: binding.findtext(
                "openbox:action/openbox:command",
                namespaces=namespace,
            )
            for binding in openbox.findall(
                "openbox:keyboard/openbox:keybind",
                namespace,
            )
        }

        self.assertEqual(
            bindings["C-A-Up"],
            "/usr/local/bin/cortex-endpoint-headphone-volume up",
        )
        self.assertEqual(
            bindings["C-A-Down"],
            "/usr/local/bin/cortex-endpoint-headphone-volume down",
        )
        self.assertIn("up) adjustment=+5%", helper)
        self.assertIn("down) adjustment=-5%", helper)
        self.assertIn(
            "sink_name=$(/usr/local/bin/cortex-endpoint-audio-route)",
            helper,
        )
        self.assertIn(
            '/usr/bin/pactl set-sink-volume "$sink_name" "$adjustment"',
            helper,
        )
        self.assertNotIn("amixer", helper)
        self.assertNotIn("Master", helper)
        self.assertNotIn("S330", helper)


if __name__ == "__main__":
    unittest.main()
