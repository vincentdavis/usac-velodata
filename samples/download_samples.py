#!/usr/bin/env python3
"""
Script to download sample HTML files from USA Cycling's website for testing.
"""
import os
import json
import time
import argparse
from datetime import datetime
from pathlib import Path
import requests
from typing import Dict, List, Optional


SAMPLE_URLS = {
    "event_lists": [
        {
            "url": "https://legacy.usacycling.org/results/browse.php?state=CO&race=&fyear=2020",
            "filename": "colorado_2020.html",
            "description": "Colorado events for 2020"
        },
        # {
        #     "url": "https://legacy.usacycling.org/results/browse.php?state=CA&race=&fyear=2020",
        #     "filename": "california_2020.html",
        #     "description": "California events for 2020"
        # },
        # {
        #     "url": "https://legacy.usacycling.org/results/browse.php?state=NY&race=&fyear=2020",
        #     "filename": "new_york_2020.html",
        #     "description": "New York events for 2020"
        # }
    ],
    "events": [],
    "permit_pages": [
        {
            "url": "https://legacy.usacycling.org/results/?permit=2020-26", # USA Cycling December VRL
            "filename": "2020-26.html",
            "description": "2020-26"
        },
        
    ],
    "load_info": [
        {
            "url": "https://legacy.usacycling.org/results/index.php?ajax=1&act=infoid&info_id=132893&label=Cross%20Country%20Ultra%20Endurance%2012/02/2020",
            "filename": "132893.html",
            "description": "132893"
        },
        
    ],
    "race_results": [
        {
            "url": "https://legacy.usacycling.org/results/index.php?ajax=1&act=loadresults&race_id=1337864",
            "filename": "1337864.html",
            "description": "1337864"
        },
        
    ]
}


def download_file(url: str, output_path: Path, delay: float = 2.0) -> Dict:
    """
    Download a file from a URL and save it to the specified path.
    
    Args:
        url: URL to download
        output_path: Path to save the file
        delay: Delay in seconds before downloading (to avoid rate limiting)
        
    Returns:
        Dict with metadata about the download
    """
    print(f"Downloading {url} to {output_path}")
    
    # Create parent directory if it doesn't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Add delay to avoid overwhelming the server
    time.sleep(delay)
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(response.text)
        
        metadata = {
            "url": url,
            "downloaded_at": datetime.now().isoformat(),
            "status_code": response.status_code,
            "content_type": response.headers.get("Content-Type", ""),
            "content_length": len(response.text)
        }
        
        # Save metadata to a .meta.json file
        with open(f"{output_path}.meta.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
        
        print(f"Successfully downloaded {url}")
        return metadata
    
    except requests.RequestException as e:
        print(f"Error downloading {url}: {str(e)}")
        return {
            "url": url,
            "error": str(e),
            "downloaded_at": datetime.now().isoformat()
        }


def download_all_samples(base_dir: Path, delay: float = 2.0) -> None:
    """
    Download all sample files.
    
    Args:
        base_dir: Base directory to save files
        delay: Delay between downloads
    """
    all_metadata = {}
    
    for category, samples in SAMPLE_URLS.items():
        category_dir = base_dir / category
        category_dir.mkdir(parents=True, exist_ok=True)
        
        all_metadata[category] = []
        
        for sample in samples:
            url = sample["url"]
            filename = sample["filename"]
            output_path = category_dir / filename
            
            metadata = download_file(url, output_path, delay)
            metadata["description"] = sample.get("description", "")
            all_metadata[category].append(metadata)
    
    # Save all metadata to a single file
    with open(base_dir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(all_metadata, f, indent=2)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Download sample HTML files from USA Cycling")
    parser.add_argument("--output-dir", type=str, default="samples",
                        help="Directory to save samples (default: samples)")
    parser.add_argument("--delay", type=float, default=2.0,
                        help="Delay between downloads in seconds (default: 2.0)")
    
    args = parser.parse_args()
    
    base_dir = Path(args.output_dir)
    delay = args.delay
    
    print(f"Downloading samples to {base_dir} with delay {delay} seconds")
    download_all_samples(base_dir, delay)
    print("Download complete!")


if __name__ == "__main__":
    main() 