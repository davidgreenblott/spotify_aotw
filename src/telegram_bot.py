import os
import re
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from logging_config import setup_logging
from validation import is_valid_spotify_album_url

logger = setup_logging()

ALLOWED_CHAT_ID = os.getenv('TELEGRAM_ALLOWED_CHAT_ID')
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Pattern: @aotw <spotify_album_url>
_TRIGGER_PATTERN = re.compile(
    r'@aotw\s+(https://open\.spotify\.com/album/[^\s]+)',
    re.IGNORECASE
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
        return  # Not a trigger message — ignore silently

    url = match.group(1)

    if not is_valid_spotify_album_url(url):
        await update.message.reply_text(
            "Couldn't add this album (reason: not a valid Spotify album link). "
            "Please post a Spotify album URL."
        )
        return

    try:
        from pipeline import process_album
        result = await process_album(
            url,
            sheet_id=os.getenv('GOOGLE_SHEET_ID'),
            sheet_tab=os.getenv('GOOGLE_SHEET_TAB'),
            creds_path=os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON'),
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

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info('Bot starting in polling mode...')
    app.run_polling()


if __name__ == '__main__':
    main()
