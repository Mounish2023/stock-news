# Daily Stock Report Generator - Setup Guide

This script fetches your Robinhood stock positions, gets the latest news for each stock, generates summaries using Claude, and emails you a daily report.

## Setup Instructions

### 1. Install Required Packages

```bash
pip install -r requirements.txt
```

### 2. Set Up Environment Variables

Create a `.env` file in the same directory as the script with the following variables (see `.env.example`):

```
# Robinhood credentials
ROBINHOOD_USERNAME=your_robinhood_email@example.com
ROBINHOOD_PASSWORD=your_robinhood_password

# API keys
SONAR_API_KEY=your_sonar_api_key
OPENAI_API_KEY=your_openai_api_key

# Email configuration
EMAIL_ADDRESS=your_email@gmail.com
EMAIL_APP_PASSWORD=your_app_password_for_gmail
RECIPIENT_EMAIL=recipient@example.com

# Set to 'true' to run the report immediately when script starts (for testing)
RUN_IMMEDIATELY=false
```

### 3. Obtain Required API Keys and Credentials

#### Robinhood Authentication
Use your regular Robinhood login credentials. If you have two-factor authentication enabled, you may need to temporarily disable it or handle the challenge in the script.
#### Robinhood API
1. Clone the [robin_stocks](https://github.com/jmfernandes/robin_stocks) repository
2. Replace `robin_stocks/robin_stocks/robinhood/authentication.py` with the version provided in this repository


#### Sonar API
1. Sign up at [Sonar API](https://www.sonar.com/)
2. Subscribe to their stock news API
3. Generate an API key from your dashboard

#### OpenAI API (Claude)
1. Sign up at [OpenAI](https://openai.com/)
2. Create an API key in your account settings

#### Gmail Setup
For the email functionality, you'll need to:
1. Enable 2-Step Verification on your Google account
2. Create an App Password:
   - Go to [Google Account Security](https://myaccount.google.com/security)
   - Find "App passwords" under the 2-Step Verification section
   - Generate a new app password for "Mail"
   - Use this password in your `.env` file (not your regular Gmail password)

### 4. Run the Script Manually (For Testing)

Set `RUN_IMMEDIATELY=true` in your `.env` file, then:

```bash
python daily_stock_report.py
```

If everything works, you should receive an email with your stock report.

### 5. Deploy for Scheduled Running

#### Method 1: Keep the Script Running
The script contains its own scheduler that will run at 8:00 AM daily:

```bash
# Set RUN_IMMEDIATELY=false in .env
python daily_stock_report.py
```

You can use a terminal multiplexer like `screen` or `tmux` to keep it running on a server:
```bash
screen -S stock_report
python daily_stock_report.py
# Press Ctrl+A, then D to detach
```

#### Method 2: Use Cron (Linux/Mac)

```bash
# Edit crontab
crontab -e

# Add this line to run at 8:00 AM every day
0 8 * * * cd /path/to/script/directory && python daily_stock_report.py
```

#### Method 3: Task Scheduler (Windows)

1. Create a batch file `run_stock_report.bat`:
   ```
   @echo off
   cd C:\path\to\script\directory
   python daily_stock_report.py
   ```
2. Open Task Scheduler
3. Create Basic Task → Set trigger time to 8:00 AM daily → Action: Start a program → Browse to your .bat file

## Customization Options

- To change the report time, modify the line in `schedule_and_run()` function:
  ```python
  schedule.every().day.at("08:00").do(run_daily_report)
  ```

- To change the number of news articles fetched per stock, modify the `limit` parameter in `get_stock_news()` function.

- You can customize the email report template by editing the HTML in the `create_email_report()` function.

## Troubleshooting

Check the `stock_report.log` file for detailed logs and error messages if the script isn't working as expected.

Common issues:
- Invalid Robinhood credentials
- API rate limits exceeded
- Email authentication problems (make sure you're using an App Password)
