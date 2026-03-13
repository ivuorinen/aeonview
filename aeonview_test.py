"""Tests for the aeonview timelapse generator."""

# vim: set ft=python ts=4 sw=4 sts=4 et wrap:
import argparse
import contextlib
import logging
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from unittest import mock

import pytest

from aeonview import (
    AeonViewApp,
    AeonViewHelpers,
    AeonViewImages,
    AeonViewMessages,
    AeonViewVideos,
)

default_dest = str(Path.cwd() / "projects")
default_project = "default"
default_fps = 10
default_timeframe = "daily"
default_simulate = False
default_verbose = False
default_image_domain = "https://example.com/image"
default_test_path = Path(tempfile.gettempdir(), "test_project").resolve()
tmp_images = Path(tempfile.gettempdir(), "images")


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def make_video_args(
    simulate=False, fps=10, day="01", month="04", year="2025"
) -> argparse.Namespace:
    """Create an ``argparse.Namespace`` with video-generation defaults."""
    return argparse.Namespace(
        simulate=simulate, fps=fps, day=day, month=month, year=year
    )


@contextlib.contextmanager
def expect_error_exit():
    """Expect ``SystemExit`` and silence ``logging.error``."""
    with pytest.raises(SystemExit), mock.patch("aeonview.logging.error"):
        yield


def make_app_with_project(tmp: str) -> tuple[AeonViewApp, Path]:
    """Create an ``AeonViewApp`` with base_path at *tmp*/'proj'."""
    app = AeonViewApp()
    app.base_path = Path(tmp).resolve()
    proj_path = app.base_path / "proj"
    proj_path.mkdir()
    return app, proj_path


# ---------------------------------------------------------------------------
# AeonViewHelpers tests
# ---------------------------------------------------------------------------


def test_build_path_resolves_correctly():
    base = Path(tempfile.gettempdir())
    result = AeonViewHelpers.build_path(base, "a", "b", "c")
    assert result == Path(base, "a", "b", "c").resolve()


def test_check_date_valid():
    assert AeonViewHelpers.check_date(2023, 12, 31)


def test_check_date_invalid():
    assert not AeonViewHelpers.check_date(2023, 2, 30)


def test_mkdir_p_creates_directory():
    with tempfile.TemporaryDirectory() as tmp:
        test_path = Path(tmp) / "a" / "b" / "c"
        AeonViewHelpers.mkdir_p(test_path)
        assert test_path.exists()
        assert test_path.is_dir()


@pytest.mark.parametrize("ext", ["jpg", "png", "gif", "webp"])
def test_get_extension_valid(ext):
    assert (
        AeonViewHelpers.get_extension(f"{default_image_domain}.{ext}")
        == f".{ext}"
    )


def test_get_extension_invalid():
    assert AeonViewHelpers.get_extension(default_image_domain) == ".jpg"
    assert AeonViewHelpers.get_extension(None) is None


def test_get_extension_jpeg():
    assert (
        AeonViewHelpers.get_extension(f"{default_image_domain}.jpeg") == ".jpeg"
    )


def test_generate_ffmpeg_command():
    input_dir = tmp_images
    output_file = Path(tempfile.gettempdir(), "output.mp4")
    fps = 24
    cmd = AeonViewHelpers.generate_ffmpeg_command(input_dir, output_file, fps)
    assert "ffmpeg" in cmd[0]
    assert str(fps) in cmd
    assert str(output_file) == cmd[-1]
    assert str(input_dir / "*.{jpg,jpeg,png,gif,webp}") in cmd


def test_generate_ffmpeg_command_output_format():
    input_dir = tmp_images
    output_file = Path(tempfile.gettempdir(), "video.mp4")
    cmd = AeonViewHelpers.generate_ffmpeg_command(input_dir, output_file, 30)
    assert str(tmp_images / "*.{jpg,jpeg,png,gif,webp}") in cmd
    assert str(output_file) in cmd
    assert "-c:v" in cmd
    assert "libx264" in cmd
    assert "-pix_fmt" in cmd
    assert "yuv420p" in cmd


