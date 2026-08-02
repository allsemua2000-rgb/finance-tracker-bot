import gspread
from google.oauth2.service_account import Credentials
from groq import Groq
import json
import config

client = Groq(api_key=config.GROQ_API_KEY)

def authenticate_sheets():
    scopes = ['https://www.googleapis.com/auth/spreadsheets']
    creds = Credentials.from_service_account_file(config.CREDENTIALS_FILE, scopes=scopes)
    gc = gspread.authorize(creds)
    return gc

def parse_transaction(message):
    prompt = f"""Extract transaction details from: {message}

Reply ONLY with JSON format like this:
{{"type":"expense","category":"Bensin","amount":30000,"description":"beli bensin","date":"2026-07-31"}}

Message: {message}
Return only JSON, no other text."""
    
    try:
        message_response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}]
        )
        response_text = message_response.choices[0].message.content
        transaction_data = json.loads(response_text)
        return transaction_data
    except json.JSONDecodeError:
        print("Error: Groq tidak return JSON")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def save_to_sheets(gc, transaction_data):
    try:
        spreadsheet = gc.open_by_key(config.SHEET_ID)
        
        if transaction_data['type'] == 'expense':
            sheet = spreadsheet.worksheet(config.EXPENSE_SHEET)
        else:
            sheet = spreadsheet.worksheet(config.INCOME_SHEET)
        
        row_data = [
            transaction_data['date'],
            transaction_data['category'],
            transaction_data['amount'],
            transaction_data['description']
        ]
        
        sheet.append_row(row_data)
        return True
    except Exception as e:
        print(f"Error simpan: {e}")
        return False

def main():
    print("=" * 50)
    print("Finance Tracker Bot (Groq)")
    print("=" * 50)
    print("Type 'exit' to quit\n")
    
    try:
        gc = authenticate_sheets()
        print("Connected to Google Sheets\n")
    except Exception as e:
        print(f"Error: {e}")
        return
    
    while True:
        try:
            user_input = input("Transaksi: ").strip()
            
            if user_input.lower() == 'exit':
                print("Bye!")
                break
            
            if not user_input:
                print("Input kosong\n")
                continue
            
            print("Parsing...")
            transaction_data = parse_transaction(user_input)
            
            if not transaction_data:
                print("Gagal parse\n")
                continue
            
            print("\nResult:")
            print(f"  Type: {transaction_data['type']}")
            print(f"  Category: {transaction_data['category']}")
            print(f"  Amount: Rp {transaction_data['amount']:,}")
            print(f"  Description: {transaction_data['description']}")
            print(f"  Date: {transaction_data['date']}")
            
            confirm = input("\nSimpan? (y/n): ").strip().lower()
            
            if confirm == 'y':
                if save_to_sheets(gc, transaction_data):
                    print("Tersimpan!\n")
                else:
                    print("Gagal\n")
            else:
                print("Dibatalkan\n")
        
        except KeyboardInterrupt:
            print("\nBye!")
            break
        except Exception as e:
            print(f"Error: {e}\n")

if __name__ == "__main__":
    main()
