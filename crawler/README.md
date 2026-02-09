# LinkedIn Profile Scraper

Scraper LinkedIn profiles dengan RabbitMQ queue system.

## Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Setup .env
```bash
cp .env.example .env
```
Edit `.env` dan isi credentials LinkedIn lu.

### 3. Start RabbitMQ
```bash
docker-compose up -d
```

## Usage

### Simple Mode (Tanpa RabbitMQ)
```bash
python main.py
```
Input URLs, tunggu selesai.

### RabbitMQ Mode (Recommended untuk banyak URLs)

**Terminal 1 - Start Workers:**
```bash
python consumer_multi.py
```
Input jumlah workers (default 3), workers jalan terus otomatis.

**Terminal 2 - Add URLs:**
```bash
python producer.py
```
Input URLs kapan aja, workers langsung process.

## Monitoring

RabbitMQ Management UI: http://localhost:15672
- Login: `guest` / `guest`

## Output

JSON files di folder: `data/output/`

## Data Structure

```json
{
  "profile_url": "...",
  "name": "...",
  "about": "...",
  "experiences": [...],
  "education": [...],
  "skills": [...],
  "projects": [...],
  "honors": [...],
  "languages": [...],
  "licenses": [...],
  "courses": [...],
  "volunteering": [...],
  "test_scores": [...]
}
```

## Files

- `main.py` - Simple mode (queue biasa)
- `producer.py` - Add URLs ke RabbitMQ
- `consumer_multi.py` - Process URLs dengan multiple workers
- `crawler.py` - Main scraper logic
- `helper/` - Helper functions
