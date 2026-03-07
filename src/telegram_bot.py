import os
import re
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from logging_config import setup_logging
from validation import is_valid_spotify_album_url

logger = setup_logging()

ALLOWED_CHAT_ID = os.getenv('TELEGRAM_ALLOWED_CHAT_ID')
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Maps Telegram username (case-insensitive) → picker initials shown on album cards
PICKER_MAP = {
    'steve':   'SS',
    'd_blott': 'DG',
    'ross':    'RB',
    'jack':    'JC',
    '@Ninajirachi_Fan':     'BR',
}

# Full pattern:  @aotw <spotify_url> <apple_music_url> [initials]
_TRIGGER_PATTERN = re.compile(
    r'@aotw\s+(https://open\.spotify\.com/album/[^\s]+)\s+(https?://[^\s]+)(?:\s+([A-Za-z]{2}))?',
    re.IGNORECASE
)
# Partial pattern — catches @aotw with something after it but wrong format
_PARTIAL_PATTERN = re.compile(r'@aotw\s+\S', re.IGNORECASE)

_FORMAT_HINT = (
    "Format: `@aotw <spotify_url> <apple_music_url> [initials]`\n"
    "Example: `@aotw https://open.spotify.com/album/... https://music.apple.com/... DG`\n"
    "Initials are optional — omit to use your registered username."
)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming group messages."""
    chat_id = str(update.effective_chat.id)

    if chat_id != ALLOWED_CHAT_ID:
        logger.warning('Ignored message from unauthorized chat: %s', chat_id)
        return

    message_text = update.message.text or ''
    username = update.effective_user.username or update.effective_user.first_name
    logger.info('Message received from %s: %s', username, message_text)

    match = _TRIGGER_PATTERN.search(message_text)
    if not match:
        if _PARTIAL_PATTERN.search(message_text):
            await update.message.reply_text(_FORMAT_HINT, parse_mode='Markdown')
        return

    spotify_url = match.group(1)
    apple_music_url = match.group(2)
    initials = match.group(3)

    if not is_valid_spotify_album_url(spotify_url):
        await update.message.reply_text(
            "Couldn't add this album — not a valid Spotify album link.\n" + _FORMAT_HINT,
            parse_mode='Markdown',
        )
        return

    picker = initials.upper() if initials else PICKER_MAP.get((username or '').lower(), '')

    try:
        from pipeline import process_album
        result = await process_album(
            spotify_url,
            sheet_id=os.getenv('GOOGLE_SHEET_ID'),
            sheet_tab=os.getenv('GOOGLE_SHEET_TAB'),
            creds_path=os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON'),
            picker=picker,
            apple_music_url=apple_music_url,
        )
        await update.message.reply_text(result['message'], parse_mode='Markdown')

        if result['success']:
            logger.info('Pipeline succeeded for %s: %s', username, result.get('data', {}).get('Album'))
        else:
            logger.warning('Pipeline rejected %s: %s', username, result['message'])

    except Exception as e:
        logger.error('Pipeline failed: %s', e, exc_info=True)
        await update.message.reply_text(
            "Something went wrong processing that album. Please try again later."
        )


def main():
    if not BOT_TOKEN:
        raise ValueError('TELEGRAM_BOT_TOKEN env var not set')
    if not ALLOWED_CHAT_ID:
        raise ValueError('TELEGRAM_ALLOWED_CHAT_ID env var not set')

    railway_domain = os.getenv('RAILWAY_PUBLIC_DOMAIN')
    if not railway_domain:
        raise ValueError('RAILWAY_PUBLIC_DOMAIN env var not set')

    port = int(os.getenv('PORT', '8080'))
    secret_token = os.getenv('WEBHOOK_SECRET_TOKEN')
    webhook_url = f'https://{railway_domain}/telegram'

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info('Bot starting in webhook mode on port %d (url: %s)...', port, webhook_url)
    app.run_webhook(
        listen='0.0.0.0',
        port=port,
        url_path='/telegram',
        webhook_url=webhook_url,
        secret_token=secret_token,
        drop_pending_updates=True,
    )


if __name__ == '__main__':
    main()
