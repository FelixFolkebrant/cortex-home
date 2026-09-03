import http.client
import json
import socket
import subprocess
import tempfile
import time
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


PROVISION_HOST = Path(__file__).parents[1] / "provision-host"
ENDPOINT_DIR = PROVISION_HOST.parent
FILES = ENDPOINT_DIR / "files"


@unittest.skipUnless(
    Path("/usr/bin/nc").is_file(),
    "OpenBSD netcat is not installed in the test environment.",
)
class AirPlayControlTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        temporary_path = Path(self.temporary_directory.name)
        self.origin = "http://coordinator.test:8080"
        coordinator_url = temporary_path / "coordinator-url"
        coordinator_url.write_text(f"{self.origin}\n")
        alarm_helper = temporary_path / "alarm-helper"
        alarm_helper.write_text(
            "#!/bin/sh\n"
            "set -eu\n"
            'case "$1" in\n'
            "  list) printf 'birds.mp3\\nwake-alarm.mp3\\n' ;;\n"
            "  selected) printf 'wake-alarm.mp3\\n' ;;\n"
            "  select) [ \"$2\" = 'birds.mp3' ] || exit 1 ;;\n"
            "  start|stop|status|ready) exit 0 ;;\n"
            "  *) exit 1 ;;\n"
            "esac\n"
        )
        alarm_helper.chmod(0o755)
        rtc_helper = temporary_path / "rtc-helper"
        rtc_helper.write_text("#!/bin/sh\nexit 0\n")
        rtc_helper.chmod(0o755)

        with socket.socket() as available_port:
            available_port.bind(("127.0.0.1", 0))
            self.port = available_port.getsockname()[1]

        control = temporary_path / "cortex-airplay-control"
        control.write_text(
            (FILES / "cortex-airplay-control")
            .read_text()
            .replace(
                "coordinator_url_file=/etc/cortex-endpoint/coordinator-url",
                f"coordinator_url_file={coordinator_url}",
            )
            .replace(
                "alarm_helper=/usr/local/bin/cortex-endpoint-alarm",
                f"alarm_helper={alarm_helper}",
            )
            .replace(
                "rtc_suspend_helper=/usr/local/bin/cortex-endpoint-rtc-suspend",
                f"rtc_suspend_helper={rtc_helper}",
            )
            .replace(
                "127.0.0.1 38019",
                f"127.0.0.1 {self.port}",
            )
        )
        control.chmod(0o755)
        self.process = subprocess.Popen(
            [control],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.addCleanup(self.stop_control)

        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            try:
                status, _ = self.request("GET", "/stats")
                if status == 200:
                    return
            except OSError:
                time.sleep(0.02)

        self.process.terminate()
        _, error = self.process.communicate(timeout=2)
        self.fail(f"The AirPlay control test server did not start: {error}")

    def stop_control(self):
        if self.process.poll() is None:
            self.process.terminate()
            self.process.wait(timeout=2)
        self.process.stderr.close()

    def request(self, method, path, origin=None):
        for attempt in range(10):
            connection = http.client.HTTPConnection(
                "127.0.0.1",
                self.port,
                timeout=2,
            )
            self.addCleanup(connection.close)
            try:
                connection.request(
                    method,
                    path,
                    headers={"Origin": origin or self.origin},
                )
                response = connection.getresponse()
                body = response.read()
                payload = json.loads(body) if body else None
                return response.status, payload
            except ConnectionRefusedError:
                if attempt == 9:
                    raise
                time.sleep(0.01)

    def test_rejects_receiver_control_and_another_origin(self):
        self.assertEqual(
            self.request("GET", "/status"),
            (404, {"error": "Route not found."}),
        )
        self.assertEqual(
            self.request("POST", "/on"),
            (404, {"error": "Route not found."}),
        )
        self.assertEqual(
            self.request("POST", "/on", "http://untrusted.test"),
            (403, {"error": "Origin not allowed."}),
        )

    def test_reports_bounded_local_system_stats(self):
        status, stats = self.request("GET", "/stats")

        self.assertEqual(status, 200)
        self.assertEqual(
            set(stats),
            {
                "cpuPercent",
                "loadOne",
                "memoryPercent",
                "memoryTotalMiB",
                "memoryUsedMiB",
                "temperatureC",
                "uptimeSeconds",
            },
        )
        self.assertGreaterEqual(stats["cpuPercent"], 0)
        self.assertLessEqual(stats["cpuPercent"], 100)
        self.assertGreater(stats["memoryTotalMiB"], 0)
        self.assertGreaterEqual(stats["memoryUsedMiB"], 0)
        self.assertLessEqual(stats["memoryUsedMiB"], stats["memoryTotalMiB"])
        self.assertGreaterEqual(stats["uptimeSeconds"], 0)

    def test_lists_and_selects_only_endpoint_alarm_files(self):
        self.assertEqual(
            self.request("GET", "/alarm/files"),
            (200, {"files": ["birds.mp3", "wake-alarm.mp3"], "selected": "wake-alarm.mp3"}),
        )
        self.assertEqual(
            self.request("POST", "/alarm/select/birds.mp3"),
            (200, {"state": "selected"}),
        )
        self.assertEqual(
            self.request("POST", "/alarm/select/other.mp3"),
            (400, {"error": "Alarm audio selection is unavailable."}),
        )


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
        self.assertIn(
            '"VideoCaptureAllowedUrls": ["%s"]',
            self.script,
        )
        self.assertEqual(
            self.script.count('"$coordinator_origin"'),
            3,
        )

    def test_media_policy_does_not_grant_wildcard_or_global_media_access(self):
        policy_template = self.script[
            self.script.index("AudioCaptureAllowedUrls") :
            self.script.index(
                "> /var/snap/chromium/current/policies/managed/"
                "cortex-home-media.json"
            )
        ]

        self.assertNotIn("*", policy_template)
        self.assertNotIn("MediaStream", policy_template)
        self.assertNotIn('"VideoCaptureAllowed": true', policy_template)

    def test_focused_media_provision_uses_existing_exact_origin(self):
        focused_script = (ENDPOINT_DIR / "provision-media-host").read_text()

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
        self.assertIn('"VideoCaptureAllowedUrls"', focused_script)
        self.assertEqual(
            focused_script.count('"$coordinator_origin"'),
            3,
        )
        self.assertIn("systemctl restart lightdm.service", focused_script)
        self.assertNotIn('["*"]', focused_script)
        self.assertNotIn('"VideoCaptureAllowed": true', focused_script)
        self.assertNotIn("netplan", focused_script)

    def test_qualification_playback_is_limited_to_the_kiosk_audio_session(self):
        helper = (
            FILES / "cortex-speech-qualification-playback"
        ).read_text()
        capture = (
            FILES / "cortex-speech-qualification-capture"
        ).read_text()
        sudoers = (
            FILES / "cortex-speech-qualification-playback.sudoers"
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
        route = (FILES / "cortex-endpoint-audio-route").read_text()
        session = (FILES / "cortex-endpoint-session").read_text()
        raspotify = (FILES / "cortex-raspotify").read_text()

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
        focused_script = (ENDPOINT_DIR / "provision-media-host").read_text()

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
        helper = (FILES / "cortex-endpoint-headphone-volume").read_text()
        openbox = ET.parse(FILES / "openbox-rc.xml")
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

    def test_airplay_runtime_is_installed_without_a_compositor(self):
        focused_script = (ENDPOINT_DIR / "provision-media-host").read_text()
        deploy_script = (ENDPOINT_DIR / "provision-media").read_text()

        for script in (self.script, focused_script):
            self.assertIn("gstreamer1.0-libav", script)
            self.assertIn("gstreamer1.0-plugins-bad", script)
            self.assertIn("gstreamer1.0-plugins-base", script)
            self.assertIn("gstreamer1.0-plugins-good", script)
            self.assertIn("gstreamer1.0-pulseaudio", script)
            self.assertIn("gstreamer1.0-x", script)
            self.assertIn("netcat-openbsd", script)
            self.assertIn("uxplay", script)
            self.assertIn(
                "/usr/local/bin/cortex-endpoint-airplay",
                script,
            )
            self.assertIn(
                "/usr/local/bin/cortex-airplay-control",
                script,
            )
            self.assertNotIn("xcompmgr", script)
            self.assertNotIn("wmctrl", script)

        self.assertIn(
            '"$script_dir/files/cortex-endpoint-airplay"',
            deploy_script,
        )
        self.assertIn(
            '"$script_dir/files/cortex-airplay-control"',
            deploy_script,
        )

    def test_airplay_helper_is_ephemeral_and_passwordless(self):
        helper = (FILES / "cortex-endpoint-airplay").read_text()
        session = (FILES / "cortex-endpoint-session").read_text()

        self.assertIn("/usr/bin/uxplay", helper)
        self.assertIn('-n "Skärmen"', helper)
        self.assertIn("-fs", helper)
        self.assertIn("-avdec", helper)
        self.assertIn("-vsync no", helper)
        self.assertIn("-vs xvimagesink", helper)
        self.assertIn("-reset 1", helper)
        self.assertIn("-as pulsesink", helper)
        self.assertNotIn("-pin", helper)
        self.assertNotIn("-reg", helper)
        self.assertIn("HOME=$home_dir", helper)
        self.assertIn('remove_runtime_home', helper)
        self.assertIn('"$coordinator_url/api/actions"', helper)
        self.assertIn("--max-time 5", helper)
        self.assertIn("post_channel airplay", helper)
        self.assertIn('post_channel "$mode"', helper)
        self.assertIn('kill -INT "$airplay_pid"', helper)
        self.assertIn('kill -TERM "$airplay_pid"', helper)
        self.assertIn('kill -KILL "$airplay_pid"', helper)
        self.assertIn(
            "/usr/local/bin/cortex-endpoint-audio-route >/dev/null",
            helper,
        )
        self.assertIn(
            "/usr/local/bin/cortex-endpoint-airplay stop-local",
            session,
        )
        self.assertIn(
            "/usr/local/bin/cortex-endpoint-airplay start-local",
            session,
        )
        self.assertIn("/usr/local/bin/cortex-airplay-control &", session)
        self.assertIn('kill "$airplay_control_pid"', session)

    def test_alarm_audio_catalog_is_single_owner_and_installed_with_the_endpoint(self):
        helper = (FILES / "cortex-endpoint-alarm").read_text()
        installer = (ENDPOINT_DIR / "provision-alarm-audio").read_text()

        self.assertIn("audio_dir=/var/lib/cortex-endpoint/alarm-audio", helper)
        self.assertIn("selection_file=/home/cortex-endpoint/.config/cortex-alarm-file", helper)
        self.assertIn("start|stop|status|list|select|selected|ready", helper)
        self.assertIn("valid_file_name", helper)
        self.assertIn('"$runtime_dir/cortex-alarm"', helper)
        self.assertIn("/usr/bin/mpg123 --loop -1", helper)
        self.assertIn("kill -TERM", helper)
        self.assertIn('"$source_dir/files/cortex-endpoint-alarm"', self.script)
        self.assertIn("mpg123", self.script)
        self.assertIn("The alarm file must be a regular file.", installer)
        self.assertIn("33554432", installer)
        self.assertIn("The alarm file does not contain an MP3 header.", installer)
        self.assertIn(
            "/var/lib/cortex-endpoint/alarm-audio/wake-alarm.mp3",
            installer,
        )
        self.assertIn("/var/lib/cortex-endpoint/alarm-audio", self.script)
        focused_host = (ENDPOINT_DIR / "provision-alarm-host").read_text()
        self.assertIn("/var/lib/cortex-endpoint/alarm-audio", focused_host)
        self.assertNotIn("/home/imac/cortex-alarm-audio", helper)
        self.assertNotIn("/home/imac/cortex-alarm-audio", installer)
        self.assertIn("ssh -tt imac", installer)

    def test_rtc_suspend_helper_is_the_only_privileged_power_boundary(self):
        helper = (FILES / "cortex-endpoint-rtc-suspend").read_text()
        sudoers = (FILES / "cortex-endpoint-rtc-suspend.sudoers").read_text()

        self.assertIn("$EUID -ne 0", helper)
        self.assertIn("$# -ne 1", helper)
        self.assertIn("93600", helper)
        self.assertIn(
            "/usr/sbin/rtcwake --utc --mode freeze --time",
            helper,
        )
        self.assertLess(
            helper.index("/usr/bin/sleep 2"),
            helper.index("/usr/sbin/rtcwake --utc --mode freeze --time"),
        )
        self.assertNotIn("--mode mem", helper)
        self.assertNotIn("/usr/bin/xrandr", helper)
        self.assertEqual(
            sudoers,
            "cortex-endpoint ALL=(root) NOPASSWD: "
            "/usr/local/bin/cortex-endpoint-rtc-suspend *\n",
        )
        self.assertIn("cortex-endpoint-rtc-suspend.sudoers", self.script)

    def test_focused_alarm_install_changes_only_the_alarm_runtime(self):
        deploy = (ENDPOINT_DIR / "provision-alarm").read_text()
        host = (ENDPOINT_DIR / "provision-alarm-host").read_text()

        self.assertIn('"$script_dir/files/cortex-endpoint-alarm"', deploy)
        self.assertIn('"$script_dir/files/cortex-endpoint-rtc-suspend"', deploy)
        self.assertIn('"$script_dir/files/cortex-airplay-control"', deploy)
        self.assertIn('"$script_dir/provision-alarm-host"', deploy)
        self.assertTrue((ENDPOINT_DIR / "provision-alarm-host").stat().st_mode & 0o111)
        self.assertIn("mpg123", host)
        self.assertIn("cortex-endpoint-rtc-suspend.sudoers", host)
        self.assertIn("systemctl restart lightdm.service", host)
        self.assertNotIn("netplan", host)
        self.assertNotIn("raspotify", host)

    def test_airplay_control_is_loopback_only_and_origin_bound(self):
        control = (FILES / "cortex-airplay-control").read_text()

        self.assertIn("/usr/bin/nc -l -N 127.0.0.1 38019", control)
        self.assertNotIn("0.0.0.0", control)
        self.assertIn('if [[ $origin != "$coordinator_url" ]]', control)
        self.assertIn("Access-Control-Allow-Private-Network: true", control)
        self.assertIn("GET && $path == /stats", control)
        self.assertNotIn("GET && $path == /status", control)
        self.assertNotIn("POST && $path == /on", control)
        self.assertNotIn("POST && $path == /off", control)
        self.assertNotIn("airplay_helper=", control)
        self.assertIn("POST && $path == /alarm/start", control)
        self.assertIn("POST && $path == /alarm/stop", control)
        self.assertIn("GET && $path == /alarm/files", control)
        self.assertIn("POST && $path =~ ^/alarm/select/.+$", control)
        self.assertIn('"$alarm_helper" list', control)
        self.assertIn('"$alarm_helper" select "$selected_file"', control)
        self.assertIn('"$alarm_helper" start', control)
        self.assertIn('"$alarm_helper" stop', control)
        self.assertIn("POST && $path =~ ^/alarm/sleep/[0-9]+$", control)
        self.assertIn('nohup sudo -n "$rtc_suspend_helper" "$wake_epoch"', control)

    def test_openbox_controls_airplay_and_raises_each_mirror_window(self):
        openbox = ET.parse(FILES / "openbox-rc.xml")
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
            bindings["C-A-4"],
            "/usr/local/bin/cortex-endpoint-airplay airplay",
        )
        self.assertEqual(
            {
                key: bindings[key]
                for key in ("C-A-1", "C-A-2", "C-A-3")
            },
            {
                "C-A-1": "/usr/local/bin/cortex-endpoint-airplay today",
                "C-A-2": "/usr/local/bin/cortex-endpoint-airplay music",
                "C-A-3": "/usr/local/bin/cortex-endpoint-airplay camera",
            },
        )

        applications = openbox.findall(
            "openbox:applications/openbox:application",
            namespace,
        )
        airplay = next(
            application
            for application in applications
            if application.attrib == {
                "name": "Skärmen",
                "class": "GStreamer",
            }
        )
        self.assertEqual(
            {
                child.tag.rsplit("}", 1)[-1]: child.text
                for child in airplay
            },
            {
                "decor": "no",
                "focus": "yes",
                "layer": "above",
                "fullscreen": "yes",
            },
        )


if __name__ == "__main__":
    unittest.main()
