# Layer 1 Raw Deliverable (Code Blocks Only)

This document is the canonical Layer 1 deliverable in raw-LLM format: copy-paste code blocks and run instructions only.


## Run Instructions

```bash
mkdir -p backend frontend
# copy each code block below into the shown path
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
export STORAGE_BACKEND=json
uvicorn backend.main:app --reload
```

Open `http://127.0.0.1:8000` and verify:
- `GET /api/health` returns `{"status":"ok"}`.
- Demo button animates chat + agent log in order: Interface -> Orchestrator -> Fetching/API -> Analytics -> Notification.
- Waitlist form creates/appends to `emails.json` and returns duplicate message for repeated emails.

## Environment Note

- Use `STORAGE_BACKEND=json` (also reflected in `.env.example`).

## Code

### `backend/requirements.txt`

```txt
fastapi
uvicorn[standard]
pydantic[email]
```

### `backend/models.py`

```python
from datetime import datetime, timezone

from pydantic import BaseModel, EmailStr, Field


class SignupIn(BaseModel):
    email: EmailStr


class SignupRecord(BaseModel):
    email: EmailStr
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )
```

### `backend/storage.py`

```python
import json
import os
import tempfile
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import SignupRecord


class SignupRepository(ABC):
    @abstractmethod
    def add_signup(self, email: str) -> tuple[SignupRecord, bool]:
        """Return (record, created)."""


class JsonSignupRepository(SignupRepository):
    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path

    def add_signup(self, email: str) -> tuple[SignupRecord, bool]:
        normalized_email = email.strip().lower()
        records = self._read_records()

        for item in records:
            stored_email = str(item.get("email", "")).strip().lower()
            if stored_email == normalized_email:
                return SignupRecord(**item), False

        record = SignupRecord(
            email=normalized_email,
            created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )
        records.append(record.model_dump())
        self._write_records(records)
        return record, True

    def _read_records(self) -> list[dict[str, Any]]:
        if not self.file_path.exists():
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            self._write_records([])
            return []

        try:
            with self.file_path.open("r", encoding="utf-8") as source:
                payload = json.load(source)
        except json.JSONDecodeError:
            corrupt_name = (
                f"{self.file_path.stem}.corrupt."
                f"{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.json"
            )
            corrupt_path = self.file_path.with_name(corrupt_name)
            self.file_path.replace(corrupt_path)
            self._write_records([])
            return []

        if not isinstance(payload, list):
            self._write_records([])
            return []

        cleaned: list[dict[str, Any]] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            email = str(item.get("email", "")).strip().lower()
            created_at = str(item.get("created_at", "")).strip()
            if not email:
                continue
            if not created_at:
                created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
            cleaned.append({"email": email, "created_at": created_at})
        return cleaned

    def _write_records(self, records: list[dict[str, Any]]) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=self.file_path.parent,
            delete=False,
        ) as temp_file:
            json.dump(records, temp_file, indent=2)
            temp_file.write("\n")
            temp_path = Path(temp_file.name)
        os.replace(temp_path, self.file_path)


def get_repository() -> SignupRepository:
    backend = os.getenv("STORAGE_BACKEND", "json").strip().lower()
    project_root = Path(__file__).resolve().parents[1]
    emails_file = project_root / "emails.json"

    if backend == "json":
        return JsonSignupRepository(file_path=emails_file)

    raise ValueError(
        f"Unsupported STORAGE_BACKEND '{backend}'. "
        "Only 'json' is available in this landing-page scope."
    )
```

### `backend/main.py`

```python
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from .models import SignupIn
from .storage import get_repository

app = FastAPI(title="FlySwarm Landing Page API")
repository = get_repository()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/signup")
def signup(payload: SignupIn) -> dict[str, object]:
    try:
        record, created = repository.add_signup(payload.email)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to save signup") from exc

    return {
        "status": "success",
        "created": created,
        "record": record.model_dump(),
    }


project_root = Path(__file__).resolve().parents[1]
frontend_dir = project_root / "frontend"

if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
```

