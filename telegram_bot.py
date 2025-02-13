from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import os
from dotenv import load_dotenv
import logging
import json
import time
import hashlib
from datetime import datetime

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
        self.user_trials = {}
        self.tokens = self.load_tokens()
        self.users = self.load_users()

    def load_tokens(self):
        """Load tokens from file"""
        try:
            with open('tokens.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {"active": {}, "expired": {}}

    def load_users(self):
        """Load user data"""
        try:
            with open('users.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_data(self):
        """Save tokens and users"""
        with open('tokens.json', 'w') as f:
            json.dump(self.tokens, f, indent=2)
        with open('users.json', 'w') as f:
            json.dump(self.users, f, indent=2)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command handler"""
        try:
            user = update.effective_user
            keyboard = [
                [
                    InlineKeyboardButton("💰 Balance", callback_data='balance'),
                    InlineKeyboardButton("🔄 Forward", callback_data='forward')
                ],
                [
                    InlineKeyboardButton("⬅️ Backup", callback_data='backup'),
                    InlineKeyboardButton("👤 Profile", callback_data='profile')
                ],
                [InlineKeyboardButton("🎫 Purchase Token", callback_data='purchase')],
            ]
            
            if update.effective_user.id == ADMIN_USER_ID:
                keyboard.append([InlineKeyboardButton("👑 Admin Panel", callback_data='admin')])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            welcome_text = (
                f"*Welcome {user.first_name}!*\n\n"
                f"🆔 Account ID: `{user.id}`\n"
                "━━━━━━━━━━━━━━━\n"
                "Select an option below:"
            )
            
            if hasattr(update, 'message') and update.message:
                await update.message.reply_text(
                    welcome_text,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            elif hasattr(update, 'callback_query') and update.callback_query:
                await update.callback_query.edit_message_text(
                    welcome_text,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
        except Exception as e:
            self.logger.error(f"Error in start: {str(e)}")
            error_message = "Sorry, something went wrong. Please try again."
            if hasattr(update, 'message') and update.message:
                await update.message.reply_text(error_message)
            elif hasattr(update, 'callback_query') and update.callback_query:
                await update.callback_query.answer(error_message)

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

    async def show_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user profile"""
        user = update.effective_user
        user_id = str(user.id)
        
        # Get user's balance
        balance = self.get_user_balance(user_id)
        
        profile_text = (
            f"*👤 Profile Information*\n\n"
            f"🆔 Account ID: `{user_id}`\n"
            f"💰 Balance: ${balance:.2f}\n"
            "━━━━━━━━━━━━━━━\n"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("💳 Add Funds", callback_data='add_funds'),
                InlineKeyboardButton("📊 History", callback_data='history')
            ],
            [InlineKeyboardButton("🔙 Back", callback_data='back_to_main')]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(
            profile_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def handle_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle crypto payments"""
        query = update.callback_query
        payment_data = query.data.split('_')  # crypto_btc_daily
        currency = payment_data[1]
        plan = payment_data[2]
        
        # Generate payment address (you'll need to implement this)
        payment_address = self.get_crypto_address(currency)
        amount = self.prices[plan]['price']
        
        payment_text = (
            f"*💰 Payment Details*\n\n"
            f"Plan: {plan.capitalize()}\n"
            f"Amount: ${amount}\n"
            f"Currency: {currency.upper()}\n"
            "━━━━━━━━━━━━━━━\n\n"
            f"Send payment to:\n`{payment_address}`\n\n"
            "Payment will be confirmed automatically.\n"
            "_Please wait for 2 confirmations._"
        )
        
        keyboard = [
            [InlineKeyboardButton("✅ I've Paid", callback_data=f'verify_{currency}_{plan}')],
            [InlineKeyboardButton("🔙 Back", callback_data='purchase')]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            payment_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    def get_user_balance(self, user_id: str) -> float:
        """Get user's current balance"""
        # Implement your balance tracking logic here
        return 0.00  # Placeholder

    def get_crypto_address(self, currency: str) -> str:
        """Get crypto payment address"""
        addresses = {
            'btc': 'your_btc_address',
            'eth': 'your_eth_address'
        }
        return addresses.get(currency, 'Invalid currency')

    async def forward_backup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle forward/backup operations"""
        query = update.callback_query
        action = query.data  # 'forward' or 'backup'
        
        if action == 'forward':
            message = (
                "*⏩ Forward Operation*\n\n"
                "Your forward progress will be saved.\n"
                "Continue with your session."
            )
        else:  # backup
            message = (
                "*⏪ Backup Operation*\n\n"
                "Your previous session will be restored.\n"
                "Please wait..."
            )
            
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data='back_to_main')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button presses"""
        try:
            query = update.callback_query
            await query.answer()

            if query.data == 'profile':
                await self.show_profile(update, context)
            elif query.data in ['forward', 'backup']:
                await self.forward_backup(update, context)
            elif query.data.startswith('crypto_'):
                await self.handle_payment(update, context)
            elif query.data == 'back_to_main':
                await self.start(update, context)
            elif query.data == 'balance':
                await self.show_balance(update, context)
            elif query.data == 'purchase':
                await self.show_purchase_options(update, context)
            elif query.data == 'admin':
                await self.show_admin_panel(query)
        except Exception as e:
            self.logger.error(f"Error in button_handler: {str(e)}")
            await query.answer("Sorry, something went wrong. Please try again.")

    async def show_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user balance"""
        try:
            user_id = str(update.effective_user.id)
            balance = self.get_user_balance(user_id)
            
            keyboard = [
                [InlineKeyboardButton("💳 Add Funds", callback_data='add_funds')],
                [InlineKeyboardButton("🔙 Back", callback_data='back_to_main')]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.callback_query.edit_message_text(
                f"*💰 Your Balance*\n\n"
                f"Current Balance: ${balance:.2f}\n"
                "━━━━━━━━━━━━━━━",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        except Exception as e:
            self.logger.error(f"Error in show_balance: {str(e)}")
            await update.callback_query.answer("Error showing balance. Please try again.")

    async def show_admin_panel(self, query):
        """Admin control panel"""
        keyboard = [
            [
                InlineKeyboardButton("👥 Users", callback_data='admin_users'),
                InlineKeyboardButton("🎫 Tokens", callback_data='admin_tokens')
            ],
            [
                InlineKeyboardButton("📊 Stats", callback_data='admin_stats'),
                InlineKeyboardButton("⚙️ Settings", callback_data='admin_settings')
            ],
            [InlineKeyboardButton("🔙 Back", callback_data='back')]
        ]
        
        await query.edit_message_text(
            "*👑 Admin Panel*\n\n"
            "Select an option to manage:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    async def handle_admin_callback(self, query, action):
        """Handle admin panel actions"""
        if action == 'users':
            total_users = len(self.users)
            active_users = sum(1 for u in self.users.values() if u.get('active_token'))
            
            stats = (
                "*👥 User Statistics*\n\n"
                f"Total Users: {total_users}\n"
                f"Active Users: {active_users}\n"
                f"Trial Users: {len(self.user_trials)}\n\n"
                "Recent Activity:"
            )
            
            # Show last 5 active users
            recent = sorted(
                self.users.items(), 
                key=lambda x: x[1].get('last_active', 0),
                reverse=True
            )[:5]
            
            for user_id, data in recent:
                last_active = datetime.fromtimestamp(data.get('last_active', 0))
                stats += f"\nID: {user_id} - {last_active.strftime('%Y-%m-%d %H:%M')}"
            
            keyboard = [[InlineKeyboardButton("🔙 Back to Admin", callback_data='admin')]]
            await query.edit_message_text(
                stats,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )

        elif action == 'tokens':
            active_tokens = len(self.tokens['active'])
            expired_tokens = len(self.tokens['expired'])
            
            stats = (
                "*🎫 Token Statistics*\n\n"
                f"Active Tokens: {active_tokens}\n"
                f"Expired Tokens: {expired_tokens}\n\n"
                "Recent Tokens:"
            )
            
            # Show last 5 active tokens
            recent = sorted(
                self.tokens['active'].items(),
                key=lambda x: x[1].get('created_at', 0),
                reverse=True
            )[:5]
            
            for token, data in recent:
                created = datetime.fromtimestamp(data.get('created_at', 0))
                stats += f"\n`{token[:15]}...`\n└ {created.strftime('%Y-%m-%d %H:%M')}"
            
            keyboard = [
                [InlineKeyboardButton("🆕 Generate Token", callback_data='admin_generate')],
                [InlineKeyboardButton("🔙 Back to Admin", callback_data='admin')]
            ]
            await query.edit_message_text(
                stats,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )

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
    
    # Get the webhook URL from environment variable
    webhook_url = os.getenv('WEBHOOK_URL')
    print(f'Webhook URL: {webhook_url}')

    if os.getenv('ENVIRONMENT') == 'production':
        # Use webhook in production
        print('Starting webhook...')
        application.run_webhook(
            listen="0.0.0.0",
            port=int(os.getenv('PORT', 8080)),
            webhook_url=webhook_url,
            drop_pending_updates=True
        )
    else:
        # Use polling in development
        print('Starting polling...')
        application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()