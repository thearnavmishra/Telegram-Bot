from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import uuid
import re

# ================= CONFIG =================

TOKEN = "8501905906:AAF87G4RKywbqD12a_yoSnYQbR8PbYdJmpE"
ADMIN_CHAT_ID = 5563259830

WALLET_ADDRESS = "0xYOUR_ERC20_WALLET_ADDRESS_HERE"
NETWORK = "ERC20"
TOKEN_NAME = "USDT"

# ================= PRODUCTS (USD) =================

PRODUCTS = {
    "p1": {"name": "Herb1", "price_usd": 24},
    "p2": {"name": "Herb2", "price_usd": 6},
    "p3": {"name": "Herb3", "price_usd": 4},
}

# ================= HELPERS =================

def cart_text(cart):
    lines = []
    for p, q in cart.items():
        price = PRODUCTS[p]["price_usd"]
        lines.append(f"{PRODUCTS[p]['name']} × {q} = USD {price*q}")
    return "\n".join(lines)

def cart_total(cart):
    return sum(PRODUCTS[p]["price_usd"] * q for p, q in cart.items())

def product_buttons(prefix="select"):
    return [
        [InlineKeyboardButton(PRODUCTS[pid]["name"], callback_data=f"{prefix}:{pid}")]
        for pid in PRODUCTS
    ]

# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data["cart"] = {}

    await update.message.reply_text(
        "🛍 Select a product:",
        reply_markup=InlineKeyboardMarkup(product_buttons())
    )

# ================= PRODUCT FLOW =================

