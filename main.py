import os
import json
import logging
from datetime import datetime
import pandas as pd
import yfinance as yf
import requests
import config

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("flash_hunter.log", encoding="utf-8")
    ]
)

# ==============================================================================
#                      0. 一次性 Webhook 連線對接測試
# ==============================================================================

def check_and_send_test_notification():
    """發送一次性的 Discord Webhook 對接成功測試通知"""
    test_file = "test_sent.txt"
    if os.path.exists(test_file):
        return

    url = config.DISCORD_WEBHOOK_URL
    if not url or url == "YOUR_DISCORD_WEBHOOK_URL_HERE":
        logging.warning("未配置 Discord Webhook，跳過一次性對接測試。")
        return

    embed = {
        "title": "🔔 AI 短線數據獵手 - 系統對接成功！",
        "description": "恭喜！您的 Discord Webhook 管道已順利打通，連線測試成功！🎉",
        "color": 3447003,  # #3498DB (藍色)
        "fields": [
            {"name": "系統狀態 (Status)", "value": "🟢 雲端實時監控中 (Online)", "inline": True},
            {"name": "初始資金池 (Cash)", "value": f"`${config.INITIAL_CASH:,.2f} USD`", "inline": True},
            {"name": "監控標的 (Symbols)", "value": f"`{', '.join(config.SYMBOLS)}`", "inline": False},
            {"name": "提示", "value": "此通知為**一次性測試通知**。未來系統將嚴格遵循防干擾原則，**只有在觸發真實模擬買入/賣出時**才會發送通知。", "inline": False}
        ],
        "footer": {
            "text": f"AI Short-Term Data Hunter Lab | 測試時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        }
    }
    payload = {"embeds": [embed]}
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 204:
            logging.info("【系統測試】成功發送對接測試通知至 Discord！")
            with open(test_file, "w", encoding="utf-8") as f:
                f.write(f"Test sent at {datetime.now()}")
        else:
            logging.error(f"【系統測試】發送測試通知失敗，狀態碼: {response.status_code}")
    except Exception as e:
        logging.error(f"【系統測試】發送測試通知時發生異常: {str(e)}")


def send_daily_report(state, tw_time):
    """發送每日定時心跳與資產健康回報"""
    url = config.DISCORD_WEBHOOK_URL
    if not url or url == "YOUR_DISCORD_WEBHOOK_URL_HERE":
        return

    cash = state["cash"]
    total_value = state["total_value"]
    positions = state["positions"]
    
    # 計算自開始以來的累計報酬率
    cum_pnl = total_value - config.INITIAL_CASH
    cum_pnl_pct = (cum_pnl / config.INITIAL_CASH) * 100
    pnl_sign = "+" if cum_pnl >= 0 else ""

    # 整理當前持倉清單
    pos_details = []
    if not positions:
        pos_str = "📭 目前無持有部位 (All Clear)"
    else:
        for sym, pos in positions.items():
            pos_details.append(f"• `{sym}`: 入場價 `${pos['buy_price']:,.4f}` | 數量 `{pos['quantity']:,.4f}` | 已持有 `{pos['bars_held']}` 根 K線")
        pos_str = "\n".join(pos_details)

    embed = {
        "title": "🔔 AI 短線數據獵手 - 每日運作健康回報",
        "description": "系統在雲端持續穩定運作中，今日心跳與資產結算報告已生成！",
        "color": 1149618,  # #118AB2 (深藍綠色)
        "fields": [
            {"name": "系統狀態 (Status)", "value": "🟢 正常實時檢測中 (Active)", "inline": True},
            {"name": "台灣時間 (Time)", "value": f"`{tw_time.strftime('%Y-%m-%d %H:%M:%S')}`", "inline": True},
            {"name": "可用現金 (Available Cash)", "value": f"`${cash:,.2f} USD`", "inline": True},
            {"name": "帳戶總淨值 (Total Net Value)", "value": f"**${total_value:,.2f} USD**", "inline": True},
            {"name": "累計總收益 (Total PnL)", "value": f"**{pnl_sign}${cum_pnl:,.2f} USD ({pnl_sign}{cum_pnl_pct:.2f}%)**", "inline": True},
            {"name": "監控商品 (Symbols)", "value": f"`{', '.join(config.SYMBOLS)}`", "inline": False},
            {"name": "當前模擬持倉狀況", "value": pos_str, "inline": False}
        ],
        "footer": {
            "text": "AI Short-Term Data Hunter Lab | 每日自動對接健康回報"
        }
    }
    
    payload = {"embeds": [embed]}
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 204:
            logging.info("【每日心跳】成功發送每日健康心跳通知至 Discord！")
        else:
            logging.error(f"【每日心跳】發送每日心跳通知失敗，狀態碼: {response.status_code}")
    except Exception as e:
        logging.error(f"【每日心跳】發送每日心跳通知時發生異常: {str(e)}")


# ==============================================================================
#                      1. 數據儲存與載入 (JSON & CSV 持久化)
# ==============================================================================

def init_portfolio_files():
    """初始化模擬帳戶狀態 JSON 與交易流水帳 CSV"""
    # 初始化 JSON 狀態
    if not os.path.exists(config.STATE_JSON):
        state = {
            "cash": config.INITIAL_CASH,
            "total_value": config.INITIAL_CASH,
            "positions": {},
            "last_daily_report_date": ""
        }
        with open(config.STATE_JSON, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=4, ensure_ascii=False)
        logging.info(f"成功初始化狀態檔案: {config.STATE_JSON}")

    # 初始化 CSV 流水帳
    if not os.path.exists(config.PORTFOLIO_CSV):
        headers = [
            "timestamp", "symbol", "action", "price", "quantity", 
            "fee", "net_pnl", "cash_balance", "portfolio_value", "notes"
        ]
        df = pd.DataFrame(columns=headers)
        df.to_csv(config.PORTFOLIO_CSV, index=False, encoding="utf-8-sig")
        logging.info(f"成功初始化交易流水帳: {config.PORTFOLIO_CSV}")


def load_state():
    """載入當前模擬帳戶狀態"""
    init_portfolio_files()
    with open(config.STATE_JSON, "r", encoding="utf-8") as f:
        state = json.load(f)
    # 確保有每日回報日期的欄位 (相容舊檔)
    if "last_daily_report_date" not in state:
        state["last_daily_report_date"] = ""
    return state


def save_state(state):
    """保存模擬帳戶狀態"""
    with open(config.STATE_JSON, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=4, ensure_ascii=False)


def log_transaction(symbol, action, price, quantity, fee, net_pnl, cash_balance, portfolio_value, notes=""):
    """將交易記錄寫入本地 CSV 流水帳"""
    new_row = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "symbol": symbol,
        "action": action,
        "price": round(price, 4),
        "quantity": round(quantity, 6),
        "fee": round(fee, 4),
        "net_pnl": round(net_pnl, 4),
        "cash_balance": round(cash_balance, 2),
        "portfolio_value": round(portfolio_value, 2),
        "notes": notes
    }
    df = pd.DataFrame([new_row])
    df.to_csv(config.PORTFOLIO_CSV, mode="a", header=False, index=False, encoding="utf-8-sig")
    logging.info(f"【CSV 記帳】{symbol} {action} | 價格: {price:.4f} | 損益: {net_pnl:.4f} | 可用現金: {cash_balance:.2f}")


