import argparse
import hashlib
import logging
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import requests


# Define messages for logging
# These messages are used for logging purposes and can be customized as needed.
class AeonViewMessages:
    INVALID_URL = 'Invalid URL provided.'
    INVALID_DATE = 'Invalid date format provided.'
    DOWNLOAD_SUCCESS = 'Image downloaded successfully.'
    DOWNLOAD_FAILURE = 'Failed to download image.'
    VIDEO_GENERATION_SUCCESS = 'Video generated successfully.'
    VIDEO_GENERATION_FAILURE = 'Failed to generate video.'
    INVALID_IMAGE_FORMAT = 'Invalid image format provided.'
    INVALID_IMAGE_EXTENSION = 'Invalid image extension provided.'


class AeonViewImages:
    """
    Class to handle image download and saving.

    This class is responsible for downloading images from a URL and saving them
    to a specified directory.
    """

    def __init__(self, project_path: Path, url: str | None, args=None):
        """
        Initialize the AeonViewImages class.
        :param project_path: Path to the project directory
        :param url: URL of the image to download
        :param args: Command line arguments passed to the class
        """
        self.project_path = project_path or None
        self.url = url or None
        self.args = args or {}

    def get_image_paths(
        self, url: str | None, destination_base: Path | None, date: datetime
    ) -> dict:
        """
        Get image paths for saving the downloaded image.
        :param url: URL of the image
        :param destination_base: Base path where the image will be saved
        :param date: Date for which the image is requested
        :return: Image object
        """
        if url is None or not isinstance(url, str):
            logging.error(AeonViewMessages.INVALID_URL)
            sys.exit(1)
        if not isinstance(date, datetime):
            logging.error(AeonViewMessages.INVALID_DATE)
            sys.exit(1)
        if not url.startswith('http'):
            logging.error(AeonViewMessages.INVALID_URL)
            sys.exit(1)
        if not url.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
            logging.error(AeonViewMessages.INVALID_IMAGE_FORMAT)
            sys.exit(1)

        if destination_base is None:
            logging.error('No destination base path provided.')
            sys.exit(1)
        if not isinstance(destination_base, Path):
            logging.error('Invalid destination base path.')
            sys.exit(1)

        year = date.strftime('%Y')
        month = date.strftime('%m')
        day = date.strftime('%d')

        year_month = f'{year}-{month}'

        destination = AeonViewHelpers.build_path(destination_base, year_month, day)
        file_name = date.strftime('%H-%M-%S') + AeonViewHelpers.get_extension(url)
        destination_file = AeonViewHelpers.build_path(destination, file_name)

        if not destination.exists():
            if self.args.simulate:
                logging.info(f'Simulate: would create {destination}')
            else:
                AeonViewHelpers.mkdir_p(destination)
                logging.info(f'Creating destination base path: {destination}')

        return {
            'url': url,
            'file': file_name,
            'date': {
                'year': year,
                'month': month,
                'day': day,
                'hour': date.strftime('%H'),
                'minute': date.strftime('%M'),
                'second': date.strftime('%S'),
            },
            'destinations': {
                'base': destination_base,
                'year_month': year_month,
                'day': day,
                'file': destination_file,
            },
        }

    def get_current_image(self):
        """
        Download the image from the URL and save it to the project directory.
        """

        if self.args.date is not None:
            try:
                date = datetime.strptime(self.args.date, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                logging.error(AeonViewMessages.INVALID_DATE)
                sys.exit(1)
        else:
            date = datetime.now()

        img_path = date.strftime('img/%Y-%m/%d')
        img_name = date.strftime('%H-%M-%S')

        if self.url is None:
            logging.error(AeonViewMessages.INVALID_URL)
            sys.exit(1)

        file_ext = AeonViewHelpers.get_extension(self.url)

        dest_dir = AeonViewHelpers.build_path(self.project_path, img_path)
        dest_file = AeonViewHelpers.build_path(dest_dir, f'{img_name}{file_ext}')

        logging.info(f'Saving image to {dest_file}')

        if not self.args.simulate:
            AeonViewHelpers.mkdir_p(dest_dir)
            self.download_image(dest_file)
        else:
            logging.info(f'Simulate: would create {dest_dir}')
            logging.info(f'Simulate: would download {self.url} to {dest_file}')

    def download_image(self, destination: Path):
        """
        Download the image using Python's requests library.
        :param destination: Path where the image will be saved
        :return: None
        """

        if self.url is None:
            logging.error(AeonViewMessages.INVALID_URL)
            sys.exit(1)

        if not isinstance(destination, Path):
            logging.error('Invalid destination path.')
            sys.exit(1)

        if self.args.simulate is False or self.args.simulate is None:
            logging.info(f'Downloading image from {self.url}')
            response = requests.get(self.url, stream=True)
            if response.status_code == 200:
                with open(destination, 'wb') as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)
                logging.info(f'{AeonViewMessages.DOWNLOAD_SUCCESS}: {destination}')
            else:
                logging.error(f'{AeonViewMessages.DOWNLOAD_FAILURE}: {self.url}')
                sys.exit(1)
        else:
            logging.info(f'Simulate: would download {self.url} to {destination}')


