"""aeonview - Timelapse generator using ffmpeg.

Downloads webcam images on a schedule and generates daily, monthly, and yearly
timelapse videos by stitching frames together with ffmpeg.
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import requests


class AeonViewMessages:
    """Constant log messages used throughout the application."""

    INVALID_URL = "Invalid URL provided."
    INVALID_DATE = "Invalid date format provided."
    DOWNLOAD_SUCCESS = "Image downloaded successfully."
    DOWNLOAD_FAILURE = "Failed to download image."
    VIDEO_GENERATION_SUCCESS = "Video generated successfully."
    VIDEO_GENERATION_FAILURE = "Failed to generate video."
    INVALID_IMAGE_FORMAT = "Invalid image format provided."
    INVALID_IMAGE_EXTENSION = "Invalid image extension provided."


class AeonViewImages:
    """Handle image download and saving.

    Downloads images from a webcam URL and saves them into a date-based
    directory structure under the project path.
    """

    def __init__(self, project_path: Path, url: str | None, args=None):
        """Initialize the AeonViewImages class.

        :param project_path: Path to the project directory.
        :param url: URL of the image to download.
        :param args: Command-line arguments passed to the class.
        """
        self.project_path = project_path
        self.url = url or None
        self.args = args or {}
        self.simulate = getattr(args, "simulate", False)

    def get_image_paths(
        self,
        url: str | None,
        destination_base: Path | None,
        date: datetime | None,
    ) -> dict:
        """Compute image paths for saving the downloaded image.

        :param url: URL of the image.
        :param destination_base: Base path where the image will be saved.
        :param date: Date for which the image is requested.
        :return: Dictionary with url, file, date, and destinations info.
        :raises SystemExit: If any parameter is invalid.
        """
        if url is None or not isinstance(url, str):
            logging.error(AeonViewMessages.INVALID_URL)
            sys.exit(1)
        if not isinstance(date, datetime):
            logging.error(AeonViewMessages.INVALID_DATE)
            sys.exit(1)
        if not url.startswith("http"):
            logging.error(AeonViewMessages.INVALID_URL)
            sys.exit(1)
        if not url.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp")):
            logging.error(AeonViewMessages.INVALID_IMAGE_FORMAT)
            sys.exit(1)

        if destination_base is None:
            logging.error("No destination base path provided.")
            sys.exit(1)
        if not isinstance(destination_base, Path):
            logging.error("Invalid destination base path.")
            sys.exit(1)

        year = date.strftime("%Y")
        month = date.strftime("%m")
        day = date.strftime("%d")

        year_month = f"{year}-{month}"

        destination = AeonViewHelpers.build_path(
            destination_base, year_month, day
        )
        extension = AeonViewHelpers.get_extension(url) or ""
        file_name = date.strftime("%H-%M-%S") + extension
        destination_file = AeonViewHelpers.build_path(destination, file_name)

        if self.simulate:
            logging.info("Simulate: would create %s", destination)
        else:
            AeonViewHelpers.mkdir_p(destination)
            logging.info("Creating destination base path: %s", destination)

        return {
            "url": url,
            "file": file_name,
            "date": {
                "year": year,
                "month": month,
                "day": day,
                "hour": date.strftime("%H"),
                "minute": date.strftime("%M"),
                "second": date.strftime("%S"),
            },
            "destinations": {
                "base": destination_base,
                "year_month": year_month,
                "day": day,
                "file": destination_file,
            },
        }

    def get_current_image(self):
        """Download the image from the URL and save it to the project directory.

        :raises SystemExit: If the URL is missing or the date format is invalid.
        """

        date_param = getattr(self.args, "date", None)

        if date_param is not None:
            try:
                date = datetime.strptime(date_param, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                logging.error(AeonViewMessages.INVALID_DATE)
                sys.exit(1)
        else:
            date = datetime.now()

        img_path = date.strftime("img/%Y-%m/%d")
        img_name = date.strftime("%H-%M-%S")

        if self.url is None:
            logging.error(AeonViewMessages.INVALID_URL)
            sys.exit(1)

        file_ext = AeonViewHelpers.get_extension(self.url)

        dest_dir = AeonViewHelpers.build_path(self.project_path, img_path)
        dest_file = AeonViewHelpers.build_path(
            dest_dir, f"{img_name}{file_ext}"
        )

        logging.info("Saving image to %s", dest_file)

        if not self.simulate:
            AeonViewHelpers.mkdir_p(dest_dir)
            self.download_image(dest_file)
        else:
            logging.info("Simulate: would create %s", dest_dir)
            logging.info(
                "Simulate: would download %s to %s", self.url, dest_file
            )

    def download_image(self, destination: Path | str):
        """Download the image using Python's requests library.

        :param destination: Path where the image will be saved.
        :raises SystemExit: If the URL is missing, destination is not a Path,
            or the HTTP request fails.
        """

        if self.url is None:
            logging.error(AeonViewMessages.INVALID_URL)
            sys.exit(1)

        if not isinstance(destination, Path):
            logging.error("Invalid destination path.")
            sys.exit(1)

        if not self.simulate:
            logging.info("Downloading image from %s", self.url)
            response = requests.get(self.url, stream=True, timeout=10)
            if response.status_code == 200:
                with open(destination, "wb") as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)
                logging.info(
                    "%s: %s", AeonViewMessages.DOWNLOAD_SUCCESS, destination
                )
            else:
                logging.error(
                    "%s: %s", AeonViewMessages.DOWNLOAD_FAILURE, self.url
                )
                sys.exit(1)
        else:
            logging.info(
                "Simulate: would download %s to %s", self.url, destination
            )


class AeonViewVideos:
    """Handle video generation and management.

    Generates daily timelapse videos from images, then concatenates daily
    videos into monthly and yearly compilations using ffmpeg.
    """

    def __init__(
        self, project_path: Path, args: argparse.Namespace | None = None
    ):
        """Initialize the AeonViewVideos class.

        :param project_path: Path to the project directory.
        :param args: Command-line arguments passed to the class.
        """
        self.project_path = project_path
        self.args = args

        self.simulate = getattr(args, "simulate", False)
        self.fps = getattr(args, "fps", 10)
        self.day = getattr(args, "day", None)
        self.month = getattr(args, "month", None)
        self.year = getattr(args, "year", None)

        self.path_images = AeonViewHelpers.build_path(self.project_path, "img")
        self.path_videos = AeonViewHelpers.build_path(self.project_path, "vid")

    def generate_daily_video(self):
        """Generate a daily timelapse video from images.

        :raises SystemExit: If the input image directory does not exist.
        """

        year_month = f"{self.year}-{self.month}"

        input_dir = AeonViewHelpers.build_path(
            self.path_images, year_month, self.day
        )
        output_dir = AeonViewHelpers.build_path(self.path_videos, year_month)
        output_file = AeonViewHelpers.build_path(output_dir, f"{self.day}.mp4")
        ffmpeg_cmd = AeonViewHelpers.generate_ffmpeg_command(
            input_dir, output_file, self.fps
        )

        logging.info("Generating video from %s", input_dir)
        logging.info("Output file will be %s", output_file)

        if not self.simulate:
            logging.info("Running ffmpeg command: %s", " ".join(ffmpeg_cmd))
            if not input_dir.exists():
                logging.error("Input directory %s does not exist", input_dir)
                sys.exit(1)
            AeonViewHelpers.mkdir_p(output_dir)
            subprocess.run(ffmpeg_cmd, check=True)
            logging.info(
                "%s: %s", AeonViewMessages.VIDEO_GENERATION_SUCCESS, output_file
            )
        else:
            logging.info("Simulate: would run %s", " ".join(ffmpeg_cmd))

    def generate_monthly_video(self):
        """Generate a monthly video by concatenating daily videos.

        Discovers daily ``.mp4`` files in ``vid/YYYY-MM/`` and concatenates
        them, excluding the monthly output file itself to avoid corruption
        on re-runs.

        :raises SystemExit: If the input directory is missing or contains
            no daily videos.
        """
        year_month = f"{self.year}-{self.month}"
        output_dir = AeonViewHelpers.build_path(self.path_videos, year_month)
        output_file = AeonViewHelpers.build_path(
            output_dir, f"{year_month}.mp4"
        )

        if not output_dir.exists():
            logging.error("Input directory %s does not exist", output_dir)
            sys.exit(1)

        daily_videos = sorted(
            f for f in output_dir.glob("*.mp4") if f != output_file
        )
        if not daily_videos:
            logging.error("No daily videos found in %s", output_dir)
            sys.exit(1)

        self._concatenate_videos(
            f"monthly video for {year_month}", daily_videos, output_file
        )

    def generate_yearly_video(self):
        """Generate a yearly video by concatenating monthly videos.

        Discovers monthly ``.mp4`` files across ``vid/YYYY-*/`` directories
        and concatenates them into a single yearly video.

        :raises SystemExit: If no monthly videos are found for the year.
        """
        year = self.year
        output_dir = AeonViewHelpers.build_path(self.path_videos, year)
        output_file = AeonViewHelpers.build_path(output_dir, f"{year}.mp4")

        monthly_videos = sorted(self.path_videos.glob(f"{year}-*/{year}-*.mp4"))

        if not monthly_videos:
            logging.error("No monthly videos found for year %s", year)
            sys.exit(1)

        self._concatenate_videos(
            f"yearly video for {year}", monthly_videos, output_file
        )

    def _concatenate_videos(
        self, label: str, input_videos: list[Path], output_file: Path
    ) -> None:
        """Concatenate video files into one using ffmpeg concat.

        :param label: Human-readable label for log messages
            (e.g. "monthly video for 2025-04").
        :param input_videos: Paths of input videos to concatenate.
        :param output_file: Path for the resulting video.
        """
        logging.info("Generating %s", label)
        logging.info("Output file will be %s", output_file)

        if not self.simulate:
            AeonViewHelpers.mkdir_p(output_file.parent)
            cmd, concat_file = AeonViewHelpers.generate_concat_command(
                input_videos, output_file
            )
            logging.info("Running ffmpeg command: %s", " ".join(cmd))
            try:
                subprocess.run(cmd, check=True)
                logging.info(
                    "%s: %s",
                    AeonViewMessages.VIDEO_GENERATION_SUCCESS,
                    output_file,
                )
            finally:
                concat_file.unlink(missing_ok=True)
        else:
            logging.info(
                "Simulate: would concatenate %d videos into %s",
                len(input_videos),
                output_file,
            )


class AeonViewHelpers:
    """Utility methods for paths, argument parsing, and ffmpeg."""

    @staticmethod
    def check_date(year: int, month: int, day: int) -> bool:
        """Check if the given year, month, and day form a valid date.

        :param year: Year to check.
        :param month: Month to check.
        :param day: Day to check.
        :return: True if valid date, False otherwise.
        """
        try:
            date = datetime(year, month, day)
            return date.year == year and date.month == month and date.day == day
        except ValueError:
            return False

    @staticmethod
    def mkdir_p(path: Path):
        """Create a directory and all parent directories if they do not exist.

        :param path: Path to the directory to create.
        """
        path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def build_path(base: Path, *args) -> Path:
        """Build a path from the base and additional arguments.

        :param base: Base path.
        :param args: Parts of the path to join.
        :return: Structured and resolved path.
        """
        return Path(base).joinpath(*args or []).resolve()

    @staticmethod
    def parse_arguments():
        """Parse command-line arguments.

        :return: Tuple of (parsed Namespace, ArgumentParser instance).
        """

        dest_default = str(Path.cwd() / "projects")

        parser = argparse.ArgumentParser(
            description="aeonview - timelapse generator using ffmpeg"
        )
        parser.add_argument(
            "--mode",
            choices=["image", "video"],
            default="image",
            help="Run mode",
        )
        parser.add_argument("--project", help="Project name", default="default")
        parser.add_argument(
            "--dest", default=dest_default, help="Destination root path"
        )
        parser.add_argument("--url", help="Webcam URL (required in image mode)")
        parser.add_argument(
            "--fps", type=int, default=10, help="Frames per second"
        )
        parser.add_argument(
            "--generate", help="Date for video generation (YYYY-MM-DD)"
        )
        parser.add_argument(
            "--timeframe",
            choices=["daily", "monthly", "yearly"],
            default="daily",
        )
        parser.add_argument(
            "--simulate",
            action="store_true",
            help="Simulation mode",
            default=False,
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Verbose output",
            default=False,
        )
        args = parser.parse_args()
        return args, parser

    @staticmethod
    def get_extension(url: str | None) -> str | None:
        """Get the file extension from the URL.

        :param url: URL to extract the extension from.
        :return: File extension string, or None if url is None.
        """
        if url is None:
            logging.error(AeonViewMessages.INVALID_IMAGE_EXTENSION)
            return None

        url_lower = url.lower()
        if url_lower.endswith(".jpeg"):
            return ".jpeg"
        if url_lower.endswith(".png"):
            return ".png"
        if url_lower.endswith(".gif"):
            return ".gif"
        if url_lower.endswith(".webp"):
            return ".webp"

        return ".jpg"

    @staticmethod
    def setup_logger(verbose: bool):
        """Set up the logger for the application.

        :param verbose: Enable verbose logging if True.
        """
        level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(level=level, format="[%(levelname)s] %(message)s")

    @staticmethod
    def generate_ffmpeg_command(
        input_dir: Path, output_file: Path, fps: int = 10
    ) -> list:
        """Generate the ffmpeg command to create a video from images.

        :param input_dir: Directory containing the images.
        :param output_file: Path to the output video file.
        :param fps: Frames per second for the video.
        :return: ffmpeg command as a list of strings.
        """
        return [
            "ffmpeg",
            "-y",
            "-framerate",
            str(fps),
            "-pattern_type",
            "glob",
            "-i",
            str(input_dir / "*.{jpg,jpeg,png,gif,webp}"),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(output_file),
        ]

    @staticmethod
    def generate_concat_command(
        input_files: list[Path], output_file: Path
    ) -> tuple[list[str], Path]:
        """Generate an ffmpeg concat demuxer command for joining video files.

        :param input_files: List of input video file paths.
        :param output_file: Path to the output video file.
        :return: Tuple of (command list, temp concat file path).
        """
        concat_list = tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False
        )
        for f in input_files:
            concat_list.write(f"file '{f}'\n")
        concat_list.close()

        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            concat_list.name,
            "-c",
            "copy",
            str(output_file),
        ]
        return cmd, Path(concat_list.name)


class AeonViewApp:
    """Main application class for AeonView.

    Parses arguments and dispatches to image download or video generation
    workflows based on the selected mode.
    """

    def __init__(self):
        args, parser = AeonViewHelpers.parse_arguments()
        self.args: argparse.Namespace = args
        self.parser: argparse.ArgumentParser = parser

        if self.args is None:
            logging.error("No arguments provided.")
            self.parser.print_help()
            sys.exit(1)

        AeonViewHelpers.setup_logger(self.args.verbose)
        self.base_path = Path(self.args.dest).resolve()

    def run(self):
        """Execute the application based on the provided arguments."""
        if self.args.simulate:
            logging.info("Simulation mode active. No actions will be executed.")

        if self.args.mode == "image":
            self.process_image()
        elif self.args.mode == "video":
            self.process_video()

    def process_image(self):
        """Process image download and saving based on the provided arguments.

        :raises SystemExit: If the URL is missing or invalid.
        """
        if not self.args.url or self.args.url is None:
            logging.error("--url is required in image mode")
            self.parser.print_help()
            sys.exit(1)

        if not isinstance(self.args.url, str) or not self.args.url.startswith(
            "http"
        ):
            logging.error("%s: %s", AeonViewMessages.INVALID_URL, self.args.url)
            sys.exit(1)

        url = self.args.url
        project = self.args.project or "default"

        if project == "default" and url:
            project = hashlib.md5(url.encode()).hexdigest()[:5]

        project_path = AeonViewHelpers.build_path(self.base_path, project)
        avi = AeonViewImages(project_path, url, self.args)
        avi.get_current_image()

    def process_video(self):
        """Process video generation based on the provided arguments.

        :raises SystemExit: If the project is missing, invalid, or the
            generate date cannot be parsed.
        """
        if not self.args.project:
            logging.error("--project is required in video mode")
            self.parser.print_help()
            sys.exit(1)

        if not isinstance(self.args.project, str):
            logging.error("Invalid project name: %s", self.args.project)
            sys.exit(1)

        project_path = AeonViewHelpers.build_path(
            self.base_path, self.args.project
        )

        if not project_path.exists():
            logging.error("Project path %s does not exist.", project_path)
            sys.exit(1)

        generate_date = None

        try:
            generate_date = (
                datetime.strptime(self.args.generate, "%Y-%m-%d")
                if self.args.generate
                else datetime.today() - timedelta(days=1)
            )
        except ValueError:
            logging.error(AeonViewMessages.INVALID_DATE)
            sys.exit(1)

        year = generate_date.strftime("%Y")
        month = generate_date.strftime("%m")
        day = generate_date.strftime("%d")

        self.args.day = day
        self.args.month = month
        self.args.year = year

        args: argparse.Namespace = self.args

        avm = AeonViewVideos(project_path, args)

        if self.args.timeframe == "daily":
            avm.generate_daily_video()
        elif self.args.timeframe == "monthly":
            avm.generate_monthly_video()
        elif self.args.timeframe == "yearly":
            avm.generate_yearly_video()


if __name__ == "__main__":  # pragma: no cover
    app = AeonViewApp()
    app.run()

# vim: set tw=100 fo=cqt wm=0 et:
