import pytest
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))


VALID_URL = "https://open.spotify.com/album/0SeRWS3scHWplJhMppd6rJ"
ALLOWED_ID = "12345678"


def make_update(text, chat_id=ALLOWED_ID):
    update = MagicMock()
    update.effective_chat.id = int(chat_id)
    update.effective_user.username = "testuser"
    update.effective_user.first_name = "Test"
    update.message.text = text
    update.message.reply_text = AsyncMock()
    return update


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    monkeypatch.setenv('TELEGRAM_ALLOWED_CHAT_ID', ALLOWED_ID)
    monkeypatch.setenv('TELEGRAM_BOT_TOKEN', 'fake-token')


@pytest.mark.asyncio
async def test_ignores_unauthorized_chat():
    import telegram_bot
    update = make_update(f"@aotw {VALID_URL}", chat_id="99999")
    await telegram_bot.handle_message(update, MagicMock())
    update.message.reply_text.assert_not_called()


@pytest.mark.asyncio
async def test_ignores_non_trigger_message():
    import telegram_bot
    update = make_update("hey anyone listening to good music?")
    await telegram_bot.handle_message(update, MagicMock())
    update.message.reply_text.assert_not_called()


@pytest.mark.asyncio
async def test_ignores_non_album_spotify_url():
    """Track/playlist URLs don't match the @aotw <album> trigger — silently ignored."""
    import telegram_bot
    update = make_update("@aotw https://open.spotify.com/track/5SBMNVrRM8xZpyGYTYtfR9")
    await telegram_bot.handle_message(update, MagicMock())
    update.message.reply_text.assert_not_called()


@pytest.mark.asyncio
async def test_calls_pipeline_for_valid_url():
    import telegram_bot
    update = make_update(f"@aotw {VALID_URL}")
    mock_result = {'success': True, 'message': 'Added *Some Album* by Some Artist — Pick #42 ✅', 'data': {'Album': 'Some Album'}}

    with patch.dict('sys.modules', {'pipeline': MagicMock(process_album=AsyncMock(return_value=mock_result))}):
        await telegram_bot.handle_message(update, MagicMock())

    call_args = update.message.reply_text.call_args
    assert call_args[0][0] == mock_result['message']
    assert call_args[1].get('parse_mode') == 'Markdown'


@pytest.mark.asyncio
async def test_handles_pipeline_exception():
    import telegram_bot
    update = make_update(f"@aotw {VALID_URL}")

    mock_pipeline = MagicMock()
    mock_pipeline.process_album = AsyncMock(side_effect=Exception("boom"))

    with patch.dict('sys.modules', {'pipeline': mock_pipeline}):
        await telegram_bot.handle_message(update, MagicMock())

    update.message.reply_text.assert_called_once()
    assert "went wrong" in update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_pattern_is_case_insensitive():
    import telegram_bot
    update = make_update(f"@AOTW {VALID_URL}")
    mock_result = {'success': True, 'message': 'Added!', 'data': {'Album': 'Test'}}

    with patch.dict('sys.modules', {'pipeline': MagicMock(process_album=AsyncMock(return_value=mock_result))}):
        await telegram_bot.handle_message(update, MagicMock())

    update.message.reply_text.assert_called_once()
