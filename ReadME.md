# Discord Verification Bot

A Discord bot that verifies and updates members using data stored in a Google Sheet. The bot creates private verification channels, checks submitted phone numbers, assigns roles, updates membership status, and syncs with a Google Apps Script webhook.

---

## Features

* Private verification channels for new members
* Google Sheets lookup via a Service Account
* Automatic role assignment based on sheet data
* Update button for refreshing membership status
* Google Apps Script webhook trigger
* Automatic persistence of verification and update messages
* Phone number normalization and matching

---

## Requirements

* Python 3.10+
* Discord Bot Application
* Google Cloud project with a Service Account
* Google Sheet containing member information
* (Optional) Google Apps Script Web App for external sync

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/yourrepo.git
cd yourrepo
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Create your `.env` file

Copy the included `.env.example` file and rename it to `.env`.

Fill it with your real values:

```
DISCORD_TOKEN=YOUR_DISCORD_BOT_TOKEN
SHEET_KEY=YOUR_GOOGLE_SHEET_KEY
WEBHOOK_URL=YOUR_GOOGLE_APPS_SCRIPT_URL
GUILD_ID=YOUR_DISCORD_SERVER_ID
VERIFY_CHANNEL_ID=YOUR_VERIFICATION_CHANNEL_ID
UPDATE_CHANNEL_ID=YOUR_UPDATE_CHANNEL_ID
```

Your `.env` file should never be committed to GitHub.

---

## Setting Up Google Services

### 1. Enable Google Sheets API

1. Go to Google Cloud Console.
2. Create or open a project.
3. Enable the **Google Sheets API**.

### 2. Create a Service Account

1. In "IAM & Admin" select "Service Accounts".
2. Create a new Service Account.
3. Generate a **JSON key**.
4. Download it and rename it to:

```
credentials.json
```

5. Place it in the project root.

### 3. Share the Sheet with your Service Account

Share the Google Sheet with the service account's email:

```
your-service-account@yourproject.iam.gserviceaccount.com
```

Give it **Viewer** or **Editor** access depending on your needs.

### 4. Provide an example credentials file

Your repository includes:

```
credentials.example.json
```

Users must rename it to `credentials.json` and fill in their own values.

---

## Google Sheet Setup

Your Google Sheet must include these columns:

* **Име и фамилия** (Full Name)
* **Телефон за контакт** (Phone Number)
* **Официален член** (TRUE/FALSE)

The bot uses the Sheet ID found in the URL:

```
https://docs.google.com/spreadsheets/d/<SHEET_KEY>/edit
```

---

## Optional: Google Apps Script Webhook

If your bot uses `WEBHOOK_URL`, set up the following:

1. Open Google Apps Script.
2. Create a script that handles GET requests.
3. Deploy as **Web App**.
4. Set access to **Anyone** (or Anyone with link).
5. Paste the deployment URL into the `.env` under `WEBHOOK_URL`.

---

## Running the Bot

```bash
python bot.py
```

---

## Runtime Files

The bot automatically creates a file:

```
message_id.json
```

This file stores the IDs and timestamps of the verification and update messages that were last published. It is created automatically the first time the bot sends those messages.

This file must **not** be committed to GitHub and is included in the `.gitignore`.

---

## .gitignore

This project includes a `.gitignore` file that prevents sensitive and runtime data from being uploaded:

```
.env
credentials.json
message_id.json
__pycache__/
*.pyc
.vscode/
```

---

## Security Notes

* Never commit your real `.env` or `credentials.json`.
* Regenerate your Discord token if it is ever exposed.
* Regenerate your Service Account key if the JSON is leaked.

---

## Support

If you encounter issues with setup or want to expand the bot's features, feel free to open an issue or request help.
