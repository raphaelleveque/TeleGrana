Here is a professional README.md for your project, written in English and formatted for GitHub.

💰 TeleGrana Bot
TeleGrana is a lightweight personal finance automation tool built with Python. It allows users to log expenses instantly via a Telegram Bot, which syncs the data directly to a Google Sheets spreadsheet in real-time.

✨ Features
Instant Logging: Send Value Description (e.g., 25.50 Lunch) and the bot logs it immediately.

Google Sheets Integration: No manual data entry in the Sheets app; the bot handles it via API.

Auto-Setup: On startup, the bot checks if your sheet is empty and automatically creates the required headers.

Security Lock: Unauthorized users cannot log expenses. The bot only responds to the Telegram ID defined in your environment variables.

Modular Design: Clean code architecture separated into bot logic and services (Google API).

🛠️ Tech Stack
Python 3.12+

aiogram 3.x: For the asynchronous Telegram Bot interface.

gspread: To interact with the Google Sheets API.

python-dotenv: For secure management of environment variables.

📁 Project Structure
Plaintext

TeleGrana/
├── main.py               # Application entry point
├── .env                  # Secret keys and IDs (ignored by Git)
├── credentials.json      # Google Service Account credentials
├── bot/
│   ├── __init__.py       # Package marker
│   ├── handlers.py       # Message processing logic
│   └── keyboards.py      # (Planned) Interactive buttons
└── services/
    ├── __init__.py       # Package marker
    └── google_sheets.py  # Google Sheets API communication service
🚀 Setup Instructions
1. Google Cloud Configuration
Go to the Google Cloud Console.

Enable the Google Drive API and Google Sheets API.

Create a Service Account, download the JSON key, and save it as credentials.json in the project root.

Open your Google Sheet and Share it with the client_email found inside your credentials.json (give it "Editor" permissions).

2. Telegram Bot Setup
Message @BotFather on Telegram and use the /newbot command.

Copy the API Token provided.

Message @userinfobot to find your personal Numeric ID.

3. Environment Variables
Create a .env file in the root directory:

Snippet de código

TELEGRAM_TOKEN=your_bot_token_here
GOOGLE_SHEET_ID=your_spreadsheet_id_from_url
MY_USER_ID=your_numeric_telegram_id
4. Installation & Execution
Bash

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # Mac/Linux
# venv\Scripts\activate   # Windows

# Install dependencies
pip install aiogram gspread google-auth python-dotenv

# Run the bot
python main.py
📊 Spreadsheet Format
The bot automatically manages the following columns: | Date | User | Value | Reimbursed | Description | Tags | | :--- | :--- | :--- | :--- | :--- | :--- |