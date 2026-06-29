# Code Review Agent

Code Review Agent is a production-ready, asynchronous multi-agent orchestrator designed to automate code reviews on pull requests. Powered by LangGraph and FastAPI, the system analyzes pull requests concurrently using specialized domain agents, synthesizes the findings, and publishes actionable code review reports directly to GitHub.

---

## Technical Overview

Code Review Agent handles code review operations by routing GitHub webhooks through a high-performance background queue to a compiled state graph:

```
                  [ GitHub Pull Request Event ]
                                │
                                ▼ HTTP POST
                    [ FastAPI /api/webhook ]
                                │ (Validates HMAC-SHA256 Signature)
                                ▼
                       [ Redis Job Queue ]
                                │
                                ▼
                     [ ARQ Review Executor ]
                                │
                                ▼ (Initiates LangGraph Workflow)
                      +─────────────────+
                      │  Context Loader │ (Fetches Metadata & Diff)
                      +────────┬────────+
                               │
            ┌──────────────────┼──────────────────┐ (Concurrently)
            ▼                  ▼                  ▼
     +─────────────+    +─────────────+    +─────────────+
     │   Quality   │    │  Security   │    │ Performance │
     │  Inspector  │    │   Auditor   │    │  Analyzer   │
     +──────┬──────+    +──────┬──────+    +──────┬──────+
            │                  │                  │
            └──────────────────┼──────────────────┘ (Fars In)
                               ▼
                      +─────────────────+
                      │     Review      │
                      │   Synthesizer   │ (Aggregates reports into Markdown)
                      +────────┬────────+
                               │
                               ▼
                [ Published Comment on GitHub ]
```

---

## Directory Structure

The project conforms to clean architectural patterns, isolating domain-specific entities from infrastructure and routing layers:

```
aegis-core/
│
├── app/
│   ├── main.py                        # FastAPI startup and lifecycle configuration
│   │
│   ├── api/
│   │   ├── dependencies.py            # API request dependency injection points
│   │   └── github_events.py           # Webhook receiver and queue dispatcher
│   │
│   ├── core/
│   │   ├── config.py                  # Pydantic environment configuration
│   │   ├── exception.py               # Application-specific exception hierarchy
│   │   ├── logger.py                  # Loguru logging setup and log rotation
│   │   └── security.py                # Cryptographic payload verification (HMAC)
│   │
│   ├── domain/
│   │   ├── constants.py               # Centralized domain enumerations
│   │   └── data_models.py             # Pydantic schemas for data validation
│   │
│   ├── workflow/
│   │   ├── context.py                 # LangGraph shared execution state
│   │   ├── orchestrator.py            # LangGraph state machine definition
│   │   └── agents/
│   │       ├── context_loader.py      # Extracts PR metadata and raw diffs
│   │       ├── quality_inspector.py   # Analysis agent for maintainability
│   │       ├── security_auditor.py    # Analysis agent for vulnerabilities and secrets
│   │       ├── performance_analyzer.py# Analysis agent for computation speed and scale
│   │       └── review_synthesizer.py  # Aggregates analysis outputs into the final report
│   │
│   ├── integrations/
│   │   ├── github_client.py           # Wrapper client for GitHub REST/GraphQL API
│   │   └── llm/
│   │       ├── base.py                # Abstract LLM communication layer
│   │       ├── claude.py              # Anthropic Claude provider client
│   │       └── openai.py              # OpenAI API provider client
│   │
│   ├── prompts/
│   │   └── system_instructions.py     # System instructions and personas for LLM nodes
│   │
│   └── jobs/
│       └── review_executor.py         # ARQ worker task declarations
│
├── scripts/
│   ├── sample_code.py                 # Target source file containing issues for testing
│   └── test_pr_review.py              # Local offline pipeline simulation tool
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── requirements-dev.txt
```

---

## Local Setup

### Prerequisites

* Python 3.11+
* Redis Server (installed locally or running in Docker)
* Active OpenAI API Key or Anthropic API Key
* GitHub Personal Access Token (Classic) with `repo` and `write:discussion` permissions

### Step 1: Clone and Configure Environment

1. Copy the template settings:
   ```bash
   cp .env.example .env
   ```
2. Configure `.env` with your API credentials:
   ```env
   # Setup active LLM Provider ("openai" or "claude")
   LLM_PROVIDER=openai
   OPENAI_API_KEY=sk-xxxx...
   OPENAI_MODEL=gpt-4o-mini

   # GitHub settings
   GITHUB_TOKEN=ghp_xxxx...
   GITHUB_WEBHOOK_SECRET=my_cryptographic_webhook_secret
   GITHUB_REPO_OWNER=my-github-username
   GITHUB_REPO_NAME=my-target-repository

   # Redis Configuration
   REDIS_URL=redis://localhost:6379
   ```

---

## Integrating with Your Own Repository

