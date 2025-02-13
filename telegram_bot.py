from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import os
from dotenv import load_dotenv
import logging
import json
import time
import hashlib

# Token Manager Class
class TokenManager:
    def __init__(self):
        self.token_file = 'tokens.json'
        self.logger = logging.getLogger(__name__)
        self.tokens = {"active_tokens": {}}
        self.load_tokens()

    def load_tokens(self):
        """Load tokens from file"""
        try:
            if os.path.exists(self.token_file):
                with open(self.token_file, 'r') as f:
                    self.tokens = json.load(f)
            else:
                self.save_tokens()
        except Exception as e:
            self.logger.error(f"Error loading tokens: {str(e)}")

    def save_tokens(self):
        """Save tokens to file"""
        try:
            with open(self.token_file, 'w') as f:
                json.dump(self.tokens, f, indent=4)
        except Exception as e:
            self.logger.error(f"Error saving tokens: {str(e)}")

    def validate_token(self, token: str) -> bool:
        """Validate a token"""
        return token in self.tokens["active_tokens"]

    def generate_token(self, user_id: str, usage_count: int = 10) -> str:
        """Generate a new token"""
        timestamp = int(time.time())
        token_base = f"PRB-{user_id}-{timestamp}-{usage_count}"
        token_hash = hashlib.sha256(token_base.encode()).hexdigest()[:8]
        token = f"{token_base}-{token_hash}"
        
        self.tokens["active_tokens"][token] = {
            "user_id": user_id,
            "created_at": timestamp,
            "uses_remaining": usage_count,
            "is_active": True
        }
        self.save_tokens()
        return token

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

    async def generate_new_token(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Generate new token - admin only"""
        if update.effective_user.id != ADMIN_USER_ID:
            await update.message.reply_text("Unauthorized access!")
            return

        try:
            user_id = str(update.effective_user.id)
            token = self.token_manager.generate_token(user_id)
            await update.message.reply_text(f"New token generated: {token}")
        except Exception as e:
            await update.message.reply_text(f"Error generating token: {str(e)}")

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

    async def show_admin_panel(self, query):
        """Show admin panel"""
        keyboard = [
            [InlineKeyboardButton("Generate Token", callback_data='gen_token')],
            [InlineKeyboardButton("View Stats", callback_data='stats')],
            [InlineKeyboardButton("Back", callback_data='back')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Admin Panel", reply_markup=reply_markup)

def main():
    """Start the bot"""
    bot = PRBotTelegram()
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CommandHandler("generate_token", bot.generate_new_token))
    application.add_handler(CallbackQueryHandler(bot.button_handler))

    # Start the bot
    print('Bot is starting...')
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()