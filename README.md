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
```

#### macOS
Using Homebrew:
```bash
brew install ffmpeg
```

#### Windows
- Download the FFmpeg build from [ffmpeg.org](https://ffmpeg.org/download.html)
- Or install using Chocolatey:
```bash
choco install ffmpeg
```
- After installation, ensure FFmpeg is added to your system's PATH

### Verify FFmpeg Installation
To verify FFmpeg is installed correctly, run:
```bash
ffmpeg -version
```

### AWS Setup
1. Create an S3 bucket
2. Set up a CloudFront distribution with the S3 bucket as origin
3. Configure AWS credentials (AWS CLI or environment variables)
4. Ensure proper IAM permissions for:
   - s3:PutObject
   - s3:GetObject
   - cloudfront:CreateInvalidation
   - cloudfront:ListDistributions

## AWS Setup

### Automatic Setup
You can automatically set up the required AWS infrastructure using the provided script:

```bash
python setup-aws.py my-podcast-bucket
```

This will:
1. Create an S3 bucket with the given name (my-podcast-bucket in this example)
2. Create a CloudFront distribution
3. Configure all necessary permissions
4. Output the configuration values for your config.yaml

Make sure you have AWS credentials configured with appropriate permissions before running the script.

### Manual Setup
If you prefer to set up the infrastructure manually:
1. Create an S3 bucket
2. Set up a CloudFront distribution with the S3 bucket as origin
3. Configure AWS credentials (AWS CLI or environment variables)
4. Ensure proper IAM permissions for:
   - s3:PutObject
   - s3:GetObject
   - cloudfront:CreateInvalidation
   - cloudfront:ListDistributions


## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/nilpod.git
cd nilpod
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

The `config.yaml` file contains all the settings for your podcast feed generator. Copy `config-sample.yaml` to `config.yaml` and configure the following settings:

### Episode Settings
- `default_description`: Default description used for episodes if none is provided during processing
- `type`: Episode type (full, trailer, or bonus)
- `explicit`: Whether the episode contains explicit content

# ... rest of README content ...