Integrating Code Review Agent with your own repository requires deploying the application to a server (or keeping a local machine active with ngrok) and configuring a GitHub Webhook to send pull request events to it:

1. **Deploy Code Review Agent**: Host the Code Review Agent API, worker, and Redis queue on a server (e.g. EC2, DigitalOcean, Railway, or Render) so it is publicly accessible from the internet.
2. **Generate GitHub Personal Access Token (PAT)**:
   - On the repository owner's GitHub account, go to **Settings ➔ Developer Settings ➔ Personal access tokens (Classic)**.
   - Click **Generate new token (classic)**, check **repo** and **write:discussion** scopes, and generate the token.
   - Configure this value as `GITHUB_TOKEN` on your Code Review Agent server.
3. **Register the Webhook**:
   - Go to your target GitHub repository, then click **Settings ➔ Webhooks ➔ Add Webhook**.
   - **Payload URL**: `https://<YOUR_DEPLOYED_AEGIS_DOMAIN>/api/webhook`
   - **Content type**: `application/json`
   - **Secret**: Set a secure random string (ensure it matches `GITHUB_WEBHOOK_SECRET` in your server's `.env`).
   - **Events**: Select **Let me select individual events**, check **Pull requests**, and uncheck everything else.
   - Click **Add Webhook**.
4. **Configure Target Repository details**:
   - On your Code Review Agent server, configure `GITHUB_REPO_OWNER` and `GITHUB_REPO_NAME` to match the target repository details.
5. **Open a PR**:
   - Any pull request lifecycle actions (opened, synchronized, or reopened) in that repository will now automatically trigger a webhook event. Code Review Agent will process the diff and post the review comment back to the PR within 30 seconds.

---

## Testing Methodologies

Code Review Agent provides two distinct methods for testing: **Offline Simulation** (verifying LLM output and LangGraph routing) and **End-to-End Live Webhook Testing** (verifying FastAPI, Redis, and GitHub integrations).

### Method 1: Local Dry Run (Offline Simulation)
This method runs the entire agent workflow locally against a mock Pull Request diff (`scripts/sample_code.py`). It makes real LLM API calls to analyze quality, security, and performance, then outputs the final markdown comment straight to the console without needing Redis, FastAPI, or GitHub webhooks.

1. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```
2. Execute the dry run script:
   ```bash
   python scripts/test_pr_review.py
   ```
3. **Expected Output:**
   You will see logs of the mock loader, parallel execution of the inspectors, and the final combined review containing security findings (e.g. hardcoded API keys) and performance warnings.

---

### Method 2: End-to-End Webhook Testing (Live Flow)
To verify the complete integration (GitHub webhooks ➔ FastAPI ➔ Redis ➔ ARQ ➔ GitHub Comment Posting):

#### 1. Spin up Redis
If you have Docker installed, you can spin up Redis easily:
```bash
docker run -d -p 6379:6379 redis:7-alpine
```

#### 2. Start the FastAPI API Server
Start the web server to listen for webhook payloads on port 8000:
```bash
uvicorn app.main:app --reload --port 8000
```
Verify the server is up by hitting the health endpoint:
```bash
curl http://localhost:8000/health
```

#### 3. Run the ARQ Worker Queue
In a new terminal window, start the worker process that consumes review tasks from Redis:
```bash
arq app.jobs.review_executor.WorkerSettings
```

#### 4. Expose FastAPI using ngrok
To allow GitHub's servers to send webhooks to your local machine, expose your local port 8000 to the web:
```bash
ngrok http 8000
```
Copy the secure `https` URL generated by ngrok (e.g., `https://abc1234.ngrok-free.app`).

#### 5. Configure GitHub Webhook
1. Navigate to your target repository on GitHub: **Settings ➔ Webhooks ➔ Add webhook**.
2. Set **Payload URL** to: `https://[YOUR_NGROK_SUBDOMAIN].ngrok-free.app/api/webhook`
3. Set **Content type** to: `application/json`
4. Set **Secret** to match `GITHUB_WEBHOOK_SECRET` in your `.env`.
5. Under "Which events would you like to trigger this webhook?", select **Let me select individual events** and check **Pull requests**. Uncheck everything else.
6. Click **Add webhook**.

#### 6. Trigger the Workflow
Create a new branch in your repo, commit changes (you can commit the bad patterns in `scripts/sample_code.py` to trigger warnings), push the branch, and open a Pull Request.

Within 30 seconds, Code Review Agent will process the webhook, execute the agent graph, and post the synthesized markdown review comment on your Pull Request discussion timeline.

---

## Running with Docker Compose

To deploy the entire production stack (FastAPI application, ARQ background worker, and Redis server) with single-command orchestration:

```bash
# Build and run containers
docker compose up --build

# Run in background (detached mode)
docker compose up -d

# View real-time logs across all services
docker compose logs -f
```