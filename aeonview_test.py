import argparse
import logging
import subprocess
import tempfile
from pathlib import Path
from unittest import TestCase, mock
from datetime import datetime

import pytest

from aeonview import AeonViewHelpers, AeonViewImages, AeonViewVideos, AeonViewMessages

# Define values used in the tests
default_dest = str(Path.cwd() / 'projects')
default_project = 'default'
default_fps = 10
default_timeframe = 'daily'
default_simulate = False
default_verbose = False
default_image_domain = 'https://example.com/image'
default_test_path = Path('/tmp/test_project').resolve()


# Define the Helpers class with methods to be tested
class TestHelpers(TestCase):
    def test_check_date_valid(self):
        self.assertTrue(AeonViewHelpers.check_date(2023, 12, 31))

    def test_check_date_invalid(self):
        self.assertFalse(AeonViewHelpers.check_date(2023, 2, 30))

    def test_mkdir_p_creates_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            test_path = Path(tmp) / 'a' / 'b' / 'c'
            AeonViewHelpers.mkdir_p(test_path)
            self.assertTrue(test_path.exists())
            self.assertTrue(test_path.is_dir())

    def test_get_extension_valid(self):
        self.assertEqual(AeonViewHelpers.get_extension(f'{default_image_domain}.png'), '.png')
        self.assertEqual(AeonViewHelpers.get_extension(f'{default_image_domain}.jpg'), '.jpg')
        self.assertEqual(AeonViewHelpers.get_extension(f'{default_image_domain}.gif'), '.gif')
        self.assertEqual(AeonViewHelpers.get_extension(f'{default_image_domain}.webp'), '.webp')

    def test_get_extension_invalid(self):
        self.assertEqual(
            AeonViewHelpers.get_extension(default_image_domain), '.jpg'
        )  # Default behavior
        self.assertIsNone(AeonViewHelpers.get_extension(None))


class TestFFmpegCommand(TestCase):
    def test_generate_ffmpeg_command(self):
        input_dir = Path('/tmp/images')
        output_file = Path('/tmp/output.mp4')
        fps = 24
        cmd = AeonViewHelpers.generate_ffmpeg_command(input_dir, output_file, fps)
        self.assertIn('ffmpeg', cmd[0])
        self.assertIn(str(fps), cmd)
        self.assertEqual(str(output_file), cmd[-1])
        self.assertIn(str(input_dir / '*.{jpg,jpeg,png,gif,webp}'), cmd)

    def test_generate_ffmpeg_command_output_format(self):
        input_dir = Path('/tmp/images')
        output_file = Path('/tmp/video.mp4')
        cmd = AeonViewHelpers.generate_ffmpeg_command(input_dir, output_file, 30)
        self.assertIn('/tmp/images/*.{jpg,jpeg,png,gif,webp}', cmd)
        self.assertIn('/tmp/video.mp4', cmd)
        self.assertIn('-c:v', cmd)
        self.assertIn('libx264', cmd)
        self.assertIn('-pix_fmt', cmd)
        self.assertIn('yuv420p', cmd)

    @mock.patch('subprocess.run')
    def test_simulate_ffmpeg_call(self, mock_run):
        input_dir = Path('/tmp/images')
        output_file = Path('/tmp/out.mp4')
        cmd = AeonViewHelpers.generate_ffmpeg_command(input_dir, output_file, 10)
        subprocess.run(cmd)
        mock_run.assert_called_once_with(cmd)


