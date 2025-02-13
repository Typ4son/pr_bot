from bot_modules.token_manager import TokenManager
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import os
from dotenv import load_dotenv
import logging

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Load environment variables
load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID'))

class PRBotTelegram:
    def __init__(self):
        self.token_manager = TokenManager()
        self.logger = logging.getLogger(__name__)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command handler"""
        keyboard = [
            [InlineKeyboardButton("Start PR Signup", callback_data='signup')],
            [InlineKeyboardButton("Check Status", callback_data='status')]
        ]
        
        if update.effective_user.id == ADMIN_USER_ID:
            keyboard.append([InlineKeyboardButton("Admin Panel", callback_data='admin')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Welcome to PR Bot!\n"
            "Please select an option:",
            reply_markup=reply_markup
        )

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button presses"""
        query = update.callback_query
        await query.answer()

        if query.data == 'signup':
            await query.edit_message_text(
                "Please enter your information in this format:\n\n"
                "Name: Your Name\n"
                "Phone: XXX-XXX-XXXX\n"
                "Email: your@email.com"
            )
        elif query.data == 'admin' and update.effective_user.id == ADMIN_USER_ID:
            await self.show_admin_panel(query)

def main():
    """Start the bot"""
    bot = PRBotTelegram()
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CallbackQueryHandler(bot.button_handler))

    # Start the bot
    print('Bot is starting...')
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()