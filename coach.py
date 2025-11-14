#!/usr/bin/env python3
import csv, os, sys, json, math, argparse, datetime as dt
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

try:
    import yaml
except Exception:
    yaml = None

try:
    from openai import OpenAI
except Exception:
    OpenAI = None
import requests

DATA_FILE = "tasks.csv"
CONFIG_FILE = "config.yaml"
DEFAULT_MODEL = "gpt-4o-mini"

SYSTEM_PROMPT = """You are an adaptive personal coach. You output ONE actionable task for TODAY,
focused on the target skill, reflecting the user's recent performance. Be concrete, measurable,
and bias toward tasks that can be finished within the proposed time. Always return STRICT JSON
matching the provided schema. Avoid meta commentary.
"""

USER_PROMPT_TEMPLATE = """Target area: {area}
Recent history (most recent first, up to last 5 days):
{history}

Constraints:
- Prefer estimated time near {target_min} minutes (±20% unless history suggests otherwise).
- Goal size is an integer 1–5 (1 tiny … 5 stretch). Use history to scale up/down.
- Return strict JSON with keys: task_title, task_description, time_minutes, goal_size, why_it_matters, acceptance_criteria (list).

Difficulty = time_minutes × goal_size. Stay realistic and single-focus.
"""

def ensure_csv():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["date","area","task_title","task_description","time_minutes","goal_size",
                        "difficulty","status","notes","score","actual_minutes"])

def call_openai_fallback(area) :
