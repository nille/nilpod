# nilpod

A simple static podcast RSS feed generator. Convert your audio files to MP3, upload to S3, and generate a valid podcast RSS feed with minimal configuration.

## Features

- Generate podcast RSS feeds from audio files
- Automatic conversion of various audio formats to MP3
- Simple YAML configuration
- Support for podcast artwork
- Episode management (new/published)
- Customizable episode metadata
- S3 storage with CloudFront distribution
- Minimal dependencies

## Requirements

### Python
- Python 3.7 or higher
- pip (Python package installer)

### FFmpeg
This project requires FFmpeg for audio conversion. Here's how to install it on different platforms:

#### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install ffmpeg
