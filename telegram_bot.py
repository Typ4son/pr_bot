from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import os
from dotenv import load_dotenv
import logging
import json
import time
import hashlib

# Add port configuration
PORT = int(os.getenv('PORT', 8080))

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
        self.prices = {
            'daily': {'price': 5, 'uses': 10},
            'weekly': {'price': 25, 'uses': 100},
            'monthly': {'price': 80, 'uses': 500}
        }

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command handler"""
        keyboard = [
            [InlineKeyboardButton("🎫 Purchase Token", callback_data='purchase')],
            [InlineKeyboardButton("💳 My Account", callback_data='account')],
            [InlineKeyboardButton("ℹ️ Help", callback_data='help')]
        ]
        
        if update.effective_user.id == ADMIN_USER_ID:
            keyboard.append([InlineKeyboardButton("👑 Admin Panel", callback_data='admin')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🤖 *Welcome to PR Bot!*\n\n"
            "I can help you with PR signups and token management.\n"
            "Please select an option:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
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

    async def show_purchase_options(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show token purchase options"""
        keyboard = [
            [InlineKeyboardButton("📅 Daily ($5)", callback_data='buy_daily')],
            [InlineKeyboardButton("📆 Weekly ($25)", callback_data='buy_weekly')],
            [InlineKeyboardButton("📅 Monthly ($80)", callback_data='buy_monthly')],
            [InlineKeyboardButton("🔙 Back", callback_data='back')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(
            "*Token Purchase Options*\n\n"
            "🎫 *Daily:* $5 (10 uses)\n"
            "🎫 *Weekly:* $25 (100 uses)\n"
            "🎫 *Monthly:* $80 (500 uses)\n\n"
            "Select a plan to continue:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def process_purchase(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process token purchase"""
        query = update.callback_query
        plan = query.data.split('_')[1]  # buy_daily -> daily
        
        # Show crypto payment options
        keyboard = [
            [InlineKeyboardButton("💰 Pay with BTC", callback_data=f'crypto_btc_{plan}')],
            [InlineKeyboardButton("💰 Pay with ETH", callback_data=f'crypto_eth_{plan}')],
            [InlineKeyboardButton("🔙 Back to Plans", callback_data='purchase')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"*Payment for {plan.capitalize()} Plan*\n\n"
            f"Amount: ${self.prices[plan]['price']}\n"
            f"Uses: {self.prices[plan]['uses']}\n\n"
            "Select payment method:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button presses"""
        query = update.callback_query
        await query.answer()

        if query.data == 'purchase':
            await self.show_purchase_options(update, context)
        elif query.data.startswith('buy_'):
            await self.process_purchase(update, context)
        elif query.data == 'account':
            await self.show_account(update, context)
        elif query.data == 'help':
            await self.show_help(update, context)
        elif query.data == 'admin' and update.effective_user.id == ADMIN_USER_ID:
            await self.show_admin_panel(query)

    async def show_account(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user account info"""
        user_id = str(update.effective_user.id)
        # Get user's active tokens
        active_tokens = [token for token, data in self.token_manager.tokens['active_tokens'].items() 
                        if data['user_id'] == user_id and data['is_active']]
        
        keyboard = [
            [InlineKeyboardButton("🔄 Top Up", callback_data='purchase')],
            [InlineKeyboardButton("🔙 Back", callback_data='back')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = "*Your Account*\n\n"
        if active_tokens:
            for token in active_tokens:
                data = self.token_manager.tokens['active_tokens'][token]
                message += f"Token: `{token}`\n"
                message += f"Uses remaining: {data['uses_remaining']}\n\n"
        else:
            message += "No active tokens found.\n"
            message += "Purchase a token to get started!"
        
        await update.callback_query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

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

    # Start the bot with port configuration
    print('Bot is starting...')
    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=os.getenv('WEBHOOK_URL', f"https://your-app.onrender.com/")
    )

if __name__ == '__main__':
    main()