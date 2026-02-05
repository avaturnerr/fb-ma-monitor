#!/usr/bin/env python3
"""
F&B M&A Weekly Monitoring Script
Searches for new deals, updates dashboard, and sends email digest
"""

import os
import anthropic
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import json
import re

# Configuration
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
GMAIL_USER = os.environ.get('GMAIL_USER')
GMAIL_APP_PASSWORD = os.environ.get('GMAIL_APP_PASSWORD')
TO_EMAIL = "ava@westerra.com"  # CHANGE THIS TO YOUR EMAIL

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

def search_for_deals():
    """Search the web for recent F&B M&A activity"""
    print("🔍 Searching for new F&B M&A deals...")
    
    # Get date range for search
    today = datetime.now()
    week_ago = today - timedelta(days=7)
    date_str = week_ago.strftime("%Y-%m-%d")
    
    search_prompt = f"""Search for Food & Beverage M&A deals and activity from the past week (since {date_str}).

Focus on:
1. New acquisition announcements
2. Deal completions
3. Companies in acquisition talks
4. Notable investments in F&B companies
5. Trend shifts in deal activity

Search for multiple queries to get comprehensive coverage:
- "food beverage M&A this week"
- "CPG acquisition announcement" 
- "food company acquired 2026"
- "beverage merger announcement"
- "functional food acquisition"

After searching, provide a structured summary with:
- NEW DEALS: List of specific deals with acquirer, target, value (if known), and brief description
- KEY TRENDS: Any notable patterns or shifts
- NOTABLE ACTIVITY: Rumors, talks, or significant movements
- METRICS UPDATE: Any new data on deal volume, values, or market activity

Be specific with company names, deal values, and dates."""

    try:
        # Make API call with web search enabled
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            tools=[{
                "type": "web_search_20250305",
                "name": "web_search"
            }],
            messages=[{
                "role": "user",
                "content": search_prompt
            }]
        )
        
        # Extract text from response
        summary = ""
        for block in response.content:
            if block.type == "text":
                summary += block.text + "\n"
        
        print("✅ Search complete!")
        return summary
        
    except Exception as e:
        print(f"❌ Error during search: {e}")
        return f"Error searching for deals: {str(e)}"


def parse_deals_from_summary(summary):
    """Extract structured deal information from the summary"""
    print("📊 Parsing deal information...")
    
    parse_prompt = f"""Based on this M&A research summary, extract specific deals into a structured JSON format.

Summary:
{summary}

Return ONLY a JSON array of deals (no other text). Each deal should have:
- title: "Company A acquires Company B" format
- value: Deal value or "Undisclosed"
- details: Brief description (1-2 sentences)
- category: One of [Better-for-You, Protein, Beverages, Functional Beverages, Energy Drinks, Alcoholic Beverages, Plant-Based, Ready Meals, Snacking, Other]
- date: Approximate date or quarter (e.g., "Feb 2026" or "Q1 2026")

Example format:
[
  {{
    "title": "PepsiCo acquires HealthyCo",
    "value": "$500M",
    "details": "Functional beverage brand with strong Gen Z following",
    "category": "Functional Beverages",
    "date": "Feb 2026"
  }}
]

If no specific deals found, return empty array: []"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{
                "role": "user",
                "content": parse_prompt
            }]
        )
        
        # Extract JSON from response
        text = response.content[0].text
        # Find JSON array in the response
        json_match = re.search(r'\[.*\]', text, re.DOTALL)
        if json_match:
            deals = json.loads(json_match.group())
            print(f"✅ Found {len(deals)} new deals")
            return deals
        else:
            print("⚠️ No deals found in expected format")
            return []
            
    except Exception as e:
        print(f"❌ Error parsing deals: {e}")
        return []


def update_dashboard_file(deals, summary):
    """Update the HTML dashboard with new deals"""
    print("📝 Updating dashboard file...")
    
    try:
        # Read current dashboard
        with open('fb_ma_monitoring_dashboard.html', 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        if not deals:
            print("ℹ️ No new deals to add to dashboard")
            return True
        
        # Generate HTML for new deals
        new_deals_html = ""
        for deal in deals:
            new_deals_html += f"""
                <div class="deal-entry">
                    <div class="deal-header">
                        <div class="deal-title">{deal['title']}</div>
                        <div class="deal-value">{deal['value']}</div>
                    </div>
                    <div class="deal-details">{deal['details']}</div>
                    <span class="deal-category">{deal['category']}</span>
                    <span class="deal-category">{deal['date']}</span>
                </div>
"""
        
        # Find the deal tracker section and insert new deals at the top
        tracker_pattern = r'(<div class="deal-tracker" id="dealTracker">)'
        replacement = r'\1' + new_deals_html
        updated_html = re.sub(tracker_pattern, replacement, html_content)
        
        # Update the "Last updated" date
        today = datetime.now().strftime("%B %Y")
        updated_html = re.sub(
            r'Last updated: [^<]+',
            f'Last updated: {today}',
            updated_html
        )
        
        # Write updated dashboard
        with open('fb_ma_monitoring_dashboard.html', 'w', encoding='utf-8') as f:
            f.write(updated_html)
        
        print("✅ Dashboard updated successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error updating dashboard: {e}")
        return False


def send_email_digest(summary, deals):
    """Send email with weekly M&A digest"""
    print("📧 Sending email digest...")
    
    try:
        # Create email
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"F&B M&A Weekly Update - {datetime.now().strftime('%B %d, %Y')}"
        msg['From'] = GMAIL_USER
        msg['To'] = TO_EMAIL
        
        # Create email body
        email_body = f"""
Food & Beverage M&A Weekly Update
{datetime.now().strftime('%B %d, %Y')}
{'=' * 50}

NEW DEALS THIS WEEK: {len(deals)}

"""
        
        if deals:
            for deal in deals:
                email_body += f"""
📌 {deal['title']}
   💰 Value: {deal['value']}
   📋 {deal['details']}
   🏷️  Category: {deal['category']} | {deal['date']}

"""
        else:
            email_body += "No new major deals announced this week.\n\n"
        
        email_body += f"""
{'=' * 50}

FULL MARKET SUMMARY:

{summary}

{'=' * 50}

📊 View your updated dashboard:
https://github.com/YOUR-USERNAME/fb-ma-monitor/blob/main/fb_ma_monitoring_dashboard.html

💡 This is an automated weekly update. New deals are added to your dashboard automatically.

"""
        
        # Attach plain text version
        text_part = MIMEText(email_body, 'plain')
        msg.attach(text_part)
        
        # Send email
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.send_message(msg)
        
        print("✅ Email sent successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error sending email: {e}")
        return False


def main():
    """Main execution function"""
    print("\n" + "=" * 60)
    print("🍽️  F&B M&A WEEKLY MONITORING SCRIPT")
    print("=" * 60 + "\n")
    
    # Step 1: Search for new deals
    summary = search_for_deals()
    
    if "Error" in summary:
        print("❌ Failed to retrieve deal information")
        return
    
    # Step 2: Parse deals into structured format
    deals = parse_deals_from_summary(summary)
    
    # Step 3: Update dashboard
    update_dashboard_file(deals, summary)
    
    # Step 4: Send email digest
    send_email_digest(summary, deals)
    
    print("\n" + "=" * 60)
    print("✅ WEEKLY UPDATE COMPLETE!")
    print(f"📊 Found {len(deals)} new deals")
    print(f"📧 Email sent to {TO_EMAIL}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