@mock.patch("subprocess.run")
def test_simulate_ffmpeg_call(mock_run):
    input_dir = tmp_images
    output_file = Path(tempfile.gettempdir(), "out.mp4")
    cmd = AeonViewHelpers.generate_ffmpeg_command(input_dir, output_file, 10)
    subprocess.run(cmd, check=True)
    mock_run.assert_called_once_with(cmd, check=True)


def test_generate_concat_command():
    with tempfile.TemporaryDirectory() as tmp:
        files = [Path(tmp) / "01.mp4", Path(tmp) / "02.mp4"]
        for f in files:
            f.touch()
        output = Path(tmp) / "output.mp4"
        cmd, concat_file = AeonViewHelpers.generate_concat_command(
            files, output
        )
        try:
            assert cmd[0] == "ffmpeg"
            assert "-f" in cmd
            assert "concat" in cmd
            assert "-safe" in cmd
            assert "0" in cmd
            assert "-c" in cmd
            assert "copy" in cmd
            assert str(output) == cmd[-1]
            assert concat_file.exists()
            content = concat_file.read_text(encoding="utf-8")
            for f in files:
                assert f"file '{f}'" in content
        finally:
            concat_file.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# AeonViewImages tests
# ---------------------------------------------------------------------------


def test_get_image_paths_valid():
    url = f"{default_image_domain}.jpg"
    destination_base = default_test_path
    date = datetime(2025, 4, 10, 12, 30, 45)
    aeon_view_images = AeonViewImages(destination_base, url)
    paths = aeon_view_images.get_image_paths(url, destination_base, date)

    a_p = destination_base / "2025-04" / "10" / "12-30-45.jpg"

    assert paths["url"] == url
    assert paths["file"] == "12-30-45.jpg"
    assert paths["destinations"]["file"] == a_p


def test_get_image_paths_invalid_url():
    with expect_error_exit():
        aeon_view_images = AeonViewImages(default_test_path, "invalid-url")
        aeon_view_images.get_image_paths(
            "invalid-url", default_test_path, datetime(2025, 4, 10)
        )


def test_get_image_paths_invalid_date():
    with expect_error_exit():
        aeon_view_images = AeonViewImages(
            default_test_path, f"{default_image_domain}.jpg"
        )
        # noinspection PyTypeChecker
        aeon_view_images.get_image_paths(
            f"{default_image_domain}.jpg",
            default_test_path,
            "invalid-date",  # pyright: ignore [reportArgumentType]
        )


def test_get_image_paths_none_url():
    avi = AeonViewImages(default_test_path, None)
    with expect_error_exit():
        avi.get_image_paths(None, default_test_path, datetime(2025, 4, 10))


def test_get_image_paths_no_image_extension():
    url = "https://example.com/image.bmp"
    avi = AeonViewImages(default_test_path, url)
    with expect_error_exit():
        avi.get_image_paths(url, default_test_path, datetime(2025, 4, 10))


def test_get_image_paths_none_destination():
    url = f"{default_image_domain}.jpg"
    avi = AeonViewImages(default_test_path, url)
    with expect_error_exit():
        avi.get_image_paths(url, None, datetime(2025, 4, 10))


def test_get_image_paths_non_path_destination():
    url = f"{default_image_domain}.jpg"
    avi = AeonViewImages(default_test_path, url)
    with expect_error_exit():
        # noinspection PyTypeChecker
        avi.get_image_paths(
            url,
            "/tmp/not-a-path-object",  # pyright: ignore [reportArgumentType]
            datetime(2025, 4, 10),
        )


def test_get_image_paths_creates_directory():
    with tempfile.TemporaryDirectory() as tmp:
        url = f"{default_image_domain}.jpg"
        dest = Path(tmp) / "newproject"
        avi = AeonViewImages(dest, url)
        paths = avi.get_image_paths(url, dest, datetime(2025, 4, 10, 12, 0, 0))
        assert paths["file"] == "12-00-00.jpg"
        assert (dest / "2025-04" / "10").exists()


def test_get_image_paths_simulate_no_mkdir():
    with tempfile.TemporaryDirectory() as tmp:
        url = f"{default_image_domain}.jpg"
        dest = Path(tmp) / "simproject"
        args = argparse.Namespace(simulate=True)
        avi = AeonViewImages(dest, url, args)
        with mock.patch("aeonview.logging.info"):
            paths = avi.get_image_paths(
                url, dest, datetime(2025, 4, 10, 12, 0, 0)
            )
        assert paths["file"] == "12-00-00.jpg"
        assert not (dest / "2025-04" / "10").exists()


