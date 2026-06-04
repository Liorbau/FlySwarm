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

  const timeSpan = document.createElement("span");
  timeSpan.textContent = `[${timestamp}]`;

  const agentSpan = document.createElement("span");
  const agentClass = AGENT_CLASS_MAP[step.agent] || "";
  agentSpan.className = `agent-tag ${agentClass}`.trim();
  agentSpan.textContent = step.agent;

  const logText = document.createTextNode(` ${step.log}`);

  entry.appendChild(timeSpan);
  entry.appendChild(document.createTextNode(" "));
  entry.appendChild(agentSpan);
  entry.appendChild(logText);
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