class AeonViewVideos:
    """
    Class to handle video generation and management.

    This class is responsible for generating daily, monthly, and yearly videos.
    It uses ffmpeg for video processing.
    """

    def __init__(self, project_path: Path, args=None):
        """
        Initialize the AeonViewVideos class.
        :param project_path: Path to the project directory
        :param args: Command line arguments passed to the class
        """
        self.project_path = project_path
        self.args = args or {}

        self.args.simulate = args.simulate or False
        self.args.fps = args.fps or 10

        self.day = args.day or None
        self.month = args.month or None
        self.year = args.year or None

        self.path_images = AeonViewHelpers.build_path(self.project_path, 'img')
        self.path_videos = AeonViewHelpers.build_path(self.project_path, 'vid')

    def generate_daily_video(self):
        """
        Generate a daily video from images.
        """

        year_month = f'{self.year}-{self.month}'

        input_dir = AeonViewHelpers.build_path(self.path_videos, year_month, self.day)
        output_dir = AeonViewHelpers.build_path(self.path_videos, year_month)
        output_file = AeonViewHelpers.build_path(output_dir, f'{self.day}.mp4')
        ffmpeg_cmd = AeonViewHelpers.generate_ffmpeg_command(input_dir, output_file, self.args.fps)

        logging.info(f'Generating video from {input_dir}')
        logging.info(f'Output file will be {output_file}')

        if not self.args.simulate:
            logging.info(f'Running ffmpeg command: {" ".join(ffmpeg_cmd)}')
            if not os.path.exists(input_dir):
                AeonViewHelpers.mkdir_p(output_dir)
            subprocess.run(ffmpeg_cmd, check=True)
            logging.info(f'{AeonViewMessages.VIDEO_GENERATION_SUCCESS}: {output_file}')
        else:
            logging.info(f'Simulate: would run {" ".join(ffmpeg_cmd)}')

    def generate_monthly_video(self, output_dir: Path):
        """
        Generate a monthly video from images.
        :param output_dir: Directory where the video will be saved
        :return: None
        """
        raise NotImplementedError('Monthly video generation is not implemented.')

    def generate_yearly_video(self, output_dir: Path):
        """
        Generate a yearly video from images.
        :param output_dir: Directory where the video will be saved
        :return: None
        """
        raise NotImplementedError('Yearly video generation is not implemented.')


class AeonViewHelpers:
    """
    Helper class for common operations.
    """

    @staticmethod
    def check_date(year: int, month: int, day: int) -> bool:
        """
        Check if the given year, month, and day form a valid date.
        :param year: Year to check
        :param month: Month to check
        :param day: Day to check
        :return: True if valid date, False otherwise
        """
        try:
            date = datetime(year, month, day)
            return date.year == year and date.month == month and date.day == day
        except ValueError:
            return False

    @staticmethod
    def mkdir_p(path: Path):
        """
        Create a directory and all parent directories if they do not exist.
        :param path: Path to the directory to create
        :return: None
        """
        path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def build_path(base: Path, *args) -> Path:
        """
        Build a path from the base and additional arguments.
        :param base: Base path
        :param args: Parts of the path to join
        :return: Structured and resolved path
        """
        return Path(base).joinpath(*args or []).resolve()

    @staticmethod
    def parse_arguments():
        """Parse command line arguments."""

        dest_default = str(Path.cwd() / 'projects')

        parser = argparse.ArgumentParser(description='aeonview - timelapse generator using ffmpeg')
        parser.add_argument('--mode', choices=['image', 'video'], default='image', help='Run mode')
        parser.add_argument('--project', help='Project name', default='default')
        parser.add_argument('--dest', default=dest_default, help='Destination root path')
        parser.add_argument('--url', help='Webcam URL (required in image mode)')
        parser.add_argument('--fps', type=int, default=10, help='Frames per second')
        parser.add_argument('--generate', help='Date for video generation (YYYY-MM-DD)')
        parser.add_argument('--timeframe', choices=['daily', 'monthly', 'yearly'], default='daily')
        parser.add_argument(
            '--simulate', action='store_true', help='Simulation mode', default=False
        )
        parser.add_argument('--verbose', action='store_true', help='Verbose output', default=False)
        args = parser.parse_args()
        return args, parser

    @staticmethod
    def get_extension(url: str | None) -> str | None:
        """
        Get the file extension from the URL.
        :return: File extension
        """
        if url is None:
            logging.error(AeonViewMessages.INVALID_IMAGE_EXTENSION)
            return None

        if url.endswith('.png'):
            return '.png'
        elif url.endswith('.gif'):
            return '.gif'
        elif url.endswith('.webp'):
            return '.webp'
        else:
            return '.jpg'

    @staticmethod
    def setup_logger(verbose: bool):
        """
        Set up the logger for the application.
        :param verbose: Enable verbose logging if True
        :return: None
        """
        level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(level=level, format='[%(levelname)s] %(message)s')

    @staticmethod
    def generate_ffmpeg_command(input_dir: Path, output_file: Path, fps: int = 10) -> list:
        """
        Generate the ffmpeg command to create a video from images.
        :param input_dir: Directory containing the images
        :param output_file: Path to the output video file
        :param fps: Frames per second for the video
        :return: Newly created ffmpeg command as a list
        """
        return [
            'ffmpeg',
            '-framerate',
            str(fps),
            '-pattern_type',
            'glob',
            '-i',
            str(input_dir / '*.{jpg,jpeg,png,gif,webp}'),
            '-c:v',
            'libx264',
            '-pix_fmt',
            'yuv420p',
            str(output_file),
        ]


