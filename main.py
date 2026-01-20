import json
import os
from datetime import datetime
from crawler import LinkedInCrawler


def save_profile_data(profile_data, output_dir='data/output'):
    """Save profile data to JSON file"""
    os.makedirs(output_dir, exist_ok=True)
    
    # Create filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    name_slug = profile_data.get('name', 'unknown').replace(' ', '_').lower()
    filename = f"{name_slug}_{timestamp}.json"
    filepath = os.path.join(output_dir, filename)
    
    # Save to file
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(profile_data, indent=2, ensure_ascii=False, fp=f)
    
    print(f"\nProfile data saved to: {filepath}")
    return filepath


def main():
    # LinkedIn profile URL to scrape
    profile_url = input("Enter LinkedIn profile URL: ").strip()
    
    if not profile_url:
        print("Error: No URL provided")
        return
    
    crawler = LinkedInCrawler()
    
    try:
        # Login
        crawler.login()
        
        # Scrape profile
        profile_data = crawler.get_profile(profile_url)
        
        # Print results
        print("\n" + "="*50)
        print("PROFILE DATA")
        print("="*50)
        print(json.dumps(profile_data, indent=2, ensure_ascii=False))
        
        # Save to file
        save_profile_data(profile_data)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Close browser automatically
        print("\nClosing browser...")
        crawler.close()
        print("Done!")


if __name__ == "__main__":
    main()
