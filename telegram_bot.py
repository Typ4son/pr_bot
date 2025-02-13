from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import os, json, time, hashlib, asyncio, random
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
        self.notification_task = None

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
        """Handle /start command"""
        user_id = str(update.effective_user.id)
        
        welcome_message = (
            f"{self.header}"
            "*Welcome to TYP4SON Bot!* 🚀\n\n"
            "*Services Available:*\n"
            "• Unique PR Text Generation\n"
            "• Multiple Subscription Plans\n"
            "• Instant Processing\n\n"
            "*Get Started:*\n"
            "1. Choose a plan below\n"
            "2. Start using the service\n"
            "3. Monitor your usage"
        )
        
        # Check if user has active subscription
        has_subscription = await self.check_subscription(user_id)
        
        if has_subscription:
            keyboard = [
                [InlineKeyboardButton("📝 Start Using", callback_data='start_processing')],
                [InlineKeyboardButton("📊 My Account", callback_data='account_status')],
                [
                    InlineKeyboardButton("💫 Upgrade", callback_data='upgrade_plan'),
                    InlineKeyboardButton("❓ Help", callback_data='show_help')
                ]
            ]
        else:
            keyboard = [
                [
                    InlineKeyboardButton("🎁 Free Trial", callback_data='trial'),
                    InlineKeyboardButton("💰 Buy Plan", callback_data='purchase')
                ],
                [
                    InlineKeyboardButton("📖 How it Works", callback_data='show_instructions'),
                    InlineKeyboardButton("❓ Help", callback_data='show_help')
                ]
            ]
        
        await update.message.reply_text(
            welcome_message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    async def check_subscription(self, user_id: str) -> bool:
        """Check if user has active subscription"""
        if not hasattr(self, 'subscriptions'):
            self.subscriptions = {}
            
        if user_id in self.subscriptions:
            sub_data = self.subscriptions[user_id]
            if sub_data['expires_at'] > time.time():
                return True
        return False

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
                await self.show_payment_options(query)
            elif data.startswith('pay_'):
                await self.handle_payment_selection(query)
            elif data == 'check_payment':
                await self.check_payment_status(query)
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
        admin_menu = (
            f"{self.header}"
            "*👑 Admin Control Panel*\n\n"
            "*Quick Stats:*\n"
            f"• Active Users: {len(self.users)}\n"
            f"• Active Tokens: {len(self.tokens.get('active', {}))}\n"
            f"• Trial Users: {len(self.user_trials)}\n"
            f"• Pending PRs: {len(self.pr_queue.get('pending', []))}\n\n"
            "*Available Actions:*\n"
            "• 👥 Users - Manage users\n"
            "• 🎫 Tokens - Manage tokens\n"
            "• 💰 Payments - Configure payments\n"
            "• 📊 Stats - View analytics\n"
            "• ⚙️ Settings - Bot configuration\n"
            "• 🔒 Security - Access controls"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("👥 Users", callback_data='admin_users'),
                InlineKeyboardButton("🎫 Tokens", callback_data='admin_tokens')
            ],
            [
                InlineKeyboardButton("💰 Payments", callback_data='admin_payments'),
                InlineKeyboardButton("📊 Stats", callback_data='admin_stats')
            ],
            [
                InlineKeyboardButton("⚙️ Settings", callback_data='admin_settings'),
                InlineKeyboardButton("🔒 Security", callback_data='admin_security')
            ],
            [InlineKeyboardButton("🔙 Main Menu", callback_data='back_main')]
        ]
        
        await query.edit_message_text(
            admin_menu,
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
        
        # Check if user already had a trial
        if user_id in self.user_trials:
            last_trial = self.user_trials[user_id]
            if time.time() - last_trial['timestamp'] < 86400 * 30:  # 30 days cooldown
                days_left = 30 - (time.time() - last_trial['timestamp']) / 86400
                await query.edit_message_text(
                    f"{self.header}"
                    "⚠️ *Trial Not Available*\n\n"
                    f"Please wait {int(days_left)} days for a new trial.\n"
                    "Or purchase a token below:",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("💰 Purchase Token", callback_data='purchase')],
                        [InlineKeyboardButton("🔙 Back", callback_data='back_main')]
                    ]),
                    parse_mode='Markdown'
                )
                return

        # Generate trial token
        trial_token = self.generate_token(86400, 3)  # 24 hours, 3 uses
        self.tokens['active'][trial_token] = {
            'type': 'trial',
            'created_at': time.time(),
            'duration': 86400,
            'uses_remaining': 3,
            'redeemed': False
        }
        
        self.save_data()
        
        await query.edit_message_text(
            f"{self.header}"
            "🎁 *Your Trial Token is Ready!*\n\n"
            "*Your Token:*\n"
            f"`{trial_token}`\n\n"
            "*How to Use:*\n"
            "1. Copy the token above\n"
            "2. Send it as a message to activate\n"
            "3. Start using the service\n\n"
            "*Token Details:*\n"
            "• Valid for 24 hours\n"
            "• 3 uses included\n"
            "• One trial per account",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📖 How to Use", callback_data='show_instructions')],
                [InlineKeyboardButton("💰 Buy Full Access", callback_data='purchase')],
                [InlineKeyboardButton("🔙 Back", callback_data='back_main')]
            ]),
            parse_mode='Markdown'
        )

    async def show_instructions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show clear usage instructions"""
        instructions = (
            f"{self.header}"
            "*📖 How to Use TYP4SON Bot*\n\n"
            "*1️⃣ Get Started:*\n"
            "• Use /start to begin\n"
            "• Get trial or buy token\n\n"
            "*2️⃣ Redeem Token:*\n"
            "• Simply send your token to the bot\n"
            "• Example: `ABC123XYZ`\n"
            "• Wait for confirmation\n\n"
            "*3️⃣ Use Service:*\n"
            "• Send your PR text\n"
            "• Bot will process it\n"
            "• Get unique version\n\n"
            "*4️⃣ Important Notes:*\n"
            "• One trial per account\n"
            "• Tokens are single-use\n"
            "• Check /status anytime\n\n"
            "*Need Help?*\n"
            "Contact support: @typ4son_support"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("🎁 Get Trial", callback_data='trial'),
                InlineKeyboardButton("💰 Buy Token", callback_data='purchase')
            ],
            [InlineKeyboardButton("📊 Check Status", callback_data='check_status')],
            [InlineKeyboardButton("🔙 Main Menu", callback_data='back_main')]
        ]
        
        if isinstance(update, Update):
            await update.message.reply_text(
                instructions,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        else:
            await update.edit_message_text(
                instructions,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )

    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages - either token redemption or PR processing"""
        message = update.message
        user_id = str(message.from_user.id)
        text = message.text.strip()

        # Check if text looks like a token (e.g., alphanumeric, specific length)
        if len(text) == 10 and text.isalnum():  # Adjust token format as needed
            await self.handle_token_redemption(message, text)
        else:
            await self.process_pr_text_message(message, text)

    async def handle_token_redemption(self, message, token: str):
        """Handle token redemption process"""
        user_id = str(message.from_user.id)

        # Check if token exists and is not used
        if token in self.tokens.get('active', {}):
            token_data = self.tokens['active'][token]
            
            # Check if token is already redeemed
            if token_data.get('redeemed'):
                await message.reply_text(
                    f"{self.header}"
                    "❌ *Token Already Used*\n\n"
                    "This token has already been redeemed.\n"
                    "Please get a new token:",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("💰 Buy Token", callback_data='purchase')]
                    ]),
                    parse_mode='Markdown'
                )
                return

            # Check if user already has a trial (for trial tokens)
            if token_data.get('type') == 'trial':
                if user_id in self.user_trials:
                    await message.reply_text(
                        f"{self.header}"
                        "❌ *Trial Limit Reached*\n\n"
                        "You have already used your trial.\n"
                        "Please purchase a token to continue:",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("💰 Buy Token", callback_data='purchase')]
                        ]),
                        parse_mode='Markdown'
                    )
                    return
                self.user_trials[user_id] = {
                    'timestamp': time.time(),
                    'token': token,
                    'uses_remaining': 3
                }

            # Add token to user and mark as redeemed
            if user_id not in self.users:
                self.users[user_id] = {'tokens': [], 'balance': 0}
            
            self.users[user_id]['tokens'].append(token)
            token_data['redeemed'] = True
            token_data['redeemed_by'] = user_id
            token_data['redeemed_at'] = time.time()
            
            self.save_data()
            
            # Send confirmation
            expiry_date = datetime.fromtimestamp(
                token_data['created_at'] + token_data['duration']
            ).strftime('%Y-%m-%d %H:%M')
            
            await message.reply_text(
                f"{self.header}"
                "✅ *Token Activated Successfully!*\n\n"
                "*Token Details:*\n"
                f"• Type: {token_data.get('type', 'Standard').title()}\n"
                f"• Uses: {token_data['uses_remaining']}\n"
                f"• Expires: {expiry_date}\n\n"
                "*Ready to Use:*\n"
                "• Send your PR text\n"
                "• Get unique version\n"
                "• Monitor with /status",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📝 Start Using", callback_data='start_processing')],
                    [InlineKeyboardButton("📊 Check Status", callback_data='check_status')]
                ]),
                parse_mode='Markdown'
            )
        else:
            await message.reply_text(
                f"{self.header}"
                "❌ *Invalid Token*\n\n"
                "This token is invalid or expired.\n"
                "Please check and try again or get a new token:",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("🎁 Free Trial", callback_data='trial'),
                        InlineKeyboardButton("💰 Buy Token", callback_data='purchase')
                    ]
                ]),
                parse_mode='Markdown'
            )

    async def show_payment_options(self, query):
        """Show available payment options"""
        message = (
            f"{self.header}"
            "*💰 Purchase Tokens*\n\n"
            "*Available Plans:*\n\n"
            "1️⃣ *Starter Pack*\n"
            "• 50 uses\n"
            "• 30 days validity\n"
            "• $10\n\n"
            "2️⃣ *Pro Pack*\n"
            "• 200 uses\n"
            "• 60 days validity\n"
            "• $30\n\n"
            "3️⃣ *Premium Pack*\n"
            "• 500 uses\n"
            "• 90 days validity\n"
            "• $60\n\n"
            "*Select a plan to continue:*"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("Starter $10", callback_data='pay_starter'),
                InlineKeyboardButton("Pro $30", callback_data='pay_pro')
            ],
            [
                InlineKeyboardButton("Premium $60", callback_data='pay_premium'),
                InlineKeyboardButton("Custom", callback_data='pay_custom')
            ],
            [InlineKeyboardButton("💳 Payment Methods", callback_data='payment_methods')],
            [InlineKeyboardButton("🔙 Back", callback_data='back_main')]
        ]
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    async def handle_payment_selection(self, query):
        """Handle payment plan selection"""
        plan = query.data.split('_')[1]
        
        plans = {
            'starter': {'price': 10, 'uses': 50, 'days': 30},
            'pro': {'price': 30, 'uses': 200, 'days': 60},
            'premium': {'price': 60, 'uses': 500, 'days': 90},
            'custom': {'price': 0, 'uses': 0, 'days': 0}  # Handled separately
        }
        
        if plan not in plans:
            await query.edit_message_text(
                f"{self.header}"
                "❌ *Invalid Selection*\n\n"
                "Please try again.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Back to Plans", callback_data='purchase')
                ]]),
                parse_mode='Markdown'
            )
            return
            
        if plan == 'custom':
            await self.show_custom_plan(query)
            return
            
        selected_plan = plans[plan]
        
        message = (
            f"{self.header}"
            "*🛒 Payment Details*\n\n"
            f"*Selected Plan:* {plan.title()}\n"
            f"*Price:* ${selected_plan['price']}\n"
            f"*Uses:* {selected_plan['uses']}\n"
            f"*Validity:* {selected_plan['days']} days\n\n"
            "*Payment Methods:*\n"
            "• Crypto (BTC/ETH/USDT)\n"
            "• Credit Card\n"
            "• Bank Transfer\n\n"
            "*Select payment method to continue:*"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("💎 Crypto", callback_data=f'crypto_{plan}'),
                InlineKeyboardButton("💳 Card", callback_data=f'card_{plan}')
            ],
            [
                InlineKeyboardButton("🏦 Bank", callback_data=f'bank_{plan}'),
                InlineKeyboardButton("❓ Help", callback_data='payment_help')
            ],
            [InlineKeyboardButton("🔙 Back to Plans", callback_data='purchase')]
        ]
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    async def show_custom_plan(self, query):
        """Show custom plan options"""
        message = (
            f"{self.header}"
            "*🎯 Custom Plan*\n\n"
            "*Choose Your Package:*\n\n"
            "• Uses: 100-1000\n"
            "• Validity: 30-180 days\n"
            "• Custom features\n\n"
            "*Contact us to create your plan:*\n"
            "• @typ4son_support\n\n"
            "*Include in your message:*\n"
            "• Desired uses\n"
            "• Validity period\n"
            "• Special requirements"
        )
        
        keyboard = [
            [InlineKeyboardButton("💬 Contact Support", url='https://t.me/typ4son_support')],
            [InlineKeyboardButton("🔙 Back to Plans", callback_data='purchase')]
        ]
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    async def show_payment_methods(self, query):
        """Show available payment methods details"""
        message = (
            f"{self.header}"
            "*💳 Payment Methods*\n\n"
            "*1. Cryptocurrency*\n"
            "• BTC\n"
            "• ETH\n"
            "• USDT (TRC20)\n\n"
            "*2. Credit Card*\n"
            "• Visa\n"
            "• Mastercard\n"
            "• American Express\n\n"
            "*3. Bank Transfer*\n"
            "• International\n"
            "• SWIFT\n"
            "• Wire Transfer\n\n"
            "*Select method for instructions*"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("🪙 Crypto", callback_data='method_crypto'),
                InlineKeyboardButton("💳 Card", callback_data='method_card')
            ],
            [
                InlineKeyboardButton("🏦 Bank", callback_data='method_bank'),
                InlineKeyboardButton("❓ Help", callback_data='payment_help')
            ],
            [InlineKeyboardButton("🔙 Back", callback_data='purchase')]
        ]
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    async def check_payment_status(self, query):
        """Check payment status"""
        user_id = str(query.from_user.id)
        
        if user_id in self.payments.get('pending', []):
            await query.edit_message_text(
                f"{self.header}"
                "*💰 Payment Status: Pending*\n\n"
                "Your payment is being processed.\n"
                "Please wait for confirmation.\n\n"
                "This usually takes 5-15 minutes.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Check Again", callback_data='check_payment')],
                    [InlineKeyboardButton("❓ Need Help", callback_data='payment_help')]
                ]),
                parse_mode='Markdown'
            )
        elif user_id in self.payments.get('completed', []):
            await query.edit_message_text(
                f"{self.header}"
                "✅ *Payment Completed*\n\n"
                "Your token has been activated.\n"
                "Check your status with /status",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📊 Check Status", callback_data='check_status')]
                ]),
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(
                f"{self.header}"
                "❌ *No Pending Payments*\n\n"
                "Would you like to purchase a token?",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💰 Purchase", callback_data='purchase')],
                    [InlineKeyboardButton("🔙 Back", callback_data='back_main')]
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

    async def show_token_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user's token status and details"""
        user_id = str(update.effective_user.id)
        
        # Check trial token
        trial_status = "No trial token"
        if user_id in self.user_trials:
            trial = self.user_trials[user_id]
            time_left = 86400 - (time.time() - trial['timestamp'])  # 24 hours in seconds
            if time_left > 0:
                hours_left = int(time_left / 3600)
                trial_status = f"Active - {trial['uses_remaining']} uses left ({hours_left}h remaining)"
            else:
                trial_status = "Expired"

        # Check purchased tokens
        active_tokens = []
        if user_id in self.users:
            for token in self.users[user_id]['tokens']:
                if token in self.tokens['active']:
                    token_data = self.tokens['active'][token]
                    expiry = datetime.fromtimestamp(
                        token_data['created_at'] + token_data['duration']
                    ).strftime('%Y-%m-%d %H:%M')
                    active_tokens.append({
                        'token': token,
                        'uses': token_data['uses_remaining'],
                        'expiry': expiry
                    })

        # Prepare status message
        status_text = (
            f"{self.header}"
            "*🎫 Token Status*\n\n"
            f"*Trial Token:*\n{trial_status}\n\n"
        )

        if active_tokens:
            status_text += "*Active Tokens:*\n"
            for token in active_tokens:
                status_text += (
                    f"• Token: `{token['token'][:10]}...`\n"
                    f"  Uses: {token['uses']}\n"
                    f"  Expires: {token['expiry']}\n"
                    "━━━━━━━━━━\n"
                )
        else:
            status_text += "*No active tokens*\n"

        # Add balance if exists
        if user_id in self.users:
            balance = self.users[user_id].get('balance', 0)
            status_text += f"\n*Balance:* ${balance:.2f}"

        keyboard = [
            [InlineKeyboardButton("🎁 Get Trial", callback_data='trial')] if trial_status == "No trial token" else [],
            [InlineKeyboardButton("💰 Buy Token", callback_data='purchase')],
            [InlineKeyboardButton("📖 How to Use", callback_data='show_instructions')],
            [InlineKeyboardButton("🔙 Main Menu", callback_data='back_main')]
        ]

        try:
            await update.message.reply_text(
                status_text,
                reply_markup=InlineKeyboardMarkup([k for k in keyboard if k]),  # Remove empty lists
                parse_mode='Markdown'
            )
        except Exception as e:
            self.logger.error(f"Status display error: {str(e)}")
            # Fallback simple status
            await update.message.reply_text(
                f"{self.header}"
                "❌ *Error Displaying Status*\n\n"
                "Please try again or contact support.",
                parse_mode='Markdown'
            )

    def get_user_preferences(self, user_id: str) -> dict:
        """Get user preferences for text processing"""
        if not hasattr(self, 'user_preferences'):
            self.user_preferences = {}
            
        if user_id not in self.user_preferences:
            # Default preferences
            self.user_preferences[user_id] = {
                'style': 'basic',
                'variations': 1,
                'format': 'markdown'
            }
            
        return self.user_preferences[user_id]

    def save_data(self):
        """Save all bot data"""
        try:
            # Save tokens
            with open('tokens.json', 'w') as f:
                json.dump(self.tokens, f)
            
            # Save users
            with open('users.json', 'w') as f:
                json.dump(self.users, f)
            
            # Save trials
            with open('trials.json', 'w') as f:
                json.dump(self.user_trials, f)
            
            # Save preferences
            with open('preferences.json', 'w') as f:
                json.dump(getattr(self, 'user_preferences', {}), f)
                
        except Exception as e:
            self.logger.error(f"Data save error: {str(e)}")

    def load_data(self):
        """Load all bot data"""
        try:
            # Load tokens
            if os.path.exists('tokens.json'):
                with open('tokens.json', 'r') as f:
                    self.tokens = json.load(f)
            else:
                self.tokens = {'active': {}, 'expired': {}}
            
            # Load users
            if os.path.exists('users.json'):
                with open('users.json', 'r') as f:
                    self.users = json.load(f)
            else:
                self.users = {}
            
            # Load trials
            if os.path.exists('trials.json'):
                with open('trials.json', 'r') as f:
                    self.user_trials = json.load(f)
            else:
                self.user_trials = {}
            
            # Load preferences
            if os.path.exists('preferences.json'):
                with open('preferences.json', 'r') as f:
                    self.user_preferences = json.load(f)
            else:
                self.user_preferences = {}
                
        except Exception as e:
            self.logger.error(f"Data load error: {str(e)}")
            # Initialize with empty data if load fails
            self.tokens = {'active': {}, 'expired': {}}
            self.users = {}
            self.user_trials = {}
            self.user_preferences = {}

    async def start_notification_checker(self, application: Application):
        """Start the notification checker"""
        async def notification_job(context: ContextTypes.DEFAULT_TYPE):
            try:
                current_time = time.time()
                
                # Check expiring tokens
                for user_id, user_data in self.users.items():
                    for token in user_data.get('tokens', []):
                        if token in self.tokens.get('active', {}):
                            token_data = self.tokens['active'][token]
                            expiry_time = token_data['created_at'] + token_data['duration']
                            days_left = (expiry_time - current_time) / 86400
                            
                            # Notify if token expires in 3 days
                            if 2.5 < days_left < 3:
                                await self.send_notification(
                                    user_id,
                                    'token_expiring',
                                    days_left=int(days_left),
                                    token=token
                                )
                            
                            # Notify if token has low uses
                            if token_data.get('uses_remaining', 0) <= 3:
                                await self.send_notification(
                                    user_id,
                                    'low_uses',
                                    uses_left=token_data['uses_remaining'],
                                    token=token
                                )
                
            except Exception as e:
                self.logger.error(f"Notification job error: {str(e)}")

        # Add job to application's job queue
        job_queue = application.job_queue
        job_queue.run_repeating(notification_job, interval=21600, first=10)  # Run every 6 hours
        self.logger.info("Notification checker started")

    async def send_notification(self, user_id: str, notification_type: str, **kwargs):
        """Send notifications to users"""
        try:
            if notification_type == 'token_expiring':
                days_left = kwargs.get('days_left', 0)
                token = kwargs.get('token', '')
                message = (
                    f"{self.header}"
                    "⚠️ *Token Expiring Soon*\n\n"
                    f"Your token `{token[:10]}...` will expire in {days_left} days.\n\n"
                    "*Actions:*\n"
                    "• Purchase new token\n"
                    "• Check remaining uses\n"
                    "• Transfer remaining balance"
                )
                keyboard = [
                    [InlineKeyboardButton("💰 Buy New Token", callback_data='purchase')],
                    [InlineKeyboardButton("📊 Check Status", callback_data='check_status')]
                ]

            elif notification_type == 'low_uses':
                uses_left = kwargs.get('uses_left', 0)
                token = kwargs.get('token', '')
                message = (
                    f"{self.header}"
                    "⚠️ *Low Token Uses*\n\n"
                    f"Your token `{token[:10]}...` has {uses_left} uses remaining.\n\n"
                    "*Recommended Actions:*\n"
                    "• Purchase new token\n"
                    "• Check current balance\n"
                    "• View available plans"
                )
                keyboard = [
                    [InlineKeyboardButton("💰 Buy New Token", callback_data='purchase')],
                    [InlineKeyboardButton("📊 Check Balance", callback_data='check_balance')]
                ]

            else:
                return

            await context.bot.send_message(
                chat_id=user_id,
                text=message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )

        except Exception as e:
            self.logger.error(f"Notification error for {user_id}: {str(e)}")

def main():
    """Start the bot"""
    # Initialize bot and application
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    bot = PRBotTelegram()
    
    # Add handlers
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CommandHandler("help", bot.show_instructions))
    application.add_handler(CommandHandler("status", bot.show_token_status))
    application.add_handler(CallbackQueryHandler(bot.handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_text))

    # Start notification checker
    bot.start_notification_checker(application)

    print('Bot is starting...')
    if os.getenv('ENVIRONMENT') == 'production':
        port = int(os.getenv('PORT', 8080))
        webhook_url = os.getenv('WEBHOOK_URL')
        application.run_webhook(
            listen="0.0.0.0",
            port=port,
            webhook_url=webhook_url,
            drop_pending_updates=True
        )
    else:
        application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()