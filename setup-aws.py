#!/usr/bin/env python3

import sys
import json
import boto3
import time
from botocore.exceptions import ClientError

def create_bucket(bucket_name, region):
    """Create an S3 bucket with proper configuration"""
    s3_client = boto3.client('s3', region_name=region)
    
    try:
        if region == 'us-east-1':
            s3_client.create_bucket(Bucket=bucket_name)
        else:
            s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': region}
            )
        
        print(f"Created bucket: {bucket_name}")
        
        # Enable versioning
        s3_client.put_bucket_versioning(
            Bucket=bucket_name,
            VersioningConfiguration={'Status': 'Enabled'}
        )
        
        # Create bucket policy
        bucket_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "PublicReadGetObject",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{bucket_name}/*"
                }
            ]
        }
        
        s3_client.put_bucket_policy(
            Bucket=bucket_name,
            Policy=json.dumps(bucket_policy)
        )
        
        return True
    except ClientError as e:
        print(f"Error creating bucket: {e}")
        return False

def create_cloudfront_distribution(bucket_name, region):
    """Create CloudFront distribution for the S3 bucket"""
    cloudfront_client = boto3.client('cloudfront')
    
    try:
        # Create CloudFront origin access identity
        oai_response = cloudfront_client.create_cloud_front_origin_access_identity(
            CloudFrontOriginAccessIdentityConfig={
                'Comment': f'OAI for {bucket_name}'
            }
        )
        oai_id = oai_response['CloudFrontOriginAccessIdentity']['Id']
        
        # Create the distribution
        distribution_config = {
            'CallerReference': str(time.time()),
            'Origins': {
                'Quantity': 1,
                'Items': [
                    {
                        'Id': 's3-origin',
                        'DomainName': f'{bucket_name}.s3.{region}.amazonaws.com',
                        'S3OriginConfig': {
                            'OriginAccessIdentity': f'origin-access-identity/cloudfront/{oai_id}'
                        }
                    }
                ]
            },
            'DefaultCacheBehavior': {
                'TargetOriginId': 's3-origin',
                'ViewerProtocolPolicy': 'redirect-to-https',
                'AllowedMethods': {
                    'Quantity': 2,
                    'Items': ['GET', 'HEAD'],
                    'CachedMethods': {
                        'Quantity': 2,
                        'Items': ['GET', 'HEAD']
                    }
                },
                'ForwardedValues': {
                    'QueryString': False,
                    'Cookies': {'Forward': 'none'}
                },
                'MinTTL': 0,
                'DefaultTTL': 86400,
                'MaxTTL': 31536000
            },
            'Comment': f'Distribution for {bucket_name}',
            'Enabled': True,
            'DefaultRootObject': 'index.html',
            'PriceClass': 'PriceClass_100'
        }
        
        response = cloudfront_client.create_distribution(
            DistributionConfig=distribution_config
        )
        
        distribution_id = response['Distribution']['Id']
        domain_name = response['Distribution']['DomainName']
        
        print(f"Created CloudFront distribution: {distribution_id}")
        print(f"Distribution domain: {domain_name}")
        
        # Update bucket policy to allow CloudFront OAI
        s3_client = boto3.client('s3')
        bucket_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "CloudFrontAccess",
                    "Effect": "Allow",
                    "Principal": {
                        "AWS": f"arn:aws:iam::cloudfront:user/CloudFront Origin Access Identity {oai_id}"
                    },
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{bucket_name}/*"
                }
            ]
        }
        
        s3_client.put_bucket_policy(
            Bucket=bucket_name,
            Policy=json.dumps(bucket_policy)
        )
        
        return domain_name
        
    except ClientError as e:
        print(f"Error creating CloudFront distribution: {e}")
        return None

def main():
    if len(sys.argv) != 2:
        print("Usage: python setup-aws.py <bucket-name>")
        sys.exit(1)
    
    bucket_name = sys.argv[1]
    
    # Get default region from AWS configuration
    session = boto3.Session()
    region = session.region_name
    
    if not region:
        print("Error: No AWS region configured. Please run 'aws configure' first.")
        sys.exit(1)
    
    print(f"Using region: {region}")
    
    # Create bucket
    if not create_bucket(bucket_name, region):
        sys.exit(1)
    
    # Create CloudFront distribution
    cloudfront_domain = create_cloudfront_distribution(bucket_name, region)
    if not cloudfront_domain:
        sys.exit(1)
    
    print("\nSetup complete!")
    print(f"Bucket: {bucket_name}")
    print(f"CloudFront URL: https://{cloudfront_domain}")
    print("\nUpdate your config.yaml with:")
    print("aws:")
    print(f"  bucket: \"{bucket_name}\"")
    print(f"  region: \"{region}\"")
    print(f"  cloudfront_url: \"https://{cloudfront_domain}\"")

if __name__ == "__main__":
    main()
