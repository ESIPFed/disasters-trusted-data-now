#!/usr/bin/env python3
"""
Site Accessibility Checker for Trusted Data Now

This script checks the accessibility of URLs in the data.json file and updates
the accessibility status and last checked timestamp.

ESIP Federation Disasters Cluster Project
Project Lead: Jeil Oh (jeoh@utexas.edu)
"""

import json
import sys
import time
import requests
from datetime import datetime, timezone
from urllib.parse import urlparse
import concurrent.futures
from typing import Dict, List, Tuple

# Configuration
TIMEOUT = 10  # seconds
MAX_WORKERS = 10  # concurrent requests
USER_AGENT = "TrustedDataNow-AccessibilityChecker/1.0"

def check_url_accessibility(url: str) -> Tuple[bool, str, int]:
    """
    Check if a URL is accessible.
    
    Returns:
        Tuple of (is_accessible, error_message, status_code)
    """
    if not url or not url.strip():
        return False, "Empty URL", 0
    
    try:
        # Add protocol if missing
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        headers = {
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        # Try HEAD request first (faster)
        try:
            response = requests.head(
                url, 
                timeout=TIMEOUT, 
                headers=headers,
                allow_redirects=True,
                verify=True
            )
            
            # Consider 2xx and 3xx as accessible
            if 200 <= response.status_code < 400:
                return True, "", response.status_code
            elif response.status_code in [404, 403, 405]:
                # Some sites don't support HEAD requests, try GET
                response = requests.get(
                    url, 
                    timeout=TIMEOUT, 
                    headers=headers,
                    allow_redirects=True,
                    verify=True
                )
                if 200 <= response.status_code < 400:
                    return True, "", response.status_code
                else:
                    return False, f"HTTP {response.status_code}", response.status_code
            else:
                return False, f"HTTP {response.status_code}", response.status_code
                
        except requests.exceptions.RequestException:
            # If HEAD fails, try GET request
            response = requests.get(
                url, 
                timeout=TIMEOUT, 
                headers=headers,
                allow_redirects=True,
                verify=True
            )
            
            if 200 <= response.status_code < 400:
                return True, "", response.status_code
            else:
                return False, f"HTTP {response.status_code}", response.status_code
            
    except requests.exceptions.Timeout:
        return False, "Timeout", 0
    except requests.exceptions.ConnectionError:
        return False, "Connection Error", 0
    except requests.exceptions.SSLError:
        return False, "SSL Error", 0
    except requests.exceptions.RequestException as e:
        return False, f"Request Error: {str(e)}", 0
    except Exception as e:
        return False, f"Unexpected Error: {str(e)}", 0

def check_urls_batch(urls: List[str]) -> List[Tuple[bool, str, int]]:
    """
    Check multiple URLs concurrently.
    """
    results = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all tasks
        future_to_url = {executor.submit(check_url_accessibility, url): url for url in urls}
        
        # Collect results as they complete
        for future in concurrent.futures.as_completed(future_to_url):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                results.append((False, f"Future Error: {str(e)}", 0))
    
    return results

def update_accessibility_data(data: List[Dict], check_all: bool = False) -> List[Dict]:
    """
    Update accessibility data for resources.
    
    Args:
        data: List of resource dictionaries
        check_all: If True, check all URLs. If False, only check URLs that haven't been checked recently.
    """
    current_time = datetime.now(timezone.utc).isoformat()
    
    # Filter URLs to check
    urls_to_check = []
    url_indices = []
    
    for i, resource in enumerate(data):
        url = resource.get('url', '')
        last_checked = resource.get('lastChecked', '')
        
        # Check if we should check this URL
        should_check = check_all
        if not should_check and last_checked:
            try:
                last_checked_dt = datetime.fromisoformat(last_checked.replace('Z', '+00:00'))
                hours_since_check = (datetime.now(timezone.utc) - last_checked_dt).total_seconds() / 3600
                should_check = hours_since_check >= 24  # Check if more than 24 hours old
            except:
                should_check = True  # If we can't parse the date, check it
        
        if should_check and url:
            urls_to_check.append(url)
            url_indices.append(i)
    
    if not urls_to_check:
        print("No URLs need to be checked at this time.")
        return data
    
    print(f"Checking accessibility of {len(urls_to_check)} URLs...")
    
    # Check URLs in batches
    results = check_urls_batch(urls_to_check)
    
    # Update the data with results
    updated_count = 0
    for i, (is_accessible, error_msg, status_code) in enumerate(results):
        resource_index = url_indices[i]
        resource = data[resource_index]
        
        # Update accessibility information
        resource['accessible'] = is_accessible
        resource['lastChecked'] = current_time
        
        if not is_accessible:
            resource['accessibilityError'] = error_msg
            resource['accessibilityStatus'] = status_code
        else:
            # Remove error fields if accessible
            resource.pop('accessibilityError', None)
            resource['accessibilityStatus'] = status_code
        
        updated_count += 1
        
        # Print progress
        status = "✓" if is_accessible else "✗"
        print(f"{status} {resource.get('name', 'Unknown')[:50]:<50} - {urls_to_check[i]}")
        if not is_accessible:
            print(f"    Error: {error_msg}")
    
    print(f"\nUpdated accessibility data for {updated_count} resources.")
    return data

def main():
    if len(sys.argv) < 2:
        print("Usage: check_accessibility.py <data.json> [--check-all]")
        print("  --check-all: Check all URLs regardless of last checked time")
        sys.exit(1)
    
    data_file = sys.argv[1]
    check_all = '--check-all' in sys.argv
    
    # Load data
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error loading {data_file}: {e}")
        sys.exit(1)
    
    if not isinstance(data, list):
        print("Error: data.json should contain a list of resources")
        sys.exit(1)
    
    print(f"Loaded {len(data)} resources from {data_file}")
    
    # Update accessibility data
    updated_data = update_accessibility_data(data, check_all)
    
    # Save updated data
    try:
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(updated_data, f, indent=2, ensure_ascii=False)
        print(f"Updated data saved to {data_file}")
    except Exception as e:
        print(f"Error saving updated data: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