@mock.patch("aeonview.AeonViewHelpers.mkdir_p")
@mock.patch("aeonview.AeonViewImages.download_image")
def test_get_current_image(mock_download_image, mock_mkdir_p):
    args = argparse.Namespace(simulate=False, date="2025-04-10 12:30:45")
    avi = AeonViewImages(default_test_path, f"{default_image_domain}.jpg", args)
    avi.get_current_image()
    mock_mkdir_p.assert_called()
    mock_download_image.assert_called()


def test_get_current_image_invalid_date_format():
    args = argparse.Namespace(simulate=False, date="not-a-date")
    avi = AeonViewImages(default_test_path, f"{default_image_domain}.jpg", args)
    with expect_error_exit():
        avi.get_current_image()


@mock.patch("aeonview.AeonViewHelpers.mkdir_p")
@mock.patch("aeonview.AeonViewImages.download_image")
def test_get_current_image_no_date_uses_now(mock_download, mock_mkdir):
    args = argparse.Namespace(simulate=False, date=None)
    avi = AeonViewImages(default_test_path, f"{default_image_domain}.jpg", args)
    avi.get_current_image()
    mock_mkdir.assert_called()
    mock_download.assert_called()


def test_get_current_image_no_url():
    args = argparse.Namespace(simulate=False, date="2025-04-10 12:30:45")
    avi = AeonViewImages(default_test_path, None, args)
    with expect_error_exit():
        avi.get_current_image()


@mock.patch("aeonview.requests.get")
def test_download_image_success(mock_get):
    mock_response = mock.Mock()
    mock_response.status_code = 200
    mock_response.iter_content = mock.Mock(return_value=[b"data"])
    mock_get.return_value = mock_response

    args = argparse.Namespace(simulate=False)
    avi = AeonViewImages(default_test_path, f"{default_image_domain}.jpg", args)
    with tempfile.NamedTemporaryFile(delete=True) as temp_file:
        destination = Path(temp_file.name)
        avi.download_image(destination)
        mock_get.assert_called_once_with(
            f"{default_image_domain}.jpg", stream=True, timeout=10
        )
        assert destination.exists()


@mock.patch("aeonview.requests.get")
def test_download_image_failure(mock_get):
    mock_response = mock.Mock()
    mock_response.status_code = 404
    mock_get.return_value = mock_response

    args = argparse.Namespace(simulate=False)
    avi = AeonViewImages(default_test_path, f"{default_image_domain}.jpg", args)
    destination = Path(tempfile.gettempdir(), "image.jpg")

    with expect_error_exit():
        avi.download_image(destination)


def test_download_image_no_url():
    args = argparse.Namespace(simulate=False)
    avi = AeonViewImages(default_test_path, None, args)
    with expect_error_exit():
        avi.download_image(Path(tempfile.gettempdir(), "image.jpg"))


def test_download_image_non_path_destination():
    args = argparse.Namespace(simulate=False)
    avi = AeonViewImages(default_test_path, f"{default_image_domain}.jpg", args)
    with expect_error_exit():
        # noinspection PyTypeChecker
        avi.download_image(
            "/tmp/image.jpg"  # pyright: ignore [reportArgumentType]
        )


def test_download_image_simulate():
    args = argparse.Namespace(simulate=True)
    avi = AeonViewImages(default_test_path, f"{default_image_domain}.jpg", args)
    with mock.patch("aeonview.logging.info") as log:
        avi.download_image(Path(tempfile.gettempdir(), "image.jpg"))
        assert any("Simulate" in str(call) for call in log.call_args_list)


@mock.patch("aeonview.AeonViewHelpers.mkdir_p")
@mock.patch("aeonview.AeonViewImages.download_image")
def test_image_simulation(mock_download_image, mock_mkdir_p):
    args = mock.MagicMock()
    args.simulate = True
    args.date = "2025-04-10 12:30:45"
    avi = AeonViewImages(default_test_path, f"{default_image_domain}.jpg", args)
    with mock.patch("aeonview.logging.info") as log:
        avi.get_current_image()
        mock_mkdir_p.assert_not_called()
        mock_download_image.assert_not_called()
        assert any(
            "Saving image to" in str(call) for call in log.call_args_list
        )