async def select_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    pid = query.data.split(":")[1]
    context.user_data["selected_product"] = pid

    keyboard = [
        [InlineKeyboardButton("➕ Add to Cart", callback_data="add")],
        [InlineKeyboardButton("🛒 View Cart", callback_data="cart")],
    ]

    await query.message.reply_text(
        f"{PRODUCTS[pid]['name']} - USD {PRODUCTS[pid]['price_usd']}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def add_to_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["awaiting_qty"] = True
    await query.message.reply_text("Enter quantity:")

# ================= CART =================

async def view_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    cart = context.user_data.get("cart", {})
    if not cart:
        await query.message.reply_text("🛒 Cart is empty.")
        return

    keyboard = [
        [InlineKeyboardButton("✏️ Change Quantity", callback_data="edit_qty")],
        [InlineKeyboardButton("❌ Remove Item", callback_data="remove_item")],
        [InlineKeyboardButton("➕ Add More Items", callback_data="more")],
        [InlineKeyboardButton("✅ Checkout", callback_data="checkout")],
    ]

    await query.message.reply_text(
        f"🛒 Your Cart:\n\n{cart_text(cart)}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def add_more_items(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.message.reply_text(
        "🛍 Select another product:",
        reply_markup=InlineKeyboardMarkup(product_buttons())
    )

# ================= EDIT / REMOVE =================

async def edit_qty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.message.reply_text(
        "Select product to change quantity:",
        reply_markup=InlineKeyboardMarkup(product_buttons("qty"))
    )

async def qty_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    pid = query.data.split(":")[1]
    context.user_data["edit_product"] = pid
    context.user_data["editing_qty"] = True

    await query.message.reply_text("Enter new quantity:")

async def remove_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.message.reply_text(
        "Select product to remove:",
        reply_markup=InlineKeyboardMarkup(product_buttons("remove"))
    )

async def remove_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    pid = query.data.split(":")[1]
    context.user_data["cart"].pop(pid, None)
    await view_cart(update, context)

# ================= CHECKOUT =================

async def checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["address_step"] = 1
    context.user_data["address"] = {}

    await query.message.reply_text("🏠 Enter Flat / House Number:")

# ================= ADDRESS FLOW =================

ADDRESS_FIELDS = ["flat", "apartment", "street", "suburb_city", "state", "postal"]

ADDRESS_PROMPTS = {
    "flat": "🏠 Enter Flat / House Number:",
    "apartment": "🏢 Enter Apartment / Building Name (write NA if not applicable):",
    "street": "🛣 Enter Street:",
    "suburb_city": "🌆 Enter Suburb / City:",
    "state": "🏙 Enter State:",
    "postal": "📮 Enter Postal Code:",
}

# ================= TEXT HANDLER =================

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    # Quantity
    if context.user_data.get("awaiting_qty"):
        if not text.isdigit() or int(text) <= 0:
            await update.message.reply_text("❌ Enter a valid number.")
            return

        pid = context.user_data["selected_product"]
        cart = context.user_data.setdefault("cart", {})
        cart[pid] = cart.get(pid, 0) + int(text)
        context.user_data["awaiting_qty"] = False

        keyboard = [
            [InlineKeyboardButton("🛒 View Cart", callback_data="cart")],
            [InlineKeyboardButton("➕ Add More Items", callback_data="more")],
            [InlineKeyboardButton("✅ Checkout", callback_data="checkout")],
        ]

        await update.message.reply_text("✅ Added to cart.", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # Edit quantity
    if context.user_data.get("editing_qty"):
        if not text.isdigit() or int(text) <= 0:
            await update.message.reply_text("❌ Enter a valid number.")
            return

        context.user_data["cart"][context.user_data["edit_product"]] = int(text)
        context.user_data.pop("editing_qty")
        context.user_data.pop("edit_product")
        await view_cart(update, context)
        return

    # Address steps
    if context.user_data.get("address_step"):
        step = context.user_data["address_step"]
        field = ADDRESS_FIELDS[step - 1]
        context.user_data["address"][field] = text

        if step < len(ADDRESS_FIELDS):
            context.user_data["address_step"] += 1
            await update.message.reply_text(ADDRESS_PROMPTS[ADDRESS_FIELDS[step]])
            return

        context.user_data.pop("address_step")

        addr = context.user_data["address"]
        preview = (
            f"📍 Address Preview:\n\n"
            f"{addr['flat']}\n"
            f"{addr['apartment']}\n"
            f"{addr['street']}\n"
            f"{addr['suburb_city']}\n"
            f"{addr['state']}\n"
            f"Postal Code: {addr['postal']}"
        )

        keyboard = [
            [InlineKeyboardButton("✅ Confirm Address", callback_data="confirm_address")],
            [InlineKeyboardButton("✏️ Edit Address", callback_data="edit_address")],
        ]

        await update.message.reply_text(preview, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # TXID
    if context.user_data.get("awaiting_txid"):
        txid = text
        cart = context.user_data["cart"]
        total = cart_total(cart)
        order_id = context.user_data["order_id"]

        addr = context.user_data["address"]
        full_address = (
            f"{addr['flat']}, {addr['apartment']}, {addr['street']}, {addr['suburb_city']}, {addr['state']}\n"
            f"Postal Code: {addr['postal']}"
        )

        user = update.effective_user
        username = f"@{user.username}" if user.username else "N/A"

        admin_message = (
            f"🆕 NEW ORDER\n\n"
            f"🧾 Order ID: {order_id}\n\n"
            f"👤 User Details:\n"
            f"Username: {username}\n"
            f"User ID: {user.id}\n\n"
            f"🛒 Items:\n{cart_text(cart)}\n\n"
            f"💰 Total: USD {total}\n\n"
            f"📍 Address:\n{full_address}\n\n"
            f"🔗 TXID:\n{txid}"
        )

        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_message)
        await update.message.reply_text("✅ Order submitted. Payment will be verified manually.")
        context.user_data.clear()
        return

    await update.message.reply_text("❌ Invalid input. Please use the buttons.")

# ================= ADDRESS CONFIRM =================

async def confirm_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    cart = context.user_data["cart"]
    total = cart_total(cart)

    order_id = str(uuid.uuid4())[:8]
    context.user_data["order_id"] = order_id

    await query.message.reply_text(
        f"🧾 ORDER ID: {order_id}\n\n"
        f"💳 Payment Details\n\n"
        f"Amount: USD {total}\n"
        f"Token: {TOKEN_NAME}\n"
        f"Network: {NETWORK}\n\n"
        f"Wallet Address:\n{WALLET_ADDRESS}\n\n"
        f"⚠️ Please note: only send {NETWORK} {TOKEN_NAME} tokens to this wallet address.\n\n"
        f"⚠️ Please note: keep your Order ID and TXID safe for order support and updates.\n\n"
        f"After payment, send TXID."
    )

    context.user_data["awaiting_txid"] = True

async def edit_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["address_step"] = 1
    context.user_data["address"] = {}
    await query.message.reply_text("🏠 Enter Flat / House Number:")

# ================= RUN =================

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))

app.add_handler(CallbackQueryHandler(select_product, pattern="^select"))
app.add_handler(CallbackQueryHandler(add_to_cart, pattern="add"))
app.add_handler(CallbackQueryHandler(view_cart, pattern="cart"))
app.add_handler(CallbackQueryHandler(add_more_items, pattern="more"))
app.add_handler(CallbackQueryHandler(edit_qty, pattern="edit_qty"))
app.add_handler(CallbackQueryHandler(qty_select, pattern="^qty"))
app.add_handler(CallbackQueryHandler(remove_item, pattern="remove_item"))
app.add_handler(CallbackQueryHandler(remove_confirm, pattern="^remove"))
app.add_handler(CallbackQueryHandler(checkout, pattern="checkout"))
app.add_handler(CallbackQueryHandler(confirm_address, pattern="confirm_address"))
app.add_handler(CallbackQueryHandler(edit_address, pattern="edit_address"))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

app.run_polling()
