# URL Shortener

A simple, lightweight URL shortening service built using **Python** and **Supabase**.

## TL;DR

A highly scalable, low-latency URL shortener built with:
- A conflict-free range-based code generator,
- A hybrid local (SQLite) + remote (Supabase PostgreSQL) database architecture,
- And a fully asynchronous backend that ensures fast reads, durable writes, and graceful shutdown.

## Tech Stack
- **Backend**: Python (FastAPI)
- **Database**: Supabase (PostgreSQL)
- **Scripts**: Bash

## Setup Instructions

1. **Clone the repository**
   ```bash
   git clone https://github.com/debayangg/url-shortner.git
   cd url-shortner
   ```
2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
3. **Prepare environment variables**
   ```ini
   POSTGRES_URI=your-supabase-postgres-connection-string
   ```
4. **Make the startup script executable**
   ```bash
   chmod +x start.sh
   ```
5. **Setup Supabase**
   Use supabase.sql to create necessary tables in your Supabase project.
6. **Run Project**
   ```bash
   ./start.sh
   ```

## Project Structure

```bash
url-shortner/
├── app.py             # Main FastAPI application server
├── codeGenerator.py   # Generates unique short codes
├── database.py        # Handles database operations with Supabase
├── utils.py           # Helper functions
├── start.sh           # Shell script to start the server
├── requirements.txt   # Python dependencies
├── supabase.sql       # SQL file to set up the Supabase database
└── README.md          # Project documentation
```

## Salient Features

- **Range-Based Code Generator**
  - Codes are generated in sequential ranges rather than randomly.
  - This avoids the common pitfall of generating random codes and checking for conflicts against existing ones.
  - Guarantees that all codes are **unique** without requiring expensive database lookups.
  - Prevents **hash collisions** and improves overall scalability.
  - A **lower availability threshold** is maintained; when the number of available codes falls below this threshold, a new batch is automatically generated in advance.

- **Minimalist Database Design**
  - The database schema is intentionally simple, storing only two key elements:
    - Link-to-code mappings
    - A single `current_max` value to track the next available code.
  - This minimalistic design keeps database operations lightweight and efficient, leading to **faster lookups** and **inserts** with minimal complexity.

- **Hybrid Local + Remote Database Architecture**
  - Combines a local embedded **SQLite** database with a remote **Supabase PostgreSQL** server.
  - **Reads** are served exclusively from the local SQLite database, ensuring **low-latency** and **high-speed** responses.
  - **Writes** are synchronized to both databases:
    - Immediate writes to the local database.
    - Background coroutine handles asynchronous writes to Supabase, ensuring **data durability** without blocking request handling.
  - This hybrid approach eliminates dependency on network latency for reads and **offloads** the remote database under heavy load.

- **Fully Asynchronous Backend**
  - The entire backend is built using **asynchronous programming paradigms**.
  - Enables the server to handle a large number of concurrent requests efficiently.
  - Significantly improves **responsiveness**, **throughput**, and **scalability** under high traffic conditions.

- **Startup Synchronization and Graceful Shutdown**
  - On startup, all existing link mappings are **synchronized** from the remote Supabase database into the local SQLite database.
  - Ensures that the local database is fully updated before the server begins handling requests.
  - A **graceful shutdown mechanism** ensures that all pending writes are **flushed** to the remote database before termination, guaranteeing **no data loss**.

Results:
- Shortening Endpoint can handle 2000 RPS
- Re-Routing Endpoint can handle 1500 RPS
