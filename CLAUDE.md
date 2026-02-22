# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A scheduled automation that scrapes solar power generation data from the Hyundai ES portal and reports it via Kakao Talk. Runs on GitHub Actions on a cron schedule during Korean daylight hours.

## Setup & Running

```bash
pip install -r requirements.txt
playwright install chromium --with-deps
python main.py
```

There are no tests or linting configurations in this project.

## Architecture

Three-module pipeline:

1. **`get_data.py`** — Playwright-based scraper that logs into `https://hs3.hyundai-es.co.kr`, navigates to the power generation dashboard, and extracts generation times for two plants using XPath selectors. Returns a dict with keys `발전소1_발전시간` and `발전소2_발전시간`.

2. **`telegram.py`** — Sends the formatted message via the Telegram Bot API (`sendMessage`). Requires a bot token and target chat ID.

3. **`main.py`** — Entry point. Gets current KST time, calls `get_data.py`, formats output, and calls `kakao.py` to send the message.

## Environment Variables

Required at runtime (configured as GitHub Actions secrets):

| Variable | Purpose |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Telegram Bot token from BotFather |
| `TELEGRAM_CHAT_ID` | Target chat/user ID to send messages to |

## GitHub Actions Workflow

`.github/workflows/solar_monitor.yml` runs on a cron schedule covering 6:00–19:00 KST (21:00–10:00 UTC) and supports `workflow_dispatch` for manual runs. The job uses Ubuntu, Python 3.11, and Playwright Chromium.
