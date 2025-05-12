import os
import requests
import datetime
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import robin_stocks.robinhood as rh
import schedule
import time
import logging
from dotenv import load_dotenv
from openai import OpenAI


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("stock_report.log"),
        logging.StreamHandler()
    ]
)

# Load environment variables
load_dotenv()

# API credentials
ROBINHOOD_USERNAME = os.getenv('ROBINHOOD_USERNAME')
ROBINHOOD_PASSWORD = os.getenv('ROBINHOOD_PASSWORD')
SONAR_API_KEY = os.getenv('SONAR_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS')
EMAIL_APP_PASSWORD = os.getenv('EMAIL_APP_PASSWORD')
RECIPIENT_EMAIL = os.getenv('RECIPIENT_EMAIL')

# Initialize Anthropic client
# anthropic = Anthropic(api_key=ANTHROPIC_API_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY)

def login_to_robinhood():
    """Login to Robinhood account"""
    try:
        login =rh.authentication.login(username=ROBINHOOD_USERNAME, password=ROBINHOOD_PASSWORD, mfa_code='')
        logging.info("Successfully logged in to Robinhood")
        return True
    except Exception as e:
        logging.error(f"Failed to login to Robinhood: {e}")
        return False

def get_robinhood_positions():
    """Get current stock positions from Robinhood"""
    try:
        # Get all positions data
        positions_data = rh.account.build_holdings()
        
        # Filter for stocks that are actually owned (positive quantity)
        owned_positions = {
            ticker: data for ticker, data in positions_data.items()
            if float(data['quantity']) > 0
        }
        
        logging.info(f"Retrieved {len(owned_positions)} stock positions from Robinhood")
        return owned_positions
    except Exception as e:
        logging.error(f"Error retrieving Robinhood positions: {e}")
        return {}

def get_stock_news(ticker, limit=5):
    """Get latest news for a stock ticker using Perplexity Sonar API"""
    SONAR_API_KEY = os.getenv("SONAR_API_KEY")
    try:
        url = "https://api.perplexity.ai/chat/completions"
        headers = {
            "Authorization": f"Bearer {SONAR_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "sonar",
            "messages": [
                {
                    "role": "user",
                    "content": f"Give me the {limit} most recent and relevant news articles for {ticker} stock."
                }
            ]
        }
        
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        response_text = response.text
        response_json = json.loads(response_text)
        print(f"Retrieved news for {ticker}")
        return {"news": response_json['choices'][0]['message']['content'], "citations": response_json['citations']}
    except Exception as e:
        print(f"Error retrieving news for {ticker}: {e}")
        return {"news": [], "citations": []}

def generate_stock_summary(ticker, position_data, news_items):
    """Generate summary for a stock using OpenAI's API"""
    try:
        if not news_items:
            return f"No recent news found for {ticker}."
        
        # Format the news items
        news_text = news_items['news']
        
        # Current position info
        position_info = (
            f"Current position: {position_data.get('quantity')} shares\n"
            f"Current value: ${position_data.get('equity')}\n"
            f"Average buy price: ${position_data.get('average_buy_price')}\n"
            f"Percent change: {position_data.get('percent_change')}%"
        )
        
        prompt = f"""
        Stock: {ticker}
        
        Position Information:
        {position_info}
        
        Recent News:
        {news_text}
        
        Based on the above information, provide a concise 2-3 paragraph summary of the current situation for {ticker}, including the most important recent news and how it might impact the stock. Focus on actionable insights.
        """
        
        # Call OpenAI API
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            max_tokens=500,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}]
        )
        
        summary = response.choices[0].message.content
        logging.info(f"Generated summary for {ticker}")
        return summary
    
    except Exception as e:
        logging.error(f"Error generating summary for {ticker}: {e}")
        return f"Error generating summary for {ticker}: {str(e)}"

def create_email_report(stock_summaries, positions):
    """Create HTML email report from stock summaries"""
    report_date = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # Start building HTML content
    html_content = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
            .container {{ max-width: 800px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #0066cc; color: white; padding: 10px; text-align: center; }}
            .stock-summary {{ margin-bottom: 30px; border-bottom: 1px solid #eee; padding-bottom: 20px; }}
            .stock-header {{ background-color: #f5f5f5; padding: 10px; margin-bottom: 10px; }}
            .stock-position {{ background-color: #f9f9f9; padding: 10px; margin-bottom: 10px; }}
            .stock-content {{ padding: 0 10px; }}
            .footer {{ font-size: 12px; color: #666; text-align: center; margin-top: 30px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Daily Stock Report</h1>
                <h2>{report_date}</h2>
            </div>
    """
    
    # Add each stock summary
    for ticker, summary in stock_summaries.items():
        position = positions.get(ticker, {})
        
        html_content += f"""
        <div class="stock-summary">
            <div class="stock-header">
                <h2>{ticker}</h2>
            </div>
            <div class="stock-position">
                <p><strong>Shares:</strong> {position.get('quantity', 'N/A')}</p>
                <p><strong>Current Value:</strong> ${position.get('equity', 'N/A')}</p>
                <p><strong>Average Buy Price:</strong> ${position.get('average_buy_price', 'N/A')}</p>
                <p><strong>Percent Change:</strong> {position.get('percent_change', 'N/A')}%</p>
            </div>
            <div class="stock-content">
                <p>{summary}</p>
            </div>
        </div>
        """
    
    # Close HTML content
    html_content += """
            <div class="footer">
                <p>This report is generated automatically and is for informational purposes only.</p>
                <p>It is not intended as investment advice.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html_content

def send_email(html_content):
    """Send HTML email with report"""
    try:
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        subject = f"Daily Stock Report - {today}"
        
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = EMAIL_ADDRESS
        message["To"] = RECIPIENT_EMAIL
        
        # Attach HTML content
        html_part = MIMEText(html_content, "html")
        message.attach(html_part)
        
        # Send email
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
            server.send_message(message)
        
        logging.info(f"Email report sent successfully to {RECIPIENT_EMAIL}")
        return True
    except Exception as e:
        logging.error(f"Failed to send email: {e}")
        return False

def run_daily_report():
    """Run the complete daily stock report process"""
    logging.info("Starting daily stock report generation")
    
    # Login to Robinhood
    if not login_to_robinhood():
        logging.error("Aborting process due to Robinhood login failure")
        return
    
    # Get positions
    positions = get_robinhood_positions()
    if not positions:
        logging.error("No positions found or error retrieving positions")
        return
    print(positions)
    # Get news and generate summaries for each stock
    
    stock_summaries = {}
    for ticker in positions.keys():
        logging.info(f"Processing stock: {ticker}")
        news_items = get_stock_news(ticker)
        summary = generate_stock_summary(ticker, positions[ticker], news_items)
        stock_summaries[ticker] = summary
    
    # Create and send report
    html_report = create_email_report(stock_summaries, positions)
    send_email(html_report)
    
    # Log out of Robinhood
    rh.logout()
    logging.info("Daily stock report completed")

def schedule_and_run():
    """Set up the schedule and run the event loop"""
    # Schedule the job to run at 8:00 AM every day
    schedule.every().day.at("08:00").do(run_daily_report)
    
    logging.info("Scheduler started. First report will run at 8:00 AM.")
    
    # Run once immediately for testing
    if os.getenv('RUN_IMMEDIATELY', 'false').lower() == 'true':
        logging.info("Running initial report immediately for testing")
        run_daily_report()
    
    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    schedule_and_run()