### `frontend/index.html`

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>FlySwarm | Personalized Flight Monitoring</title>
    <link rel="stylesheet" href="/styles.css" />
  </head>
  <body>
    <main class="page">
      <header class="hero">
        <p class="eyebrow">FlySwarm</p>
        <h1>Your personal flight-price monitoring swarm</h1>
        <p class="subtitle">
          Describe your ideal flight once, then let an AI-inspired swarm monitor prices
          and alert you when a meaningful drop appears.
        </p>
      </header>

      <section class="card features">
        <h2>How the swarm works</h2>
        <ul>
          <li>
            <strong>Interface Agent</strong> captures natural-language requests from
            chat.
          </li>
          <li>
            <strong>Orchestrator Agent</strong> schedules scans and manages rate
            budgets.
          </li>
          <li>
            <strong>Fetching/API Agent</strong> checks flight offers across providers.
          </li>
          <li>
            <strong>Analytics Agent</strong> evaluates trends and confirms true drops.
          </li>
          <li>
            <strong>Notification Agent</strong> sends useful alerts when deals appear.
          </li>
        </ul>
      </section>

      <section class="card demo">
        <div class="demo-header">
          <h2>Interactive demo</h2>
          <button id="demo-button" type="button">Try Telegram Demo</button>
        </div>
        <p class="demo-note">
          This is a simulated flow for the landing page only. No real Telegram or
          travel APIs are used.
        </p>
        <div class="demo-grid">
          <div class="panel">
            <h3>Telegram chat simulation</h3>
            <div id="chat-panel" class="chat-panel" aria-live="polite"></div>
          </div>
          <div class="panel">
            <h3>Live agent activity log</h3>
            <div id="agent-log" class="agent-log" aria-live="polite"></div>
          </div>
        </div>
      </section>

      <section class="card waitlist">
        <h2>Join the waitlist</h2>
        <p>Get early access updates as FlySwarm evolves.</p>
        <form id="waitlist-form" novalidate>
          <label for="email-input">Email</label>
          <div class="form-row">
            <input
              id="email-input"
              name="email"
              type="email"
              placeholder="you@example.com"
              required
            />
            <button id="submit-button" type="submit">Join</button>
          </div>
          <p id="form-status" class="form-status" role="status" aria-live="polite"></p>
        </form>
      </section>
    </main>
    <script src="/app.js" defer></script>
  </body>
</html>
```

### `frontend/styles.css`

```css
:root {
  color-scheme: dark;
  --bg: #0a0f1f;
  --bg-alt: #121a31;
  --text: #e8ecff;
  --muted: #aab5db;
  --line: #27345e;
  --accent: #5f8dff;
  --accent-2: #31d4b0;
  --danger: #ff6d8a;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: radial-gradient(circle at 20% 0%, #1a2b63 0%, var(--bg) 45%);
  color: var(--text);
}

.page {
  width: min(1040px, 92%);
  margin: 0 auto;
  padding: 3rem 0 4rem;
  display: grid;
  gap: 1.25rem;
}

.hero h1 {
  margin: 0.3rem 0 0.7rem;
  font-size: clamp(1.8rem, 3vw, 2.8rem);
}

.eyebrow {
  margin: 0;
  color: var(--accent-2);
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-size: 0.75rem;
}

.subtitle {
  margin: 0;
  max-width: 65ch;
  color: var(--muted);
  line-height: 1.5;
}

.card {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.03), rgba(0, 0, 0, 0.06));
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 1.25rem;
  backdrop-filter: blur(5px);
}

h2 {
  margin: 0 0 0.8rem;
}

.features ul {
  margin: 0;
  padding-left: 1rem;
  display: grid;
  gap: 0.6rem;
}

.features li {
  color: var(--muted);
}

.demo-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
}

