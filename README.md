```
                               _)
    _` |   -_)   _ \    \ \ \ / |   -_) \ \  \ /
  \__,_| \___| \___/ _| _| \_/ _| \___|  \_/\_/
   aeonview - a simple timelapse tool
```

**aeonview** is a Python-based tool for generating timelapse videos
from webcam images using `ffmpeg`. It supports automated image
downloading, video stitching, and is fully scriptable via CLI.
Includes developer tooling and tests.

[![CI][ci-b]][ci-l] [![ruff][cc-b]][cc-l] [![MIT][lm-b]][lm-l]

Low quality sample: [aeonview 2min preview/Tampere Jan. 2008][sample]

## Features

- Timelapse image capture (`--mode image`)
- Video generation (`--mode video`)
- Support for daily, monthly, yearly video runs *(daily implemented)*
- Uses `ffmpeg` and `curl`
- Fully tested with `pytest`
- Linting and formatting via `ruff`
- Pre-commit hooks and CI-ready

## Requirements

- Python 3.11+
- `ffmpeg` and `curl` (system tools)
- lots of hard drive space
- Optional: `pyenv` for managing Python versions
  (see `pyenv_requirements`)

## Installation

```bash
# Clone the repo
git clone https://github.com/ivuorinen/aeonview.git
cd aeonview

# Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Install pre-commit hooks
pre-commit install
```

## Usage

```bash
# Capture an image
python aeonview.py \
  --mode image \
  --project example \
  --url "https://example.com/webcam.jpg"

# Generate a video from yesterday's images
python aeonview.py --mode video --project example
```

## Development

```bash
# Format code
make format

# Lint code
make lint

# Run tests
make test
```

## System Setup for ffmpeg

```bash
sudo apt update
sudo apt install ffmpeg curl
```

## License

MIT License © 2025 Ismo Vuorinen

[ci-b]: https://github.com/ivuorinen/aeonview/actions/workflows/python-tests.yml/badge.svg
[ci-l]: https://github.com/ivuorinen/aeonview/actions/workflows/python-tests.yml
[cc-b]: https://img.shields.io/badge/code%20style-ruff-blueviolet
[cc-l]: https://github.com/astral-sh/ruff
[lm-b]: https://img.shields.io/badge/License-MIT-yellow.svg
[lm-l]: https://opensource.org/licenses/MIT
[sample]: https://www.youtube.com/watch?v=SnywvnjHpUk

<!-- vim: set sw=2 ts=2 tw=72 fo=cqt wm=0 et: -->
