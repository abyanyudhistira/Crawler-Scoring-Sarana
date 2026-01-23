import json
import os
import queue
import threading
import time
from datetime import datetime
from crawler import LinkedInCrawler

COOKIES_FILE = "data/cookie/.linkedin_cookies.json"


def save_profile_data(profile_data, output_dir='data/output'):
    """Save profile data to JSON file"""
    os.makedirs(output_dir, exist_ok=True)
    
    # Create filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Clean name for filename (remove invalid chars, handle N/A)
    name = profile_data.get('name', 'unknown')
    if not name or name == 'N/A' or len(name.strip()) == 0:
        name = 'unknown'
    
    # Remove invalid filename characters
    name_slug = name.replace(' ', '_').replace('/', '_').replace('\\', '_').lower()
    # Remove any remaining invalid chars
    name_slug = ''.join(c for c in name_slug if c.isalnum() or c in ('_', '-'))
    
    filename = f"{name_slug}_{timestamp}.json"
    filepath = os.path.join(output_dir, filename)
    
    # Save to file
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(profile_data, indent=2, ensure_ascii=False, fp=f)
    
    print(f"\n✓ Profile data saved to: {filepath}")
    return filepath


def worker(worker_id, url_queue, stats):
    """Worker function to process URLs from queue"""
    print(f"[Worker {worker_id}] Started")
    
    crawler = None
    
    while True:
        try:
            # Get URL from queue (timeout 2 seconds)
            url = url_queue.get(timeout=2)
            
            print(f"\n[Worker {worker_id}] 📥 Processing: {url}")
            stats['processing'] += 1
            
            crawler = LinkedInCrawler()
            
            try:
                # Login (will use cookies if available)
                crawler.login()
                
                # Scrape profile
                profile_data = crawler.get_profile(url)
                
                # Save to file
                save_profile_data(profile_data)
                
                stats['completed'] += 1
                print(f"[Worker {worker_id}] ✓ Completed: {profile_data.get('name', 'Unknown')}")
                
            except Exception as e:
                stats['failed'] += 1
                print(f"[Worker {worker_id}] ✗ Error: {e}")
                import traceback
                traceback.print_exc()
            
            finally:
                # Close browser after each profile
                if crawler:
                    print(f"[Worker {worker_id}] Closing browser...")
                    crawler.close()
                    crawler = None
                url_queue.task_done()
                stats['processing'] -= 1
            
        except queue.Empty:
            # Queue empty, check if really done
            if url_queue.empty():
                print(f"[Worker {worker_id}] No more URLs, stopping")
                break


def print_stats(stats, total):
    """Print current statistics"""
    print("\n" + "="*60)
    print("PROGRESS")
    print("="*60)
    print(f"Total URLs: {total}")
    print(f"Processing: {stats['processing']}")
    print(f"Completed: {stats['completed']}")
    print(f"Failed: {stats['failed']}")
    print(f"Remaining: {total - stats['completed'] - stats['failed']}")
    print("="*60)


def main():
    print("="*60)
    print("LINKEDIN PROFILE SCRAPER - QUEUE MODE")
    print("="*60)
    
    # Get URLs from user
    print("\nEnter LinkedIn profile URLs (one per line).")
    print("Press Enter twice when done:")
    
    urls = []
    while True:
        url = input().strip()
        if not url:
            break
        urls.append(url)
    
    if not urls:
        print("Error: No URLs provided")
        return
    
    print(f"\n→ Total profiles to scrape: {len(urls)}")
    
    # Get max workers
    try:
        max_workers = int(input("\nMax concurrent workers (default 3): ").strip() or "3")
        if max_workers < 1:
            max_workers = 3
    except:
        max_workers = 3
    
    print(f"→ Using {max_workers} workers")
    
    # Check if cookies exist
    if not os.path.exists(COOKIES_FILE):
        print("\n⚠ No cookies found. Need to login first...")
        print("Opening browser for login...")
        
        # Login once to save cookies
        temp_crawler = LinkedInCrawler()
        temp_crawler.login()
        temp_crawler.close()
        
        print("\n✓ Cookies saved!")
    else:
        print("\n✓ Cookies found!")
    
    # Create queue
    url_queue = queue.Queue()
    
    # Put all URLs to queue
    print(f"\n→ Adding {len(urls)} URLs to queue...")
    for url in urls:
        url_queue.put(url)
    
    # Statistics
    stats = {
        'processing': 0,
        'completed': 0,
        'failed': 0
    }
    
    # Start workers
    print(f"\n→ Starting {max_workers} workers...")
    threads = []
    
    for i in range(max_workers):
        t = threading.Thread(target=worker, args=(i+1, url_queue, stats))
        t.daemon = True
        t.start()
        threads.append(t)
        time.sleep(1)  # Small delay between starting workers
    
    # Monitor progress
    print("\n→ Workers are processing URLs...")
    print("→ Press Ctrl+C to stop (gracefully)\n")
    
    try:
        # Print stats every 30 seconds (reduced spam)
        while not url_queue.empty() or stats['processing'] > 0:
            time.sleep(60)
            print_stats(stats, len(urls))
        
        # Wait for all tasks to complete
        url_queue.join()
        
    except KeyboardInterrupt:
        print("\n\n⚠ Interrupted by user. Waiting for current tasks to finish...")
        url_queue.join()
    
    # Final stats
    print("\n" + "="*60)
    print("FINAL RESULTS")
    print("="*60)
    print(f"Total URLs: {len(urls)}")
    print(f"✓ Completed: {stats['completed']}")
    print(f"✗ Failed: {stats['failed']}")
    print(f"Success Rate: {stats['completed']/len(urls)*100:.1f}%")
    print("="*60)
    print(f"\nOutput directory: data/output/")


if __name__ == "__main__":
    main()
