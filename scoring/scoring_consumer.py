"""
Scoring Consumer - Process profiles from RabbitMQ and calculate scores
"""
import json
import os
import threading
import time
from datetime import datetime
import pika
from score import Scorer
from supabase import create_client, Client


# Configuration
RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'localhost')
RABBITMQ_PORT = int(os.getenv('RABBITMQ_PORT', 5672))
RABBITMQ_USER = os.getenv('RABBITMQ_USER', 'guest')
RABBITMQ_PASSWORD = os.getenv('RABBITMQ_PASSWORD', 'guest')
SCORING_QUEUE = os.getenv('SCORING_QUEUE', 'scoring_queue')

# Supabase Configuration
SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://hzkgpdnlkihnlosxwwig.supabase.co')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh6a2dwZG5sa2lobmxvc3h3d2lnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njc2ODQ1NzYsImV4cCI6MjA4MzI2MDU3Nn0.M8aoPh1BrSGr47ix0Fd9jUJdK16Vd_MIge4uXKcHlHc')

OUTPUT_DIR = 'data/scores'
REQUIREMENTS_DIR = 'requirements'

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Statistics
stats = {
    'processing': 0,
    'completed': 0,
    'failed': 0,
    'supabase_updated': 0,
    'supabase_failed': 0,
    'lock': threading.Lock()
}


def load_requirements(requirements_id):
    """Load requirements JSON file"""
    filepath = os.path.join(REQUIREMENTS_DIR, f"{requirements_id}.json")
    
    if not os.path.exists(filepath):
        print(f"⚠ Requirements file not found: {filepath}")
        return None
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"✗ Error loading requirements: {e}")
        return None