button {
  border: 0;
  border-radius: 10px;
  padding: 0.65rem 1rem;
  font-weight: 600;
  cursor: pointer;
  background: linear-gradient(90deg, var(--accent), #819cff);
  color: #08112f;
}

button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.demo-note {
  margin: 0 0 1rem;
  color: var(--muted);
  font-size: 0.95rem;
}

.demo-grid {
  display: grid;
  gap: 1rem;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.panel {
  background: var(--bg-alt);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 0.8rem;
}

.panel h3 {
  margin: 0 0 0.6rem;
  font-size: 0.95rem;
  color: var(--muted);
}

.chat-panel,
.agent-log {
  min-height: 230px;
  max-height: 320px;
  overflow-y: auto;
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 0.75rem;
  background: #090d1a;
  display: grid;
  gap: 0.55rem;
}

.chat-msg {
  width: fit-content;
  max-width: 90%;
  padding: 0.55rem 0.7rem;
  border-radius: 10px;
  font-size: 0.92rem;
  line-height: 1.35;
}

.chat-msg.user {
  justify-self: end;
  background: #213464;
}

.chat-msg.bot {
  justify-self: start;
  background: #1a2948;
}

.log-entry {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.82rem;
  color: #d1dbff;
  line-height: 1.35;
}

.agent-tag {
  display: inline-block;
  min-width: 112px;
  font-weight: 700;
}

.agent-interface {
  color: #7fd2ff;
}

.agent-orchestrator {
  color: #b0a0ff;
}

.agent-fetching-api {
  color: #6be6c1;
}

.agent-analytics {
  color: #ffd27f;
}

.agent-notification {
  color: #ff8faf;
}

.waitlist p {
  color: var(--muted);
  margin-top: 0;
}

.form-row {
  display: flex;
  gap: 0.6rem;
}

input[type="email"] {
  flex: 1;
  border: 1px solid var(--line);
  background: #090d1a;
  color: var(--text);
  border-radius: 10px;
  padding: 0.65rem 0.8rem;
  font-size: 0.95rem;
}

.form-status {
  min-height: 1.3rem;
  margin: 0.6rem 0 0;
  font-size: 0.92rem;
}

.form-status.success {
  color: var(--accent-2);
}

.form-status.error {
  color: var(--danger);
}

@media (max-width: 860px) {
  .demo-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 620px) {
  .demo-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .form-row {
    flex-direction: column;
  }

  button {
    width: 100%;
  }
}
```

### `frontend/app.js`

```javascript
const demoButton = document.getElementById("demo-button");
const chatPanel = document.getElementById("chat-panel");
const agentLog = document.getElementById("agent-log");
const waitlistForm = document.getElementById("waitlist-form");
const emailInput = document.getElementById("email-input");
const submitButton = document.getElementById("submit-button");
const formStatus = document.getElementById("form-status");

const demoSteps = [
  {
    delay: 450,
    agent: "Interface",
    log: 'Parsed request: "TLV -> NYC, under $450, Jun".',
    chat: {
      speaker: "user",
      message: "Track TLV to NYC for June, budget under $450.",
    },
  },
  {
    delay: 900,
    agent: "Orchestrator",
    log: "Scheduled scan and verified provider rate budget.",
  },
  {
    delay: 1200,
    agent: "Fetching/API",
    log: "Queried providers and returned 3 fare candidates.",
  },
  {
    delay: 1550,
    agent: "Analytics",
    log: "Compared history: $612 -> $438 (-28% vs 30-day average).",
  },
  {
    delay: 1950,
    agent: "Notification",
    log: "Prepared and sent booking alert to Telegram user.",
    chat: {
      speaker: "bot",
      message:
        "Price drop found: TLV -> NYC now $438 in June. That's 28% below recent trend.",
    },
  },
];

const AGENT_CLASS_MAP = {
  Interface: "agent-interface",
  Orchestrator: "agent-orchestrator",
  "Fetching/API": "agent-fetching-api",
  Analytics: "agent-analytics",
  Notification: "agent-notification",
};

function clearDemoPanels() {
  chatPanel.innerHTML = "";
  agentLog.innerHTML = "";
}

function appendChatMessage(stepChat) {
  const line = document.createElement("div");
  line.className = `chat-msg ${stepChat.speaker}`;
  line.textContent = stepChat.message;
  chatPanel.appendChild(line);
  chatPanel.scrollTop = chatPanel.scrollHeight;
}

function appendLogEntry(step) {
  const entry = document.createElement("div");
  entry.className = "log-entry";

  const timestamp = new Date().toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });

  const agentClass = AGENT_CLASS_MAP[step.agent] || "";
  entry.innerHTML = `<span>[${timestamp}]</span> <span class="agent-tag ${agentClass}">${step.agent}</span> ${step.log}`;
  agentLog.appendChild(entry);
  agentLog.scrollTop = agentLog.scrollHeight;
}

function runDemo() {
  clearDemoPanels();
  demoButton.disabled = true;
  demoButton.textContent = "Running demo...";

  let finishedCount = 0;
  demoSteps.forEach((step) => {
    window.setTimeout(() => {
      appendLogEntry(step);
      if (step.chat) {
        appendChatMessage(step.chat);
      }
      finishedCount += 1;
      if (finishedCount === demoSteps.length) {
        demoButton.disabled = false;
        demoButton.textContent = "Replay Demo";
      }
    }, step.delay);
  });
}

async function submitWaitlist(event) {
  event.preventDefault();

  formStatus.className = "form-status";
  formStatus.textContent = "";

  const email = emailInput.value.trim();
  if (!email) {
    formStatus.classList.add("error");
    formStatus.textContent = "Please enter an email address.";
    return;
  }

  submitButton.disabled = true;
  submitButton.textContent = "Saving...";

  try {
    const response = await fetch("/api/signup", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ email }),
    });

    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.detail || "Request failed");
    }

    formStatus.classList.add("success");
    if (payload.created) {
      formStatus.textContent = "You're on the waitlist. We'll keep you posted.";
    } else {
      formStatus.textContent = "You're already on the waitlist.";
    }
    waitlistForm.reset();
  } catch (error) {
    formStatus.classList.add("error");
    formStatus.textContent =
      error instanceof Error
        ? `Could not save signup: ${error.message}`
        : "Could not save signup. Please try again.";
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = "Join";
  }
}

demoButton.addEventListener("click", runDemo);
waitlistForm.addEventListener("submit", submitWaitlist);
```

