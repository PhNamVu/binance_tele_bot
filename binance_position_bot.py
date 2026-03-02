import logging
from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
import os
from binance.client import Client

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
BINANCE_API_KEY = os.getenv('BINANCE_API_KEY')
BINANCE_SECRET_KEY = os.getenv('BINANCE_SECRET_KEY')
ALLOWED_CHAT_ID = int(os.getenv('ALLOWED_CHAT_ID'))

# Logging để debug
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Kết nối Binance Futures
client = Client(BINANCE_API_KEY, BINANCE_SECRET_KEY)

# Hàm lấy vị thế mở
def get_open_positions():
    try:
        positions = client.futures_position_information()
        open_positions = []
        
        for pos in positions:
            position_amt_str = pos.get('positionAmt', '0')
            if float(position_amt_str) == 0:
                continue
            
            symbol = pos.get('symbol', 'UNKNOWN')
            side = '🟢' if float(position_amt_str) > 0 else '🔴'
            notional = float(pos.get('notional', '0.0'))
            entry_price = float(pos.get('entryPrice', 0.000))
            mark_price = float(pos.get('markPrice', 0.000))
            unrealized_pnl = float(pos.get('unRealizedProfit', 0.0))
            initial_margin = float(pos.get('initialMargin', 0.0))
            
            roe_percent = 0.0
            if initial_margin > 0:
                roe_percent = (unrealized_pnl / initial_margin) * 100
            
            open_positions.append({
                'symbol': symbol,
                'side': side,
                'notional': notional,
                'entry_price': entry_price,
                'mark_price': mark_price,
                'unrealized_pnl': unrealized_pnl,
                'roe_percent': roe_percent,
            })
        
        return open_positions
    except Exception as e:
        logger.error(f"Lỗi lấy position từ Binance: {e}")
        return []

# Lệnh /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
   
    
    if chat_id != ALLOWED_CHAT_ID:
        await update.message.reply_text("Bạn không có quyền sử dụng bot này.")
        return
    
    await update.message.reply_text(
        "Chào bạn! Tôi là bot kiểm tra vị thế Binance Futures.\n"
        "Dùng /opens để xem vị thế đang mở."
    )

# Lệnh /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
   
    
    if chat_id != ALLOWED_CHAT_ID:
        await update.message.reply_text("Bạn không có quyền sử dụng bot này.")
        return
    
    await update.message.reply_text(
        "Lệnh có sẵn:\n"
        "/start - Bắt đầu bot\n"
        "/opens - Xem vị thế mở\n"
        "/help - Hiển thị hướng dẫn"
    )

# Lệnh /opens
async def open_position(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    
    if chat_id != ALLOWED_CHAT_ID:
        await update.message.reply_text("Bạn không có quyền sử dụng bot này.")
        return
    
    positions = get_open_positions()
    
    if not positions:
        message = "Hiện tại không có vị thế mở nào trên Binance Futures."
    else:
        message = "<b>🚨 Opening Positions:</b>\n\n"
        for pos in positions:
            message += f"• {pos['side']} <b>{pos['symbol']}</b> \n"
            message += f"  PNL: ${pos['unrealized_pnl']:.2f}\n"
            message += f"  Volume: ${abs(pos['notional']):.4f}\n"
            message += f"  Entry: ${pos['entry_price']:.4f}\n"
            message += f"  Current: ${pos['mark_price']:.4f}\n"
            message += f"  ROI: {pos['roe_percent']:.2f}%\n"
    
    await update.message.reply_html(message)

# Xử lý lệnh lạ
async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    
    if chat_id != ALLOWED_CHAT_ID:
        return
    await update.message.reply_text("Lệnh không tồn tại. Dùng /help để xem danh sách.")

# Hàm set menu commands tự động
async def set_bot_commands(application: Application) -> None:
    await application.bot.delete_my_commands()
    await application.bot.set_my_commands([
        BotCommand("start", "Bắt đầu sử dụng bot"),
        BotCommand("opens", "Xem vị thế đang mở trên Binance Futures"),
        BotCommand("help", "Hiển thị hướng dẫn lệnh"),
    ])
    logger.info("Đã tự động set menu commands cho bot!")

# Main chạy bot
if __name__ == '__main__':
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Set menu commands tự động khi bot khởi động
    application.post_init = set_bot_commands
    
    # Thêm các handler lệnh
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("opens", open_position))
    
    # Xử lý lệnh không tồn tại
    application.add_handler(MessageHandler(filters.COMMAND, unknown))
    
    print("Bot đang khởi động... Menu commands sẽ tự động được set.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)
