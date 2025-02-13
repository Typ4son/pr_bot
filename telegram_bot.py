from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
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
        self.payments = {}
        self.header = (
            "🤖 *TYP4SON PR BOT*\n"
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
        try:
            with open('tokens.json', 'w') as f:
                json.dump(self.tokens, f, indent=2)
            with open('users.json', 'w') as f:
                json.dump(self.users, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving data: {str(e)}")

    def generate_token(self, duration: int, uses: int) -> str:
        timestamp = int(time.time())
        token_base = f"PR-{timestamp}-{duration}-{uses}"
        token_hash = hashlib.sha256(token_base.encode()).hexdigest()[:8]
        token = f"{token_base}-{token_hash}"
        
        self.tokens['active'][token] = {
            'created_at': timestamp,
            'duration': duration,
            'uses_remaining': uses
        }
        self.save_data()
        return token

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command handler"""
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
                    await query.edit_message_text(
                        f"{self.header}❌ Unauthorized access!",
                        parse_mode='Markdown'
                    )
            elif data == 'trial':
                await self.handle_trial(query)
            elif data == 'purchase':
                await self.show_purchase_options(query)
            elif data.startswith('buy_'):
                plan = data.split('_')[1]
                await self.handle_purchase(query, plan)
            elif data == 'back_main':
                await self.show_main_menu(query)
            elif data.startswith('admin_'):
                if query.from_user.id == ADMIN_USER_ID:
                    action = data.split('_')[1]
                    await self.handle_admin_action(query, action)

        except Exception as e:
            self.logger.error(f"Callback error: {str(e)}")
            await query.edit_message_text(
                f"{self.header}❌ An error occurred.\nPlease try /start again.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔄 Start Over", callback_data='back_main')
                ]]),
                parse_mode='Markdown'
            )

    async def show_main_menu(self, query):
        """Show main menu"""
        keyboard = [
            [InlineKeyboardButton("🎁 Free Trial", callback_data='trial')],
            [InlineKeyboardButton("💰 Buy Token", callback_data='purchase')],
            [InlineKeyboardButton("👤 Profile", callback_data='profile')]
        ]
        
        if query.from_user.id == ADMIN_USER_ID:
            keyboard.append([InlineKeyboardButton("👑 Admin Panel", callback_data='admin')])

        await query.edit_message_text(
            f"{self.header}"
            "Choose an option below:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    async def handle_admin_action(self, query, action):
        """Handle admin panel actions"""
        if action == 'users':
            await self.show_users_list(query)
        elif action == 'tokens':
            await self.show_tokens_list(query)
        elif action == 'stats':
            await self.show_stats(query)
        elif action == 'settings':
            await self.show_settings(query)

    async def show_users_list(self, query):
        """Show users list with pagination"""
        users_text = (
            f"{self.header}"
            "*👥 User Management*\n\n"
        )
        
        if not self.users:
            users_text += "No users found."
        else:
            for user_id, data in list(self.users.items())[:5]:  # Show first 5 users
                users_text += f"ID: `{user_id}`\n"
                users_text += f"Balance: ${data.get('balance', 0):.2f}\n"
                users_text += "━━━━━━━━━━\n"

        keyboard = [
            [InlineKeyboardButton("🔙 Back to Admin", callback_data='admin')]
        ]
        
        await query.edit_message_text(
            users_text,
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

    async def show_tokens_list(self, query):
        """Show active tokens list"""
        tokens_text = (
            f"{self.header}"
            "*🎫 Token Management*\n\n"
        )
        
        active_tokens = self.tokens.get('active', {})
        if not active_tokens:
            tokens_text += "No active tokens found."
        else:
            for token, data in list(active_tokens.items())[:5]:
                expiry = datetime.fromtimestamp(data['created_at'] + data['duration'])
                tokens_text += f"Token: `{token[:15]}...`\n"
                tokens_text += f"Uses Left: {data['uses_remaining']}\n"
                tokens_text += f"Expires: {expiry.strftime('%Y-%m-%d %H:%M')}\n"
                tokens_text += "━━━━━━━━━━\n"

        keyboard = [
            [InlineKeyboardButton("🆕 Generate Token", callback_data='admin_generate')],
            [InlineKeyboardButton("🔙 Back to Admin", callback_data='admin')]
        ]
        
        await query.edit_message_text(
            tokens_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    async def show_stats(self, query):
        """Show system statistics"""
        total_users = len(self.users)
        total_active_tokens = len(self.tokens.get('active', {}))
        total_expired_tokens = len(self.tokens.get('expired', {}))
        total_trials = len(self.user_trials)
        
        stats_text = (
            f"{self.header}"
            "*📊 System Statistics*\n\n"
            f"👥 Total Users: {total_users}\n"
            f"🎫 Active Tokens: {total_active_tokens}\n"
            f"📅 Expired Tokens: {total_expired_tokens}\n"
            f"🎁 Trial Users: {total_trials}\n"
            "━━━━━━━━━━\n\n"
            "*Recent Activity:*\n"
        )
        
        # Add recent activity
        recent_tokens = sorted(
            self.tokens.get('active', {}).items(),
            key=lambda x: x[1]['created_at'],
            reverse=True
        )[:3]
        
        for token, data in recent_tokens:
            created = datetime.fromtimestamp(data['created_at'])
            stats_text += f"Token Created: {created.strftime('%Y-%m-%d %H:%M')}\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Admin", callback_data='admin')]]
        
        await query.edit_message_text(
            stats_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    async def handle_pr(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle PR submission and processing"""
        message = update.message
        user_id = str(message.from_user.id)
        
        # Check if message contains PR URL
        text = message.text.strip()
        if not text.startswith(('http://github.com/', 'https://github.com/')):
            await message.reply_text(
                f"{self.header}"
                "❌ *Invalid PR URL*\n\n"
                "Please send a valid GitHub PR URL.",
                parse_mode='Markdown'
            )
            return
        
        # Validate token
        valid_token = await self.validate_user_token(user_id)
        if not valid_token:
            await message.reply_text(
                f"{self.header}"
                "❌ *No Valid Token Found*\n\n"
                "Please purchase a token or get a trial:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎁 Free Trial", callback_data='trial')],
                    [InlineKeyboardButton("💰 Buy Token", callback_data='purchase')]
                ]),
                parse_mode='Markdown'
            )
            return
        
        # Process PR
        try:
            await message.reply_text(
                f"{self.header}"
                "🔄 *Processing PR*\n\n"
                "Please wait...",
                parse_mode='Markdown'
            )
            
            # Your PR processing logic here
            pr_result = await self.process_pr(text)
            
            if pr_result['success']:
                # Update token usage
                await self.update_token_usage(valid_token, user_id)
                
                await message.reply_text(
                    f"{self.header}"
                    "✅ *PR Processed Successfully*\n\n"
                    f"Status: {pr_result['status']}\n"
                    f"Uses remaining: {pr_result['uses_remaining']}",
                    parse_mode='Markdown'
                )
            else:
                await message.reply_text(
                    f"{self.header}"
                    "❌ *PR Processing Failed*\n\n"
                    f"Error: {pr_result['error']}",
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            self.logger.error(f"PR processing error: {str(e)}")
            await message.reply_text(
                f"{self.header}"
                "❌ *Error Processing PR*\n\n"
                "Please try again later.",
                parse_mode='Markdown'
            )

    async def handle_payment(self, query, payment_method: str):
        """Handle payment processing"""
        user_id = str(query.from_user.id)
        payment_data = query.data.split('_')  # payment_crypto_btc_amount
        amount = float(payment_data[3])
        
        payment_info = {
            'crypto': {
                'btc': {'address': 'your_btc_address', 'network': 'Bitcoin'},
                'eth': {'address': 'your_eth_address', 'network': 'Ethereum'},
                'usdt': {'address': 'your_usdt_address', 'network': 'TRC20'}
            }
        }
        
        if payment_method == 'crypto':
            crypto = payment_data[2]
            if crypto in payment_info['crypto']:
                crypto_data = payment_info['crypto'][crypto]
                
                message = (
                    f"{self.header}"
                    "*💰 Crypto Payment*\n\n"
                    f"Amount: ${amount}\n"
                    f"Currency: {crypto.upper()}\n"
                    f"Network: {crypto_data['network']}\n\n"
                    "*Payment Address:*\n"
                    f"`{crypto_data['address']}`\n\n"
                    "Send the exact amount to this address.\n"
                    "_Payment will be confirmed automatically._"
                )
                
                keyboard = [
                    [InlineKeyboardButton("✅ I've Paid", callback_data=f'verify_{crypto}_{amount}')],
                    [InlineKeyboardButton("🔙 Back", callback_data='purchase')]
                ]
                
                await query.edit_message_text(
                    message,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
                
                # Create payment record
                payment_id = f"PAY-{user_id}-{int(time.time())}"
                self.payments[payment_id] = {
                    'user_id': user_id,
                    'amount': amount,
                    'method': 'crypto',
                    'currency': crypto,
                    'status': 'pending',
                    'created_at': int(time.time())
                }
                self.save_data()

    async def verify_payment(self, query, payment_id: str):
        """Verify payment status"""
        payment = self.payments.get(payment_id)
        if not payment:
            await query.edit_message_text(
                f"{self.header}"
                "❌ *Payment Not Found*\n\n"
                "Please try again or contact support.",
                parse_mode='Markdown'
            )
            return
        
        try:
            # Implement your payment verification logic here
            # For example, check blockchain for crypto payments
            payment_verified = True  # Replace with actual verification
            
            if payment_verified:
                user_id = payment['user_id']
                amount = payment['amount']
                
                # Update user balance
                if user_id not in self.users:
                    self.users[user_id] = {'balance': 0, 'tokens': []}
                self.users[user_id]['balance'] += amount
                
                # Update payment status
                payment['status'] = 'completed'
                self.save_data()
                
                await query.edit_message_text(
                    f"{self.header}"
                    "✅ *Payment Confirmed*\n\n"
                    f"Amount: ${amount}\n"
                    f"New Balance: ${self.users[user_id]['balance']:.2f}",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🎫 Buy Token", callback_data='purchase')],
                        [InlineKeyboardButton("🔙 Main Menu", callback_data='back_main')]
                    ]),
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text(
                    f"{self.header}"
                    "⏳ *Payment Pending*\n\n"
                    "Please wait for confirmation...",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔄 Check Again", callback_data=f'verify_{payment_id}')]
                    ]),
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            self.logger.error(f"Payment verification error: {str(e)}")
            await query.edit_message_text(
                f"{self.header}"
                "❌ *Verification Error*\n\n"
                "Please try again later or contact support.",
                parse_mode='Markdown'
            )

def main():
    """Start the bot"""
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    bot = PRBotTelegram()

    # Add handlers
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CallbackQueryHandler(bot.handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_pr))

    print('Bot is starting...')
    if os.getenv('ENVIRONMENT') == 'production':
        port = int(os.getenv('PORT', 8080))
        webhook_url = os.getenv('WEBHOOK_URL')
        application.run_webhook(listen="0.0.0.0", port=port, webhook_url=webhook_url)
    else:
        application.run_polling()

if __name__ == '__main__':
    main()