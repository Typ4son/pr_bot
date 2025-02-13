from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters
)
from token_manager import TokenManager
from pr import PRBot  # Import your existing PR bot
import logging
import os
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Load environment variables
load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID'))

# States for conversation
AWAITING_TOKEN = 1
AWAITING_INFO = 2
PROCESSING = 3

class TelegramPRBot:
    def __init__(self):
        self.token_manager = TokenManager()
        self.pr_bot = PRBot()  # Initialize your existing PR bot
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

    async def admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin panel handler"""
        if update.effective_user.id != ADMIN_USER_ID:
            await update.callback_query.answer("Unauthorized access!")
            return

        keyboard = [
            [InlineKeyboardButton("Generate Token", callback_data='gen_token')],
            [InlineKeyboardButton("Manage Sites", callback_data='manage_sites')],
            [InlineKeyboardButton("View Analytics", callback_data='analytics')],
            [InlineKeyboardButton("Back", callback_data='back')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(
            "Admin Panel\nSelect an option:",
            reply_markup=reply_markup
        )

    async def process_token(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process user token"""
        token = update.message.text
        result = self.token_manager.validate_token(token)
        
        if result["valid"]:
            context.user_data['token'] = token
            await update.message.reply_text(
                f"Token valid! Uses remaining: {result['uses_remaining']}\n"
                "Please enter your information in the following format:\n\n"
                "Name: Your Name\n"
                "Phone: XXX-XXX-XXXX\n"
                "Email: your@email.com\n"
                "Address: Your Address\n"
                "City, State ZIP: City, ST 12345"
            )
            return AWAITING_INFO
        else:
            await update.message.reply_text(
                f"Invalid token: {result['message']}\n"
                "Please try again or contact administrator."
            )
            return AWAITING_TOKEN

    async def process_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process user information and start PR signup"""
        try:
            # Parse user information
            info_text = update.message.text
            user_info = self.parse_user_info(info_text)
            
            await update.message.reply_text("Starting PR signup process...")
            
            # Start PR signup process
            success = self.pr_bot.process_single_signup(user_info)
            
            if success:
                await update.message.reply_text(
                    "✅ PR signup completed successfully!"
                )
            else:
                await update.message.reply_text(
                    "❌ PR signup failed. Please try again later."
                )
                
        except Exception as e:
            self.logger.error(f"Error processing signup: {str(e)}")
            await update.message.reply_text(
                "An error occurred during signup. Please try again later."
            )
        
        return ConversationHandler.END

    def parse_user_info(self, info_text: str) -> dict:
        """Parse user information from message text"""
        info_dict = {}
        lines = info_text.split('\n')
        
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                info_dict[key.strip().lower()] = value.strip()
                
        return info_dict

    async def handle_signup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle PR signup process"""
        message = update.message.text
        try:
            # Parse user information from message
            info_lines = message.split('\n')
            user_info = {}
            for line in info_lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    user_info[key.strip().lower()] = value.strip()

            # Use your existing PR bot to process signup
            success = self.pr_bot.process_single_signup(user_info)
            
            if success:
                await update.message.reply_text("✅ PR signup completed successfully!")
            else:
                await update.message.reply_text("❌ PR signup failed. Please try again.")
                
        except Exception as e:
            self.logger.error(f"Error in signup: {str(e)}")
            await update.message.reply_text(
                "An error occurred during signup. Please try again."
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
                "Email: your@email.com\n"
                "Address: Your Address\n"
                "City: Your City\n"
                "State: YS\n"
                "ZIP: 12345"
            )
        elif query.data == 'admin' and update.effective_user.id == ADMIN_USER_ID:
            await self.show_admin_panel(query)

def main():
    """Start the bot"""
    bot = TelegramPRBot()
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CallbackQueryHandler(bot.button_handler))
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, 
        bot.handle_signup
    ))

    # Start the bot
    print('Bot is starting...')
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main() 