# ==============================================================================
#                      2. Discord 精美通知發送機制 (Rich Embeds)
# ==============================================================================

def send_discord_notification(event_type, symbol, price, quantity, fee, net_pnl, cash_balance, total_value, notes=""):
    """使用 Discord Webhook Rich Embeds 發送精美的交易日誌"""
    url = config.DISCORD_WEBHOOK_URL
    if not url or url == "YOUR_DISCORD_WEBHOOK_URL_HERE":
        logging.warning("未配置有效的 Discord Webhook URL，跳過發送通知。")
        return

    # 定義事件視覺化格式
    event_styles = {
        "BUY": {
            "title": "🚀 AI 數據獵手 - 虛擬買入建倉",
            "color": 3120708,  # #2F9E44 (綠色)
            "emoji": "🟢"
        },
        "SELL_TP": {
            "title": "🏆 AI 數據獵手 - 虛擬停利出場",
            "color": 2853438,  # #2B8A3E (亮綠色)
            "emoji": "🏆"
        },
        "SELL_SL": {
            "title": "🚨 AI 數據獵手 - 虛擬停損割肉",
            "color": 13183530,  # #C92A2A (紅色)
            "emoji": "🔴"
        },
        "SELL_TIMEOUT": {
            "title": "⏰ AI 數據獵手 - 超時強制平倉",
            "color": 15105570,  # #E67E22 (橘色)
            "emoji": "⏳"
        }
    }

    style = event_styles.get(event_type, {
        "title": "📈 AI 數據獵手 - 交易事件",
        "color": 8421504,
        "emoji": "ℹ️"
    })

    # 本次交易的百分比損益
    pnl_pct_str = ""
    if "SELL" in event_type:
        pnl_pct = (net_pnl / config.TRADE_AMOUNT_USD) * 100
        pnl_sign = "+" if net_pnl >= 0 else ""
        pnl_pct_str = f" ({pnl_sign}{pnl_pct:.2f}%)"

    pnl_display = "N/A"
    if "SELL" in event_type:
        pnl_sign = "+" if net_pnl >= 0 else ""
        pnl_display = f"**{pnl_sign}${net_pnl:.2f} USD**{pnl_pct_str}"

    embed = {
        "title": f"{style['emoji']} {style['title']}",
        "color": style["color"],
        "fields": [
            {"name": "商品代碼 (Symbol)", "value": f"`{symbol}`", "inline": True},
            {"name": "事件類型 (Event)", "value": f"**{event_type}**", "inline": True},
            {"name": "觸發價格 (Price)", "value": f"`${price:,.4f} USD`", "inline": True},
            {"name": "持有數量 (Quantity)", "value": f"`{quantity:,.6f}`", "inline": True},
            {"name": "單邊手續費 (Fee)", "value": f"`${fee:,.4f} USD`", "inline": True},
            {"name": "本次淨損益 (Net PnL)", "value": pnl_display, "inline": True},
            {"name": "帳戶現金餘額 (Cash)", "value": f"`${cash_balance:,.2f} USD`", "inline": True},
            {"name": "帳戶總淨值 (Total Value)", "value": f"`${total_value:,.2f} USD`", "inline": True},
            {"name": "系統原因 (Reason)", "value": notes, "inline": False}
        ],
        "footer": {
            "text": f"AI Short-Term Data Hunter Lab | 執行時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        }
    }

    payload = {"embeds": [embed]}
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 204:
            logging.info(f"Discord 通知發送成功: {symbol} {event_type}")
        else:
            logging.error(f"Discord 通知發送失敗，狀態碼: {response.status_code}, 內容: {response.text}")
    except Exception as e:
        logging.error(f"發送 Discord 通知時發生異常: {str(e)}")


# ==============================================================================
#                      3. 技術指標計算 (ATR & Volume SMA)
# ==============================================================================

def calculate_indicators(df):
    """
    計算 True Range (TR), ATR (14), 以及 Volume SMA (14)
    """
    df = df.copy()
    
    # 1. 計算 True Range (TR)
    df["Prev_Close"] = df["Close"].shift(1)
    df["TR"] = pd.concat([
        df["High"] - df["Low"],
        (df["High"] - df["Prev_Close"]).abs(),
        (df["Low"] - df["Prev_Close"]).abs()
    ], axis=1).max(axis=1)

    # 2. 計算 ATR (14) 簡單移動平均
    df["ATR"] = df["TR"].rolling(window=config.ATR_PERIOD).mean()

    # 3. 計算 Volume SMA (14) 簡單移動平均
    df["Vol_SMA"] = df["Volume"].rolling(window=config.ATR_PERIOD).mean()

    return df


# ==============================================================================
#                      4. 交易引擎主邏輯
# ==============================================================================

def run_trading_bot():
    logging.info("==================================================")
    logging.info("🚀 AI 短線數據獵手實驗室 - 開始掃描高頻訊號...")
    logging.info("==================================================")

    # 執行一次性 Webhook 連線測試
    check_and_send_test_notification()

    from datetime import timezone, timedelta
    # 獲取台灣時間 (UTC+8)，以進行精準的每日定時回報
    tw_time = datetime.now(timezone.utc) + timedelta(hours=8)

    # 載入當前狀態
    state = load_state()
    cash = state["cash"]
    positions = state["positions"]
    
    updated_positions = positions.copy()
    any_state_changed = False

    for symbol in config.SYMBOLS:
        logging.info(f"正在掃描標的: {symbol}...")
        
        try:
            # 抓取最近 5 天的 5分鐘 K 線數據
            ticker = yf.Ticker(symbol)
            df = ticker.history(interval="5m", period="5d")
            
            if df.empty or len(df) < config.ATR_PERIOD + 2:
                logging.warning(f"{symbol} 獲取的歷史數據不足，跳過。")
                continue

            # 計算指標
            df = calculate_indicators(df)

            # 獲取最新實時價與最新完成 K 線資料
            # df.iloc[-1] 是當前未完成的 K 線 (即時波動中)
            # df.iloc[-2] 是最新完整已收盤的 5m K 線 (用於訊號判定)
            latest_live_price = float(df["Close"].iloc[-1])
            latest_live_time = df.index[-1]
            
            latest_completed_candle = df.iloc[-2]
            completed_time = df.index[-2]

            # ------------------------------------------------------------------
            # A. 持倉監控與出場判定 (若目前持有該商品)
            # ------------------------------------------------------------------
            if symbol in positions:
                pos = positions[symbol]
                buy_price = pos["buy_price"]
                quantity = pos["quantity"]
                entry_candle_time_str = pos["entry_candle_time"]
                
                # 1. 計算當前淨報酬率 (已扣除買入+賣出雙邊手續費)
                # 淨收益 = 數量 * 當前價 * 0.999 (扣賣出手續費 0.1%)
                # 淨報酬率 = (淨收益 - 1000) / 1000
                net_revenue = quantity * latest_live_price * (1 - config.FEE_RATE)
                net_pnl = net_revenue - config.TRADE_AMOUNT_USD
                net_return = net_pnl / config.TRADE_AMOUNT_USD

                # 2. 計算持有 K 線數 (Bars Held)
                # 找尋 entry_candle_time 在當前資料集中的位置，以進行精確 K 線計數
                try:
                    entry_candle_time = pd.Timestamp(entry_candle_time_str)
                    # 統一去時區化以防比較錯誤
                    df_tzless_index = df.index.tz_localize(None)
                    entry_tzless = entry_candle_time.tz_localize(None)
                    latest_tzless = latest_live_time.tz_localize(None)

                    if entry_tzless in df_tzless_index:
                        entry_idx = df_tzless_index.get_loc(entry_tzless)
                        current_idx = len(df) - 1
                        bars_held = current_idx - entry_idx
                    else:
                        # 若 entry_candle_time 不在 index 中，則採用時間差估算
                        time_diff_sec = (latest_tzless - entry_tzless).total_seconds()
                        bars_held = int(time_diff_sec // 300) # 5分鐘 = 300秒
                except Exception as ex:
                    logging.warning(f"計算持倉 K 線數時出錯: {str(ex)}，使用預設遞增")
                    bars_held = pos.get("bars_held", 0) + 1

                logging.info(
                    f"【持倉監控】{symbol} | 入場價: {buy_price:.4f} | 當前價: {latest_live_price:.4f} | "
                    f"淨回報: {net_return*100:.2f}% | 已持有 {bars_held} 根 K 線"
                )

                # 3. 檢查出場條件
                exit_triggered = False
                exit_action = ""
                exit_reason = ""

                if net_return >= config.TAKE_PROFIT_PCT:
                    exit_triggered = True
                    exit_action = "SELL_TP"
                    exit_reason = f"🏆 淨報酬率達到停利門檻 ({net_return*100:.2f}% >= {config.TAKE_PROFIT_PCT*100:.1f}%)"
                elif net_return <= config.STOP_LOSS_PCT:
                    exit_triggered = True
                    exit_action = "SELL_SL"
                    exit_reason = f"🔴 淨報酬率達到停損門檻 ({net_return*100:.2f}% <= {config.STOP_LOSS_PCT*100:.1f}%)"
                elif bars_held >= config.MAX_HOLD_BARS:
                    exit_triggered = True
                    exit_action = "SELL_TIMEOUT"
                    exit_reason = f"⏳ 持有達到時間限制限制 ({bars_held} 根 K 線 >= {config.MAX_HOLD_BARS} 根，約 30 分鐘)"

                if exit_triggered:
                    # 執行虛擬賣出
                    sell_fee = quantity * latest_live_price * config.FEE_RATE
                    final_net_revenue = quantity * latest_live_price - sell_fee
                    
                    cash += final_net_revenue
                    any_state_changed = True
                    del updated_positions[symbol]

                    # 更新最新總資產 (將剩下持倉價值 + 現金)
                    temp_positions_val = sum(
                        p["quantity"] * latest_live_price for s, p in updated_positions.items()
                    ) # 此處簡化，暫用當前商品的 live price 代替，稍後會全盤更新
                    new_total_value = cash + temp_positions_val

                    # 寫入 CSV 與發送 Discord
                    log_transaction(
                        symbol=symbol,
                        action=exit_action,
                        price=latest_live_price,
                        quantity=quantity,
                        fee=sell_fee,
                        net_pnl=net_pnl,
                        cash_balance=cash,
                        portfolio_value=new_total_value,
                        notes=exit_reason
                    )
                    
                    send_discord_notification(
                        event_type=exit_action,
                        symbol=symbol,
                        price=latest_live_price,
                        quantity=quantity,
                        fee=sell_fee,
                        net_pnl=net_pnl,
                        cash_balance=cash,
                        total_value=new_total_value,
                        notes=exit_reason
                    )
                else:
                    # 更新持有計數
                    updated_positions[symbol]["bars_held"] = bars_held

            # ------------------------------------------------------------------
            # B. 突破訊號判定與建倉邏輯 (若目前未持有該商品)
            # ------------------------------------------------------------------
            else:
                # 判定所需要的指標數值 (以最新收盤 completed_time 之前的 14 期為計算基準)
                # 即 completed_time 對應的指標的前一期數據 (index 是 df.iloc[-3])
                mean_atr = float(df["ATR"].iloc[-3])
                mean_vol = float(df["Vol_SMA"].iloc[-3])

                # 提取最新完整收盤 K 線數值
                close_price = float(latest_completed_candle["Close"])
                open_price = float(latest_completed_candle["Open"])
                high_price = float(latest_completed_candle["High"])
                low_price = float(latest_completed_candle["Low"])
                volume = float(latest_completed_candle["Volume"])
                
                amplitude = high_price - low_price
                is_red_candle = close_price > open_price

                # 判定訊號條件
                cond_amp = amplitude > (mean_atr * config.ATR_MULTIPLIER)
                cond_vol = volume > (mean_vol * config.VOLUME_MULTIPLIER)
                
                logging.info(
                    f"【策略掃描】{symbol} | 收盤價: {close_price:.4f} | 紅K: {is_red_candle} | "
                    f"震幅: {amplitude:.4f} (門檻: {mean_atr * config.ATR_MULTIPLIER:.4f}) | "
                    f"成交量: {volume:,.0f} (門檻: {mean_vol * config.VOLUME_MULTIPLIER:,.0f})"
                )

                if cond_amp and cond_vol and is_red_candle:
                    # 判斷剩餘現金是否足夠建倉
                    if cash >= config.TRADE_AMOUNT_USD:
                        # 執行虛擬買入建倉
                        buy_fee = config.TRADE_AMOUNT_USD * config.FEE_RATE
                        net_invest = config.TRADE_AMOUNT_USD - buy_fee
                        quantity = net_invest / close_price

                        cash -= config.TRADE_AMOUNT_USD
                        any_state_changed = True

                        updated_positions[symbol] = {
                            "buy_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "buy_price": close_price,
                            "quantity": quantity,
                            "invested_amount": config.TRADE_AMOUNT_USD,
                            "bars_held": 0,
                            "entry_candle_time": str(completed_time)
                        }

                        # 計算最新總資產
                        temp_positions_val = sum(
                            p["quantity"] * close_price for s, p in updated_positions.items()
                        )
                        new_total_value = cash + temp_positions_val

                        reason_str = (
                            f"🟢 5m K線爆量突破: 震幅({amplitude:.4f}) > 3x ATR({mean_atr * config.ATR_MULTIPLIER:.4f}) "
                            f"且 成交量({volume:,.0f}) > 3x 均量({mean_vol * config.VOLUME_MULTIPLIER:,.0f}) 且為紅K。"
                        )

                        log_transaction(
                            symbol=symbol,
                            action="BUY",
                            price=close_price,
                            quantity=quantity,
                            fee=buy_fee,
                            net_pnl=0.0,
                            cash_balance=cash,
                            portfolio_value=new_total_value,
                            notes=reason_str
                        )

                        send_discord_notification(
                            event_type="BUY",
                            symbol=symbol,
                            price=close_price,
                            quantity=quantity,
                            fee=buy_fee,
                            net_pnl=0.0,
                            cash_balance=cash,
                            total_value=new_total_value,
                            notes=reason_str
                        )
                    else:
                        logging.warning(
                            f"【資金不足】{symbol} 觸發買入信號，但當前可用現金 (${cash:.2f} USD) 不足建倉金 (${config.TRADE_AMOUNT_USD} USD)！"
                        )

        except Exception as e:
            logging.error(f"掃描或處理標的 {symbol} 時發生異常: {str(e)}", exc_info=True)

    # ------------------------------------------------------------------
    # C. 更新整體資產淨值並存檔
    # ------------------------------------------------------------------
    # 再次精確計算所有持有倉位的即時市值，以獲得正確的資產總值
    total_positions_value = 0.0
    for sym, pos in updated_positions.items():
        try:
            # 獲取該商品的最新價格
            live_df = yf.Ticker(sym).history(period="1d", interval="5m")
            if not live_df.empty:
                current_price = float(live_df["Close"].iloc[-1])
            else:
                current_price = pos["buy_price"]
            total_positions_value += pos["quantity"] * current_price
        except Exception:
            total_positions_value += pos["quantity"] * pos["buy_price"]

    current_total_value = cash + total_positions_value

    # ------------------------------------------------------------------
    # D. 每日定時發送健康回報
    # ------------------------------------------------------------------
    tw_date_str = tw_time.strftime("%Y-%m-%d")
    last_report_date = state.get("last_daily_report_date", "")
    
    if tw_time.hour >= config.DAILY_REPORT_HOUR and tw_date_str != last_report_date:
        logging.info(f"偵測到台灣時間下午 {config.DAILY_REPORT_HOUR} 點已過，且今日尚未發送健康日報。準備發送...")
        send_daily_report(state, tw_time)
        state["last_daily_report_date"] = tw_date_str

    # 更新並儲存 JSON 狀態
    state["cash"] = cash
    state["total_value"] = current_total_value
    state["positions"] = updated_positions
    save_state(state)

    logging.info("==================================================")
    logging.info(f"📊 帳戶掃描完畢 | 可用現金: ${cash:,.2f} USD | 持倉市值: ${total_positions_value:,.2f} USD | 總資產淨值: ${current_total_value:,.2f} USD")
    logging.info("==================================================")


if __name__ == "__main__":
    run_trading_bot()
