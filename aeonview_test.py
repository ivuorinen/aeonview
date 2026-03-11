# vim: set ft=python ts=4 sw=4 sts=4 et wrap:
import argparse
import logging
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from unittest import mock

import pytest

from aeonview import (
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
    with pytest.raises(SystemExit), mock.patch("aeonview.logging.error"):
        aeon_view_images = AeonViewImages(default_test_path, "invalid-url")
        aeon_view_images.get_image_paths(
            "invalid-url", default_test_path, datetime(2025, 4, 10)
        )


def test_get_image_paths_invalid_date():
    with pytest.raises(SystemExit), mock.patch("aeonview.logging.error"):
        aeon_view_images = AeonViewImages(
            default_test_path, f"{default_image_domain}.jpg"
        )
        # noinspection PyTypeChecker
        aeon_view_images.get_image_paths(
            f"{default_image_domain}.jpg",
            default_test_path,
            "invalid-date",  # pyright: ignore [reportArgumentType]
        )


@mock.patch("aeonview.AeonViewHelpers.mkdir_p")
@mock.patch("aeonview.AeonViewImages.download_image")
def test_get_current_image(mock_download_image, mock_mkdir_p):
    args = argparse.Namespace(simulate=False, date="2025-04-10 12:30:45")
    avi = AeonViewImages(default_test_path, f"{default_image_domain}.jpg", args)
    avi.get_current_image()
    mock_mkdir_p.assert_called()
    mock_download_image.assert_called()


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

    with pytest.raises(SystemExit), mock.patch("aeonview.logging.error"):
        avi.download_image(destination)


@mock.patch("subprocess.run")
def test_generate_daily_video(mock_subprocess_run):
    with tempfile.TemporaryDirectory() as tmp:
        project_path = Path(tmp).resolve()
        args = argparse.Namespace(
            simulate=False, fps=10, day="01", month="04", year="2025"
        )
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
    args = argparse.Namespace(
        simulate=True, fps=10, day="01", month="04", year="2025"
    )
    avv = AeonViewVideos(default_test_path, args)
    avv.generate_daily_video()
    mock_mkdir_p.assert_not_called()


def test_generate_monthly_video_not_implemented():
    args = argparse.Namespace(
        simulate=False, fps=10, day="01", month="04", year="2025"
    )
    avv = AeonViewVideos(default_test_path, args)
    with pytest.raises(NotImplementedError):
        avv.generate_monthly_video(Path(tempfile.gettempdir()))


def test_generate_yearly_video_not_implemented():
    args = argparse.Namespace(
        simulate=False, fps=10, day="01", month="04", year="2025"
    )
    avv = AeonViewVideos(default_test_path, args)
    with pytest.raises(NotImplementedError):
        avv.generate_yearly_video(Path(tempfile.gettempdir()))


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