# ---------------------------------------------------------------------------
# AeonViewVideos tests
# ---------------------------------------------------------------------------


@mock.patch("subprocess.run")
def test_generate_daily_video(mock_subprocess_run):
    with tempfile.TemporaryDirectory() as tmp:
        project_path = Path(tmp).resolve()
        args = make_video_args()
        avv = AeonViewVideos(project_path, args)
        # Create input directory so the existence check passes
        (project_path / "img" / "2025-04" / "01").mkdir(parents=True)
        with mock.patch("aeonview.AeonViewHelpers.mkdir_p") as mock_mkdir_p:
            with mock.patch("aeonview.logging.info") as log:
                avv.generate_daily_video()
                last_call_args = log.call_args_list[-1][0]
                assert last_call_args[0] == "%s: %s"
                assert (
                    last_call_args[1]
                    == AeonViewMessages.VIDEO_GENERATION_SUCCESS
                )
                assert last_call_args[2] == (
                    project_path / "vid" / "2025-04" / "01.mp4"
                )
            mock_mkdir_p.assert_called()
    mock_subprocess_run.assert_called()


@mock.patch("aeonview.AeonViewHelpers.mkdir_p")
def test_generate_daily_video_simulate(mock_mkdir_p):
    args = make_video_args(simulate=True)
    avv = AeonViewVideos(default_test_path, args)
    avv.generate_daily_video()
    mock_mkdir_p.assert_not_called()


def test_generate_daily_video_missing_input_dir():
    with tempfile.TemporaryDirectory() as tmp:
        project_path = Path(tmp).resolve()
        args = make_video_args()
        avv = AeonViewVideos(project_path, args)
        with expect_error_exit():
            avv.generate_daily_video()


@mock.patch("aeonview.AeonViewHelpers.mkdir_p")
@mock.patch("subprocess.run")
def test_video_simulation(mock_subprocess_run, mock_mkdir_p):
    args = mock.MagicMock()
    args.simulate = True
    args.fps = 10
    args.day = "01"
    args.month = "01"
    args.year = "2023"
    avv = AeonViewVideos(default_test_path, args)
    with mock.patch("aeonview.logging.info") as log:
        avv.generate_daily_video()
        mock_mkdir_p.assert_not_called()
        mock_subprocess_run.assert_not_called()
        assert any(
            "Generating video from" in str(call) for call in log.call_args_list
        )


# --- Monthly video tests ---


@mock.patch("subprocess.run")
def test_generate_monthly_video(mock_subprocess_run):
    with tempfile.TemporaryDirectory() as tmp:
        project_path = Path(tmp).resolve()
        vid_dir = project_path / "vid" / "2025-04"
        vid_dir.mkdir(parents=True)
        # Create fake daily videos
        for day in ["01", "02", "03"]:
            (vid_dir / f"{day}.mp4").touch()
        args = make_video_args()
        avv = AeonViewVideos(project_path, args)
        avv.generate_monthly_video()
        mock_subprocess_run.assert_called_once()
        call_cmd = mock_subprocess_run.call_args[0][0]
        assert "concat" in call_cmd
        assert str(vid_dir / "2025-04.mp4") == call_cmd[-1]


@mock.patch("subprocess.run")
def test_generate_monthly_video_excludes_output_file(mock_subprocess_run):
    """Verify monthly output file is excluded from inputs on re-runs."""
    captured_content = {}

    def capture_concat(cmd, **_kwargs):
        idx = cmd.index("-i") + 1
        captured_content["text"] = Path(cmd[idx]).read_text(encoding="utf-8")

    mock_subprocess_run.side_effect = capture_concat

    with tempfile.TemporaryDirectory() as tmp:
        project_path = Path(tmp).resolve()
        vid_dir = project_path / "vid" / "2025-04"
        vid_dir.mkdir(parents=True)
        # Create daily videos plus a leftover monthly output
        for day in ["01", "02"]:
            (vid_dir / f"{day}.mp4").touch()
        (vid_dir / "2025-04.mp4").touch()  # leftover from previous run
        args = make_video_args()
        avv = AeonViewVideos(project_path, args)
        avv.generate_monthly_video()
        mock_subprocess_run.assert_called_once()
        content = captured_content["text"]
        assert "2025-04.mp4" not in content
        assert "01.mp4" in content
        assert "02.mp4" in content


