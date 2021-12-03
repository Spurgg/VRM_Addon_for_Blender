import contextlib
import os
import platform
import subprocess
import tempfile
from unittest import TestCase


class BaseBlenderTestCase(TestCase):
    def __init__(self, *args: str, **kwargs: str) -> None:
        # https://stackoverflow.com/a/19102520
        super().__init__(*args, **kwargs)

        self.windows = platform.system() == "Windows"
        if self.windows:
            self.exeext = ".exe"
        else:
            self.exeext = ""

        self.repository_root_dir = os.path.dirname(
            os.path.dirname(os.path.realpath(__file__))
        )
        self.user_scripts_dir = tempfile.mkdtemp()
        os.mkdir(os.path.join(self.user_scripts_dir, "addons"))
        addon_dir = os.path.join(
            self.user_scripts_dir, "addons", "io_scene_vrm_saturday06"
        )
        if self.windows:
            import _winapi

            _winapi.CreateJunction(self.repository_root_dir, addon_dir)
        else:
            os.symlink(self.repository_root_dir, addon_dir)

        test_vrm_dir = os.environ.get(
            "BLENDER_VRM_TEST_VRM_DIR",
            os.path.join(self.repository_root_dir, "tests", "vrm"),
        )

        command = [self.find_blender_command(), "--version"]
        completed_process = subprocess.run(
            command,
            check=False,
            capture_output=True,
        )
        stdout_str = self.process_output_to_str(completed_process.stdout)
        stderr_str = self.process_output_to_str(completed_process.stderr)
        output = (
            "\n  ".join(command)
            + "\n===== stdout =====\n"
            + stdout_str
            + "===== stderr =====\n"
            + stderr_str
            + "=================="
        )
        if completed_process.returncode != 0:
            raise Exception("Failed to execute command:\n" + output)
        self.major_minor = ".".join(
            stdout_str.splitlines()[0].split(" ")[1].split(".")[:2]
        )

        test_temp_vrm_dir = os.path.join(test_vrm_dir, self.major_minor, "temp")
        test_out_vrm_dir = os.path.join(test_vrm_dir, self.major_minor, "out")
        test_out2_vrm_dir = os.path.join(test_vrm_dir, self.major_minor, "out2")
        os.makedirs(test_temp_vrm_dir, exist_ok=True)
        os.makedirs(test_out_vrm_dir, exist_ok=True)
        os.makedirs(test_out2_vrm_dir, exist_ok=True)

    def process_output_to_str(self, process_output: bytes) -> str:
        output = None
        if platform.system() != "Windows":
            output = process_output.decode()
        else:
            with contextlib.suppress(UnicodeDecodeError):
                output = process_output.decode("ansi")
            if output is None:
                output = process_output.decode()
        if output != "" and not output.endswith("\n"):
            output += "\n"
        return output

    def find_blender_command(self) -> str:
        try:
            import bpy

            bpy_binary_path = str(bpy.app.binary_path)
            if bpy_binary_path and os.path.exists(bpy_binary_path):
                return bpy_binary_path
        except ImportError:
            pass
        env = os.environ.get("BLENDER_VRM_TEST_BLENDER_PATH")
        if env:
            return env
        if self.windows:
            completed_process = subprocess.run(
                "where blender", shell=True, capture_output=True, check=False
            )
            if completed_process.returncode == 0:
                return self.process_output_to_str(
                    completed_process.stdout
                ).splitlines()[0]
        if os.name == "posix":
            completed_process = subprocess.run(
                "which blender", shell=True, capture_output=True, check=False
            )
            if completed_process.returncode == 0:
                return self.process_output_to_str(
                    completed_process.stdout
                ).splitlines()[0]
        if platform.system() == "Darwin":
            default_path = "/Applications/Blender.app/Contents/MacOS/Blender"
            if os.path.exists(default_path):
                return default_path
        raise Exception(
            "Failed to discover blender executable. "
            + "Please set blender executable location to "
            + 'environment variable "BLENDER_VRM_TEST_BLENDER_PATH"'
        )

    def run_script(self, script: str, *args: str) -> None:
        env = os.environ.copy()
        env["BLENDER_USER_SCRIPTS"] = self.user_scripts_dir
        env["BLENDER_VRM_AUTOMATIC_LICENSE_CONFIRMATION"] = "true"
        env["BLENDER_VRM_BLENDER_MAJOR_MINOR_VERSION"] = self.major_minor

        command = [
            self.find_blender_command(),
            "-noaudio",  # sound system to None (less output on stdout)
            "--factory-startup",  # factory settings
            "--addons",
            "io_scene_vrm_saturday06",  # enable the addon
            "--python-exit-code",
            "1",
            "--background",
            "--python",
            os.path.join(
                self.repository_root_dir, "tests", script
            ),  # run the test script
            "--",
            *args,
        ]
        completed_process = subprocess.run(
            command,
            check=False,
            capture_output=True,
            cwd=self.repository_root_dir,
            env=env,
        )
        stdout_str = self.process_output_to_str(completed_process.stdout)
        stderr_str = self.process_output_to_str(completed_process.stderr)
        output = (
            "\n  ".join(command)
            + "\n===== stdout =====\n"
            + stdout_str
            + "===== stderr =====\n"
            + stderr_str
            + "=================="
        )
        self.assertEqual(
            completed_process.returncode,
            0,
            "Failed to execute command:\n" + output,
        )