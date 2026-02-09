"""Producer - Publish LinkedIn profile URLs to RabbitMQ queue"""
from helper.rabbitmq_helper import RabbitMQManager


def main():
    print("="*60)
    print("LINKEDIN SCRAPER - PRODUCER (RabbitMQ)")
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
    
    print(f"\n→ Total profiles to queue: {len(urls)}")
    
    # Connect to RabbitMQ
    mq = RabbitMQManager()
    if not mq.connect():
        print("✗ Failed to connect to RabbitMQ. Is it running?")
        print("\nTo start RabbitMQ with Docker:")
        print("  docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management")
        return
    
    # Publish URLs
    print(f"\n→ Publishing URLs to queue '{mq.queue_name}'...")
    success_count = mq.publish_urls(urls)
    
    # Show queue status
    queue_size = mq.get_queue_size()
    print(f"\n✓ Queue status:")
    print(f"  - Total messages in queue: {queue_size}")
    print(f"  - Successfully published: {success_count}/{len(urls)}")
    
    # Close connection
    mq.close()
    
    print("\n✓ Done! URLs are now in the queue.")
    print("  Run 'python consumer.py' to start processing.")
    print("  You can run multiple consumers for parallel processing.")
    print(f"\n  Management UI: http://localhost:15672 (guest/guest)")


if __name__ == "__main__":
    main()