def test_generate_monthly_video_simulate():
    with tempfile.TemporaryDirectory() as tmp:
        project_path = Path(tmp).resolve()
        vid_dir = project_path / "vid" / "2025-04"
        vid_dir.mkdir(parents=True)
        (vid_dir / "01.mp4").touch()
        args = make_video_args(simulate=True)
        avv = AeonViewVideos(project_path, args)
        with mock.patch("subprocess.run") as mock_run:
            avv.generate_monthly_video()
            mock_run.assert_not_called()


def test_generate_monthly_video_no_input_dir():
    with tempfile.TemporaryDirectory() as tmp:
        project_path = Path(tmp).resolve()
        # Don't create the vid directory
        args = make_video_args()
        avv = AeonViewVideos(project_path, args)
        with expect_error_exit():
            avv.generate_monthly_video()


def test_generate_monthly_video_no_mp4_files():
    with tempfile.TemporaryDirectory() as tmp:
        project_path = Path(tmp).resolve()
        vid_dir = project_path / "vid" / "2025-04"
        vid_dir.mkdir(parents=True)
        # No mp4 files in directory
        args = make_video_args()
        avv = AeonViewVideos(project_path, args)
        with expect_error_exit():
            avv.generate_monthly_video()


# --- Yearly video tests ---


@mock.patch("subprocess.run")
def test_generate_yearly_video(mock_subprocess_run):
    with tempfile.TemporaryDirectory() as tmp:
        project_path = Path(tmp).resolve()
        # Create monthly video files in their directories
        for month in ["01", "02", "03"]:
            month_dir = project_path / "vid" / f"2025-{month}"
            month_dir.mkdir(parents=True)
            (month_dir / f"2025-{month}.mp4").touch()
        args = make_video_args(month="01", year="2025")
        avv = AeonViewVideos(project_path, args)
        avv.generate_yearly_video()
        mock_subprocess_run.assert_called_once()
        call_cmd = mock_subprocess_run.call_args[0][0]
        assert "concat" in call_cmd
        output_dir = project_path / "vid" / "2025"
        assert str(output_dir / "2025.mp4") == call_cmd[-1]


def test_generate_yearly_video_simulate():
    with tempfile.TemporaryDirectory() as tmp:
        project_path = Path(tmp).resolve()
        month_dir = project_path / "vid" / "2025-01"
        month_dir.mkdir(parents=True)
        (month_dir / "2025-01.mp4").touch()
        args = make_video_args(simulate=True, month="01", year="2025")
        avv = AeonViewVideos(project_path, args)
        with mock.patch("subprocess.run") as mock_run:
            avv.generate_yearly_video()
            mock_run.assert_not_called()


def test_generate_yearly_video_no_monthly_videos():
    with tempfile.TemporaryDirectory() as tmp:
        project_path = Path(tmp).resolve()
        (project_path / "vid").mkdir(parents=True)
        args = make_video_args(month="01", year="2025")
        avv = AeonViewVideos(project_path, args)
        with expect_error_exit():
            avv.generate_yearly_video()


# ---------------------------------------------------------------------------
# Argument parsing tests
# ---------------------------------------------------------------------------


@mock.patch(
    "sys.argv",
    ["aeonview.py", "--mode", "image", "--url", f"{default_image_domain}.jpg"],
)
def test_parse_arguments_image_mode():
    args, _ = AeonViewHelpers.parse_arguments()
    assert args.mode == "image"
    assert args.url == f"{default_image_domain}.jpg"
    assert args.dest == default_dest


@mock.patch(
    "sys.argv",
    ["aeonview.py", "--mode", "video", "--project", f"{default_project}"],
)
def test_parse_arguments_video_mode():
    args, _ = AeonViewHelpers.parse_arguments()
    assert args.mode == "video"
    assert args.project == default_project
    assert args.dest == default_dest


