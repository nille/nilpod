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

1. Copy the sample configuration file:
```bash
cp config-sample.yaml config.yaml
```

2. Edit `config.yaml` with your podcast details:
```yaml
podcast:
  title: "My Podcast"
  description: "My awesome podcast description"
  author: "Your Name"
  email: "your@email.com"
  # ... more settings

aws:
  bucket: "your-s3-bucket-name"
  region: "your-aws-region"
  cloudfront_url: "https://your-cloudfront-distribution.cloudfront.net"
```

## Directory Structure

```
nilpod/
├── assets/          # Static assets (artwork, etc.)
├── episodes/        # New episodes to be processed
├── processed/       # Processed original files
├── published/       # Converted MP3 files
├── feed/           # Generated RSS feed
└── config.yaml     # Your configuration
```

## Usage

1. Place your audio files in the `episodes` directory
2. Place your podcast artwork in the `assets` directory (as specified in config.yaml)
3. Run the generator:
```bash
python generate-pod.py
```

4. For each new episode, you'll be prompted for:
   - Episode title (optional, uses default if empty)
   - Episode description (optional, uses default if empty)

5. The script will:
   - Convert audio files to MP3 if necessary
   - Move original files to the processed directory
   - Store converted files in the published directory
   - Upload MP3 files to S3
   - Store episode metadata in S3
   - Generate and upload the RSS feed
   - Create CloudFront invalidations for updated content

## Feed Validation

The generated RSS feed is compatible with major podcast platforms including:
- Apple Podcasts
- Spotify
- Google Podcasts
- Pocket Casts
- Overcast

## Dependencies

- pyyaml (YAML file parsing)
- pydub (audio processing)
- feedgen (RSS feed generation)
- validators (URL validation)
- mutagen (audio metadata handling)
- boto3 (AWS SDK)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [ffmpeg](https://ffmpeg.org/) for audio conversion
- [Python-feedgen](https://github.com/lkiesow/python-feedgen) for RSS generation
- [boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html) for AWS integration

## Support

If you encounter any problems or have suggestions, please [open an issue](https://github.com/yourusername/nilpod/issues).
