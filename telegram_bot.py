from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import os, json, time, hashlib, asyncio
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
        self.token_history = {}
        self.pr_queue = {
            'pending': [],
            'active': [],
            'completed': [],
            'failed': []
        }
        self.active_sessions = {}
        self.blocked_ips = set()

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
        """Enhanced Admin Control Panel"""
        keyboard = [
            [
                InlineKeyboardButton("👥 Users", callback_data='admin_users'),
                InlineKeyboardButton("🎫 Tokens", callback_data='admin_tokens')
            ],
            [
                InlineKeyboardButton("📊 Stats", callback_data='admin_stats'),
                InlineKeyboardButton("⚙️ Settings", callback_data='admin_settings')
            ],
            [
                InlineKeyboardButton("🔄 Queue", callback_data='admin_queue'),
                InlineKeyboardButton("🔒 Security", callback_data='admin_security')
            ],
            [InlineKeyboardButton("🔙 Back", callback_data='back_main')]
        ]
        
        await query.edit_message_text(
            f"{self.header}"
            "*👑 Admin Control Panel*\n\n"
            "Select a module to manage:\n\n"
            "• 👥 Users: Manage user accounts\n"
            "• 🎫 Tokens: Generate/monitor tokens\n"
            "• 📊 Stats: System analytics\n"
            "• ⚙️ Settings: Bot configuration\n"
            "• 🔄 Queue: PR processing queue\n"
            "• 🔒 Security: Security controls",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    async def admin_bulk_tokens(self, query):
        """Generate multiple tokens"""
        keyboard = [
            [
                InlineKeyboardButton("Daily (10)", callback_data='gen_bulk_daily_10'),
                InlineKeyboardButton("Weekly (5)", callback_data='gen_bulk_weekly_5')
            ],
            [
                InlineKeyboardButton("Monthly (3)", callback_data='gen_bulk_monthly_3'),
                InlineKeyboardButton("Custom", callback_data='gen_bulk_custom')
            ],
            [InlineKeyboardButton("🔙 Back to Tokens", callback_data='admin_tokens')]
        ]
        
        await query.edit_message_text(
            f"{self.header}"
            "*🎫 Bulk Token Generation*\n\n"
            "Select a preset or custom amount:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    async def admin_security(self, query):
        """Security controls"""
        security_settings = self.get_security_settings()
        status = "✅" if security_settings.get('ip_logging', False) else "❌"
        rate_limit = security_settings.get('rate_limit', '10/minute')
        
        keyboard = [
            [
                InlineKeyboardButton(f"IP Logging: {status}", callback_data='toggle_ip_logging'),
                InlineKeyboardButton("Rate Limit", callback_data='set_rate_limit')
            ],
            [
                InlineKeyboardButton("View Logs", callback_data='view_security_logs'),
                InlineKeyboardButton("Blocked IPs", callback_data='view_blocked_ips')
            ],
            [InlineKeyboardButton("🔙 Back to Admin", callback_data='admin')]
        ]
        
        await query.edit_message_text(
            f"{self.header}"
            "*🔒 Security Controls*\n\n"
            f"• IP Logging: {status}\n"
            f"• Rate Limit: {rate_limit}\n"
            f"• Active Sessions: {len(self.active_sessions)}\n"
            f"• Blocked IPs: {len(self.blocked_ips)}\n\n"
            "Select an option to configure:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    async def admin_queue(self, query):
        """PR Queue Management"""
        active_prs = len(self.pr_queue.get('active', []))
        pending_prs = len(self.pr_queue.get('pending', []))
        failed_prs = len(self.pr_queue.get('failed', []))
        
        keyboard = [
            [
                InlineKeyboardButton(f"Active ({active_prs})", callback_data='queue_active'),
                InlineKeyboardButton(f"Pending ({pending_prs})", callback_data='queue_pending')
            ],
            [
                InlineKeyboardButton(f"Failed ({failed_prs})", callback_data='queue_failed'),
                InlineKeyboardButton("Settings", callback_data='queue_settings')
            ],
            [InlineKeyboardButton("🔙 Back to Admin", callback_data='admin')]
        ]
        
        await query.edit_message_text(
            f"{self.header}"
            "*🔄 PR Queue Management*\n\n"
            f"• Active PRs: {active_prs}\n"
            f"• Pending PRs: {pending_prs}\n"
            f"• Failed PRs: {failed_prs}\n\n"
            "Select a category to manage:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    async def admin_payment_verification(self, query):
        """Payment verification panel"""
        pending_payments = len(self.payments.get('pending', []))
        
        keyboard = [
            [
                InlineKeyboardButton(f"Pending ({pending_payments})", callback_data='verify_pending'),
                InlineKeyboardButton("History", callback_data='payment_history')
            ],
            [
                InlineKeyboardButton("Settings", callback_data='payment_settings'),
                InlineKeyboardButton("Reports", callback_data='payment_reports')
            ],
            [InlineKeyboardButton("🔙 Back to Admin", callback_data='admin')]
        ]
        
        await query.edit_message_text(
            f"{self.header}"
            "*💰 Payment Management*\n\n"
            f"• Pending Verifications: {pending_payments}\n"
            "• Auto-verification: Enabled\n"
            "• Payment Methods: BTC, ETH, USDT\n\n"
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

    async def show_settings(self, query):
        """Show admin settings"""
        settings_text = (
            f"{self.header}"
            "*⚙️ Bot Settings*\n\n"
            "🔐 *Security Settings*\n"
            "• Token Duration: 24h/7d/30d\n"
            "• Max Uses: 10/100/500\n\n"
            "💰 *Payment Settings*\n"
            "• Min Deposit: $5\n"
            "• Accepted: BTC/ETH/USDT\n\n"
            "🤖 *Bot Settings*\n"
            "• Auto-approve: Enabled\n"
            "• Notifications: Enabled"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("🔐 Security", callback_data='settings_security'),
                InlineKeyboardButton("💰 Payment", callback_data='settings_payment')
            ],
            [InlineKeyboardButton("🔙 Back to Admin", callback_data='admin')]
        ]
        
        await query.edit_message_text(
            settings_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    async def redeem_token(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle token redemption"""
        message = update.message
        user_id = str(message.from_user.id)
        token = message.text.replace("/redeem ", "").strip()

        if token in self.tokens['active']:
            token_data = self.tokens['active'][token]
            
            # Check if token is valid
            if time.time() - token_data['created_at'] <= token_data['duration']:
                if token_data['uses_remaining'] > 0:
                    # Add token to user
                    if user_id not in self.users:
                        self.users[user_id] = {'balance': 0, 'tokens': []}
                    
                    if token not in self.users[user_id]['tokens']:
                        self.users[user_id]['tokens'].append(token)
                        self.save_data()
                        
                        await message.reply_text(
                            f"{self.header}"
                            "✅ *Token Redeemed Successfully*\n\n"
                            f"Uses Remaining: {token_data['uses_remaining']}\n"
                            "Expiry: " + datetime.fromtimestamp(
                                token_data['created_at'] + token_data['duration']
                            ).strftime('%Y-%m-%d %H:%M'),
                            parse_mode='Markdown'
                        )
                    else:
                        await message.reply_text(
                            f"{self.header}"
                            "⚠️ *Token Already Redeemed*\n\n"
                            "This token is already linked to your account.",
                            parse_mode='Markdown'
                        )
                else:
                    await message.reply_text(
                        f"{self.header}"
                        "❌ *Token Depleted*\n\n"
                        "This token has no uses remaining.",
                        parse_mode='Markdown'
                    )
            else:
                await message.reply_text(
                    f"{self.header}"
                    "❌ *Token Expired*\n\n"
                    "This token has expired.",
                    parse_mode='Markdown'
                )
        else:
            await message.reply_text(
                f"{self.header}"
                "❌ *Invalid Token*\n\n"
                "Please check your token and try again.",
                parse_mode='Markdown'
            )

    async def show_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show help and usage instructions"""
        help_text = (
            f"{self.header}"
            "*📖 How to Use TYP4SON Bot*\n\n"
            "*🎫 Token Management:*\n"
            "• /start - Start the bot\n"
            "• /redeem <token> - Redeem a token\n"
            "• /balance - Check your balance\n"
            "• /help - Show this help\n\n"
            "*🔄 Using PR Service:*\n"
            "1. Get a token (trial or purchase)\n"
            "2. Copy your GitHub PR URL\n"
            "3. Send the URL to this bot\n"
            "4. Wait for processing\n\n"
            "*💡 Tips:*\n"
            "• Keep your tokens secure\n"
            "• Check token expiry dates\n"
            "• Monitor remaining uses\n"
            "• Contact support if needed"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("🎁 Get Trial", callback_data='trial'),
                InlineKeyboardButton("💰 Buy Token", callback_data='purchase')
            ],
            [InlineKeyboardButton("👤 Profile", callback_data='profile')]
        ]
        
        await update.message.reply_text(
            help_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    async def admin_token_history(self, query):
        """View token usage history"""
        history_text = (
            f"{self.header}"
            "*📜 Token Usage History*\n\n"
        )
        
        recent_usage = sorted(
            self.token_history.items(),
            key=lambda x: x[1]['timestamp'],
            reverse=True
        )[:5]
        
        for token_id, data in recent_usage:
            history_text += (
                f"Token: `{token_id[:10]}...`\n"
                f"Used: {datetime.fromtimestamp(data['timestamp']).strftime('%Y-%m-%d %H:%M')}\n"
                f"User: `{data['user_id']}`\n"
                f"Status: {'✅' if data['success'] else '❌'}\n"
                "━━━━━━━━━━\n"
            )
        
        keyboard = [
            [
                InlineKeyboardButton("📊 Analytics", callback_data='token_analytics'),
                InlineKeyboardButton("🔍 Search", callback_data='token_search')
            ],
            [InlineKeyboardButton("🔙 Back", callback_data='admin_tokens')]
        ]
        
        await query.edit_message_text(
            history_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    def get_security_settings(self):
        """Get current security settings"""
        return {
            'ip_logging': True,
            'rate_limit': '10/minute',
            'active_sessions': {},
            'blocked_ips': set(),
            '2fa_enabled': True,
            'suspicious_activity_detection': True
        }

    async def process_pr_queue(self):
        """Process PR queue"""
        while True:
            if self.pr_queue['pending']:
                pr_data = self.pr_queue['pending'].pop(0)
                self.pr_queue['active'].append(pr_data)
                
                try:
                    # Process PR logic here
                    success = True  # Replace with actual processing
                    
                    if success:
                        self.pr_queue['completed'].append(pr_data)
                    else:
                        self.pr_queue['failed'].append(pr_data)
                        
                except Exception as e:
                    self.logger.error(f"PR processing error: {str(e)}")
                    self.pr_queue['failed'].append(pr_data)
                
                finally:
                    self.pr_queue['active'].remove(pr_data)
            
            await asyncio.sleep(1)  # Prevent CPU overload

    def initialize_data(self):
        """Initialize bot data structures"""
        self.token_history = {}
        self.pr_queue = {
            'pending': [],
            'active': [],
            'completed': [],
            'failed': []
        }
        self.payments = {
            'pending': [],
            'completed': [],
            'failed': []
        }
        self.active_sessions = {}
        self.blocked_ips = set()

def main():
    """Start the bot"""
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    bot = PRBotTelegram()

    # Add handlers
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CommandHandler("help", bot.show_help))
    application.add_handler(CommandHandler("redeem", bot.redeem_token))
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