@mock.patch("sys.argv", ["aeonview.py", "--mode", "image", "--simulate"])
def test_parse_arguments_simulate_mode():
    args, _ = AeonViewHelpers.parse_arguments()
    assert args.mode == "image"
    assert args.simulate


@mock.patch("sys.argv", ["aeonview.py", "--mode", "video", "--fps", "30"])
def test_parse_arguments_fps():
    args, _ = AeonViewHelpers.parse_arguments()
    assert args.mode == "video"
    assert args.project == default_project
    assert args.dest == default_dest
    assert args.fps == 30


@mock.patch(
    "sys.argv", ["aeonview.py", "--mode", "video", "--generate", "2023-10-01"]
)
def test_parse_arguments_generate_date():
    args, _ = AeonViewHelpers.parse_arguments()
    assert args.mode == "video"
    assert args.generate == "2023-10-01"


@mock.patch("sys.argv", ["aeonview.py", "--mode", "image", "--verbose"])
def test_parse_arguments_verbose():
    args, _ = AeonViewHelpers.parse_arguments()
    assert args.mode == "image"
    assert args.verbose


@mock.patch("sys.argv", ["aeonview.py"])
def test_parse_arguments_defaults():
    args, _ = AeonViewHelpers.parse_arguments()
    assert args.mode == "image"
    assert args.project == default_project
    assert args.dest == default_dest
    assert args.fps == 10
    assert args.timeframe == "daily"
    assert not args.simulate
    assert not args.verbose


# ---------------------------------------------------------------------------
# Logger tests
# ---------------------------------------------------------------------------


@mock.patch("logging.basicConfig")
def test_setup_logger_verbose(mock_basic_config):
    AeonViewHelpers.setup_logger(verbose=True)
    mock_basic_config.assert_called_once_with(
        level=logging.DEBUG, format="[%(levelname)s] %(message)s"
    )


@mock.patch("logging.basicConfig")
def test_setup_logger_non_verbose(mock_basic_config):
    AeonViewHelpers.setup_logger(verbose=False)
    mock_basic_config.assert_called_once_with(
        level=logging.INFO, format="[%(levelname)s] %(message)s"
    )


# ---------------------------------------------------------------------------
# AeonViewApp tests
# ---------------------------------------------------------------------------


@mock.patch(
    "sys.argv",
    ["aeonview", "--mode", "image", "--url", "https://example.com/image.jpg"],
)
def test_app_init():
    app = AeonViewApp()
    assert app.args.mode == "image"
    assert app.args.url == "https://example.com/image.jpg"


@mock.patch(
    "sys.argv",
    ["aeonview", "--mode", "image", "--url", "https://example.com/image.jpg"],
)
@mock.patch("aeonview.AeonViewApp.process_image")
def test_app_run_image_mode(mock_process):
    app = AeonViewApp()
    app.run()
    mock_process.assert_called_once()


@mock.patch(
    "sys.argv",
    [
        "aeonview",
        "--mode",
        "video",
        "--project",
        "myproj",
    ],
)
@mock.patch("aeonview.AeonViewApp.process_video")
def test_app_run_video_mode(mock_process):
    app = AeonViewApp()
    app.run()
    mock_process.assert_called_once()


@mock.patch(
    "sys.argv",
    [
        "aeonview",
        "--mode",
        "image",
        "--simulate",
        "--url",
        "https://example.com/image.jpg",
    ],
)
def test_app_run_simulate_logs():
    app = AeonViewApp()
    with (
        mock.patch("aeonview.AeonViewApp.process_image"),
        mock.patch("aeonview.logging.info") as log,
    ):
        app.run()
        assert any("Simulation" in str(call) for call in log.call_args_list)


@mock.patch("sys.argv", ["aeonview", "--mode", "image"])
def test_app_process_image_no_url():
    app = AeonViewApp()
    with expect_error_exit():
        app.process_image()


@mock.patch("sys.argv", ["aeonview", "--mode", "image", "--url", "not-http"])
def test_app_process_image_invalid_url():
    app = AeonViewApp()
    with expect_error_exit():
        app.process_image()


@mock.patch(
    "sys.argv",
    ["aeonview", "--mode", "image", "--url", "https://example.com/image.jpg"],
)
@mock.patch("aeonview.AeonViewImages.get_current_image")
def test_app_process_image_default_project_hash(mock_get_image):
    app = AeonViewApp()
    app.process_image()
    mock_get_image.assert_called_once()


@mock.patch(
    "sys.argv",
    [
        "aeonview",
        "--mode",
        "image",
        "--url",
        "https://example.com/image.jpg",
        "--project",
        "myproject",
    ],
)
@mock.patch("aeonview.AeonViewImages.get_current_image")
def test_app_process_image_named_project(mock_get_image):
    app = AeonViewApp()
    app.process_image()
    mock_get_image.assert_called_once()


@mock.patch(
    "sys.argv",
    ["aeonview", "--mode", "video", "--project", ""],
)
def test_app_process_video_no_project():
    app = AeonViewApp()
    app.args.project = ""
    with expect_error_exit():
        app.process_video()


@mock.patch(
    "sys.argv",
    ["aeonview", "--mode", "video", "--project", "nonexistent"],
)
def test_app_process_video_missing_path():
    app = AeonViewApp()
    with expect_error_exit():
        app.process_video()


@mock.patch(
    "sys.argv",
    [
        "aeonview",
        "--mode",
        "video",
        "--project",
        "proj",
        "--generate",
        "2025-04-10",
    ],
)
@mock.patch("aeonview.AeonViewVideos.generate_daily_video")
def test_app_process_video_with_generate_date(mock_gen):
    with tempfile.TemporaryDirectory() as tmp:
        app, _ = make_app_with_project(tmp)
        app.process_video()
        mock_gen.assert_called_once()


@mock.patch(
    "sys.argv",
    ["aeonview", "--mode", "video", "--project", "proj"],
)
@mock.patch("aeonview.AeonViewVideos.generate_daily_video")
def test_app_process_video_default_date(mock_gen):
    with tempfile.TemporaryDirectory() as tmp:
        app, _ = make_app_with_project(tmp)
        app.process_video()
        mock_gen.assert_called_once()


@mock.patch(
    "sys.argv",
    [
        "aeonview",
        "--mode",
        "video",
        "--project",
        "proj",
        "--generate",
        "invalid-date",
    ],
)
def test_app_process_video_invalid_date():
    with tempfile.TemporaryDirectory() as tmp:
        app, _ = make_app_with_project(tmp)
        with expect_error_exit():
            app.process_video()


@mock.patch(
    "sys.argv",
    [
        "aeonview",
        "--mode",
        "video",
        "--project",
        "proj",
        "--timeframe",
        "monthly",
    ],
)
@mock.patch("aeonview.AeonViewVideos.generate_monthly_video")
def test_app_process_video_monthly(mock_gen):
    with tempfile.TemporaryDirectory() as tmp:
        app, _ = make_app_with_project(tmp)
        app.process_video()
        mock_gen.assert_called_once()


@mock.patch(
    "sys.argv",
    [
        "aeonview",
        "--mode",
        "video",
        "--project",
        "proj",
        "--timeframe",
        "yearly",
    ],
)
@mock.patch("aeonview.AeonViewVideos.generate_yearly_video")
def test_app_process_video_yearly(mock_gen):
    with tempfile.TemporaryDirectory() as tmp:
        app, _ = make_app_with_project(tmp)
        app.process_video()
        mock_gen.assert_called_once()


@mock.patch("sys.argv", ["aeonview"])
def test_app_init_no_args():
    with (
        mock.patch(
            "aeonview.AeonViewHelpers.parse_arguments",
            return_value=(None, argparse.ArgumentParser()),
        ),
        pytest.raises(SystemExit),
    ):
        AeonViewApp()


@mock.patch(
    "sys.argv",
    [
        "aeonview",
        "--mode",
        "video",
        "--project",
        "proj",
        "--generate",
        "2025-04-10",
    ],
)
def test_app_process_video_invalid_project_type():
    with tempfile.TemporaryDirectory() as tmp:
        app, _ = make_app_with_project(tmp)
        # noinspection PyTypeChecker
        app.args.project = 12345  # pyright: ignore [reportAttributeAccessIssue]
        with expect_error_exit():
            app.process_video()
