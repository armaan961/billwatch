"""Tools for BillWatch AI Agent.

This module provides Strands-compatible tools for:
1. Fetching upcoming bills from data/bills.csv
2. Calculating bill urgency based on due dates
3. Dispatching formatted, timestamped notifications
"""

from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List
import pandas as pd
from strands import tool

# Reference data path
DATA_DIR = Path(__file__).resolve().parent / "data"
DEFAULT_BILLS_PATH = DATA_DIR / "bills.csv"


@tool
def get_upcoming_bills() -> List[Dict[str, Any]]:
    """Fetch the list of upcoming bills from the local storage (data/bills.csv).

    Reads the CSV data file using pandas and converts each row into a dictionary
    containing bill details: name, amount, due_date, autopay, and status.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, where each dictionary
        represents a bill record with keys: 'name', 'amount', 'due_date',
        'autopay', and 'status'.
    """
    csv_path = DEFAULT_BILLS_PATH
    if not csv_path.exists():
        # Fallback check for relative execution paths
        csv_path = Path("data/bills.csv")

    if not csv_path.exists():
        raise FileNotFoundError(f"Bills data file not found at {csv_path.resolve()}")

    df = pd.read_csv(csv_path)

    # Clean and convert types cleanly
    df["name"] = df["name"].astype(str)
    df["amount"] = df["amount"].astype(float)
    df["due_date"] = df["due_date"].astype(str)
    df["autopay"] = df["autopay"].astype(bool)
    df["status"] = df["status"].astype(str)

    return df.to_dict(orient="records")


@tool
def check_urgency(bill: Dict[str, Any]) -> str:
    """Evaluate how urgent a bill is by comparing its due date to today's date.

    Args:
        bill (Dict[str, Any]): A dictionary containing at least the 'due_date' key
            formatted as 'YYYY-MM-DD'. Example: {'name': 'Electric', 'due_date': '2026-08-20'}

    Returns:
        str: Urgency status:
            - 'overdue' if the due date is strictly in the past (< today)
            - 'due_soon' if the due date is today or within the next 3 days (0 to 3 days)
            - 'fine' if the due date is more than 3 days in the future
    """
    due_date_raw = bill.get("due_date")
    if not due_date_raw:
        raise ValueError(f"Bill record is missing required 'due_date' field: {bill}")

    if isinstance(due_date_raw, str):
        due_date = datetime.strptime(due_date_raw.strip(), "%Y-%m-%d").date()
    elif isinstance(due_date_raw, (datetime, date)):
        due_date = due_date_raw if isinstance(due_date_raw, date) else due_date_raw.date()
    else:
        raise ValueError(f"Unsupported due_date type: {type(due_date_raw)}")

    today = date.today()
    delta_days = (due_date - today).days

    if delta_days < 0:
        return "overdue"
    elif 0 <= delta_days <= 3:
        return "due_soon"
    else:
        return "fine"


@tool
def send_notification(message: str) -> str:
    """Send an alert/notification to the user with a timestamp.

    Prints the notification message with an ISO formatted timestamp to the console
    and returns a confirmation message string.

    Args:
        message (str): The notification text to dispatch to the user.

    Returns:
        str: Confirmation string verifying the notification was dispatched.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_msg = f"[{timestamp}] NOTIFICATION: {message}"
    print(formatted_msg)
    return f"Notification sent successfully at {timestamp}: {message}"