class AeonViewApp:
    """
    Main application class for AeonView.
    """

    def __init__(self):
        self.args, self.parser = AeonViewHelpers.parse_arguments()
        AeonViewHelpers.setup_logger(self.args.verbose)
        self.base_path = Path(self.args.dest).resolve()

    def run(self):
        """
        Execute the application based on the provided arguments.
        """
        if self.args.simulate:
            logging.info('Simulation mode active. No actions will be executed.')

        if self.args.mode == 'image':
            self.process_image()
        elif self.args.mode == 'video':
            self.process_video()

    def process_image(self):
        """
        Process image download and saving based on the provided arguments.
        """
        if not self.args.url or self.args.url is None:
            logging.error('--url is required in image mode')
            self.parser.print_help()
            sys.exit(1)

        if not isinstance(self.args.url, str) or not self.args.url.startswith('http'):
            logging.error(f'{AeonViewMessages.INVALID_URL}: {self.args.url}')
            sys.exit(1)

        url = self.args.url
        project = self.args.project or 'default'

        if project == 'default' and url:
            project = hashlib.md5(url.encode()).hexdigest()[:5]

        project_path = AeonViewHelpers.build_path(self.base_path, project)
        avi = AeonViewImages(project_path, url, self.args)
        avi.get_current_image()

    def process_video(self):
        """
        Process video generation based on the provided arguments.
        """
        if not self.args.project:
            logging.error('--project is required in video mode')
            self.parser.print_help()
            sys.exit(1)

        if not isinstance(self.args.project, str):
            logging.error(f'Invalid project name: {self.args.project}')
            sys.exit(1)

        project_path = AeonViewHelpers.build_path(self.base_path, self.args.project)

        if not os.path.exists(project_path):
            logging.error(f'Project path {project_path} does not exist.')
            sys.exit(1)

        try:
            generate_date = (
                datetime.strptime(self.args.generate, '%Y-%m-%d')
                if self.args.generate
                else datetime.today() - timedelta(days=1)
            )
        except ValueError:
            logging.error(AeonViewMessages.INVALID_DATE)
            sys.exit(1)

        year = generate_date.strftime('%Y')
        month = generate_date.strftime('%m')
        day = generate_date.strftime('%d')

        self.args.day = day
        self.args.month = month
        self.args.year = year

        if not AeonViewHelpers.check_date(int(year), int(month), int(day)):
            logging.error(f'Invalid date: {year}-{month}-{day}')
            sys.exit(1)

        avm = AeonViewVideos(project_path, self.args)

        if self.args.timeframe == 'daily':
            avm.generate_daily_video()
        elif self.args.timeframe == 'monthly':
            output_dir = AeonViewHelpers.build_path(project_path, 'vid', f'{year}-{month}')
            avm.generate_monthly_video(output_dir)
        elif self.args.timeframe == 'yearly':
            output_dir = AeonViewHelpers.build_path(project_path, 'vid', year)
            avm.generate_yearly_video(output_dir)


if __name__ == '__main__':
    app = AeonViewApp()
    app.run()

# vim: set tw=100 fo=cqt wm=0 et:
