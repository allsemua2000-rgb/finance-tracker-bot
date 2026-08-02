import os
import json
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import gspread
from google.oauth2.service_account import Credentials
from groq import Groq

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load credentials from environment variable
creds_json_str = os.getenv('CREDENTIALS_JSON')
if creds_json_str:
    creds_dict = json.loads(creds_json_str)
    with open('credentials.json', 'w') as f:
        json.dump(creds_dict, f)

# Initialize Groq client
client = Groq(api_key=os.getenv('GROQ_API_KEY'))

# Google Sheets config
SHEET_ID = os.getenv('SHEET_ID')
EXPENSE_SHEET = os.getenv('EXPENSE_SHEET', 'Expense')
INCOME_SHEET = os.getenv('INCOME_SHEET', 'Income')

def authenticate_sheets():
    """Authenticate with Google Sheets"""
    scopes = ['https://www.googleapis.com/auth/spreadsheets']
    creds = Credentials.from_service_account_file('credentials.json', scopes=scopes)
    gc = gspread.authorize(creds)
    return gc

def parse_transaction(message):
    """Parse transaction using Groq AI"""
    prompt = f"""Extract transaction details from: {message}

Reply ONLY with JSON format like this:
{{"type":"expense","category":"Bensin","amount":30000,"description":"beli bensin","date":"2026-07-31"}}

Message: {message}
Return only JSON, no other text."""
    
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}]
    )
    
    try:
        return json.loads(response.content[0].text)
    except:
        return None

def save_to_sheets(transaction):
    """Save transaction to Google Sheets"""
    try:
        gc = authenticate_sheets()
        sheet = gc.open_by_key(SHEET_ID)
        
        sheet_name = INCOME_SHEET if transaction['type'] == 'income' else EXPENSE_SHEET
        ws = sheet.worksheet(sheet_name)
        
        ws.append_row([
            transaction['date'],
            transaction['category'],
            transaction['amount'],
            transaction['description']
        ])
        return True
    except Exception as e:
        logger.error(f"Error saving to Sheets: {e}")
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command"""
    await update.message.reply_text(
        "🤖 Finance Tracker Bot\n\n"
        "Kirim transaksi dengan format natural:\n"
        "- 'beli bensin 30k'\n"
        "- 'makan siang 50rb'\n"
        "- 'gaji bulan ini 5jt'\n\n"
        "Bot akan otomatis parse & simpan ke Sheets! 💰"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages"""
    user_message = update.message.text
    
    # Parse transaction
    transaction = parse_transaction(user_message)
    
    if not transaction:
        await update.message.reply_text("❌ Tidak bisa parse transaksi. Coba format lain.")
        return
    
    # Show parsed result
    result_text = (
        f"📊 Parsed Transaction:\n"
        f"Type: {transaction['type']}\n"
        f"Category: {transaction['category']}\n"
        f"Amount: Rp {transaction['amount']:,}\n"
        f"Description: {transaction['description']}\n"
        f"Date: {transaction['date']}\n\n"
        f"Saving..."
    )
    await update.message.reply_text(result_text)
    
    # Save to Sheets
    if save_to_sheets(transaction):
        await update.message.reply_text("✅ Saved to Sheets!")
    else:
        await update.message.reply_text("❌ Error saving to Sheets")

def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not found in environment")
        return

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot started polling...")
    app.run_polling()

if name == "main":
    main()
