# DE Platform

Data engineering platform for real-time and batch processing.

## Stack
- **Ingestion:** Python, Kafka, Airbyte
- **Processing:** Apache Spark, Kafka Streams
- **Warehouse:** Snowflake + dbt
- **Orchestration:** Apache Airflow
- **Cloud:** AWS (S3, MSK, Glue, ECS)

## Quick Start (WSL2 Terminal)
```bash
# ▶ Run in: WSL2 terminal (Ubuntu tab)

# 1. Clone into your Linux home — NOT /mnt/c/...
cd ~/projects
git clone https://github.com/yourorg/de-platform.git
cd de-platform

# 2. Create and activate Python virtual environment
python3.12 -m venv .venv
source .venv/bin/activate
# Prompt should show: (.venv) harsh@MSI:~/projects/de-platform$

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 4. Copy environment config
cp .env.example .env
# Edit .env with your credentials: nano .env  or open in Antigravity

# 5. Start local services (Docker Desktop must be running on Windows)
docker-compose up -d

# 6. Run tests
make test
```

## Project Structure
See [docs/architecture/overview.md](docs/architecture/overview.md) for full details.

## Contributing
See [CONTRIBUTING.md](CONTRIBUTING.md) for branching strategy and commit conventions.
