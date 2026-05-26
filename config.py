import os

# ==============================================================================
#                      AI 短線數據獵手實驗室 - 核心配置參數
# ==============================================================================

# 1. 監控商品清單 (加密貨幣 24/7, 美股開盤時間交易)
SYMBOLS = ["BTC-USD", "ETH-USD", "SOL-USD", "NVDA", "TSLA"]

# 2. 資金與交易規模
INITIAL_CASH = 10000.0        # 初始虛擬本金 (USD)
TRADE_AMOUNT_USD = 1000.0     # 每筆交易固定投入金額 (USD)
FEE_RATE = 0.001              # 單邊手續費率 (0.1%)

# 3. 數據獵手策略參數 (5分鐘 K 線爆量突破)
ATR_PERIOD = 14               # ATR 計算期數
ATR_MULTIPLIER = 3.0          # 震幅突破 ATR 倍數
VOLUME_MULTIPLIER = 3.0       # 成交量突破均量倍數

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

# 6. 本地數據持久化檔案路徑
PORTFOLIO_CSV = "portfolio_flash.csv"
STATE_JSON = "portfolio_state.json"
