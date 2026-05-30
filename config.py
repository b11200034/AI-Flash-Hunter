import os

# ==============================================================================
#                      AI 短線數據獵手實驗室 - 核心配置參數
# ==============================================================================

# 1. 監控商品清單 (加密貨幣 24/7, 美股開盤時間交易)
# 已擴展至 16 個高流動性、高波動性商品 (8個加密貨幣 + 8個美股熱門科技股)
SYMBOLS = [
    # --- 加密貨幣 (Crypto 24/7 盯盤) ---
    "BTC-USD", "ETH-USD", "SOL-USD", "DOGE-USD", "XRP-USD", "AVAX-USD", "LINK-USD", "ADA-USD",
    # --- 熱門美股科技與 AI 概念股 (美股時間盯盤) ---
    "NVDA", "TSLA", "AMD", "COIN", "PLTR", "META", "MSFT", "AMZN"
]

# 2. 資金與交易規模
INITIAL_CASH = 10000.0        # 初始虛擬本金 (USD)
TRADE_AMOUNT_USD = 1000.0     # 每筆交易固定投入金額 (USD)
FEE_RATE = 0.001              # 單邊手續費率 (0.1%)

# 3. 數據獵手策略參數 (5分鐘 K 線爆量突破 - 已還原為嚴格黃金突破版)
ATR_PERIOD = 14               # ATR 計算期數
ATR_MULTIPLIER = 3.0          # 震幅突破 ATR 倍數 (還原為嚴格的 3.0 倍)
VOLUME_MULTIPLIER = 3.0       # 成交量突破均量倍數 (還原為嚴格的 3.0 倍)

# 4. 鋼鐵風控與出場條件
TAKE_PROFIT_PCT = 0.02        # 淨報酬率停利門檻 (+2%)
STOP_LOSS_PCT = -0.01         # 淨虧損停損門檻 (-1%)
MAX_HOLD_BARS = 6             # 時間限制強制出場 K 線數 (6 根 5m K線 = 30分鐘)

# 5. Discord Webhook 配置
# 優先從環境變數讀取 (GitHub Actions 部署最佳實踐)，若無則使用此處的預設字串 (本地測試用)
DISCORD_WEBHOOK_URL = os.getenv(
    "DISCORD_WEBHOOK_URL",
    "YOUR_DISCORD_WEBHOOK_URL_HERE"  # 請在此處填入您的 Discord Webhook 網址 (本地測試時)
)

# 6. 每日定時心跳回報設定
DAILY_REPORT_HOUR = 18         # 每日定時發送健康回報的台灣時間小時數 (18 代表下午 6 點)

# 7. 本地數據持久化檔案路徑
PORTFOLIO_CSV = "portfolio_flash.csv"
STATE_JSON = "portfolio_state.json"
