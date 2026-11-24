# SALMAN SMM PANEL

Telegram SMM order bot with Firebase Firestore and manual admin processing.

## Features
- Telegram user registration and balance
- Service list (admin-managed)
- Orders with link, quantity, price calculation
- Admin approve/process/complete/reject + refund
- Manual Add Funds request and approval
- Order history and basic statistics

## Firebase setup
1. Create a Firebase project at https://console.firebase.google.com/
2. Create a Firestore Database (Production mode is fine).
3. Project settings → Service accounts → Generate new private key.
4. Keep the JSON private. Copy its full one-line JSON content for Render's `FIREBASE_CREDENTIALS_JSON` environment variable.

## Telegram setup
1. Open @BotFather, create a bot, copy its token.
2. Get your numeric Telegram user ID from a trusted ID bot.
3. Set `BOT_TOKEN` and `ADMIN_IDS=6305047037` (numeric ID; multiple IDs comma-separated). This is the admin ID supplied for this project.

## Run locally
Python 3.10+:
```bash
pip install -r requirements.txt
export BOT_TOKEN="..."
export ADMIN_IDS="123456789"
export FIREBASE_CREDENTIALS_JSON='{"type":"service_account", ...}'
python main.py
```

## Deploy from Android phone
1. Extract this ZIP.
2. Create a GitHub repository and upload all project files (not your real token or Firebase key).
3. In Render, create a new **Background Worker** from that GitHub repository.
4. Build command: `pip install -r requirements.txt`
5. Start command: `python main.py`
6. Add environment variables: `BOT_TOKEN`, `ADMIN_IDS`, `FIREBASE_CREDENTIALS_JSON`, `PAYMENT_INSTRUCTIONS`, `CURRENCY`.
7. Deploy. Use Render logs to check startup.

## Admin commands
- `/admin` — Admin panel
- `/addservice Category | Service name | Price per 1000 | Min | Max`

Example:
`/addservice Instagram | Instagram Followers | 120 | 100 | 10000`

Services are added inactive? No, they become active immediately and appear in the user menu.

## Important
- Never commit your Telegram token or Firebase service-account JSON to GitHub.
- Add Funds requests are not automatic payment verification. Admin must verify transaction details before approval.
- Orders are manual; this project does not connect to any SMM provider API.
- Before accepting real payments, test with a private test bot and small amounts. Review local laws and platform rules.
