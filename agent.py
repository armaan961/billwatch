"""BillWatch Autonomous AI Agent.

Built with the Strands Agents SDK for AWS "Agents for Humans" Hackathon.
Monitors recurring bills, detects overdue/due-soon items, and dispatches timely alerts.
"""

import argparse
from datetime import datetime
import os
from pathlib import Path
import sys
import time
from dotenv import load_dotenv

# Ensure local imports work regardless of execution directory
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from tools import check_urgency, get_upcoming_bills, send_notification

# Load environment variables (.env in current directory or agent directory)
load_dotenv(dotenv_path=CURRENT_DIR / ".env")
load_dotenv()

SYSTEM_PROMPT = (
    "You are BillWatch, an autonomous agent that monitors a user's bills. "
    "Check all upcoming bills. Only call send_notification for bills that are overdue "
    "or due_soon. Stay silent about bills that are fine. When you do notify, be specific: "
    "bill name, amount, due date, and whether autopay is on."
)


def get_anthropic_model(api_key: str):
    """Initialize AnthropicModel with direct Anthropic API key."""
    from strands.models.anthropic import AnthropicModel

    return AnthropicModel(
        client_args={"api_key": api_key},
        model_id="claude-3-5-sonnet-20241022",
        max_tokens=1024,
    )


def create_agent(api_key: str):
    """Create a Strands Agent configured with tools and system prompt."""
    from strands import Agent

    model = get_anthropic_model(api_key)
    agent = Agent(
        model=model,
        tools=[get_upcoming_bills, check_urgency, send_notification],
        system_prompt=SYSTEM_PROMPT,
    )
    return agent


def run_simulated_check():
    """Fallback execution demonstrating autonomous tool-calling logic.

    Used when ANTHROPIC_API_KEY is not configured or in offline demo environments.
    """
    print("\n--- BillWatch Autonomous Check (Simulated Mode) ---")
    bills = get_upcoming_bills()
    print(f"Loaded {len(bills)} bill records.")

    for bill in bills:
        urgency = check_urgency(bill)
        if urgency in ("overdue", "due_soon"):
            status_desc = "OVERDUE" if urgency == "overdue" else "DUE SOON"
            autopay_str = "ON" if bill.get("autopay") else "OFF"
            msg = (
                f"[{status_desc}] {bill['name']} of ${bill['amount']:.2f} "
                f"is due on {bill['due_date']} (Autopay: {autopay_str}). "
                f"Status: {bill['status']}."
            )
            send_notification(msg)
        else:
            # Stay silent about fine bills as instructed in system prompt
            pass

    print("Check complete. Processed all bills.\n")


def check_bills_cycle(agent=None):
    """Execute a single bill monitoring cycle."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] checking bills...")

    if agent is not None:
        try:
            prompt = (
                "Perform a scheduled check of all upcoming bills. Review each bill, "
                "evaluate its urgency, and notify the user about any overdue or due soon bills."
            )
            result = agent(prompt)
            if result:
                print(f"Agent Response: {result}")
        except Exception as e:
            print(f"Notice: LLM invocation failed ({e}). Falling back to direct tool execution:")
            run_simulated_check()
    else:
        run_simulated_check()


def run_once(agent=None):
    """Run a single check and exit."""
    check_bills_cycle(agent=agent)


def run_forever(agent=None, interval_seconds: int = 60):
    """Run continuous monitoring loop checking every interval_seconds."""
    print(f"Starting BillWatch continuous monitoring (interval: {interval_seconds}s). Press Ctrl+C to stop.\n")
    try:
        while True:
            check_bills_cycle(agent=agent)
            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        print("\nBillWatch monitoring stopped by user.")


def main():
    parser = argparse.ArgumentParser(
        description="BillWatch - Autonomous Bill Tracking & Reminder Agent (Strands SDK)"
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--once",
        action="store_true",
        help="Run a single bill check cycle and exit.",
    )
    mode_group.add_argument(
        "--loop",
        action="store_true",
        help="Run continuous autonomous background monitoring (checks every 60s).",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Interval in seconds for continuous monitoring (default: 60).",
    )

    args = parser.parse_args()

    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    agent = None

    if not api_key or api_key == "your_key_here":
        print(
            "INFO: No active ANTHROPIC_API_KEY detected in .env. Running in simulated agent mode.\n"
            "(To use live Claude LLM reasoning, add ANTHROPIC_API_KEY=your_key to billwatch/.env)\n"
        )
    else:
        try:
            agent = create_agent(api_key)
            print("INFO: Initialized Strands Agent with Anthropic Claude model.\n")
        except Exception as err:
            print(f"WARNING: Could not initialize AnthropicModel ({err}). Using tool-driven fallback.\n")

    # Default to --once if neither flag is specified
    if args.loop:
        run_forever(agent=agent, interval_seconds=args.interval)
    else:
        run_once(agent=agent)


if __name__ == "__main__":
    main()