class TestAeonViewImages(TestCase):
    def setUp(self):
        self.args = argparse.Namespace()
        self.args.simulate = False
        self.args.date = '2025-04-10 12:30:45'
        self.args.url = f'{default_image_domain}.jpg'
        self.args.dest = default_test_path
        self.args.project = default_project
        self.args.verbose = default_verbose
        self.args.fps = default_fps
        self.args.timeframe = default_timeframe
        self.project_path = default_test_path
        self.url = f'{default_image_domain}.jpg'

    def test_get_image_paths_valid(self):
        url = f'{default_image_domain}.jpg'
        destination_base = default_test_path
        date = datetime(2025, 4, 10, 12, 30, 45)
        paths = AeonViewImages.get_image_paths(self, url, destination_base, date)
        self.assertEqual(paths['url'], url)
        self.assertEqual(paths['file'], '12-30-45.jpg')
        self.assertEqual(
            paths['destinations']['file'], destination_base / '2025-04' / '10' / '12-30-45.jpg'
        )

    def test_get_image_paths_invalid_url(self):
        with pytest.raises(SystemExit):
            with self.assertLogs(level='ERROR') as log:
                AeonViewImages.get_image_paths(
                    self, 'invalid-url', default_test_path, datetime(2025, 4, 10)
                )
                self.assertIn(AeonViewMessages.INVALID_URL, log.output[0])

    def test_get_image_paths_invalid_date(self):
        with pytest.raises(SystemExit):
            with self.assertLogs(level='ERROR') as log:
                AeonViewImages.get_image_paths(
                    self, f'{default_image_domain}.jpg', default_test_path, 'invalid-date'
                )
                self.assertIn(AeonViewMessages.INVALID_DATE, log.output[0])

    @mock.patch('aeonview.AeonViewHelpers.mkdir_p')
    @mock.patch('aeonview.AeonViewImages.download_image')
    def test_get_current_image(self, mock_download_image, mock_mkdir_p):
        project_path = default_test_path
        url = f'{default_image_domain}.jpg'
        args = argparse.Namespace(simulate=False, date='2025-04-10 12:30:45')
        avi = AeonViewImages(project_path, url, args)
        avi.get_current_image()
        mock_mkdir_p.assert_called()
        mock_download_image.assert_called()

    @mock.patch('aeonview.requests.get')
    def test_download_image_success(self, mock_get):
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.iter_content = mock.Mock(return_value=[b'data'])
        mock_get.return_value = mock_response

        project_path = default_test_path
        url = f'{default_image_domain}.jpg'
        args = argparse.Namespace(simulate=False)
        avi = AeonViewImages(project_path, url, args)
        destination = Path('/tmp/image.jpg')
        avi.download_image(destination)

        mock_get.assert_called_once_with(url, stream=True)
        self.assertTrue(destination.exists())

    @mock.patch('aeonview.requests.get')
    def test_download_image_failure(self, mock_get):
        mock_response = mock.Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        project_path = default_test_path
        url = f'{default_image_domain}.jpg'
        args = argparse.Namespace(simulate=False)
        avi = AeonViewImages(project_path, url, args)
        destination = Path('/tmp/image.jpg')

        with pytest.raises(SystemExit):
            with self.assertLogs(level='ERROR') as log:
                avi.download_image(destination)
                self.assertIn(AeonViewMessages.DOWNLOAD_FAILURE, log.output[0])


class TestAeonViewVideos(TestCase):
    @mock.patch('aeonview.AeonViewHelpers.mkdir_p')
    @mock.patch('subprocess.run')
    def test_generate_daily_video(self, mock_subprocess_run, mock_mkdir_p):
        project_path = default_test_path
        args = argparse.Namespace(simulate=False, fps=10, day='01', month='04', year='2025')
        avv = AeonViewVideos(project_path, args)
        with self.assertLogs(level='INFO') as log:
            avv.generate_daily_video()
            expected_message = f'{AeonViewMessages.VIDEO_GENERATION_SUCCESS}: {default_test_path / "vid/2025-04/01.mp4"}'
            self.assertIn(expected_message, log.output[-1])  # Ensure it's the last log entry
        mock_mkdir_p.assert_called()
        mock_subprocess_run.assert_called()

    @mock.patch('aeonview.AeonViewHelpers.mkdir_p')
    def test_generate_daily_video_simulate(self, mock_mkdir_p):
        project_path = default_test_path
        args = argparse.Namespace(simulate=True, fps=10, day='01', month='04', year='2025')
        avv = AeonViewVideos(project_path, args)
        avv.generate_daily_video()
        mock_mkdir_p.assert_not_called()

    def test_generate_monthly_video_not_implemented(self):
        project_path = default_test_path
        args = argparse.Namespace(simulate=False, fps=10, day='01', month='04', year='2025')
        avv = AeonViewVideos(project_path, args)
        with pytest.raises(NotImplementedError):
            avv.generate_monthly_video(Path('/tmp'))

    def test_generate_yearly_video_not_implemented(self):
        project_path = default_test_path
        args = argparse.Namespace(simulate=False, fps=10, day='01', month='04', year='2025')
        avv = AeonViewVideos(project_path, args)
        with pytest.raises(NotImplementedError):
            avv.generate_yearly_video(Path('/tmp'))


