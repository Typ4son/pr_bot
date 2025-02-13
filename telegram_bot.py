from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import os, json, time, hashlib
from dotenv import load_dotenv
import logging
from datetime import datetime

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID'))

class PRBotTelegram:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.user_trials = {}
        self.tokens = self.load_tokens()
        self.users = self.load_users()
        self.header = (
            "🤖 *TYP4SON BOT*\n"
            "━━━━━━━━━━━━━━━\n\n"
        )

    def load_tokens(self):
        try:
            with open('tokens.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {"active": {}, "expired": {}}

    def load_users(self):
        try:
            with open('users.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_data(self):
        with open('tokens.json', 'w') as f:
            json.dump(self.tokens, f, indent=2)
        with open('users.json', 'w') as f:
            json.dump(self.users, f, indent=2)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Simple start menu"""
        keyboard = [
            [InlineKeyboardButton("🎁 Free Trial", callback_data='trial')],
            [InlineKeyboardButton("💰 Buy Token", callback_data='purchase')],
            [InlineKeyboardButton("👤 Profile", callback_data='profile')]
        ]
        
        if update.effective_user.id == ADMIN_USER_ID:
            keyboard.append([InlineKeyboardButton("👑 Admin Panel", callback_data='admin')])

        await update.message.reply_text(
            f"{self.header}"
            "Welcome! Choose an option below:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    async def show_profile(self, query):
        """Show user profile"""
        user_id = query.from_user.id
        user_data = self.users.get(str(user_id), {})
        
        profile_text = (
            f"{self.header}"
            "*👤 Profile Information*\n\n"
            f"🆔 User ID: `{user_id}`\n"
            f"💰 Balance: ${user_data.get('balance', 0):.2f}\n"
            f"🎫 Active Tokens: {len(user_data.get('tokens', []))}\n"
            "━━━━━━━━━━━━━━━"
        )
        
        keyboard = [
            [InlineKeyboardButton("💳 Add Funds", callback_data='add_funds')],
            [InlineKeyboardButton("🔙 Back", callback_data='back_main')]
        ]
        
        await query.edit_message_text(
            profile_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    async def handle_admin(self, query):
        """Admin panel handler"""
        keyboard = [
            [
                InlineKeyboardButton("👥 Users", callback_data='admin_users'),
                InlineKeyboardButton("🎫 Tokens", callback_data='admin_tokens')
            ],
            [
                InlineKeyboardButton("📊 Stats", callback_data='admin_stats'),
                InlineKeyboardButton("⚙️ Settings", callback_data='admin_settings')
            ],
            [InlineKeyboardButton("🔙 Back", callback_data='back_main')]
        ]
        
        await query.edit_message_text(
            f"{self.header}"
            "*👑 Admin Control Panel*\n\n"
            "Select an option to manage:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button presses"""
        query = update.callback_query
        data = query.data
        
        try:
            await query.answer()
            
            if data == 'profile':
                await self.show_profile(query)
            elif data == 'admin':
                if query.from_user.id == ADMIN_USER_ID:
                    await self.handle_admin(query)
                else:
                    await query.edit_message_text("Unauthorized access!")
            elif data.startswith('admin_'):
                if query.from_user.id == ADMIN_USER_ID:
                    action = data.split('_')[1]
                    await self.handle_admin_action(query, action)
            elif data == 'back_main':
                keyboard = [
                    [InlineKeyboardButton("🎁 Free Trial", callback_data='trial')],
                    [InlineKeyboardButton("💰 Buy Token", callback_data='purchase')],
                    [InlineKeyboardButton("👤 Profile", callback_data='profile')]
                ]
                
                if query.from_user.id == ADMIN_USER_ID:
                    keyboard.append([InlineKeyboardButton("👑 Admin Panel", callback_data='admin')])
                
                await query.edit_message_text(
                    f"{self.header}"
                    "Welcome! Choose an option below:",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
            elif data == 'trial':
                await self.handle_trial(query)
            elif data == 'purchase':
                await self.show_purchase_options(query)

        except Exception as e:
            self.logger.error(f"Callback error: {str(e)}")
            await query.edit_message_text(
                f"{self.header}"
                "An error occurred. Please try /start again.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔄 Start Over", callback_data='back_main')
                ]])
            )

    async def handle_admin_action(self, query, action):
        """Handle admin panel actions"""
        if action == 'users':
            page = 0
            users_per_page = 5
            all_users = list(self.users.items())
            total_pages = (len(all_users) + users_per_page - 1) // users_per_page
            
            users_text = f"{self.header}👥 User Management*\n\n"
            start_idx = page * users_per_page
            end_idx = min(start_idx + users_per_page, len(all_users))
            
            for user_id, data in all_users[start_idx:end_idx]:
                users_text += f"ID: `{user_id}`\n"
                users_text += f"Balance: ${data.get('balance', 0):.2f}\n"
                users_text += "━━━━━━━━━━\n"
            
            keyboard = [
                [
                    InlineKeyboardButton("⬅️ Prev", callback_data='admin_users_prev'),
                    InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data='page_info'),
                    InlineKeyboardButton("➡️ Next", callback_data='admin_users_next')
                ],
                [InlineKeyboardButton("🔙 Back to Admin", callback_data='admin')]
            ]
            
            await query.edit_message_text(
                users_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )

    async def handle_trial(self, query):
        """Handle free trial token generation"""
        user_id = str(query.from_user.id)
        
        if user_id in self.user_trials:
            last_trial = self.user_trials[user_id]
            if time.time() - last_trial < 86400:
                hours_left = 24 - (time.time() - last_trial) / 3600
                await query.edit_message_text(
                    f"{self.header}"
                    "⚠️ *Trial Limit Reached*\n\n"
                    f"Please wait {int(hours_left)} hours for a new trial.\n"
                    "Or purchase a token below:",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("💰 Purchase Token", callback_data='purchase')],
                        [InlineKeyboardButton("🔙 Back", callback_data='back_main')]
                    ]),
                    parse_mode='Markdown'
                )
                return

        trial_token = self.generate_token(86400, 3)
        self.user_trials[user_id] = time.time()
        
        if user_id not in self.users:
            self.users[user_id] = {'balance': 0, 'tokens': []}
        self.users[user_id]['tokens'].append(trial_token)
        self.save_data()
        
        await query.edit_message_text(
            f"{self.header}"
            "🎁 *Your Trial Token*\n\n"
            f"`{trial_token}`\n\n"
            "✨ *Features*:\n"
            "• Valid for 24 hours\n"
            "• 3 uses included\n"
            "• Full access to all features\n\n"
            "_Use this token to test our services_",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💰 Buy Full Access", callback_data='purchase')],
                [InlineKeyboardButton("🔙 Back", callback_data='back_main')]
            ]),
            parse_mode='Markdown'
        )

    async def show_purchase_options(self, query):
        """Show available purchase plans"""
        plans = {
            'daily': {'price': 5, 'uses': 10, 'duration': '1 Day'},
            'weekly': {'price': 25, 'uses': 100, 'duration': '1 Week'},
            'monthly': {'price': 80, 'uses': 500, 'duration': '1 Month'}
        }
        
        message = f"{self.header}💰 Available Plans*\n\n"
        keyboard = []
        
        for plan_id, details in plans.items():
            message += (
                f"*{details['duration']}*\n"
                f"💵 Price: ${details['price']}\n"
                f"🎫 Uses: {details['uses']}\n"
                "━━━━━━━━━━\n"
            )
            keyboard.append([
                InlineKeyboardButton(
                    f"Buy {details['duration']} (${details['price']})",
                    callback_data=f'buy_{plan_id}'
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton("💳 Add Funds", callback_data='add_funds'),
            InlineKeyboardButton("🔙 Back", callback_data='back_main')
        ])
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    async def handle_purchase(self, query, plan):
        """Handle token purchase"""
        user_id = str(query.from_user.id)
        plans = {
            'daily': {'price': 5, 'uses': 10, 'duration': 86400},
            'weekly': {'price': 25, 'uses': 100, 'duration': 604800},
            'monthly': {'price': 80, 'uses': 500, 'duration': 2592000}
        }
        
        if plan not in plans:
            await query.edit_message_text(
                f"{self.header}"
                "❌ Invalid plan selected.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Back", callback_data='purchase')
                ]])
            )
            return
        
        plan_details = plans[plan]
        user_balance = self.users.get(user_id, {}).get('balance', 0)
        
        if user_balance < plan_details['price']:
            await query.edit_message_text(
                f"{self.header}"
                "❌ *Insufficient Balance*\n\n"
                f"Required: ${plan_details['price']}\n"
                f"Your Balance: ${user_balance}\n\n"
                "Please add funds to continue:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💳 Add Funds", callback_data='add_funds')],
                    [InlineKeyboardButton("🔙 Back", callback_data='purchase')]
                ]),
                parse_mode='Markdown'
            )
            return
        
        # Generate token
        token = self.generate_token(
            plan_details['duration'],
            plan_details['uses']
        )
        
        # Update user data
        if user_id not in self.users:
            self.users[user_id] = {'balance': 0, 'tokens': []}
        self.users[user_id]['balance'] -= plan_details['price']
        self.users[user_id]['tokens'].append(token)
        self.save_data()
        
        await query.edit_message_text(
            f"{self.header}"
            "✅ *Purchase Successful!*\n\n"
            f"Your new token:\n`{token}`\n\n"
            f"Duration: {plan_details['duration'] // 86400} days\n"
            f"Uses: {plan_details['uses']}\n"
            f"Remaining Balance: ${self.users[user_id]['balance']:.2f}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Shop", callback_data='purchase')],
                [InlineKeyboardButton("🏠 Main Menu", callback_data='back_main')]
            ]),
            parse_mode='Markdown'
        )

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    bot = PRBotTelegram()

    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CallbackQueryHandler(bot.handle_callback))

    print('Bot is starting...')
    if os.getenv('ENVIRONMENT') == 'production':
        port = int(os.getenv('PORT', 8080))
        webhook_url = os.getenv('WEBHOOK_URL')
        application.run_webhook(listen="0.0.0.0", port=port, webhook_url=webhook_url)
    else:
        application.run_polling()

if __name__ == '__main__':
    main()