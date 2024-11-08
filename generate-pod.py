#!/usr/bin/env python3

import os
import sys
import yaml
import json
import shutil
import pytz
import hashlib
import boto3
from datetime import datetime
from pathlib import Path
from pydub import AudioSegment
from feedgen.feed import FeedGenerator
from botocore.exceptions import ClientError

def load_config():
    """Load configuration from config.yaml"""
    try:
        with open('config.yaml', 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print("Error: config.yaml not found. Please copy config-sample.yaml to config.yaml and configure it.")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing config.yaml: {e}")
        sys.exit(1)

def ensure_directories(config):
    """Ensure all required directories exist"""
    required_dirs = [
        config['directories']['assets'],
        config['directories']['episodes'],
        config['directories']['published'],
        config['directories']['feed'],
        config['directories']['processed']
    ]

    for dir_path in required_dirs:
        path = Path(dir_path)
        if not path.exists():
            print(f"Creating directory: {path}")
            path.mkdir(parents=True, exist_ok=True)

def sanitize_filename(filename):
    """Convert filename to lowercase, replace spaces and special characters with underscores"""
    name, ext = os.path.splitext(filename)
    sanitized = ''.join(c if c.isalnum() or c in '-_' else '_' for c in name.lower())
    sanitized = '_'.join(filter(None, sanitized.split('_')))
    return f"{sanitized}{ext.lower()}"

def save_episode_metadata(episode_info, config):
    """Save episode metadata to S3"""
    s3_client = boto3.client('s3', region_name=config['aws']['region'])
    metadata_key = f"assets/metadata/{Path(episode_info['filename']).stem}.json"
    
    # Convert datetime to string for JSON serialization
    episode_data = episode_info.copy()
    episode_data['date'] = episode_data['date'].isoformat()
    
    try:
        s3_client.put_object(
            Bucket=config['aws']['bucket'],
            Key=metadata_key,
            Body=json.dumps(episode_data, indent=2),
            ContentType='application/json'
        )
        print(f"Saved metadata to S3: {metadata_key}")
        return True
    except ClientError as e:
        print(f"Error saving metadata to S3: {e}")
        return False

def load_episode_metadata(filename, config):
    """Load episode metadata from S3"""
    s3_client = boto3.client('s3', region_name=config['aws']['region'])
    metadata_key = f"assets/metadata/{Path(filename).stem}.json"
    
    try:
        response = s3_client.get_object(Bucket=config['aws']['bucket'], Key=metadata_key)
        metadata = json.loads(response['Body'].read().decode('utf-8'))
        metadata['date'] = datetime.fromisoformat(metadata['date'])
        return metadata
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            return None
        print(f"Error loading metadata from S3: {e}")
        return None

def get_episode_info(config, filename):
    """Prompt for episode information with filename-based default title"""
    print(f"\nProcessing: {filename}")
    
    # Extract title from filename: remove extension, replace dashes/underscores with spaces, capitalize words
    default_title = Path(filename).stem
    default_title = default_title.replace('-', ' ').replace('_', ' ')
    default_title = ' '.join(word.capitalize() for word in default_title.split())
    
    default_description = config['episode']['default_description']
    
    title = input(f"Episode title (press Enter for: '{default_title}'): ").strip()
    if not title:
        title = default_title
    
    description = input(f"Episode description (press Enter for: '{default_description}'): ").strip()
    if not description:
        description = default_description
    
    # Get timezone from config and create timezone-aware datetime
    tz = pytz.timezone(config['system']['timezone'])
    current_time = datetime.now(tz)
    
    return {
        'title': title,
        'description': description,
        'date': current_time,
        'filename': filename
    }

def convert_to_mp3(input_path, output_path, config):
    """Convert audio file to MP3 with specified settings"""
    try:
        audio = AudioSegment.from_file(input_path)
        
        if config['audio']['normalize_audio']:
            audio = audio.normalize()
        
        audio.export(
            output_path,
            format='mp3',
            bitrate=config['audio']['bitrate'],
            parameters=[
                "-ar", str(config['audio']['sample_rate']),
                "-ac", str(config['audio']['channels'])
            ]
        )
        return True
    except Exception as e:
        print(f"Error converting {input_path}: {e}")
        return False

def upload_to_s3(local_file_path, s3_key, config):
    """Upload a file to S3 with correct content type"""
    s3_client = boto3.client('s3', region_name=config['aws']['region'])
    
    content_types = {
        '.xml': 'application/xml',
        '.mp3': 'audio/mpeg',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.json': 'application/json'
    }
    
    _, ext = os.path.splitext(local_file_path)
    content_type = content_types.get(ext.lower(), 'application/octet-stream')
    
    try:
        s3_client.upload_file(
            str(local_file_path), 
            config['aws']['bucket'], 
            s3_key,
            ExtraArgs={'ContentType': content_type}
        )
        return True
    except ClientError as e:
        print(f"Error uploading to S3: {e}")
        return False

def check_file_exists_in_s3(s3_key, config):
    """Check if a file exists in S3 and get its MD5 hash"""
    s3_client = boto3.client('s3', region_name=config['aws']['region'])
    try:
        response = s3_client.head_object(Bucket=config['aws']['bucket'], Key=s3_key)
        return True, response.get('ETag', '').strip('"')
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            return False, None
        else:
            print(f"Error checking S3: {e}")
            return False, None

def get_file_md5(file_path):
    """Calculate MD5 hash of a file"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def handle_artwork(config, paths_to_invalidate):
    """Handle artwork upload and return the CloudFront URL"""
    artwork_path = Path(config['directories']['assets']) / config['feed']['artwork']
    if not artwork_path.exists():
        print(f"Warning: Artwork file {artwork_path} not found")
        return None

    s3_key = f"assets/{config['feed']['artwork']}"
    artwork_url = f"{config['aws']['cloudfront_url']}/{s3_key}"

    exists_in_s3, s3_hash = check_file_exists_in_s3(s3_key, config)
    local_hash = get_file_md5(artwork_path)

    if not exists_in_s3 or s3_hash != local_hash:
        if upload_to_s3(artwork_path, s3_key, config):
            print(f"Uploaded artwork to S3: {s3_key}")
            paths_to_invalidate.append(f"/{s3_key}")
        else:
            print("Failed to upload artwork")
            return None

    return artwork_url

def invalidate_cloudfront(paths, config):
    """Create a CloudFront invalidation for the given paths"""
    cloudfront_client = boto3.client('cloudfront')
    try:
        distributions = cloudfront_client.list_distributions()['DistributionList']['Items']
        distribution_id = None
        
        for dist in distributions:
            if dist['DomainName'] in config['aws']['cloudfront_url']:
                distribution_id = dist['Id']
                break
        
        if not distribution_id:
            print("Error: Could not find CloudFront distribution")
            return False

        response = cloudfront_client.create_invalidation(
            DistributionId=distribution_id,
            InvalidationBatch={
                'Paths': {
                    'Quantity': len(paths),
                    'Items': paths
                },
                'CallerReference': str(datetime.now().timestamp())
            }
        )
        print(f"Created CloudFront invalidation: {response['Invalidation']['Id']}")
        return True
    except ClientError as e:
        print(f"Error creating CloudFront invalidation: {e}")
        return False

def get_all_episodes(config, new_episodes):
    """Combine new episodes with existing processed episodes by reading from S3 metadata folder"""
    s3_client = boto3.client('s3', region_name=config['aws']['region'])
    all_episodes = []
    
    print("\n=== DEBUG INFO ===")
    print(f"New episodes to process: {len(new_episodes)}")
    for ep in new_episodes:
        print(f"- New episode: {ep['filename']}")
    
    try:
        # First, get all existing episodes from S3 metadata
        print("\nListing contents of S3 metadata folder...")
        paginator = s3_client.get_paginator('list_objects_v2')
        metadata_files_found = 0
        
        for page in paginator.paginate(
            Bucket=config['aws']['bucket'],
            Prefix='assets/metadata/'
        ):
            print(f"\nFound page in S3 listing")
            if 'Contents' not in page:
                print("No contents in this page")
                continue
            
            print(f"Found {len(page['Contents'])} items in this page")
            for obj in page['Contents']:
                metadata_files_found += 1
                print(f"\nProcessing metadata file: {obj['Key']}")
                try:
                    response = s3_client.get_object(
                        Bucket=config['aws']['bucket'],
                        Key=obj['Key']
                    )
                    metadata = json.loads(response['Body'].read().decode('utf-8'))
                    metadata['date'] = datetime.fromisoformat(metadata['date'])
                    all_episodes.append(metadata)
                    print(f"Successfully loaded metadata for: {metadata['filename']}")
                except Exception as e:
                    print(f"Error loading metadata from {obj['Key']}: {e}")
        
        print(f"\nTotal metadata files found in S3: {metadata_files_found}")
        print(f"Episodes loaded from S3: {len(all_episodes)}")
        
        # Then add any new episodes, replacing existing ones if necessary
        for new_episode in new_episodes:
            # Remove any existing episode with the same filename
            original_count = len(all_episodes)
            all_episodes = [ep for ep in all_episodes if ep['filename'] != new_episode['filename']]
            if len(all_episodes) != original_count:
                print(f"Replaced existing episode: {new_episode['filename']}")
            all_episodes.append(new_episode)
            print(f"Added/Updated episode: {new_episode['filename']}")
        
        # Sort all episodes by date, newest first
        all_episodes.sort(key=lambda x: x['date'], reverse=True)
        
        print("\n=== FINAL RESULTS ===")
        print(f"Total episodes in feed: {len(all_episodes)}")
        print("Episodes in chronological order:")
        for ep in all_episodes:
            print(f"- {ep['date'].isoformat()}: {ep['filename']}")
        
        return all_episodes
        
    except ClientError as e:
        print(f"\nError accessing S3: {e}")
        return new_episodes

def generate_feed(config, episodes, paths_to_invalidate):
    """Generate the RSS feed"""
    fg = FeedGenerator()
    
    # Load podcast extension once at the start
    fg.load_extension('podcast')
    
    fg.title(config['podcast']['title'])
    fg.description(config['podcast']['description'])
    fg.author({'name': config['podcast']['author'], 'email': config['podcast']['email']})
    fg.language(config['podcast']['language'])
    fg.copyright(config['podcast']['copyright'])
    fg.link(href=config['podcast']['website'], rel='alternate')
    
    artwork_url = handle_artwork(config, paths_to_invalidate)
    if artwork_url:
        fg.logo(artwork_url)
    
    for episode in episodes:
        fe = fg.add_entry()
        fe.title(episode['title'])
        fe.description(episode['description'])
        fe.published(episode['date'])
        
        media_url = f"{config['aws']['cloudfront_url']}/episodes/{episode['filename']}"
        
        # Add GUID using media URL as the unique identifier
        fe.guid(media_url, permalink=True)
        
        duration_ms = episode.get('duration', 0)
        duration_sec = int(duration_ms / 1000)
        hours = duration_sec // 3600
        minutes = (duration_sec % 3600) // 60
        seconds = duration_sec % 60
        duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        fe.enclosure(media_url, episode.get('size', 0), 'audio/mpeg')
        
        # Add iTunes specific episode elements
        fe.podcast.itunes_duration(duration_str)  # Corrected here
    
    feed_path = Path(config['directories']['feed']) / config['feed']['filename']
    fg.rss_file(str(feed_path))


def main():
    config = load_config()
    ensure_directories(config)
    
    episodes_dir = Path(config['directories']['episodes'])
    published_dir = Path(config['directories']['published'])
    processed_dir = Path(config['directories']['processed'])
    
    if not episodes_dir.exists():
        print("Error: Episodes directory not found")
        sys.exit(1)
    
    episode_files = list(episodes_dir.glob('*'))
    if not episode_files:
        print("No new episodes found to process")
        sys.exit(0)
    
    processed_episodes = []
    paths_to_invalidate = []
    
    for episode_path in episode_files:
        sanitized_name = sanitize_filename(episode_path.name)
        episode_info = get_episode_info(config, sanitized_name)
        
        if episode_path.suffix.lower() != '.mp3':
            output_path = published_dir / f"{Path(sanitized_name).stem}.mp3"
            if convert_to_mp3(str(episode_path), str(output_path), config):
                episode_info['filename'] = output_path.name
                processed_episodes.append(episode_info)
                shutil.move(str(episode_path), processed_dir / sanitized_name)
                
                s3_key = f"episodes/{output_path.name}"
                if upload_to_s3(output_path, s3_key, config):
                    print(f"Uploaded {output_path.name} to S3")
                    paths_to_invalidate.append(f"/episodes/{output_path.name}")
                    
                    # Save metadata to S3
                    save_episode_metadata(episode_info, config)
        else:
            published_path = published_dir / sanitized_name
            shutil.copy2(str(episode_path), published_path)
            shutil.move(str(episode_path), processed_dir / sanitized_name)
            episode_info['filename'] = sanitized_name
            processed_episodes.append(episode_info)
            
            s3_key = f"episodes/{sanitized_name}"
            if upload_to_s3(published_path, s3_key, config):
                print(f"Uploaded {sanitized_name} to S3")
                paths_to_invalidate.append(f"/episodes/{sanitized_name}")
                
                # Save metadata to S3
                save_episode_metadata(episode_info, config)
    
    # Get all episodes including processed ones
    all_episodes = get_all_episodes(config, processed_episodes)
    
    # Generate feed with all episodes
    generate_feed(config, all_episodes, paths_to_invalidate)
    
    # Upload feed to S3
    feed_path = Path(config['directories']['feed']) / config['feed']['filename']
    if upload_to_s3(feed_path, config['feed']['filename'], config):
        print(f"Uploaded feed to S3")
        paths_to_invalidate.append(f"/{config['feed']['filename']}")
    
    # Invalidate CloudFront cache
    if paths_to_invalidate:
        if invalidate_cloudfront(paths_to_invalidate, config):
            print("CloudFront cache invalidation created")
    
    print(f"\nProcessed {len(processed_episodes)} episodes")
    print(f"Feed available at: {config['aws']['cloudfront_url']}/{config['feed']['filename']}")

if __name__ == "__main__":
    main()