class TestHelpersArguments(TestCase):
    def setUp(self):
        self.default_dest = str(Path.cwd() / 'projects')

    @mock.patch(
        'sys.argv', ['aeonview.py', '--mode', 'image', '--url', f'{default_image_domain}.jpg']
    )
    def test_parse_arguments_image_mode(self):
        args, _ = AeonViewHelpers.parse_arguments()
        self.assertEqual(args.mode, 'image')
        self.assertEqual(args.url, f'{default_image_domain}.jpg')
        self.assertEqual(args.dest, self.default_dest)

    @mock.patch('sys.argv', ['aeonview.py', '--mode', 'video', '--project', f'{default_project}'])
    def test_parse_arguments_video_mode(self):
        args, _ = AeonViewHelpers.parse_arguments()
        self.assertEqual(args.mode, 'video')
        self.assertEqual(args.project, f'{default_project}')
        self.assertEqual(args.dest, self.default_dest)

    @mock.patch('sys.argv', ['aeonview.py', '--mode', 'image', '--simulate'])
    def test_parse_arguments_simulate_mode(self):
        args, _ = AeonViewHelpers.parse_arguments()
        self.assertEqual(args.mode, 'image')
        self.assertTrue(args.simulate)

    @mock.patch('sys.argv', ['aeonview.py', '--mode', 'video', '--fps', '30'])
    def test_parse_arguments_fps(self):
        args, _ = AeonViewHelpers.parse_arguments()
        self.assertEqual(args.mode, 'video')
        self.assertEqual(args.project, f'{default_project}')
        self.assertEqual(args.dest, self.default_dest)
        self.assertEqual(args.fps, 30)

    @mock.patch('sys.argv', ['aeonview.py', '--mode', 'video', '--generate', '2023-10-01'])
    def test_parse_arguments_generate_date(self):
        args, _ = AeonViewHelpers.parse_arguments()
        self.assertEqual(args.mode, 'video')
        self.assertEqual(args.generate, '2023-10-01')

    @mock.patch('sys.argv', ['aeonview.py', '--mode', 'image', '--verbose'])
    def test_parse_arguments_verbose(self):
        args, _ = AeonViewHelpers.parse_arguments()
        self.assertEqual(args.mode, 'image')
        self.assertTrue(args.verbose)

    @mock.patch('sys.argv', ['aeonview.py'])
    def test_parse_arguments_defaults(self):
        args, _ = AeonViewHelpers.parse_arguments()
        self.assertEqual(args.mode, 'image')
        self.assertEqual(args.project, f'{default_project}')
        self.assertEqual(args.dest, self.default_dest)
        self.assertEqual(args.fps, 10)
        self.assertEqual(args.timeframe, 'daily')
        self.assertFalse(args.simulate)
        self.assertFalse(args.verbose)


class TestAeonViewSimulation(TestCase):
    @mock.patch('aeonview.AeonViewHelpers.mkdir_p')
    @mock.patch('aeonview.AeonViewImages.download_image')
    def test_image_simulation(self, mock_download_image, mock_mkdir_p):
        args = mock.MagicMock()
        args.simulate = True
        args.date = '2025-04-10 12:30:45'

        url = f'{default_image_domain}.jpg'
        project_path = Path('/tmp/test_project').resolve()

        avi = AeonViewImages(project_path, url, args)
        with mock.patch('aeonview.logging.info') as mock_logging:
            avi.get_current_image()
            mock_mkdir_p.assert_not_called()
            mock_download_image.assert_not_called()
            mock_logging.assert_any_call(
                f'Saving image to {project_path}/img/2025-04/10/12-30-45.jpg'
            )

    @mock.patch('aeonview.AeonViewHelpers.mkdir_p')
    @mock.patch('subprocess.run')
    def test_video_simulation(self, mock_subprocess_run, mock_mkdir_p):
        args = mock.MagicMock()
        args.simulate = True
        args.fps = 10
        args.day = '01'
        args.month = '01'
        args.year = '2023'
        project_path = Path('/tmp/test_project').resolve()

        avv = AeonViewVideos(project_path, args)
        with mock.patch('aeonview.logging.info') as mock_logging:
            avv.generate_daily_video()
            mock_mkdir_p.assert_not_called()
            mock_subprocess_run.assert_not_called()
            mock_logging.assert_any_call(f'Generating video from {project_path}/vid/2023-01/01')


class TestSetupLogger(TestCase):
    @mock.patch('logging.basicConfig')
    def test_setup_logger_verbose(self, mock_basic_config):
        AeonViewHelpers.setup_logger(verbose=True)
        mock_basic_config.assert_called_once_with(
            level=logging.DEBUG, format='[%(levelname)s] %(message)s'
        )

    @mock.patch('logging.basicConfig')
    def test_setup_logger_non_verbose(self, mock_basic_config):
        AeonViewHelpers.setup_logger(verbose=False)
        mock_basic_config.assert_called_once_with(
            level=logging.INFO, format='[%(levelname)s] %(message)s'
        )
        mock_basic_config.reset_mock()