def save_score_result(profile_data, score_result, requirements_id):
    """Save scoring result to JSON file"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Create filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    name = profile_data.get('name', 'unknown')
    
    if not name or name == 'N/A' or len(name.strip()) == 0:
        name = 'unknown'
    
    # Clean name for filename
    name_slug = name.replace(' ', '_').replace('/', '_').replace('\\', '_').lower()
    name_slug = ''.join(c for c in name_slug if c.isalnum() or c in ('_', '-'))
    
    filename = f"{name_slug}_{requirements_id}_{timestamp}_score.json"
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    # Prepare output
    output = {
        'profile': profile_data,
        'requirements_id': requirements_id,
        'score': score_result,
        'scored_at': datetime.now().isoformat()
    }
    
    # Save to file
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Score saved to: {filepath}")
    return filepath


def update_supabase_score(profile_url, total_score):
    """Update score in Supabase leads_list table"""
    try:
        print(f"📤 Updating Supabase...")
        
        # Update score in leads_list table where profile_url matches
        response = supabase.table('leads_list').update({
            'score': total_score
        }).eq('profile_url', profile_url).execute()
        
        # Check if update was successful
        if response.data:
            print(f"✓ Supabase updated: {profile_url} → score: {total_score}")
            return True
        else:
            print(f"⚠ No matching profile_url found in Supabase: {profile_url}")
            return False
    
    except Exception as e:
        print(f"✗ Failed to update Supabase: {e}")
        return False


def print_stats():
    """Print current statistics"""
    print("\n" + "="*60)
    print("SCORING STATISTICS")
    print("="*60)
    print(f"Processing: {stats['processing']}")
    print(f"Completed: {stats['completed']}")
    print(f"Failed: {stats['failed']}")
    print(f"Supabase Updated: {stats['supabase_updated']}")
    print(f"Supabase Failed: {stats['supabase_failed']}")
    if stats['completed'] + stats['failed'] > 0:
        success_rate = stats['completed'] / (stats['completed'] + stats['failed']) * 100
        print(f"Success Rate: {success_rate:.1f}%")
    print("="*60)


def process_message(message_data):
    """Process a single scoring message"""
    try:
        profile_data = message_data.get('profile_data')
        requirements_id = message_data.get('requirements_id', 'default')
        
        if not profile_data:
            print("✗ No profile data in message")
            return False
        
        name = profile_data.get('name', 'Unknown')
        print(f"\n📥 Processing: {name}")
        print(f"   Requirements: {requirements_id}")
        
        # Load requirements
        requirements = load_requirements(requirements_id)
        
        if not requirements:
            print(f"✗ Failed to load requirements: {requirements_id}")
            return False
        
        # Calculate score
        print(f"🔢 Calculating score...")
        scorer = Scorer(requirements)
        score_result = scorer.score(profile_data)
        
        # Print result
        print(f"\n{'='*60}")
        print(f"SCORE RESULT: {name}")
        print(f"{'='*60}")
        print(f"Total Score: {score_result['total_score']}/{score_result['max_score']}")
        print(f"Percentage: {score_result['percentage']}%")
        
        breakdown = score_result.get('breakdown', {})
        print(f"\nBreakdown:")
        print(f"  - Skills: {breakdown.get('skills', {}).get('score', 0)}/40")
        print(f"  - Text Similarity: {breakdown.get('text_similarity', {}).get('score', 0)}/30")
        print(f"  - Experience: {breakdown.get('experience', {}).get('score', 0)}/20")
        print(f"  - Education: {breakdown.get('education', {}).get('score', 0)}/10")
        print(f"  - Gender: {breakdown.get('gender', {}).get('score', 0)}/10")
        print(f"  - Location: {breakdown.get('location', {}).get('score', 0)}/10")
        print(f"  - Age: {breakdown.get('age', {}).get('score', 0)}/10")
        print(f"{'='*60}")
        
        # Save result
        save_score_result(profile_data, score_result, requirements_id)
        
        # Update Supabase
        profile_url = profile_data.get('profile_url', '')
        total_score = score_result.get('total_score', 0)
        if profile_url:
            if update_supabase_score(profile_url, total_score):
                with stats['lock']:
                    stats['supabase_updated'] += 1
            else:
                with stats['lock']:
                    stats['supabase_failed'] += 1
        
        print(f"✓ Completed: {name} - Score: {score_result['percentage']}%")
        
        return True
    
    except Exception as e:
        print(f"✗ Error processing message: {e}")
        import traceback
        traceback.print_exc()
        return False


def worker_thread(worker_id):
    """Worker thread that continuously processes messages from RabbitMQ"""
    print(f"[Worker {worker_id}] Started")
    
    # Connect to RabbitMQ
    try:
        credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
        parameters = pika.ConnectionParameters(
            host=RABBITMQ_HOST,
            port=RABBITMQ_PORT,
            credentials=credentials,
            heartbeat=600,
            blocked_connection_timeout=300
        )
        
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
        
        # Declare queue
        channel.queue_declare(queue=SCORING_QUEUE, durable=True)
        
        # Set QoS - only process 1 message at a time
        channel.basic_qos(prefetch_count=1)
        
        print(f"[Worker {worker_id}] Connected to RabbitMQ")
        print(f"[Worker {worker_id}] Listening to queue: {SCORING_QUEUE}")
        
    except Exception as e:
        print(f"[Worker {worker_id}] Failed to connect to RabbitMQ: {e}")
        return
    
    def callback(ch, method, properties, body):
        """Process each message"""
        try:
            with stats['lock']:
                stats['processing'] += 1
            
            # Parse message
            message_data = json.loads(body)
            
            # Process
            success = process_message(message_data)
            
            if success:
                with stats['lock']:
                    stats['completed'] += 1
                ch.basic_ack(delivery_tag=method.delivery_tag)
            else:
                with stats['lock']:
                    stats['failed'] += 1
                # Don't requeue to avoid infinite loop
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            
            # Print stats
            print_stats()
        
        except Exception as e:
            print(f"[Worker {worker_id}] Fatal error: {e}")
            with stats['lock']:
                stats['failed'] += 1
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        
        finally:
            with stats['lock']:
                stats['processing'] -= 1
    
    try:
        # Start consuming
        channel.basic_consume(
            queue=SCORING_QUEUE,
            on_message_callback=callback,
            auto_ack=False
        )
        
        print(f"[Worker {worker_id}] Waiting for messages...")
        channel.start_consuming()
    
    except KeyboardInterrupt:
        print(f"\n[Worker {worker_id}] Interrupted")
    except Exception as e:
        print(f"[Worker {worker_id}] Error: {e}")
    finally:
        try:
            connection.close()
        except:
            pass
        print(f"[Worker {worker_id}] Stopped")


def main():
    print("="*60)
    print("PROFILE SCORING CONSUMER")
    print("="*60)
    
    # Check requirements directory
    if not os.path.exists(REQUIREMENTS_DIR):
        print(f"\n⚠ Requirements directory not found: {REQUIREMENTS_DIR}")
        print("Creating directory...")
        os.makedirs(REQUIREMENTS_DIR, exist_ok=True)
        print("✓ Please add requirements JSON files to this directory")
    
    # List available requirements
    req_files = [f for f in os.listdir(REQUIREMENTS_DIR) if f.endswith('.json')]
    if req_files:
        print(f"\n✓ Found {len(req_files)} requirements file(s):")
        for f in req_files:
            print(f"  - {f}")
    else:
        print(f"\n⚠ No requirements files found in {REQUIREMENTS_DIR}/")
        print("  Please add at least one requirements JSON file")
    
    # Get number of workers
    try:
        num_workers = int(input("\nNumber of workers (default 2): ").strip() or "2")
        if num_workers < 1:
            num_workers = 2
    except:
        num_workers = 2
    
    print(f"\n→ Configuration:")
    print(f"  - RabbitMQ: {RABBITMQ_HOST}:{RABBITMQ_PORT}")
    print(f"  - Queue: {SCORING_QUEUE}")
    print(f"  - Workers: {num_workers}")
    print(f"  - Output: {OUTPUT_DIR}/")
    
    # Test RabbitMQ connection
    print(f"\n→ Testing RabbitMQ connection...")
    try:
        credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
        parameters = pika.ConnectionParameters(
            host=RABBITMQ_HOST,
            port=RABBITMQ_PORT,
            credentials=credentials
        )
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
        
        # Declare queue
        result = channel.queue_declare(queue=SCORING_QUEUE, durable=True, passive=True)
        queue_size = result.method.message_count
        
        print(f"✓ Connected to RabbitMQ")
        print(f"  - Messages in queue: {queue_size}")
        
        connection.close()
    except Exception as e:
        print(f"✗ Failed to connect to RabbitMQ: {e}")
        print("\nMake sure RabbitMQ is running:")
        print("  docker-compose up -d")
        return
    
    # Start workers
    print(f"\n→ Starting {num_workers} workers...")
    print("  Press Ctrl+C to stop")
    
    threads = []
    for i in range(num_workers):
        t = threading.Thread(target=worker_thread, args=(i+1,), daemon=True)
        t.start()
        threads.append(t)
        time.sleep(0.5)
    
    print(f"\n✓ All {num_workers} workers are running!")
    print("  Waiting for messages from crawler...")
    
    try:
        # Keep main thread alive
        while True:
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\n\n⚠ Interrupted by user. Stopping all workers...")
        print("  (Workers will finish current tasks)")
    
    finally:
        # Wait for workers to finish
        time.sleep(2)
        
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
