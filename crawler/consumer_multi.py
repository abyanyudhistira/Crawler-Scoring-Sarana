"""Multi-threaded Consumer - Process URLs with configurable workers"""
import json
import threading
import time
from datetime import datetime
from crawler import LinkedInCrawler
from helper.rabbitmq_helper import RabbitMQManager, ack_message, nack_message
from main import save_profile_data


# Statistics
stats = {
    'processing': 0,
    'completed': 0,
    'failed': 0,
    'lock': threading.Lock()
}


def print_stats():
    """Print current statistics"""
    print("\n" + "="*60)
    print("STATISTICS")
    print("="*60)
    print(f"Processing: {stats['processing']}")
    print(f"Completed: {stats['completed']}")
    print(f"Failed: {stats['failed']}")
    if stats['completed'] + stats['failed'] > 0:
        success_rate = stats['completed'] / (stats['completed'] + stats['failed']) * 100
        print(f"Success Rate: {success_rate:.1f}%")
    print("="*60)


def worker_thread(worker_id, mq_config):
    """Worker thread that continuously processes messages"""
    print(f"[Worker {worker_id}] Started")
    
    # Each worker has its own RabbitMQ connection
    mq = RabbitMQManager()
    mq.host = mq_config['host']
    mq.port = mq_config['port']
    mq.username = mq_config['username']
    mq.password = mq_config['password']
    mq.queue_name = mq_config['queue_name']
    
    if not mq.connect():
        print(f"[Worker {worker_id}] Failed to connect to RabbitMQ")
        return
    
    # Set QoS - only process 1 message at a time
    mq.channel.basic_qos(prefetch_count=1)
    
    def callback(ch, method, properties, body):
        """Process each message"""
        crawler = None
        
        try:
            # Parse message
            message = json.loads(body)
            url = message.get('url')
            
            if not url:
                print(f"[Worker {worker_id}] ✗ Invalid message")
                ack_message(ch, method.delivery_tag)
                return
            
            print(f"\n[Worker {worker_id}] 📥 Processing: {url}")
            
            with stats['lock']:
                stats['processing'] += 1
            
            # Create crawler and process
            crawler = LinkedInCrawler()
            
            try:
                # Login (will use cookies if available)
                crawler.login()
                
                # Scrape profile
                profile_data = crawler.get_profile(url)
                
                # Save to file
                save_profile_data(profile_data)
                
                with stats['lock']:
                    stats['completed'] += 1
                
                print(f"[Worker {worker_id}] ✓ Completed: {profile_data.get('name', 'Unknown')}")
                
                # Print stats after completion
                print_stats()
                
                # Acknowledge message
                ack_message(ch, method.delivery_tag)
                
            except Exception as e:
                with stats['lock']:
                    stats['failed'] += 1
                
                print(f"[Worker {worker_id}] ✗ Error: {e}")
                
                # Print stats after failure
                print_stats()
                
                # Don't requeue to avoid infinite loop
                nack_message(ch, method.delivery_tag, requeue=False)
            
            finally:
                # Close browser
                if crawler:
                    crawler.close()
                
                with stats['lock']:
                    stats['processing'] -= 1
        
        except Exception as e:
            print(f"[Worker {worker_id}] ✗ Fatal error: {e}")
            nack_message(ch, method.delivery_tag, requeue=False)
    
    try:
        # Start consuming
        mq.channel.basic_consume(
            queue=mq.queue_name,
            on_message_callback=callback,
            auto_ack=False
        )
        
        print(f"[Worker {worker_id}] Waiting for messages...")
        mq.channel.start_consuming()
    
    except Exception as e:
        print(f"[Worker {worker_id}] Error: {e}")
    
    finally:
        mq.close()
        print(f"[Worker {worker_id}] Stopped")


def main():
    print("="*60)
    print("LINKEDIN SCRAPER - MULTI-WORKER CONSUMER")
    print("="*60)
    
    # Get number of workers
    try:
        num_workers = int(input("\nNumber of workers (default 3): ").strip() or "3")
        if num_workers < 1:
            num_workers = 3
    except:
        num_workers = 3
    
    print(f"→ Using {num_workers} workers")
    
    # Connect to RabbitMQ to check status
    mq = RabbitMQManager()
    if not mq.connect():
        print("✗ Failed to connect to RabbitMQ. Is it running?")
        print("\nTo start RabbitMQ with Docker:")
        print("  docker-compose up -d")
        return
    
    # Show queue status
    queue_size = mq.get_queue_size()
    print(f"\n→ Queue status:")
    print(f"  - Messages in queue: {queue_size}")
    print(f"  - Queue name: {mq.queue_name}")
    
    # Save config for workers
    mq_config = {
        'host': mq.host,
        'port': mq.port,
        'username': mq.username,
        'password': mq.password,
        'queue_name': mq.queue_name
    }
    
    mq.close()
    
    print(f"\n→ Starting {num_workers} workers...")
    print("  Workers will automatically process URLs as they arrive")
    print("  Press Ctrl+C to stop all workers")
    print(f"  Management UI: http://localhost:15672 (guest/guest)")
    
    # Start worker threads
    threads = []
    for i in range(num_workers):
        t = threading.Thread(target=worker_thread, args=(i+1, mq_config), daemon=True)
        t.start()
        threads.append(t)
        time.sleep(0.5)  # Small delay between starting workers
    
    print(f"\n✓ All {num_workers} workers are running!")
    print("  Add URLs anytime with: python producer.py")
    print("  Statistics will update after each completed/failed task")
    
    try:
        # Keep main thread alive
        while True:
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\n\n⚠ Interrupted by user. Stopping all workers...")
        print("  (Workers will finish current tasks)")
    
    finally:
        # Wait a bit for workers to finish current tasks
        time.sleep(3)
        
        # Final stats
        print("\n" + "="*60)
        print("FINAL RESULTS")
        print("="*60)
        print(f"✓ Completed: {stats['completed']}")
        print(f"✗ Failed: {stats['failed']}")
        if stats['completed'] + stats['failed'] > 0:
            success_rate = stats['completed'] / (stats['completed'] + stats['failed']) * 100
            print(f"📊 Success Rate: {success_rate:.1f}%")
        print("="*60)


if __name__ == "__main__":
    main()
