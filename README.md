# 🎯 AI 短線數據獵手實驗室 (AI Short-Term Data Hunter Lab)

> **極短線高頻當沖模擬交易實驗室**  
> 一個專門針對高波動標的（Crypto & 美股）設計的 5分鐘線爆量突破策略模擬平台。本系統完全不涉及真錢交易，純粹基於本地端 CSV / JSON 進行虛擬記帳，並結合 **Discord Webhook** 進行全自動化交易信號瘋狂轟炸，支援 **GitHub Actions 24/7 全天候雲端無狀態排程部署**。

---

## ⚡ 核心交易策略與風控

### 1. 狩獵商品清單
*   **加密貨幣 (24/7 交易)**: `BTC-USD`, `ETH-USD`, `SOL-USD`
*   **熱門美股 (美股交易時間)**: `NVDA`, `TSLA`

### 2. 數據獵手策略：5分鐘線爆量突破
程式每次運行時，會自動下載最新的 5分鐘 K 線資料，並以**最新一根已收盤的完整 K 線**作為訊號觸發基準（防止指標漂移）：
*   **震幅突破**: 最新 K 線震幅 $(\text{High} - \text{Low}) > 3 \times \text{過去 14 期平均 ATR}$。
*   **成交量暴增**: 最新 K 線成交量 $\text{Volume} > 3 \times \text{過去 14 期平均成交量}$。
*   **紅 K 確認**: 最新 K 線收盤價 > 開盤價 ($\text{Close} > \text{Open}$)，判定主力爆量強勢拉升。
*   **交易執行**: 立刻以該 K 線收盤價虛擬買入價值 **1,000 USD** 的該商品（扣除 0.1% 單邊手續費後，實際持有價值 999 USD 的資產）。
*   **限制**: 同一商品同一時間只能持有單一倉位，絕不重複加碼。

### 3. 鋼鐵風控與閃電出場
本系統採用量化交易最嚴格的風控守則（已精確計算雙邊手續費）：
*   **單邊手續費**: 0.1% (買入扣 0.1%，賣出扣 0.1%)。
*   **賺錢停利 (Take Profit)**: 扣除手續費後的淨報酬率達 **+2.0%** 時，立刻以最新價格虛擬賣出清倉。
*   **賠錢停損 (Stop Loss)**: 加上手續費後的淨虧損達 **-1.0%** 時，立刻割肉虛擬賣出。
*   **超時強制平倉 (Timeout)**: 若持倉時間達到 **30 分鐘 (6 根 5m K線)** 且未觸發停利/停損，程式將於第 6 根 K 線不計代價強制平倉賣出。

---

## 📂 專案目錄結構

```
AI-Flash-Hunter/
│
├── .github/
│   └── workflows/
│       └── flash_hunter.yml      # GitHub Actions 自動排程與狀態同步工作流
│
├── config.py                     # 核心設定檔 (交易參數、Discord Webhook、檔案路徑)
├── main.py                       # 交易引擎主程式 (數據抓取、指標計算、交易邏輯)
├── requirements.txt              # Python 套件依賴檔
├── README.md                     # 專案部署與操作說明書 (本檔案)
│
├── portfolio_state.json          # 實時帳戶餘額、資產淨值與持倉狀態 (自動生成)
└── portfolio_flash.csv           # 模擬交易流水帳 (自動生成)
```

---

## 💻 本地端快速啟動

### 1. 複製專案並安裝依賴
確保您的系統已安裝 Python 3.8+，並在專案根目錄下執行以下指令：

```bash
# 建立虛擬環境 (選用，但強烈推薦)
python -m venv venv
venv\Scripts\activate  # Windows 系統

# 安裝依賴套件
pip install -r requirements.txt
```

### 2. 配置 Discord Webhook
打開 `config.py` 檔案，在下方欄位填入您的 Discord Webhook 網址：

```python
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/your_actual_webhook_url"
```

### 3. 手動運行交易引擎
```bash
python main.py
```
程式運行後，將在終端輸出交易日誌，自動更新 `portfolio_state.json` 與 `portfolio_flash.csv`，並在觸發交易時向您的 Discord 發送精美的通知！

---

## ☁️ 雲端高頻部署指南 (GitHub Actions)

為了解決 5 分鐘高頻檢測需要 24/7 持續運作的問題，我們使用 **GitHub Actions** 作為免費運算伺服器。

### 1. 建立 GitHub 儲存庫 (Repository)
1. 在 GitHub 上建立一個新的儲存庫，命名為 `AI-Flash-Hunter`。
2. **特別建議 (省錢密技)**：將儲存庫設為 **Public (公開)**。
   > [!TIP]
   > * GitHub 對於 **Private (私有)** 倉庫的 Actions 執行時間限制為每月 **2,000 分鐘**。若每 5 分鐘執行一次，一個月約執行 8,640 次，可能會耗盡免費額度。
   > * 對於 **Public (公開)** 倉庫，GitHub Actions 的執行時間是 **100% 完全免費且無上限** 的！因此將本專案設為 Public 倉庫是最佳選擇。

### 2. 配置 Webhook 安全密鑰 (Secrets)
為了保護您的 Discord Webhook 不被公開：
1. 進入您 GitHub 倉庫的 `Settings` -> `Secrets and variables` -> `Actions`。
2. 點擊 `New repository secret`。
3. 名稱填入：`DISCORD_WEBHOOK_URL`。
4. 內容填入：您的 Discord Webhook 網址（例如：`https://discord.com/api/webhooks/...`）。
5. 點擊 `Add secret`。

### 3. 將程式碼推送到 GitHub
在本地專案目錄下執行以下指令（請替換為您的 Git 倉庫 URL）：

```bash
git init
git add .
git commit -m "Initialize AI Flash Hunter Lab"
git branch -M main
git remote add origin https://github.com/您的用戶名/AI-Flash-Hunter.git
git push -u origin main
```

### 4. 運作原理解析 & 避開執行限制
*   **Git Auto-Commit 技術**：因為 GitHub Actions 的虛擬機是隨用隨銷毀的無狀態容器，我們在工作流 (`flash_hunter.yml`) 中配置了寫入權限，當每次執行有交易產生時，機器人會自動執行 `git commit` 並將更新後的 `portfolio_flash.csv` 和 `portfolio_state.json` 推送回 GitHub 倉庫。
*   **避開 Actions 排程延遲**：GitHub Actions 的 cron 排程有時會因為伺服器隊列負載而延遲 2 到 10 分鐘。我們的程式採用了 **Index-Based (基於 K 線索引) 檢測**。每次執行時，程式會根據歷史數據對比 `positions.json` 中的持倉入場 K 線時間戳。不論這次執行是準時還是遲到，程式均能精準定位自買入後經歷了幾根完整的 5m K 線，實現 100% 的無縫追蹤。
*   **防止無限循環**：Auto-commit 提交時附帶了 `[skip ci]` 標記，這會告訴 GitHub Actions 不要對這個自動提交重複觸發工作流，安全且符合規範。
*   **手動觸發測試**：您可以在 GitHub 倉庫的 `Actions` 分頁中點選 `AI Short-Term Data Hunter Lab Runner`，然後點擊 `Run workflow` 手動立即執行腳本！
