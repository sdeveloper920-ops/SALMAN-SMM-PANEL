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

## Deploy from Android phone (Render Free Web Service)
1. Extract this ZIP and upload the project files to your GitHub repository. Do not upload real tokens or Firebase keys.
2. In Render choose **New → Web Service** (not Background Worker).
3. Connect your GitHub repository. Select the Free plan.
4. Build command: `pip install -r requirements.txt`
5. Start command: `python main.py`
6. Add environment variables:
   - `BOT_TOKEN`: your BotFather token
   - `ADMIN_IDS`: `6305047037`
   - `FIREBASE_CREDENTIALS_JSON`: full Firebase service-account JSON on one line
   - `RENDER_EXTERNAL_URL`: your public Render URL, e.g. `https://salman-smm-panel.onrender.com`
   - `WEBHOOK_SECRET`: a long random secret (letters/numbers/underscore/hyphen; at least 32 characters)
   - `PAYMENT_INSTRUCTIONS`: your payment instructions
   - `CURRENCY`: `৳`
7. Deploy. The app sets the Telegram webhook automatically when it starts.

Render Free Web Services can sleep after inactivity and may take time to wake. This is not guaranteed 24/7 hosting. If the service sleeps, Telegram may retry webhook deliveries; test the bot after deployment.

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
