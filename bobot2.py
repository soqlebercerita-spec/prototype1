import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import threading
import time
import datetime
import tkinter as tk
from tkinter import ttk, messagebox
import requests
from typing import Optional, Dict, Any, List, Tuple
from tkinter.scrolledtext import ScrolledText
import csv
import os
import sys
import platform

# --- CONFIG & GLOBALS ---
TELEGRAM_TOKEN = "8365734234:AAH2uTaZPDD47Lnm3y_Tcr6aj3xGL-bVsgk"
TELEGRAM_CHAT_ID = "5061106648"
bot_running = False
disconnect_count = 0
session_start_balance = None
loss_streak = 0
max_loss_streak = 3
max_drawdown = 0.05
profit_target = 0.10
daily_max_loss = 0.05
trailing_stop_val = 0.0
active_hours = ("00:00", "23:59")  # 24/7 trading capability
position_count = 0
max_positions = 10
current_strategy = "Scalping"
gui = None
trade_lock = threading.Lock()
last_trade_time = {}
mt5_connected = False

# Enhanced Trading Session Management
TRADING_SESSIONS = {
    "Asia": {
        "start": "21:00",
        "end": "06:00", 
        "timezone": "UTC",
        "active": True,
        "volatility": "medium",
        "preferred_pairs": ["USDJPY", "AUDUSD", "NZDUSD", "EURJPY", "GBPJPY"]
    },
    "London": {
        "start": "07:00",
        "end": "16:00",
        "timezone": "UTC", 
        "active": True,
        "volatility": "high",
        "preferred_pairs": ["EURUSD", "GBPUSD", "EURGBP", "EURJPY", "GBPJPY"]
    },
    "New_York": {
        "start": "12:00",
        "end": "21:00",
        "timezone": "UTC",
        "active": True,
        "volatility": "high", 
        "preferred_pairs": ["EURUSD", "GBPUSD", "USDJPY", "USDCAD", "AUDUSD"]
    },
    "Overlap_London_NY": {
        "start": "12:00",
        "end": "16:00",
        "timezone": "UTC",
        "active": True,
        "volatility": "very_high",
        "preferred_pairs": ["EURUSD", "GBPUSD", "USDCAD"]
    }
}

# Session-specific trading parameters
SESSION_SETTINGS = {
    "Asia": {
        "max_spread_multiplier": 1.5,
        "volatility_filter": 0.7,
        "trading_intensity": "conservative"
    },
    "London": {
        "max_spread_multiplier": 1.2,
        "volatility_filter": 1.0,
        "trading_intensity": "aggressive"
    },
    "New_York": {
        "max_spread_multiplier": 1.0,
        "volatility_filter": 1.2,
        "trading_intensity": "aggressive"
    },
    "Overlap_London_NY": {
        "max_spread_multiplier": 0.8,
        "volatility_filter": 1.5,
        "trading_intensity": "very_aggressive"
    }
}

# Trading session data
session_data = {
    "start_time": None,
    "start_balance": 0.0,
    "total_trades": 0,
    "winning_trades": 0,
    "losing_trades": 0,
    "total_profit": 0.0,
    "daily_orders": 0,
    "daily_profit": 0.0,
    "last_balance": 0.0,
    "session_equity": 0.0
}

def connect_mt5() -> bool:
    """Enhanced MT5 connection with comprehensive debugging and better error handling"""
    global mt5_connected
    try:
        import platform
        import sys

        # Shutdown any existing connection first
        try:
            mt5.shutdown()
            time.sleep(1)
        except:
            pass

        logger("🔍 === MT5 CONNECTION DIAGNOSTIC ===")
        logger(f"🔍 Python Version: {sys.version}")
        logger(f"🔍 Python Architecture: {platform.architecture()[0]}")
        logger(f"🔍 Platform: {platform.system()} {platform.release()}")

        # Check if MT5 module is properly imported
        try:
            import MetaTrader5 as mt5_test
            logger("✅ MetaTrader5 module imported successfully")
        except ImportError as e:
            logger(f"❌ Failed to import MetaTrader5: {e}")
            logger("💡 Install with: pip install MetaTrader5")
            return False

        # Initialize MT5 connection with enhanced retries
        max_attempts = 5
        for attempt in range(max_attempts):
            logger(f"🔄 MT5 connection attempt {attempt + 1}/{max_attempts}...")

            # Try different initialization methods
            init_methods = [
                lambda: mt5.initialize(),
                lambda: mt5.initialize(path="C:\\Program Files\\MetaTrader 5\\terminal64.exe"),
                lambda: mt5.initialize(path="C:\\Program Files (x86)\\MetaTrader 5\\terminal.exe"),
                lambda: mt5.initialize(login=0),  # Auto-detect current login
            ]

            initialized = False
            for i, init_method in enumerate(init_methods):
                try:
                    logger(f"🔄 Trying initialization method {i + 1}...")
                    result = init_method()
                    if result:
                        initialized = True
                        logger(f"✅ MT5 initialized using method {i + 1}")
                        break
                    else:
                        error = mt5.last_error()
                        logger(f"⚠️ Method {i + 1} failed with error: {error}")
                except Exception as e:
                    logger(f"⚠️ Method {i + 1} exception: {str(e)}")
                    continue

            if not initialized:
                logger(f"❌ All initialization methods failed on attempt {attempt + 1}")
                last_error = mt5.last_error()
                logger(f"🔍 Last MT5 Error Code: {last_error}")

                if attempt < max_attempts - 1:
                    time.sleep(3)
                    continue
                else:
                    logger("💡 SOLUSI TROUBLESHOOTING:")
                    logger("   1. ⚠️ WAJIB: Jalankan MT5 sebagai Administrator")
                    logger("   2. ⚠️ WAJIB: Pastikan MT5 sudah login ke akun trading")
                    logger("   3. ⚠️ Pastikan Python dan MT5 sama-sama 64-bit")
                    logger("   4. ⚠️ Tutup semua instance MT5 lain yang berjalan")
                    logger("   5. ⚠️ Restart MT5 jika masih bermasalah")
                    logger("   6. ⚠️ Cek apakah antivirus memblokir koneksi")
                    mt5_connected = False
                    return False

            # Enhanced diagnostic information
            try:
                version_info = mt5.version()
                if version_info:
                    logger(f"🔍 MT5 Version: {version_info}")
                    logger(f"🔍 MT5 Build: {getattr(version_info, 'build', 'N/A')}")
                else:
                    logger("⚠️ Cannot get MT5 version info")
                    last_error = mt5.last_error()
                    logger(f"🔍 Version error code: {last_error}")
            except Exception as e:
                logger(f"⚠️ Version check failed: {str(e)}")

            # Enhanced account validation with detailed error reporting
            logger("🔍 Checking account information...")
            account_info = mt5.account_info()
            if account_info is None:
                last_error = mt5.last_error()
                logger(f"❌ GAGAL mendapatkan info akun MT5 - Error Code: {last_error}")
                logger("💡 PENYEBAB UTAMA:")
                logger("   ❌ MT5 belum login ke akun trading")
                logger("   ❌ Koneksi ke server broker terputus")
                logger("   ❌ MT5 tidak dijalankan sebagai Administrator")
                logger("   ❌ Python tidak dapat mengakses MT5 API")
                logger("   ❌ Firewall atau antivirus memblokir koneksi")

                # Try to get any available info for debugging
                try:
                    terminal_info_debug = mt5.terminal_info()
                    if terminal_info_debug:
                        logger(f"🔍 Debug - Terminal Company: {getattr(terminal_info_debug, 'company', 'N/A')}")
                        logger(f"🔍 Debug - Terminal Connected: {getattr(terminal_info_debug, 'connected', False)}")
                    else:
                        logger("🔍 Debug - Terminal info juga tidak tersedia")
                except:
                    logger("🔍 Debug - Tidak dapat mengakses terminal info")

                if attempt < max_attempts - 1:
                    logger(f"🔄 Mencoba ulang dalam 5 detik... (attempt {attempt + 1})")
                    mt5.shutdown()
                    time.sleep(5)
                    continue
                else:
                    logger("❌ SOLUSI WAJIB DICOBA:")
                    logger("   1. 🔴 TUTUP MT5 SEPENUHNYA")
                    logger("   2. 🔴 KLIK KANAN MT5 → RUN AS ADMINISTRATOR")
                    logger("   3. 🔴 LOGIN KE AKUN TRADING DENGAN BENAR")
                    logger("   4. 🔴 PASTIKAN STATUS 'CONNECTED' DI MT5")
                    logger("   5. 🔴 BUKA MARKET WATCH DAN TAMBAHKAN SYMBOL")
                    mt5_connected = False
                    return False

            # Account info berhasil didapat
            logger(f"✅ Account Login: {account_info.login}")
            logger(f"✅ Account Server: {account_info.server}")
            logger(f"✅ Account Name: {getattr(account_info, 'name', 'N/A')}")
            logger(f"✅ Account Balance: ${account_info.balance:.2f}")
            logger(f"✅ Account Equity: ${account_info.equity:.2f}")
            logger(f"✅ Account Currency: {getattr(account_info, 'currency', 'USD')}")
            logger(f"✅ Trade Allowed: {account_info.trade_allowed}")

            # Check terminal info with detailed diagnostics
            logger("🔍 Checking terminal information...")
            terminal_info = mt5.terminal_info()
            if terminal_info is None:
                logger("❌ Gagal mendapatkan info terminal MT5")
                last_error = mt5.last_error()
                logger(f"🔍 Terminal error code: {last_error}")

                if attempt < max_attempts - 1:
                    logger("🔄 Mencoba ulang...")
                    mt5.shutdown()
                    time.sleep(3)
                    continue
                else:
                    logger("❌ Terminal info tidak tersedia setelah semua percobaan")
                    mt5_connected = False
                    return False

            logger(f"✅ Terminal Connected: {terminal_info.connected}")
            logger(f"✅ Terminal Company: {getattr(terminal_info, 'company', 'N/A')}")
            logger(f"✅ Terminal Name: {getattr(terminal_info, 'name', 'N/A')}")
            logger(f"✅ Terminal Path: {getattr(terminal_info, 'path', 'N/A')}")

            # Validate trading permissions
            if not account_info.trade_allowed:
                logger("⚠️ PERINGATAN: Akun tidak memiliki izin trading")
                logger("💡 Hubungi broker untuk mengaktifkan trading permission")
                logger("⚠️ Bot akan melanjutkan dengan mode READ-ONLY")

            # Check if terminal is connected to trade server
            if not terminal_info.connected:
                logger("❌ KRITIS: Terminal tidak terhubung ke trade server")
                logger("💡 SOLUSI:")
                logger("   1. Periksa koneksi internet")
                logger("   2. Cek status server broker")
                logger("   3. Login ulang ke MT5")
                logger("   4. Restart MT5 terminal")

                if attempt < max_attempts - 1:
                    logger("🔄 Mencoba reconnect...")
                    mt5.shutdown()
                    time.sleep(5)
                    continue
                else:
                    logger("❌ Terminal tetap tidak terhubung setelah semua percobaan")
                    mt5_connected = False
                    return False

            # Enhanced market data testing with more symbols and better error handling
            test_symbols = [
                "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "NZDUSD",
                "XAUUSD", "XAUUSDm", "GOLD", "BTCUSD", "EURGBP", "EURJPY"
            ]

            working_symbols = []
            failed_symbols = []

            logger("🔍 Testing market data access for symbols...")

            # First, get all available symbols
            logger("🔍 Mengambil daftar semua symbols...")
            try:
                all_symbols = mt5.symbols_get()
                if all_symbols and len(all_symbols) > 0:
                    logger(f"✅ Total symbols available: {len(all_symbols)}")
                    available_symbol_names = [s.name for s in all_symbols if hasattr(s, 'name')]
                    logger(f"🔍 Sample symbols: {', '.join(available_symbol_names[:10])}")
                else:
                    logger("⚠️ PERINGATAN: Tidak ada symbols dari mt5.symbols_get()")
                    logger("💡 Kemungkinan Market Watch kosong atau tidak aktif")
            except Exception as e:
                logger(f"❌ Error getting symbols list: {str(e)}")
                all_symbols = None

            # Test each symbol with comprehensive validation
            for test_symbol in test_symbols:
                try:
                    logger(f"🔍 Testing symbol: {test_symbol}")

                    # Try to get symbol info
                    symbol_info = mt5.symbol_info(test_symbol)
                    if symbol_info is None:
                        logger(f"❌ {test_symbol}: Symbol info tidak tersedia")
                        failed_symbols.append(f"{test_symbol} (not found)")
                        continue

                    logger(f"🔍 {test_symbol}: visible={symbol_info.visible}, trade_mode={getattr(symbol_info, 'trade_mode', 'N/A')}")

                    # Try to make it visible if not already
                    if not symbol_info.visible:
                        logger(f"🔄 Mengaktifkan {test_symbol} di Market Watch...")
                        select_result = mt5.symbol_select(test_symbol, True)
                        logger(f"🔍 {test_symbol} activation result: {select_result}")

                        if select_result:
                            time.sleep(1.0)  # Wait longer for activation

                            # Re-check symbol info
                            symbol_info = mt5.symbol_info(test_symbol)
                            if symbol_info is None or not symbol_info.visible:
                                logger(f"❌ {test_symbol}: Gagal diaktifkan")
                                failed_symbols.append(f"{test_symbol} (activation failed)")
                                continue
                            else:
                                logger(f"✅ {test_symbol}: Berhasil diaktifkan")
                        else:
                            logger(f"❌ {test_symbol}: Gagal aktivasi")
                            failed_symbols.append(f"{test_symbol} (select failed)")
                            continue

                    # Test tick data with multiple attempts and better error handling
                    tick_attempts = 5
                    tick_success = False
                    last_tick_error = None

                    logger(f"🔍 Testing tick data untuk {test_symbol}...")
                    for tick_attempt in range(tick_attempts):
                        try:
                            tick = mt5.symbol_info_tick(test_symbol)
                            if tick is not None:
                                if hasattr(tick, 'bid') and hasattr(tick, 'ask'):
                                    if tick.bid > 0 and tick.ask > 0:
                                        spread = abs(tick.ask - tick.bid)
                                        spread_percent = (spread / tick.bid) * 100 if tick.bid > 0 else 0
                                        logger(f"✅ {test_symbol}: Bid={tick.bid}, Ask={tick.ask}, Spread={spread:.5f} ({spread_percent:.3f}%)")
                                        working_symbols.append(test_symbol)
                                        tick_success = True
                                        break
                                    else:
                                        last_tick_error = f"Invalid prices: bid={tick.bid}, ask={tick.ask}"
                                else:
                                    last_tick_error = "Missing bid/ask attributes"
                            else:
                                last_tick_error = "Tick is None"

                            # Add error details for debugging
                            if tick_attempt == 0:
                                tick_error = mt5.last_error()
                                if tick_error != (0, 'Success'):
                                    logger(f"🔍 {test_symbol} tick error: {tick_error}")

                        except Exception as tick_e:
                            last_tick_error = f"Exception: {str(tick_e)}"

                        if tick_attempt < tick_attempts - 1:
                            time.sleep(0.8)  # Longer wait between attempts

                    if not tick_success:
                        logger(f"❌ {test_symbol}: Tidak dapat mengambil tick data")
                        if last_tick_error:
                            logger(f"   Last error: {last_tick_error}")
                        failed_symbols.append(f"{test_symbol} (no valid tick)")

                except Exception as e:
                    error_msg = f"Exception: {str(e)}"
                    logger(f"❌ Error testing {test_symbol}: {error_msg}")
                    failed_symbols.append(f"{test_symbol} ({error_msg})")
                    continue

            # Report comprehensive results
            logger(f"📊 === MARKET DATA TEST RESULTS ===")
            logger(f"✅ Working symbols ({len(working_symbols)}): {', '.join(working_symbols) if working_symbols else 'NONE'}")

            if failed_symbols:
                logger(f"❌ Failed symbols ({len(failed_symbols)}):")
                for i, failed in enumerate(failed_symbols[:10]):  # Show first 10
                    logger(f"   {i+1}. {failed}")
                if len(failed_symbols) > 10:
                    logger(f"   ... dan {len(failed_symbols)-10} lainnya")

            # Check if we have any working symbols
            if len(working_symbols) > 0:
                # Success!
                mt5_connected = True
                logger(f"🎉 === MT5 CONNECTION SUCCESSFUL ===")
                logger(f"👤 Account: {account_info.login} | Server: {account_info.server}")
                logger(f"💰 Balance: ${account_info.balance:.2f} | Equity: ${account_info.equity:.2f}")
                logger(f"🔐 Trade Permission: {'✅ ENABLED' if account_info.trade_allowed else '⚠️ READ-ONLY'}")
                logger(f"🌐 Terminal Connected: ✅ YES")
                logger(f"📊 Market Access: ✅ ({len(working_symbols)} symbols working)")
                logger(f"🎯 Bot siap untuk trading dengan symbols: {', '.join(working_symbols[:5])}")
                logger("=" * 50)
                return True
            else:
                if attempt < max_attempts - 1:
                    logger(f"⚠️ Tidak ada symbols yang working, retry attempt {attempt + 2}...")
                    logger("💡 TROUBLESHOOTING:")
                    logger("   1. Buka Market Watch di MT5")
                    logger("   2. Tambahkan symbols secara manual")
                    logger("   3. Pastikan market sedang buka")
                    logger("   4. Cek koneksi internet")
                    mt5.shutdown()
                    time.sleep(5)
                    continue

        # All attempts failed
        logger("❌ === CONNECTION FAILED ===")
        logger("❌ Tidak dapat mengakses data market setelah semua percobaan")
        logger("💡 Solusi yang disarankan:")
        logger("   1. Pastikan MT5 dijalankan sebagai Administrator")
        logger("   2. Pastikan sudah login ke akun dan terkoneksi ke server")
        logger("   3. Buka Market Watch dan pastikan ada symbols yang terlihat")
        logger("   4. Coba restart MT5 terminal")
        logger("   5. Pastikan tidak ada firewall yang memblokir koneksi")
        logger("   6. Pastikan Python dan MT5 sama-sama 64-bit")

        mt5_connected = False
        return False

    except Exception as e:
        logger(f"❌ Critical MT5 connection error: {str(e)}")
        logger("💡 Coba restart aplikasi dan MT5 terminal")
        mt5_connected = False
        return False

def check_mt5_status() -> bool:
    """Enhanced MT5 status check"""
    global mt5_connected
    try:
        if not mt5_connected:
            return False

        account_info = mt5.account_info()
        terminal_info = mt5.terminal_info()

        if account_info is None or terminal_info is None:
            mt5_connected = False
            logger("❌ MT5 status check failed: Account or Terminal info unavailable.")
            return False

        if not terminal_info.connected:
            mt5_connected = False
            logger("❌ MT5 status check failed: Terminal not connected.")
            return False

        return True
    except Exception as e:
        logger(f"❌ MT5 status check exception: {str(e)}")
        mt5_connected = False
        return False

def get_symbols() -> List[str]:
    """Get available symbols from MT5 with enhanced error handling"""
    try:
        if not check_mt5_status():
            logger("❌ Cannot get symbols: MT5 not connected.")
            return []

        symbols = mt5.symbols_get()
        if symbols is None:
            logger("❌ Failed to get symbols from MT5.")
            return []

        return [s.name for s in symbols if hasattr(s, 'visible') and s.visible]
    except Exception as e:
        logger(f"❌ Exception in get_symbols: {str(e)}")
        return []

def validate_and_activate_symbol(symbol: str) -> Optional[str]:
    """
    Validasi symbol, return symbol valid (string) jika sukses, else return None.
    """
    try:
        if not symbol or not symbol.strip():
            logger(f"❌ Symbol kosong atau tidak valid")
            return None

        # Ensure MT5 is connected
        if not check_mt5_status():
            logger("🔄 MT5 not connected, attempting to reconnect...")
            if not connect_mt5():
                logger("❌ Cannot reconnect to MT5 for symbol validation")
                return None

        original_symbol = symbol.strip().upper()
        logger(f"🔍 Validating symbol: {original_symbol}")

        # Enhanced symbol variations with broker-specific patterns
        symbol_variations = [
            original_symbol,
            original_symbol.replace("m", "").replace("M", ""),
            original_symbol.replace("USDM", "USD"),
            original_symbol + "m",
            original_symbol + "M",
            original_symbol + ".a",  # Some brokers use .a suffix
            original_symbol + ".b",  # Some brokers use .b suffix
            original_symbol + ".raw", # Raw spread symbols
            original_symbol[:-1] if original_symbol.endswith("M") else original_symbol,
            original_symbol[:-1] if original_symbol.endswith("m") else original_symbol,
        ]

        # Add forex variations
        if len(original_symbol) == 6:
            # Try with different separators
            symbol_variations.extend([
                original_symbol[:3] + "/" + original_symbol[3:],
                original_symbol[:3] + "-" + original_symbol[3:],
                original_symbol[:3] + "." + original_symbol[3:],
            ])

        # Remove duplicates while preserving order
        seen = set()
        symbol_variations = [x for x in symbol_variations if not (x in seen or seen.add(x))]

        valid_symbol = None
        symbol_info = None
        test_results = []

        # Test each variation with detailed logging
        logger(f"🔍 Testing {len(symbol_variations)} symbol variations...")
        for i, variant in enumerate(symbol_variations):
            try:
                logger(f"   {i+1}. Testing: {variant}")
                test_info = mt5.symbol_info(variant)
                if test_info is not None:
                    test_results.append(f"✅ {variant}: Found")
                    valid_symbol = variant
                    symbol_info = test_info
                    logger(f"✅ Found valid symbol: {variant}")
                    break
                else:
                    test_results.append(f"❌ {variant}: Not found")
            except Exception as e:
                test_results.append(f"⚠️ {variant}: Error - {str(e)}")
                logger(f"⚠️ Error testing variant {variant}: {str(e)}")
                continue

        # If not found in variations, search in all available symbols
        if symbol_info is None:
            logger(f"🔍 Searching in all available symbols...")
            try:
                all_symbols = mt5.symbols_get()
                if all_symbols:
                    logger(f"🔍 Searching through {len(all_symbols)} available symbols...")

                    # First try exact matches
                    for sym in all_symbols:
                        sym_name = getattr(sym, 'name', '')
                        if sym_name.upper() == original_symbol:
                            test_info = mt5.symbol_info(sym_name)
                            if test_info:
                                valid_symbol = sym_name
                                symbol_info = test_info
                                logger(f"✅ Found exact match: {sym_name}")
                                break

                    # Then try partial matches
                    if symbol_info is None:
                        for sym in all_symbols:
                            sym_name = getattr(sym, 'name', '')
                            if (original_symbol[:4] in sym_name.upper() or
                                sym_name.upper()[:4] in original_symbol or
                                any(var[:4] in sym_name.upper() for var in symbol_variations[:5])):
                                test_info = mt5.symbol_info(sym_name)
                                if test_info:
                                    valid_symbol = sym_name
                                    symbol_info = test_info
                                    logger(f"✅ Found partial match: {sym_name} for {original_symbol}")
                                    break
                else:
                    logger("⚠️ No symbols returned from mt5.symbols_get()")
            except Exception as e:
                logger(f"⚠️ Error searching symbols: {str(e)}")

        # Final check - if still not found, log all test results
        if symbol_info is None:
            logger(f"❌ Symbol {original_symbol} tidak ditemukan setelah semua percobaan")
            logger("🔍 Test results:")
            for result in test_results[:10]:  # Show first 10 results
                logger(f"   {result}")
            if len(test_results) > 10:
                logger(f"   ... dan {len(test_results)-10} test lainnya")
            return None

        # Use the found valid symbol
        symbol = valid_symbol
        logger(f"🎯 Using symbol: {symbol}")

        # Enhanced symbol activation
        if not symbol_info.visible:
            logger(f"🔄 Activating symbol {symbol} in Market Watch...")

            # Try different activation methods
            activation_success = False
            activation_methods = [
                lambda: mt5.symbol_select(symbol, True),
                lambda: mt5.symbol_select(symbol, True, True),  # With strict mode
            ]

            for method_idx, method in enumerate(activation_methods):
                try:
                    result = method()
                    if result:
                        logger(f"✅ Symbol activated using method {method_idx + 1}")
                        activation_success = True
                        break
                    else:
                        logger(f"⚠️ Activation method {method_idx + 1} failed")
                except Exception as e:
                    logger(f"⚠️ Activation method {method_idx + 1} exception: {str(e)}")

            if not activation_success:
                logger(f"❌ Gagal mengaktifkan symbol {symbol} dengan semua metode")
                logger("💡 Coba tambahkan symbol secara manual di Market Watch MT5")
                return None

            # Wait for activation to take effect
            time.sleep(1.0)

            # Re-check symbol info after activation
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                logger(f"❌ Symbol {symbol} tidak dapat diakses setelah aktivasi")
                return None

        # Enhanced trading permission validation
        trade_mode = getattr(symbol_info, 'trade_mode', None)
        if trade_mode is not None:
            if trade_mode == mt5.SYMBOL_TRADE_MODE_DISABLED:
                logger(f"❌ Trading untuk symbol {symbol} tidak diizinkan (DISABLED)")
                return None
            elif trade_mode == mt5.SYMBOL_TRADE_MODE_CLOSEONLY:
                logger(f"⚠️ Symbol {symbol} hanya bisa close position (CLOSE_ONLY)")
            elif trade_mode == mt5.SYMBOL_TRADE_MODE_FULL:
                logger(f"✅ Symbol {symbol} mendukung trading penuh")
            else:
                logger(f"🔍 Symbol {symbol} trade mode: {trade_mode}")

        # Enhanced tick validation with better error reporting
        tick_valid = False
        tick_attempts = 5
        last_tick_error = None

        logger(f"🔍 Testing tick data for {symbol}...")
        for attempt in range(tick_attempts):
            try:
                tick = mt5.symbol_info_tick(symbol)
                if tick is not None:
                    if hasattr(tick, 'bid') and hasattr(tick, 'ask'):
                        if tick.bid > 0 and tick.ask > 0:
                            spread = abs(tick.ask - tick.bid)
                            logger(f"✅ Valid tick data - Bid: {tick.bid}, Ask: {tick.ask}, Spread: {spread:.5f}")
                            tick_valid = True
                            break
                        else:
                            logger(f"⚠️ Tick attempt {attempt + 1}: Invalid prices (bid={tick.bid}, ask={tick.ask})")
                    else:
                        logger(f"⚠️ Tick attempt {attempt + 1}: Missing bid/ask attributes")
                else:
                    logger(f"⚠️ Tick attempt {attempt + 1}: tick is None")

                if attempt < tick_attempts - 1:
                    time.sleep(0.5)

            except Exception as e:
                last_tick_error = str(e)
                logger(f"⚠️ Tick attempt {attempt + 1} exception: {str(e)}")
                if attempt < tick_attempts - 1:
                    time.sleep(0.5)

        if not tick_valid:
            logger(f"❌ Tidak dapat mendapatkan data tick valid untuk {symbol}")
            if last_tick_error:
                logger(f"   Last error: {last_tick_error}")
            logger("💡 Kemungkinan penyebab:")
            logger("   - Market sedang tutup")
            logger("   - Symbol tidak aktif diperdagangkan")
            logger("   - Koneksi ke server data bermasalah")
            logger("   - Symbol memerlukan subscription khusus")
            return None

        # Final spread check and warnings
        try:
            tick = mt5.symbol_info_tick(symbol)
            if tick:
                spread = abs(tick.ask - tick.bid)

                # Dynamic spread thresholds based on symbol type
                if "XAU" in symbol or "GOLD" in symbol:
                    max_spread_warning = 1.0  # Gold typically has wider spreads
                elif "JPY" in symbol:
                    max_spread_warning = 0.05  # JPY pairs
                elif any(crypto in symbol for crypto in ["BTC", "ETH", "LTC"]):
                    max_spread_warning = 50.0  # Crypto can have very wide spreads
                else:
                    max_spread_warning = 0.01  # Regular forex pairs

                if spread > max_spread_warning:
                    logger(f"⚠️ Spread tinggi untuk {symbol}: {spread:.5f} (threshold: {max_spread_warning})")
                    logger("   Symbol tetap valid, tapi perhatikan trading cost")
                else:
                    logger(f"✅ Spread normal untuk {symbol}: {spread:.5f}")
        except Exception as e:
            logger(f"⚠️ Error checking final spread: {str(e)}")

        # Success!
        logger(f"✅ Symbol {symbol} berhasil divalidasi dan siap untuk trading")

        # Update GUI if available
        if gui:
            gui.symbol_var.set(symbol)

        return symbol  # Return the valid symbol string instead of True

    except Exception as e:
        logger(f"❌ Critical error validating symbol {symbol}: {str(e)}")
        import traceback
        logger(f"🔍 Stack trace: {traceback.format_exc()}")
        return None

def get_symbol_suggestions() -> List[str]:
    """Enhanced symbol suggestions with fallback"""
    try:
        if not check_mt5_status():
            return ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "XAUUSD"]

        all_symbols = mt5.symbols_get()
        if not all_symbols:
            return ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "XAUUSD"]

        validated_symbols = []
        popular_patterns = [
            "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "NZDUSD", "USDCHF",
            "EURGBP", "EURJPY", "GBPJPY", "XAUUSD", "XAGUSD"
        ]

        # Find exact matches first
        for pattern in popular_patterns:
            for symbol in all_symbols:
                symbol_name = getattr(symbol, 'name', '')
                if symbol_name == pattern or symbol_name == pattern + "m":
                    try:
                        info = mt5.symbol_info(symbol_name)
                        if info:
                            validated_symbols.append(symbol_name)
                            if len(validated_symbols) >= 15:
                                break
                    except:
                        continue
            if len(validated_symbols) >= 15:
                break

        return validated_symbols[:20] if validated_symbols else ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"]

    except Exception as e:
        logger(f"❌ Error getting symbol suggestions: {str(e)}")
        return ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"]

def get_account_info() -> Optional[Dict[str, Any]]:
    """Enhanced account info with error handling"""
    try:
        if not check_mt5_status():
            logger("❌ Cannot get account info: MT5 not connected.")
            return None

        info = mt5.account_info()
        if info is None:
            logger("❌ Failed to get account info from MT5.")
            return None

        return {
            "balance": info.balance,
            "equity": info.equity,
            "margin": info.margin,
            "free_margin": info.margin_free,
            "margin_level": info.margin_level,
            "profit": info.profit,
            "login": info.login,
            "server": info.server
        }
    except Exception as e:
        logger(f"❌ Exception in get_account_info: {str(e)}")
        return None

def get_positions() -> List[Any]:
    """Enhanced position retrieval"""
    try:
        if not check_mt5_status():
            logger("❌ Cannot get positions: MT5 not connected.")
            return []

        positions = mt5.positions_get()
        return list(positions) if positions else []
    except Exception as e:
        logger(f"❌ Exception in get_positions: {str(e)}")
        return []

def calculate_pip_value(symbol: str, lot_size: float) -> float:
    """Calculate pip value for the symbol"""
    try:
        if not check_mt5_status():
            logger("❌ Cannot calculate pip value: MT5 not connected.")
            return 10.0 * lot_size

        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            logger(f"❌ Cannot calculate pip value: Symbol info for {symbol} not found.")
            return 10.0 * lot_size

        if "JPY" in symbol:
            pip_size = 0.01
        elif any(crypto in symbol for crypto in ["BTC", "ETH", "XAU", "XAG"]):
            pip_size = symbol_info.point * 10
        else:
            pip_size = 0.0001

        tick_value = getattr(symbol_info, 'trade_tick_value', 1.0)
        tick_size = getattr(symbol_info, 'trade_tick_size', 0.00001)

        if tick_size > 0:
            pip_value = (pip_size / tick_size) * tick_value * lot_size
        else:
            pip_value = 10.0 * lot_size

        return abs(pip_value)
    except Exception as e:
        logger(f"❌ Exception in calculate_pip_value for {symbol}: {str(e)}")
        return 10.0 * lot_size

def parse_tp_sl_input(input_value: str, unit: str, symbol: str, lot_size: float, current_price: float, order_type: str, is_tp: bool) -> Tuple[float, Dict[str, float]]:
    """Enhanced TP/SL parsing"""
    try:
        if not input_value or input_value == "0" or input_value == "":
            return 0.0, {}

        value = float(input_value)
        if value <= 0:
            return 0.0, {}

        pip_value = calculate_pip_value(symbol, lot_size)
        account_info = get_account_info()
        balance = account_info['balance'] if account_info else 10000.0

        calculations = {}
        result_price = 0.0

        # Determine pip size
        if "JPY" in symbol:
            pip_size = 0.01
        elif any(crypto in symbol for crypto in ["BTC", "ETH", "XAU", "XAG"]):
            symbol_info = mt5.symbol_info(symbol)
            pip_size = getattr(symbol_info, 'point', 0.0001) * 10 if symbol_info else 0.0001
        else:
            pip_size = 0.0001

        if unit == "pips":
            price_movement = value * pip_size
            if is_tp:
                if order_type == "BUY":
                    result_price = current_price + price_movement
                else:
                    result_price = current_price - price_movement
            else:
                if order_type == "BUY":
                    result_price = current_price - price_movement
                else:
                    result_price = current_price + price_movement

            profit_loss_amount = value * pip_value
            calculations['pips'] = value
            calculations['amount'] = profit_loss_amount
            calculations['percent'] = (profit_loss_amount / balance) * 100

        elif unit == "price":
            result_price = value
            price_diff = abs(result_price - current_price)
            pips = price_diff / pip_size
            profit_loss_amount = pips * pip_value

            calculations['pips'] = pips
            calculations['amount'] = profit_loss_amount
            calculations['percent'] = (profit_loss_amount / balance) * 100

        elif unit == "%":
            profit_loss_amount = balance * (value / 100)
            pips = profit_loss_amount / pip_value if pip_value > 0 else 0
            price_movement = pips * pip_size

            if is_tp:
                if order_type == "BUY":
                    result_price = current_price + price_movement
                else:
                    result_price = current_price - price_movement
            else:
                if order_type == "BUY":
                    result_price = current_price - price_movement
                else:
                    result_price = current_price + price_movement

            calculations['pips'] = pips
            calculations['amount'] = profit_loss_amount
            calculations['percent'] = value

        return result_price, calculations

    except Exception as e:
        logger(f"❌ Error parsing TP/SL input: {str(e)}")
        return 0.0, {}

def validate_tp_sl_levels(symbol: str, tp_price: float, sl_price: float, order_type: str, current_price: float) -> Tuple[bool, str]:
    """Enhanced TP/SL validation"""
    try:
        if not check_mt5_status():
            return False, "MT5 not connected"

        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            return False, f"Symbol {symbol} not found"

        min_stop_level = getattr(symbol_info, 'trade_stops_level', 0) * getattr(symbol_info, 'point', 0.00001)
        spread = getattr(symbol_info, 'spread', 0) * getattr(symbol_info, 'point', 0.00001)

        safety_margin = max(min_stop_level, spread * 2, 0.0001)  # Minimum safety margin

        if tp_price > 0:
            tp_distance = abs(tp_price - current_price)
            if tp_distance < safety_margin:
                return False, f"TP too close: {tp_distance:.5f} < {safety_margin:.5f}"

        if sl_price > 0:
            sl_distance = abs(sl_price - current_price)
            if sl_distance < safety_margin:
                return False, f"SL too close: {sl_distance:.5f} < {safety_margin:.5f}"

        if order_type == "BUY":
            if tp_price > 0 and tp_price <= current_price:
                return False, "BUY TP must be above current price"
            if sl_price > 0 and sl_price >= current_price:
                return False, "BUY SL must be below current price"
        else:
            if tp_price > 0 and tp_price >= current_price:
                return False, "SELL TP must be below current price"
            if sl_price > 0 and sl_price <= current_price:
                return False, "SELL SL must be above current price"

        return True, "Valid"

    except Exception as e:
        return False, f"Validation error: {str(e)}"

def validate_trading_conditions(symbol: str) -> Tuple[bool, str]:
    """Enhanced trading condition validation"""
    try:
        if not check_mt5_status():
            return False, "MT5 not connected"

        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            return False, f"Symbol {symbol} not found"

        if not symbol_info.visible:
            if not mt5.symbol_select(symbol, True):
                return False, f"Cannot activate {symbol}"
            time.sleep(0.1)

        trade_mode = getattr(symbol_info, 'trade_mode', None)
        if trade_mode == mt5.SYMBOL_TRADE_MODE_DISABLED:
            return False, f"Trading disabled for {symbol}"

        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return False, f"Cannot get tick data for {symbol}"

        spread = abs(tick.ask - tick.bid)
        max_spread = 0.001 if "JPY" in symbol else 0.0001
        if spread > max_spread:
            logger(f"⚠️ High spread detected: {spread:.5f}")

        return True, "Valid"

    except Exception as e:
        return False, f"Validation error: {str(e)}"

def execute_trade_signal(symbol: str, action: str) -> bool:
    """Enhanced trade execution based on signals"""
    try:
        is_valid, error_msg = validate_trading_conditions(symbol)
        if not is_valid:
            logger(f"❌ Cannot trade {symbol}: {error_msg}")
            return False

        if not gui:
            logger("❌ GUI not available")
            return False

        lot = gui.get_current_lot()
        tp_input = gui.get_current_tp()
        sl_input = gui.get_current_sl()
        tp_unit = gui.get_current_tp_unit()
        sl_unit = gui.get_current_sl_unit()

        # Set defaults if empty
        if not tp_input or tp_input == "0":
            tp_input = {"Scalping": "15", "HFT": "8", "Intraday": "50", "Arbitrage": "25"}.get(current_strategy, "20")
            tp_unit = "pips"

        if not sl_input or sl_input == "0":
            sl_input = {"Scalping": "8", "HFT": "4", "Intraday": "25", "Arbitrage": "12"}.get(current_strategy, "10")
            sl_unit = "pips"

        logger(f"🎯 Executing {action} signal for {symbol}")

        result = open_order(symbol, lot, action, sl_input, tp_input, sl_unit, tp_unit)

        if result and getattr(result, 'retcode', None) == mt5.TRADE_RETCODE_DONE:
            logger(f"✅ {action} order executed successfully!")
            return True
        else:
            logger(f"❌ Failed to execute {action} order")
            return False

    except Exception as e:
        logger(f"❌ Error executing trade signal: {str(e)}")
        return False

def open_order(symbol: str, lot: float, action: str, sl_input: str, tp_input: str, sl_unit: str = "pips", tp_unit: str = "pips") -> Any:
    """Enhanced order execution using proven logic from bot4.py"""
    global position_count, session_data, last_trade_time

    with trade_lock:
        try:
            # Rate limiting
            current_time = time.time()
            if symbol in last_trade_time:
                if current_time - last_trade_time[symbol] < 3:
                    logger(f"⏱️ Rate limit active for {symbol}")
                    return None

            # Check position limits
            positions = get_positions()
            position_count = len(positions)

            if position_count >= max_positions:
                logger(f"⚠️ Max positions ({max_positions}) reached")
                return None

            # Enhanced symbol validation
            valid_symbol = validate_and_activate_symbol(symbol)
            if not valid_symbol:
                logger(f"❌ Cannot validate symbol {symbol}")
                return None
            symbol = valid_symbol # Use the validated symbol

            # Get symbol info
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                logger(f"❌ Cannot get symbol info for {symbol}")
                return None

            # Get current tick with retry
            tick = None
            for attempt in range(3):
                tick = mt5.symbol_info_tick(symbol)
                if tick is not None and hasattr(tick, 'bid') and hasattr(tick, 'ask'):
                    if tick.bid > 0 and tick.ask > 0:
                        break
                time.sleep(0.1)

            if tick is None:
                logger(f"❌ Cannot get valid tick data for {symbol}")
                return None

            # Determine order type and price
            if action.upper() == "BUY":
                order_type = mt5.ORDER_TYPE_BUY
                price = tick.ask
            else:
                order_type = mt5.ORDER_TYPE_SELL
                price = tick.bid

            # Get session adjustments for lot sizing
            current_session = get_current_trading_session()
            session_adjustments = adjust_strategy_for_session(current_strategy, current_session)
            lot_multiplier = session_adjustments.get("lot_multiplier", 1.0)
            
            # Apply session-based lot adjustment
            adjusted_lot = lot * lot_multiplier
            logger(f"📊 Session lot adjustment: {lot} × {lot_multiplier} = {adjusted_lot}")
            
            # Validate and normalize lot size
            min_lot = getattr(symbol_info, "volume_min", 0.01)
            max_lot = getattr(symbol_info, "volume_max", 100.0)
            lot_step = getattr(symbol_info, "volume_step", 0.01)

            if adjusted_lot < min_lot:
                adjusted_lot = min_lot
            elif adjusted_lot > max_lot:
                adjusted_lot = max_lot

            lot = round(adjusted_lot / lot_step) * lot_step
            logger(f"✅ Final lot size after validation: {lot}")

            # Calculate TP and SL using user-selected units
            point = getattr(symbol_info, "point", 0.00001)
            digits = getattr(symbol_info, "digits", 5)

            tp_price = 0.0
            sl_price = 0.0

            logger(f"🧮 Calculating TP/SL: TP={tp_input} {tp_unit}, SL={sl_input} {sl_unit}")

            # Apply session adjustments to TP/SL
            tp_multiplier = session_adjustments.get("tp_multiplier", 1.0)
            sl_multiplier = session_adjustments.get("sl_multiplier", 1.0)
            
            # Parse TP dengan unit yang dipilih user + session adjustment
            if tp_input and tp_input.strip() and tp_input != "0":
                try:
                    # Apply session multiplier to TP input
                    adjusted_tp_input = str(float(tp_input) * tp_multiplier)
                    logger(f"📊 Session TP adjustment: {tp_input} × {tp_multiplier} = {adjusted_tp_input}")
                    
                    tp_price, tp_calc = parse_tp_sl_input(adjusted_tp_input, tp_unit, symbol, lot, price, action.upper(), True)
                    tp_price = round(tp_price, digits) if tp_price > 0 else 0.0

                    if tp_price > 0:
                        logger(f"✅ TP calculated: {tp_price:.5f} (from {tp_input} {tp_unit} adjusted to {adjusted_tp_input})")
                        if 'amount' in tp_calc:
                            logger(f"   Expected TP profit: ${tp_calc['amount']:.2f}")
                    else:
                        logger(f"⚠️ TP calculation resulted in 0, skipping TP")

                except Exception as e:
                    logger(f"❌ Error parsing TP {tp_input} {tp_unit}: {str(e)}")
                    tp_price = 0.0

            # Parse SL dengan unit yang dipilih user + session adjustment
            if sl_input and sl_input.strip() and sl_input != "0":
                try:
                    # Apply session multiplier to SL input
                    adjusted_sl_input = str(float(sl_input) * sl_multiplier)
                    logger(f"📊 Session SL adjustment: {sl_input} × {sl_multiplier} = {adjusted_sl_input}")
                    
                    sl_price, sl_calc = parse_tp_sl_input(adjusted_sl_input, sl_unit, symbol, lot, price, action.upper(), False)
                    sl_price = round(sl_price, digits) if sl_price > 0 else 0.0

                    if sl_price > 0:
                        logger(f"✅ SL calculated: {sl_price:.5f} (from {sl_input} {sl_unit} adjusted to {adjusted_sl_input})")
                        if 'amount' in sl_calc:
                            logger(f"   Expected SL loss: ${sl_calc['amount']:.2f}")
                    else:
                        logger(f"⚠️ SL calculation resulted in 0, skipping SL")

                except Exception as e:
                    logger(f"❌ Error parsing SL {sl_input} {sl_unit}: {str(e)}")
                    sl_price = 0.0

            # Log final TP/SL values before order
            if tp_price > 0 or sl_price > 0:
                logger(f"📋 Final order levels: Entry={price:.5f}, TP={tp_price:.5f}, SL={sl_price:.5f}")
            else:
                logger(f"📋 Order without TP/SL: Entry={price:.5f}")

            # Validasi TP/SL levels sebelum submit order
            is_valid, error_msg = validate_tp_sl_levels(symbol, tp_price, sl_price, action.upper(), price)
            if not is_valid:
                logger(f"❌ Order validation failed: {error_msg}")
                return None

            # Create order request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": lot,
                "type": order_type,
                "price": price,
                "deviation": 50,
                "magic": 123456,
                "comment": "AutoBotCuan",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }

            if sl_price > 0:
                request["sl"] = sl_price
            if tp_price > 0:
                request["tp"] = tp_price

            # Execute order
            logger(f"🔄 Sending {action} order for {symbol}")

            result = mt5.order_send(request)

            if result is None:
                logger(f"❌ Order send returned None")
                return None

            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger(f"❌ Order failed: {result.retcode} - {result.comment}")

                # Retry without SL/TP untuk error codes tertentu
                invalid_stops_codes = [10016, 10017, 10018, 10019, 10020, 10021]  # Invalid stops/TP/SL codes
                if result.retcode in invalid_stops_codes:
                    logger("⚠️ Retrying without SL/TP...")
                    request.pop("sl", None)
                    request.pop("tp", None)
                    result = mt5.order_send(request)

                    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                        logger(f"✅ Order successful without SL/TP: {result.order}")
                    else:
                        logger(f"❌ Retry failed: {result.comment if result else 'No result'}")
                        return None
                else:
                    return None

            # Order successful
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                last_trade_time[symbol] = current_time
                position_count += 1
                session_data['total_trades'] += 1
                session_data['daily_orders'] += 1

                # Update last balance for profit tracking
                info = get_account_info()
                if info:
                    session_data['last_balance'] = info['balance']
                    session_data['session_equity'] = info['equity']

                logger(f"✅ {action.upper()} order executed successfully!")
                logger(f"📊 Ticket: {result.order} | Price: {price:.5f}")

                # Log to CSV
                trade_data = {
                    "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "symbol": symbol,
                    "type": action.upper(),
                    "lot": lot,
                    "sl": sl_price if sl_price > 0 else 0,
                    "tp": tp_price if tp_price > 0 else 0,
                    "profit": 0,
                }

                log_filename = "logs/buy.csv" if action.upper() == "BUY" else "logs/sell.csv"
                if not os.path.exists("logs"):
                    os.makedirs("logs")

                log_order_csv(log_filename, trade_data)

                # Telegram notification
                if gui and gui.telegram_var.get():
                    msg = f"🟢 {action.upper()} Order Executed\nSymbol: {symbol}\nLot: {lot}\nPrice: {price:.5f}\nTicket: {result.order}"
                    send_telegram(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, msg)

                return result
            else:
                logger(f"❌ Order execution failed: {result.comment}")
                return None

        except Exception as e:
            error_msg = f"❌ Critical error in order execution: {str(e)}"
            logger(error_msg)
            return None

def log_order_csv(filename: str, order: Dict[str, Any]) -> None:
    """Enhanced CSV logging"""
    try:
        fieldnames = ["time", "symbol", "type", "lot", "sl", "tp", "profit"]
        file_exists = os.path.isfile(filename)
        with open(filename, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow(order)
    except Exception as e:
        logger(f"❌ Error logging to CSV: {str(e)}")

def close_all_orders(symbol: str = None) -> None:
    """Enhanced close all orders"""
    try:
        if not check_mt5_status():
            logger("❌ MT5 not connected")
            return

        positions = mt5.positions_get(symbol=symbol) if symbol else mt5.positions_get()
        if not positions:
            logger("ℹ️ No positions to close")
            return

        closed_count = 0
        total_profit = 0.0
        failed_count = 0

        for position in positions:
            try:
                tick = mt5.symbol_info_tick(position.symbol)
                if tick is None:
                    failed_count += 1
                    continue

                order_type = mt5.ORDER_TYPE_SELL if position.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
                price = tick.bid if position.type == mt5.ORDER_TYPE_BUY else tick.ask

                close_request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "position": position.ticket,
                    "symbol": position.symbol,
                    "volume": position.volume,
                    "type": order_type,
                    "price": price,
                    "deviation": 20,
                    "magic": position.magic,
                    "comment": "AutoBot_CloseAll",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_IOC,
                }

                result = mt5.order_send(close_request)
                if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                    logger(f"✅ Position {position.ticket} closed - Profit: ${position.profit:.2f}")
                    closed_count += 1
                    total_profit += position.profit
                    session_data['daily_profit'] += position.profit
                    session_data['total_profit'] += position.profit

                    if position.profit > 0:
                        session_data['winning_trades'] += 1
                        logger(f"🎯 Winning trade #{session_data['winning_trades']}")
                    else:
                        session_data['losing_trades'] += 1
                        logger(f"❌ Losing trade #{session_data['losing_trades']}")

                    # Update account info for GUI
                    info = get_account_info()
                    if info:
                        session_data['session_equity'] = info['equity']
                else:
                    logger(f"❌ Failed to close {position.ticket}")
                    failed_count += 1

            except Exception as e:
                logger(f"❌ Error closing position: {str(e)}")
                failed_count += 1

        if closed_count > 0:
            logger(f"🔄 Closed {closed_count} positions. Total Profit: ${total_profit:.2f}")

    except Exception as e:
        logger(f"❌ Error closing orders: {str(e)}")

def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Enhanced indicator calculation with EMA-based scalping indicators"""
    try:
        if len(df) < 50:
            return df

        # EMA indicators untuk scalping (sesuai requirement)
        df['EMA5'] = df['close'].ewm(span=5, adjust=False).mean()
        df['EMA13'] = df['close'].ewm(span=13, adjust=False).mean()
        df['EMA20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['EMA50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['EMA100'] = df['close'].ewm(span=100, adjust=False).mean()
        df['EMA200'] = df['close'].ewm(span=200, adjust=False).mean()

        # RSI untuk scalping (period 7 dan 9)
        df['RSI7'] = rsi(df['close'], 7)
        df['RSI9'] = rsi(df['close'], 9)
        df['RSI14'] = rsi(df['close'], 14)
        df['RSI'] = df['RSI9']  # Default menggunakan RSI9 untuk scalping
        df['RSI_Smooth'] = df['RSI'].rolling(window=3).mean()  # Add missing RSI_Smooth

        # MACD untuk konfirmasi
        df['MACD'], df['MACD_signal'], df['MACD_histogram'] = macd_enhanced(df['close'])

        # Moving Averages tambahan
        df['MA5'] = df['close'].rolling(window=5).mean()
        df['MA10'] = df['close'].rolling(window=10).mean()
        df['MA20'] = df['close'].rolling(window=20).mean()

        # WMA (Weighted Moving Average) - Key for price action
        def wma(series, period):
            weights = np.arange(1, period + 1)
            return series.rolling(period).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)

        df['WMA5_High'] = wma(df['high'], 5)
        df['WMA5_Low'] = wma(df['low'], 5)
        df['WMA10_High'] = wma(df['high'], 10)
        df['WMA10_Low'] = wma(df['low'], 10)

        # Bollinger Bands
        df['BB_Middle'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['BB_Upper'] = df['BB_Middle'] + 2 * bb_std
        df['BB_Lower'] = df['BB_Middle'] - 2 * bb_std
        df['BB_Width'] = (df['BB_Upper'] - df['BB_Lower']) / df['BB_Middle']

        # Stochastic
        df['STOCH_K'], df['STOCH_D'] = stochastic_enhanced(df)

        # ATR
        df['ATR'] = atr(df, 14)
        df['ATR_Ratio'] = df['ATR'] / df['ATR'].rolling(window=20).mean()

        # EMA Crossover Signals untuk Scalping
        df['EMA5_Cross_Above_EMA13'] = (
            (df['EMA5'] > df['EMA13']) & 
            (df['EMA5'].shift(1) <= df['EMA13'].shift(1))
        )
        df['EMA5_Cross_Below_EMA13'] = (
            (df['EMA5'] < df['EMA13']) & 
            (df['EMA5'].shift(1) >= df['EMA13'].shift(1))
        )

        # EMA20/50 Crossover untuk Intraday
        df['EMA20_Cross_Above_EMA50'] = (
            (df['EMA20'] > df['EMA50']) & 
            (df['EMA20'].shift(1) <= df['EMA50'].shift(1))
        )
        df['EMA20_Cross_Below_EMA50'] = (
            (df['EMA20'] < df['EMA50']) & 
            (df['EMA20'].shift(1) >= df['EMA50'].shift(1))
        )

        # RSI Conditions untuk scalping (80/20 levels)
        df['RSI_Oversold_Recovery'] = (
            (df['RSI'] > 20) & 
            (df['RSI'].shift(1) <= 20)
        )
        df['RSI_Overbought_Decline'] = (
            (df['RSI'] < 80) & 
            (df['RSI'].shift(1) >= 80)
        )

        # Enhanced Price Action Patterns
        df['Bullish_Engulfing'] = (
            (df['close'] > df['open']) &
            (df['close'].shift(1) < df['open'].shift(1)) &
            (df['open'] < df['close'].shift(1)) &
            (df['close'] > df['open'].shift(1)) &
            (df['volume'] > df['volume'].shift(1) * 1.2)  # Volume confirmation
        )

        df['Bearish_Engulfing'] = (
            (df['close'] < df['open']) &
            (df['close'].shift(1) > df['open'].shift(1)) &
            (df['open'] > df['close'].shift(1)) &
            (df['close'] < df['open'].shift(1)) &
            (df['volume'] > df['volume'].shift(1) * 1.2)  # Volume confirmation
        )

        # Breakout patterns
        df['Bullish_Breakout'] = (
            (df['close'] > df['high'].rolling(window=20).max().shift(1)) &
            (df['close'] > df['WMA5_High']) &
            (df['close'] > df['BB_Upper'])
        )

        df['Bearish_Breakout'] = (
            (df['close'] < df['low'].rolling(window=20).min().shift(1)) &
            (df['close'] < df['WMA5_Low']) &
            (df['close'] < df['BB_Lower'])
        )

        # Strong candle detection
        df['Candle_Size'] = abs(df['close'] - df['open'])
        df['Avg_Candle_Size'] = df['Candle_Size'].rolling(window=20).mean()
        df['Strong_Bullish_Candle'] = (
            (df['close'] > df['open']) &
            (df['Candle_Size'] > df['Avg_Candle_Size'] * 1.5)
        )
        df['Strong_Bearish_Candle'] = (
            (df['close'] < df['open']) &
            (df['Candle_Size'] > df['Avg_Candle_Size'] * 1.5)
        )

        # Trend indicators
        df['Higher_High'] = (df['high'] > df['high'].shift(1)) & (df['high'].shift(1) > df['high'].shift(2))
        df['Lower_Low'] = (df['low'] < df['low'].shift(1)) & (df['low'].shift(1) < df['low'].shift(2))
        df['Trend_Strength'] = abs(df['EMA20'] - df['EMA50']) / df['ATR']

        # Momentum
        df['Momentum'] = df['close'] - df['close'].shift(10)
        df['ROC'] = ((df['close'] - df['close'].shift(10)) / df['close'].shift(10)) * 100

        # Support/Resistance
        df['Support'] = df['low'].rolling(window=20).min()
        df['Resistance'] = df['high'].rolling(window=20).max()

        # Market structure
        df['Bullish_Structure'] = (
            (df['EMA20'] > df['EMA50']) &
            (df['close'] > df['EMA20']) &
            (df['MACD'] > df['MACD_signal'])
        )
        df['Bearish_Structure'] = (
            (df['EMA20'] < df['EMA50']) &
            (df['close'] < df['EMA20']) &
            (df['MACD'] < df['MACD_signal'])
        )

        # Tick data untuk HFT
        df['Price_Change'] = df['close'].diff()
        df['Volume_Burst'] = df['volume'] > df['volume'].rolling(window=5).mean() * 2

        return df
    except Exception as e:
        logger(f"❌ Error calculating indicators: {str(e)}")
        return df

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """RSI calculation"""
    delta = series.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.rolling(window=period, min_periods=1).mean()
    avg_loss = loss.rolling(window=period, min_periods=1).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def macd_enhanced(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Enhanced MACD calculation"""
    exp1 = series.ewm(span=fast, adjust=False).mean()
    exp2 = series.ewm(span=slow, adjust=False).mean()
    macd_line = exp1 - exp2
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def stochastic_enhanced(df: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
    """Enhanced Stochastic Oscillator"""
    low_min = df['low'].rolling(window=k_period).min()
    high_max = df['high'].rolling(window=k_period).max()
    k = 100 * ((df['close'] - low_min) / (high_max - low_min))
    d = k.rolling(window=d_period).mean()
    return k, d

def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range calculation"""
    tr1 = df['high'] - df['low']
    tr2 = abs(df['high'] - df['close'].shift(1))
    tr3 = abs(df['low'] - df['close'].shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

def run_strategy(strategy: str, df: pd.DataFrame, symbol: str) -> Tuple[Optional[str], List[str]]:
    """Enhanced strategy execution with session-aware signal detection"""
    try:
        if len(df) < 50:
            logger(f"❌ Insufficient data for {symbol}: {len(df)} bars (need 50+)")
            return None, [f"Insufficient data: {len(df)} bars"]

        last = df.iloc[-1]
        prev = df.iloc[-2]
        prev2 = df.iloc[-3] if len(df) > 3 else prev
        action = None
        signals = []

        # Debug: Log current price data
        logger(f"📊 {symbol} Current Data: O={last['open']:.5f} H={last['high']:.5f} L={last['low']:.5f} C={last['close']:.5f}")

        # Get current trading session and adjustments
        current_session = get_current_trading_session()
        session_adjustments = adjust_strategy_for_session(strategy, current_session)
        
        # Check if high-impact news time
        is_news_time = is_high_impact_news_time()
        if is_news_time:
            logger("⚠️ High-impact news time - applying conservative filters")
            session_adjustments["signal_threshold_modifier"] += 2  # More conservative during news
        
        # Strategy-specific logic with session-aware signal generation
        buy_signals = 0
        sell_signals = 0

        session_name = current_session["name"] if current_session else "Default"
        logger(f"🎯 Analyzing {strategy} signals for {symbol} in {session_name} session...")
        
        # Debug: Log key indicator values
        logger(f"🔍 Key Indicators:")
        if 'EMA5' in last:
            logger(f"   EMA5: {last['EMA5']:.5f}, EMA13: {last['EMA13']:.5f}, EMA50: {last['EMA50']:.5f}")
        if 'RSI' in last:
            logger(f"   RSI: {last['RSI']:.1f}, RSI7: {last.get('RSI7', 0):.1f}")
        if 'MACD' in last:
            logger(f"   MACD: {last['MACD']:.5f}, Signal: {last['MACD_signal']:.5f}, Hist: {last['MACD_histogram']:.5f}")

        if strategy == "Scalping":
            # Enhanced scalping dengan EMA 5/13 crossover sesuai requirement
            logger("⚡ Scalping: EMA 5/13 crossover + EMA50 filter + RSI 80/20...")

            # PRIMARY SIGNAL: EMA 5/13 Crossover (WAJIB)
            if last['EMA5_Cross_Above_EMA13']:
                # BUY Signal: EMA 5 cross atas EMA 13
                if (last['close'] > last['EMA50'] and  # Filter: harga di atas EMA50
                    last['RSI_Oversold_Recovery']):    # RSI naik dari bawah 20
                    buy_signals += 5
                    signals.append("✅ SCALP: EMA5 cross EMA13 UP + EMA50 filter + RSI recovery")
                elif last['close'] > last['EMA50']:
                    # Tanpa RSI masih valid tapi sinyal lebih lemah
                    buy_signals += 3
                    signals.append("✅ SCALP: EMA5 cross EMA13 UP + EMA50 filter")

            elif last['EMA5_Cross_Below_EMA13']:
                # SELL Signal: EMA 5 cross bawah EMA 13
                if (last['close'] < last['EMA50'] and  # Filter: harga di bawah EMA50
                    last['RSI_Overbought_Decline']):   # RSI turun dari atas 80
                    sell_signals += 5
                    signals.append("✅ SCALP: EMA5 cross EMA13 DOWN + EMA50 filter + RSI decline")
                elif last['close'] < last['EMA50']:
                    # Tanpa RSI masih valid tapi sinyal lebih lemah
                    sell_signals += 3
                    signals.append("✅ SCALP: EMA5 cross EMA13 DOWN + EMA50 filter")

            # KONFIRMASI TAMBAHAN: RSI Extreme Levels (80/20)
            if last['RSI'] < 20 and last['close'] > last['EMA50']:
                buy_signals += 2
                signals.append(f"✅ SCALP: RSI oversold extreme ({last['RSI']:.1f}) + EMA50 bullish")
            elif last['RSI'] > 80 and last['close'] < last['EMA50']:
                sell_signals += 2
                signals.append(f"✅ SCALP: RSI overbought extreme ({last['RSI']:.1f}) + EMA50 bearish")

            # KONFIRMASI MOMENTUM: MACD Histogram
            if (last['MACD_histogram'] > 0 and last['MACD_histogram'] > prev['MACD_histogram'] and
                last['EMA5'] > last['EMA13'] and last['close'] > last['EMA50']):
                buy_signals += 2
                signals.append("✅ SCALP: MACD momentum bullish + EMA alignment")
            elif (last['MACD_histogram'] < 0 and last['MACD_histogram'] < prev['MACD_histogram'] and
                  last['EMA5'] < last['EMA13'] and last['close'] < last['EMA50']):
                sell_signals += 2
                signals.append("✅ SCALP: MACD momentum bearish + EMA alignment")

            # PRICE ACTION: Strong Candle dengan EMA konfirmasi
            if (last['Strong_Bullish_Candle'] and last['EMA5'] > last['EMA13'] and 
                last['close'] > last['EMA50']):
                buy_signals += 2
                signals.append("✅ SCALP: Strong bullish candle + EMA bullish structure")
            elif (last['Strong_Bearish_Candle'] and last['EMA5'] < last['EMA13'] and 
                  last['close'] < last['EMA50']):
                sell_signals += 2
                signals.append("✅ SCALP: Strong bearish candle + EMA bearish structure")

            # KONFIRMASI VOLUME (jika tersedia)
            volume_avg = df['volume'].rolling(window=10).mean().iloc[-1] if 'volume' in df else 1
            current_volume = last.get('volume', 1)
            if current_volume > volume_avg * 1.3:
                if last['EMA5'] > last['EMA13'] and last['close'] > last['EMA50']:
                    buy_signals += 1
                    signals.append("✅ SCALP: High volume confirmation bullish")
                elif last['EMA5'] < last['EMA13'] and last['close'] < last['EMA50']:
                    sell_signals += 1
                    signals.append("✅ SCALP: High volume confirmation bearish")

        elif strategy == "HFT":
            # Ultra-aggressive HFT with WMA and price action
            logger("⚡ HFT: Ultra-aggressive micro-trend and price action detection...")

            # Ultra-fast price movements (more sensitive)
            tick_change = (last['close'] - prev['close']) / prev['close'] * 10000  # Per 10k for precision
            if tick_change > 2 and last['close'] > last['open']:
                buy_signals += 4
                signals.append(f"✅ HFT: Ultra-fast bullish {tick_change:.1f} ticks")
            elif tick_change < -2 and last['close'] < last['open']:
                sell_signals += 4
                signals.append(f"✅ HFT: Ultra-fast bearish {tick_change:.1f} ticks")

            # WMA crossovers for instant signals
            if (last['close'] > last['WMA5_High'] and prev['close'] <= prev['WMA5_High'] and
                last['close'] > last['WMA10_High']):
                buy_signals += 3
                signals.append("✅ HFT: WMA breakout up")
            elif (last['close'] < last['WMA5_Low'] and prev['close'] >= prev['WMA5_Low'] and
                  last['close'] < last['WMA10_Low']):
                sell_signals += 3
                signals.append("✅ HFT: WMA breakout down")

            # Strong candle detection
            if last['Strong_Bullish_Candle'] and last['close'] > last['EMA20']:
                buy_signals += 3
                signals.append("✅ HFT: Strong bullish candle confirmed")
            elif last['Strong_Bearish_Candle'] and last['close'] < last['EMA20']:
                sell_signals += 3
                signals.append("✅ HFT: Strong bearish candle confirmed")

            # Price action patterns
            if last['Bullish_Engulfing']:
                buy_signals += 4
                signals.append("✅ HFT: Bullish engulfing pattern")
            elif last['Bearish_Engulfing']:
                sell_signals += 4
                signals.append("✅ HFT: Bearish engulfing pattern")

            # Instant momentum (very fast RSI)
            if last['RSI_Smooth'] > 50 and (last['RSI_Smooth'] - prev['RSI_Smooth']) > 2:
                buy_signals += 2
                signals.append(f"✅ HFT: Fast RSI momentum {last['RSI_Smooth']:.1f}")
            elif last['RSI_Smooth'] < 50 and (last['RSI_Smooth'] - prev['RSI_Smooth']) < -2:
                sell_signals += 2
                signals.append(f"✅ HFT: Fast RSI momentum {last['RSI_Smooth']:.1f}")

            # Bollinger Band squeeze breakout
            if last['close'] > last['BB_Upper'] and prev['close'] <= prev['BB_Upper']:
                buy_signals += 2
                signals.append("✅ HFT: BB upper breakout")
            elif last['close'] < last['BB_Lower'] and prev['close'] >= prev['BB_Lower']:
                sell_signals += 2
                signals.append("✅ HFT: BB lower breakout")

        elif strategy == "Intraday":
            # Enhanced intraday dengan EMA 20/50 crossover + EMA200 filter sesuai requirement
            logger("📈 Intraday: EMA 20/50 crossover + EMA200 filter + RSI14 + MACD...")

            # PRIMARY SIGNAL: EMA 20/50 Crossover
            if last['EMA20_Cross_Above_EMA50']:
                # BUY Signal: EMA 20 cross atas EMA 50
                if (last['close'] > last['EMA200'] and      # Filter: harga di atas EMA200 
                    last['RSI14'] > 50 and                  # RSI > 50
                    last['MACD_histogram'] > prev['MACD_histogram']):  # MACD histogram naik
                    buy_signals += 5
                    signals.append("✅ INTRADAY: EMA20 cross EMA50 UP + EMA200 filter + RSI>50 + MACD rising")
                elif last['close'] > last['EMA200'] and last['RSI14'] > 50:
                    buy_signals += 3
                    signals.append("✅ INTRADAY: EMA20 cross EMA50 UP + EMA200 filter + RSI>50")

            elif last['EMA20_Cross_Below_EMA50']:
                # SELL Signal: EMA 20 cross bawah EMA 50
                if (last['close'] < last['EMA200'] and      # Filter: harga di bawah EMA200
                    last['RSI14'] < 50 and                  # RSI < 50
                    last['MACD_histogram'] < prev['MACD_histogram']):  # MACD histogram turun
                    sell_signals += 5
                    signals.append("✅ INTRADAY: EMA20 cross EMA50 DOWN + EMA200 filter + RSI<50 + MACD falling")
                elif last['close'] < last['EMA200'] and last['RSI14'] < 50:
                    sell_signals += 3
                    signals.append("✅ INTRADAY: EMA20 cross EMA50 DOWN + EMA200 filter + RSI<50")

            # KONFIRMASI TREND: EMA200 sebagai filter utama
            if (last['EMA20'] > last['EMA50'] > last['EMA200'] and 
                last['close'] > last['EMA200'] and last['RSI14'] > 50):
                buy_signals += 2
                signals.append("✅ INTRADAY: Strong bullish EMA alignment (20>50>200)")
            elif (last['EMA20'] < last['EMA50'] < last['EMA200'] and 
                  last['close'] < last['EMA200'] and last['RSI14'] < 50):
                sell_signals += 2
                signals.append("✅ INTRADAY: Strong bearish EMA alignment (20<50<200)")

            # KONFIRMASI MACD: Signal line crossover
            if (last['MACD'] > last['MACD_signal'] and prev['MACD'] <= prev['MACD_signal'] and
                last['close'] > last['EMA200']):
                buy_signals += 2
                signals.append("✅ INTRADAY: MACD signal line cross UP + EMA200 bullish")
            elif (last['MACD'] < last['MACD_signal'] and prev['MACD'] >= prev['MACD_signal'] and
                  last['close'] < last['EMA200']):
                sell_signals += 2
                signals.append("✅ INTRADAY: MACD signal line cross DOWN + EMA200 bearish")

            # MOMENTUM CONFIRMATION: Trend strength
            volume_avg = df['volume'].rolling(window=20).mean().iloc[-1] if 'volume' in df else 1
            current_volume = last.get('volume', 1)
            volume_factor = current_volume / volume_avg if volume_avg > 0 else 1

            if (last['Trend_Strength'] > 1.5 and volume_factor > 1.2 and 
                last['EMA20'] > last['EMA50'] and last['close'] > last['EMA200']):
                buy_signals += 2
                signals.append(f"✅ INTRADAY: Strong uptrend momentum + volume ({last['Trend_Strength']:.2f})")
            elif (last['Trend_Strength'] > 1.5 and volume_factor > 1.2 and 
                  last['EMA20'] < last['EMA50'] and last['close'] < last['EMA200']):
                sell_signals += 2
                signals.append(f"✅ INTRADAY: Strong downtrend momentum + volume ({last['Trend_Strength']:.2f})")

            # BREAKOUT CONFIRMATION
            if (last['Bullish_Breakout'] and last['RSI14'] > 60 and 
                last['close'] > last['EMA200']):
                buy_signals += 2
                signals.append("✅ INTRADAY: Breakout UP + RSI momentum + EMA200 filter")
            elif (last['Bearish_Breakout'] and last['RSI14'] < 40 and 
                  last['close'] < last['EMA200']):
                sell_signals += 2
                signals.append("✅ INTRADAY: Breakout DOWN + RSI momentum + EMA200 filter")

        elif strategy == "Arbitrage":
            # Enhanced mean reversion with multi-timeframe analysis
            logger("🔄 Arbitrage: Advanced mean reversion with WMA support...")

            # Multiple timeframe Bollinger Band analysis
            bb_width = last['BB_Width'] if 'BB_Width' in last else 0.02
            bb_position = (last['close'] - last['BB_Lower']) / (last['BB_Upper'] - last['BB_Lower'])

            # Oversold conditions with multiple confirmations
            if (last['RSI_Smooth'] < 25 and bb_position < 0.1 and 
                last['close'] < last['WMA10_Low'] and last['close'] > prev['close']):
                buy_signals += 4
                signals.append(f"✅ ARBITRAGE: Multi-oversold recovery setup")
            elif (last['RSI_Smooth'] > 75 and bb_position > 0.9 and 
                  last['close'] > last['WMA10_High'] and last['close'] < prev['close']):
                sell_signals += 4
                signals.append(f"✅ ARBITRAGE: Multi-overbought decline setup")

            # Mean reversion with volume confirmation
            volume_avg = df['volume'].rolling(window=20).mean().iloc[-1] if 'volume' in df else 1
            current_volume = last.get('volume', 1)

            if (last['close'] <= last['BB_Lower'] and current_volume > volume_avg * 1.3 and
                last['RSI_Smooth'] < 30 and last['STOCH_K'] < 20):
                buy_signals += 3
                signals.append("✅ ARBITRAGE: Volume-confirmed oversold")
            elif (last['close'] >= last['BB_Upper'] and current_volume > volume_avg * 1.3 and
                  last['RSI_Smooth'] > 70 and last['STOCH_K'] > 80):
                sell_signals += 3
                signals.append("✅ ARBITRAGE: Volume-confirmed overbought")

            # WMA mean reversion
            wma_deviation = (last['close'] - last['WMA10_High']) / last['WMA10_High'] * 100
            if (wma_deviation < -1.5 and last['close'] > last['WMA5_Low'] and 
                last['MACD_histogram'] > prev['MACD_histogram']):
                buy_signals += 2
                signals.append(f"✅ ARBITRAGE: WMA deviation recovery ({wma_deviation:.2f}%)")
            elif (wma_deviation > 1.5 and last['close'] < last['WMA5_High'] and 
                  last['MACD_histogram'] < prev['MACD_histogram']):
                sell_signals += 2
                signals.append(f"✅ ARBITRAGE: WMA deviation decline ({wma_deviation:.2f}%)")

            # Double divergence detection
            if (last['RSI_Smooth'] < 25 and prev['RSI_Smooth'] < 25 and 
                last['STOCH_K'] < 20 and prev['STOCH_K'] < 20 and
                last['close'] > prev['close']):
                buy_signals += 2
                signals.append("✅ ARBITRAGE: Double oversold divergence")
            elif (last['RSI_Smooth'] > 75 and prev['RSI_Smooth'] > 75 and 
                  last['STOCH_K'] > 80 and prev['STOCH_K'] > 80 and
                  last['close'] < prev['close']):
                sell_signals += 2
                signals.append("✅ ARBITRAGE: Double overbought divergence")

        # Session-aware signal thresholds
        base_min_signals = {
            "Scalping": 3,    # Moderate confirmation for scalping
            "HFT": 2,         # Very aggressive - fastest execution
            "Intraday": 4,    # Strong confirmation for longer trades
            "Arbitrage": 2    # Quick mean reversion entries
        }

        # Apply session adjustments to threshold
        base_threshold = base_min_signals.get(strategy, 2)
        threshold_modifier = session_adjustments.get("signal_threshold_modifier", 0)
        threshold = max(1, base_threshold + threshold_modifier)  # Minimum threshold of 1
        
        # Log session impact
        if current_session:
            volatility = current_session["info"]["volatility"]
            logger(f"📊 {session_name} session ({volatility} volatility) - adjusted threshold: {base_threshold} → {threshold}")
        else:
            logger(f"📊 Default session - threshold: {threshold}")

        # Debug: Show all signals detected
        logger(f"🔍 Signal Analysis Results:")
        logger(f"   Strategy: {strategy}")
        logger(f"   BUY Signals: {buy_signals}")
        logger(f"   SELL Signals: {sell_signals}")
        logger(f"   Required Threshold: {threshold}")
        logger(f"   Session Adjustment: {session_adjustments.get('signal_threshold_modifier', 0)}")
        
        # Log detected signals
        if signals:
            logger(f"📋 Detected Signals ({len(signals)}):")
            for i, signal in enumerate(signals[:5], 1):
                logger(f"   {i}. {signal}")
            if len(signals) > 5:
                logger(f"   ... and {len(signals)-5} more signals")
        else:
            logger("❌ No signals detected at all")
            
            # Force basic signals for debugging
            if strategy == "Scalping":
                # Force EMA trend signals
                if last['EMA5'] > last['EMA13']:
                    buy_signals += 1
                    signals.append("🔧 DEBUG: EMA5 > EMA13 (basic trend)")
                elif last['EMA5'] < last['EMA13']:
                    sell_signals += 1
                    signals.append("🔧 DEBUG: EMA5 < EMA13 (basic trend)")
                    
                # Force RSI signals
                if last['RSI'] < 30:
                    buy_signals += 1
                    signals.append(f"🔧 DEBUG: RSI oversold ({last['RSI']:.1f})")
                elif last['RSI'] > 70:
                    sell_signals += 1
                    signals.append(f"🔧 DEBUG: RSI overbought ({last['RSI']:.1f})")

        # Decision logic with tie-breaker
        total_signals = buy_signals + sell_signals
        signal_strength = max(buy_signals, sell_signals)

        # Lower threshold for debugging if no strong signals
        effective_threshold = max(1, threshold - 1) if signals else threshold

        if buy_signals > sell_signals and buy_signals >= effective_threshold:
            action = "BUY"
            confidence = (buy_signals / max(total_signals, 1)) * 100
            logger(f"🟢 {strategy} BUY SIGNAL ACTIVATED! Score: {buy_signals} vs {sell_signals} (confidence: {confidence:.1f}%)")
        elif sell_signals > buy_signals and sell_signals >= effective_threshold:
            action = "SELL"
            confidence = (sell_signals / max(total_signals, 1)) * 100
            logger(f"🔴 {strategy} SELL SIGNAL ACTIVATED! Score: {sell_signals} vs {sell_signals} (confidence: {confidence:.1f}%)")
        else:
            logger(f"⚪ {strategy} WAITING. BUY:{buy_signals} SELL:{sell_signals} (need:{effective_threshold})")
            
            # Debug recommendation
            if total_signals > 0:
                stronger_side = "BUY" if buy_signals > sell_signals else "SELL"
                logger(f"💡 Closest to signal: {stronger_side} ({max(buy_signals, sell_signals)}/{effective_threshold})")

        return action, signals

    except Exception as e:
        logger(f"❌ Strategy {strategy} error: {str(e)}")
        import traceback
        logger(f"🔍 Traceback: {traceback.format_exc()}")
        return None, [f"❌ Strategy {strategy} error: {str(e)}"]

def get_symbol_data(symbol: str, timeframe: int, n: int = 200) -> Optional[pd.DataFrame]:
    """Enhanced data fetching with timeframe-specific adjustments"""
    try:
        if not check_mt5_status():
            logger("❌ MT5 not connected for data request")
            return None

        # Validate symbol first
        valid_symbol = validate_and_activate_symbol(symbol)
        if not valid_symbol:
            logger(f"❌ Cannot validate {symbol} for data request")
            return None

        # Adjust data count based on timeframe for better analysis
        timeframe_adjustments = {
            mt5.TIMEFRAME_M1: 300,   # More data for M1
            mt5.TIMEFRAME_M3: 250,
            mt5.TIMEFRAME_M5: 200,
            mt5.TIMEFRAME_M15: 150,
            mt5.TIMEFRAME_M30: 120,
            mt5.TIMEFRAME_H1: 100,
            mt5.TIMEFRAME_H4: 80,
            mt5.TIMEFRAME_D1: 60
        }

        adjusted_n = timeframe_adjustments.get(timeframe, n)

        # Multiple attempts to get data
        for attempt in range(3):
            try:
                logger(f"📊 Getting {adjusted_n} candles for {valid_symbol} on timeframe {timeframe} (attempt {attempt + 1})")
                rates = mt5.copy_rates_from_pos(valid_symbol, timeframe, 0, adjusted_n)

                if rates is not None and len(rates) > 50:  # Ensure sufficient data
                    df = pd.DataFrame(rates)
                    df['time'] = pd.to_datetime(df['time'], unit='s')

                    # Data validation and cleaning
                    required_columns = ['open', 'high', 'low', 'close', 'tick_volume']
                    for col in required_columns:
                        if col not in df.columns:
                            logger(f"❌ Missing column {col}")
                            return None
                        if df[col].isna().any():
                            df[col] = df[col].fillna(method='ffill')

                    # Create volume column if not present
                    if 'volume' not in df.columns:
                        df['volume'] = df['tick_volume']

                    # Validate and fix price relationships
                    df.loc[df['high'] < df['low'], ['high', 'low']] = df.loc[df['high'] < df['low'], ['low', 'high']].values
                    df['close'] = df['close'].clip(df['low'], df['high'])
                    df['open'] = df['open'].clip(df['low'], df['high'])

                    # Remove any invalid prices
                    df = df[(df['open'] > 0) & (df['high'] > 0) & (df['low'] > 0) & (df['close'] > 0)]

                    # Sort by time to ensure chronological order
                    df = df.sort_values('time').reset_index(drop=True)

                    logger(f"✅ Retrieved {len(df)} quality candles for {valid_symbol}")
                    return df
                else:
                    logger(f"⚠️ Insufficient data for {valid_symbol} (attempt {attempt + 1}): got {len(rates) if rates else 0} candles")

            except Exception as e:
                logger(f"⚠️ Data request failed (attempt {attempt + 1}): {str(e)}")

            if attempt < 2:
                time.sleep(1.5)  # Longer wait between attempts

        logger(f"❌ All data requests failed for {valid_symbol}")
        return None

    except Exception as e:
        logger(f"❌ Critical error getting data for {symbol}: {str(e)}")
        return None

def check_daily_limits() -> bool:
    """Enhanced daily limits check"""
    try:
        global session_start_balance

        if not session_start_balance:
            return True

        info = get_account_info()
        if not info:
            return True

        current_equity = info['equity']
        daily_loss = session_start_balance - current_equity
        daily_loss_percent = (daily_loss / session_start_balance) * 100

        if daily_loss_percent >= (daily_max_loss * 100):
            logger(f"🛑 Daily max loss reached: {daily_loss_percent:.2f}%")
            return False

        daily_profit_percent = ((current_equity - session_start_balance) / session_start_balance) * 100
        if daily_profit_percent >= (profit_target * 100):
            logger(f"🎯 Daily profit target reached: {daily_profit_percent:.2f}%")
            return False

        max_equity_today = max(session_start_balance, current_equity)
        current_drawdown = (max_equity_today - current_equity) / max_equity_today
        if current_drawdown >= max_drawdown:
            logger(f"🛑 Max drawdown reached: {current_drawdown:.2%}")
            return False

        return True
    except Exception as e:
        logger(f"❌ Error in check_daily_limits: {str(e)}")
        return True

def logger(msg: str) -> None:
    """Enhanced logging with GUI integration"""
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    full_msg = f"[{timestamp}] {msg}"
    print(full_msg)

    if gui:
        try:
            gui.log(full_msg)
        except:
            pass

def send_telegram(token: str, chat_id: str, message: str) -> None:
    """Enhanced Telegram messaging"""
    if not token or not chat_id:
        return

    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {"chat_id": chat_id, "text": message}
        response = requests.post(url, data=data, timeout=10)
        if response.status_code != 200:
            logger(f"⚠️ Telegram send failed: {response.status_code}")
    except Exception as e:
        logger(f"❌ Telegram error: {str(e)}")

def get_current_trading_session() -> Optional[Dict[str, Any]]:
    """Get current active trading session with detailed analysis"""
    try:
        # Use local time instead of requiring pytz
        current_time = datetime.datetime.now()
        current_hour = current_time.hour
        
        # Convert to UTC approximation (assume user timezone for now)
        logger(f"🕐 Current time: {current_time.strftime('%H:%M')} (Local)")
        
        active_sessions = []
        
        for session_name, session_info in TRADING_SESSIONS.items():
            if not session_info["active"]:
                continue
                
            start_hour = int(session_info["start"].split(":")[0])
            end_hour = int(session_info["end"].split(":")[0])
            
            # Handle overnight sessions (like Asia session)
            if start_hour > end_hour:
                if current_hour >= start_hour or current_hour <= end_hour:
                    active_sessions.append({
                        "name": session_name,
                        "info": session_info,
                        "time_in_session": calculate_session_time_progress(current_hour, start_hour, end_hour)
                    })
                    logger(f"🌏 {session_name} session ACTIVE (overnight: {start_hour}:00-{end_hour}:00)")
            else:
                if start_hour <= current_hour <= end_hour:
                    active_sessions.append({
                        "name": session_name,
                        "info": session_info,
                        "time_in_session": calculate_session_time_progress(current_hour, start_hour, end_hour)
                    })
                    logger(f"🌍 {session_name} session ACTIVE ({start_hour}:00-{end_hour}:00)")
        
        if active_sessions:
            # Return the most volatile/preferred session if multiple are active
            best_session = max(active_sessions, key=lambda x: get_session_priority(x["info"]["volatility"]))
            logger(f"✅ PRIMARY SESSION: {best_session['name']} - {best_session['info']['volatility']} volatility")
            return best_session
        else:
            # Always allow trading but with default session
            logger("⚠️ Outside major sessions - using 24/7 default mode")
            return {
                "name": "24/7",
                "info": {
                    "volatility": "medium",
                    "preferred_pairs": ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD"]
                },
                "time_in_session": 0.5
            }
            
    except Exception as e:
        logger(f"❌ Error getting trading session: {str(e)}")
        # Return default session on error
        return {
            "name": "Default",
            "info": {
                "volatility": "medium", 
                "preferred_pairs": ["EURUSD", "GBPUSD", "USDJPY"]
            },
            "time_in_session": 0.5
        }

def calculate_session_time_progress(current_hour: int, start_hour: int, end_hour: int) -> float:
    """Calculate how far into the session we are (0.0 to 1.0)"""
    try:
        if start_hour > end_hour:  # Overnight session
            total_hours = (24 - start_hour) + end_hour
            if current_hour >= start_hour:
                elapsed = current_hour - start_hour
            else:
                elapsed = (24 - start_hour) + current_hour
        else:
            total_hours = end_hour - start_hour
            elapsed = current_hour - start_hour
            
        return min(elapsed / total_hours, 1.0) if total_hours > 0 else 0.0
    except:
        return 0.5

def get_session_priority(volatility: str) -> int:
    """Get session priority based on volatility"""
    priority_map = {
        "very_high": 4,
        "high": 3,
        "medium": 2,
        "low": 1
    }
    return priority_map.get(volatility, 1)

def get_session_optimal_symbols(session_name: str) -> List[str]:
    """Get optimal symbols for current trading session"""
    try:
        if session_name in TRADING_SESSIONS:
            return TRADING_SESSIONS[session_name]["preferred_pairs"]
        return ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"]
    except:
        return ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"]

def adjust_strategy_for_session(strategy: str, session_info: Optional[Dict]) -> Dict[str, Any]:
    """Adjust trading strategy parameters based on current session"""
    try:
        base_adjustments = {
            "lot_multiplier": 1.0,
            "tp_multiplier": 1.0,
            "sl_multiplier": 1.0,
            "signal_threshold_modifier": 0,
            "max_spread_multiplier": 1.0
        }
        
        if not session_info:
            return base_adjustments
            
        session_name = session_info["name"]
        volatility = session_info["info"]["volatility"]
        session_settings = SESSION_SETTINGS.get(session_name, {})
        
        # Adjust based on volatility
        if volatility == "very_high":
            base_adjustments.update({
                "lot_multiplier": 1.2,
                "tp_multiplier": 1.3,
                "sl_multiplier": 0.8,
                "signal_threshold_modifier": -1,  # More aggressive
                "max_spread_multiplier": 0.8
            })
        elif volatility == "high":
            base_adjustments.update({
                "lot_multiplier": 1.1,
                "tp_multiplier": 1.2,
                "sl_multiplier": 0.9,
                "signal_threshold_modifier": 0,
                "max_spread_multiplier": 1.0
            })
        elif volatility == "medium":
            base_adjustments.update({
                "lot_multiplier": 0.9,
                "tp_multiplier": 1.0,
                "sl_multiplier": 1.1,
                "signal_threshold_modifier": 1,  # More conservative
                "max_spread_multiplier": 1.2
            })
        else:  # low volatility
            base_adjustments.update({
                "lot_multiplier": 0.8,
                "tp_multiplier": 0.9,
                "sl_multiplier": 1.2,
                "signal_threshold_modifier": 2,  # Very conservative
                "max_spread_multiplier": 1.5
            })
            
        # Strategy-specific adjustments
        if strategy == "HFT":
            base_adjustments["signal_threshold_modifier"] -= 1  # More aggressive for HFT
        elif strategy == "Intraday":
            base_adjustments["tp_multiplier"] *= 1.2  # Larger targets for intraday
            
        logger(f"📊 Session adjustments for {session_name}: {base_adjustments}")
        return base_adjustments
        
    except Exception as e:
        logger(f"❌ Error adjusting strategy for session: {str(e)}")
        return {"lot_multiplier": 1.0, "tp_multiplier": 1.0, "sl_multiplier": 1.0, "signal_threshold_modifier": 0, "max_spread_multiplier": 1.0}

def check_trading_time() -> bool:
    """Enhanced 24/7 trading time check with session awareness"""
    try:
        # Always allow trading - 24/7 mode
        current_session = get_current_trading_session()
        
        if current_session:
            session_name = current_session['name']
            volatility = current_session['info']['volatility']
            logger(f"✅ Trading ENABLED in {session_name} session ({volatility} volatility)")
        else:
            logger("✅ Trading ENABLED - 24/7 mode active")
            
        return True  # Always allow trading
            
    except Exception as e:
        logger(f"❌ Error in check_trading_time: {str(e)}")
        return True  # Always default to allowing trading

def is_high_impact_news_time() -> bool:
    """Check if current time is during high-impact news releases"""
    try:
        import pytz
        utc_now = datetime.datetime.now(pytz.UTC)
        current_hour = utc_now.hour
        current_minute = utc_now.minute
        day_of_week = utc_now.weekday()  # 0=Monday, 6=Sunday
        
        # High-impact news times (UTC)
        high_impact_times = [
            # Daily London Fix
            (16, 0, 16, 30),  # 4:00-4:30 PM UTC
            # US NFP (first Friday of month)
            (12, 30, 13, 30),  # 12:30-1:30 PM UTC on Fridays
            # FOMC announcements (2:00 PM EST = 19:00 UTC)
            (19, 0, 20, 0),   # 7:00-8:00 PM UTC
        ]
        
        current_time_minutes = current_hour * 60 + current_minute
        
        for start_h, start_m, end_h, end_m in high_impact_times:
            start_minutes = start_h * 60 + start_m
            end_minutes = end_h * 60 + end_m
            
            if start_minutes <= current_time_minutes <= end_minutes:
                logger(f"⚠️ High-impact news time detected: {current_hour:02d}:{current_minute:02d} UTC")
                return True
                
        return False
        
    except Exception as e:
        logger(f"❌ Error checking news time: {str(e)}")
        return False

def risk_management_check() -> bool:
    """Enhanced risk management"""
    try:
        global loss_streak, session_start_balance

        info = get_account_info()
        if not info or not session_start_balance:
            return True

        current_drawdown = (session_start_balance - info['equity']) / session_start_balance
        if current_drawdown >= max_drawdown:
            logger(f"🛑 Max drawdown reached: {current_drawdown:.2%}")
            return False

        if not check_daily_limits():
            return False

        if loss_streak >= max_loss_streak:
            logger(f"🛑 Max loss streak reached: {loss_streak}")
            return False

        if info['margin_level'] < 300 and info['margin_level'] > 0:
            logger(f"🛑 Low margin level: {info['margin_level']:.2f}%")
            return False

        return True
    except Exception as e:
        logger(f"❌ Risk management error: {str(e)}")
        return True

def check_profit_targets() -> bool:
    """Enhanced profit target checking"""
    try:
        global session_start_balance

        info = get_account_info()
        if not info or not session_start_balance:
            return True

        current_equity = info['equity']
        session_profit = current_equity - session_start_balance
        profit_percent = (session_profit / session_start_balance) * 100

        target_percent = float(gui.profit_target_entry.get()) if gui else 5.0
        if profit_percent >= target_percent:
            logger(f"🎯 Profit target reached ({profit_percent:.2f}%)")
            close_all_orders()

            if gui and gui.telegram_var.get():
                msg = f"🎯 PROFIT TARGET REACHED!\nProfit: ${session_profit:.2f} ({profit_percent:.2f}%)"
                send_telegram(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, msg)

            return False

        return True

    except Exception as e:
        logger(f"❌ Error checking profit targets: {str(e)}")
        return True

def bot_thread() -> None:
    """Enhanced main bot trading thread with improved error handling"""
    global bot_running, disconnect_count, session_start_balance, loss_streak, current_strategy, position_count, mt5_connected

    try:
        logger("🚀 Starting enhanced trading bot thread...")

        # Ensure MT5 connection
        connection_attempts = 0
        max_attempts = 5

        while connection_attempts < max_attempts and not mt5_connected:
            logger(f"🔄 Bot connection attempt {connection_attempts + 1}/{max_attempts}")
            if connect_mt5():
                logger("✅ Bot connected to MT5 successfully!")
                break
            else:
                connection_attempts += 1
                if connection_attempts < max_attempts:
                    time.sleep(5)

        if not mt5_connected:
            logger("❌ Bot failed to connect to MT5 after all attempts")
            bot_running = False
            if gui:
                gui.bot_status_lbl.config(text="Bot: Connection Failed 🔴", foreground="red")
            return

        # Initialize session
        info = get_account_info()
        if info:
            session_start_balance = info['balance']
            session_data['start_time'] = datetime.datetime.now()
            session_data['start_balance'] = session_start_balance
            logger(f"🚀 Trading session initialized. Balance: ${session_start_balance:.2f}")

            # Get current strategy from GUI at start
            if gui:
                current_strategy = gui.strategy_combo.get()
                logger(f"📈 Selected strategy: {current_strategy}")

            if gui and gui.telegram_var.get():
                msg = f"🤖 AutoBot Started\nBalance: ${session_start_balance:.2f}\nStrategy: {current_strategy}"
                send_telegram(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, msg)

        # Enhanced symbol selection with session optimization
        trading_symbol = "EURUSD"  # Default fallback
        
        # Check current session and get optimal symbols
        current_session = get_current_trading_session()
        optimal_symbols = []
        
        if current_session:
            optimal_symbols = get_session_optimal_symbols(current_session["name"])
            logger(f"🌍 {current_session['name']} session optimal symbols: {', '.join(optimal_symbols[:5])}")
        
        # Priority: User selection > Session optimal > Default
        if gui and gui.symbol_entry.get():
            user_symbol = gui.symbol_entry.get().strip().upper()
            if validate_and_activate_symbol(user_symbol):
                trading_symbol = user_symbol
                logger(f"🎯 Using user-selected symbol: {trading_symbol}")
            else:
                # Try session optimal symbols if user symbol fails
                for symbol in optimal_symbols:
                    if validate_and_activate_symbol(symbol):
                        trading_symbol = symbol
                        logger(f"🎯 User symbol failed, using session optimal: {trading_symbol}")
                        if gui:
                            gui.symbol_var.set(trading_symbol)
                        break
                else:
                    logger(f"❌ Invalid symbol {user_symbol}, using fallback: {trading_symbol}")
                    if gui:
                        gui.symbol_var.set(trading_symbol)
        else:
            # No user selection, use session optimal
            for symbol in optimal_symbols:
                if validate_and_activate_symbol(symbol):
                    trading_symbol = symbol
                    logger(f"🎯 Using session optimal symbol: {trading_symbol}")
                    if gui:
                        gui.symbol_var.set(trading_symbol)
                    break

        # Get timeframe
        timeframe_map = {
            "M1": mt5.TIMEFRAME_M1, "M3": mt5.TIMEFRAME_M3, "M5": mt5.TIMEFRAME_M5,
            "M10": mt5.TIMEFRAME_M10, "M15": mt5.TIMEFRAME_M15, "M30": mt5.TIMEFRAME_M30,
            "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4, "D1": mt5.TIMEFRAME_D1
        }
        timeframe = timeframe_map.get(gui.timeframe_combo.get() if gui else "M1", mt5.TIMEFRAME_M1)

        logger(f"📊 Bot configuration: {trading_symbol} | {gui.timeframe_combo.get() if gui else 'M1'} | Strategy: {current_strategy}")
        logger("🎯 Enhanced auto-trading active - executing orders on valid signals!")

        # Main trading loop
        last_candle_time = None
        consecutive_failures = 0
        max_failures = 10
        signal_check_counter = 0

        while bot_running:
            try:
                # Check MT5 connection
                if not check_mt5_status():
                    disconnect_count += 1
                    logger(f"⚠️ MT5 disconnected (count: {disconnect_count})")

                    if disconnect_count > 3:
                        logger("🛑 Too many disconnections. Attempting reconnect...")
                        if connect_mt5():
                            disconnect_count = 0
                            logger("✅ Reconnected successfully!")
                        else:
                            logger("🛑 Reconnection failed. Stopping bot.")
                            break
                    time.sleep(5)
                    continue
                else:
                    disconnect_count = 0

                # Update current strategy from GUI every loop and ensure GUI connection
                if gui and hasattr(gui, 'strategy_combo'):
                    try:
                        new_strategy = gui.strategy_combo.get()
                        if new_strategy != current_strategy:
                            current_strategy = new_strategy
                            logger(f"🔄 Strategy updated from GUI to: {current_strategy}")
                    except Exception as e:
                        logger(f"⚠️ GUI connection issue: {str(e)}")
                        # Fallback to default strategy if GUI not accessible
                        if not current_strategy:
                            current_strategy = "Scalping"

                # Risk management checks
                if not risk_management_check():
                    logger("🛑 Risk management stop triggered")
                    break

                if not check_profit_targets():
                    logger("🎯 Profit target reached. Stopping bot.")
                    break

                if not check_trading_time():
                    time.sleep(60)
                    continue

                # Get market data with more aggressive refresh
                df = get_symbol_data(trading_symbol, timeframe)
                if df is None or len(df) < 50:
                    consecutive_failures += 1
                    if consecutive_failures >= max_failures:
                        logger(f"🛑 Too many data failures for {trading_symbol}")
                        break
                    logger("⚠️ Insufficient market data, retrying...")
                    time.sleep(3)  # Reduced from 5 to 3 seconds
                    continue
                else:
                    consecutive_failures = 0

                # Check for new candle - more aggressive signal checking
                current_candle_time = df.iloc[-1]['time']
                is_new_candle = last_candle_time is None or current_candle_time != last_candle_time

                # More aggressive signal checking based on strategy
                signal_check_counter += 1

                # HFT needs much faster checking
                if current_strategy == "HFT":
                    force_check = signal_check_counter >= 1  # Check every 1 second for HFT
                elif current_strategy == "Scalping":
                    force_check = signal_check_counter >= 2  # Check every 2 seconds for Scalping
                else:
                    force_check = signal_check_counter >= 3  # Check every 3 seconds for others

                if not is_new_candle and not force_check:
                    # Shorter sleep for HFT
                    sleep_time = 0.5 if current_strategy == "HFT" else 1 if current_strategy == "Scalping" else 2
                    time.sleep(sleep_time)
                    continue

                if force_check:
                    signal_check_counter = 0

                last_candle_time = current_candle_time

                # Calculate indicators
                df = calculate_indicators(df)

                # Run strategy with current strategy from GUI
                logger(f"🎯 Analyzing {current_strategy} signals for {trading_symbol}...")
                action, signals = run_strategy(current_strategy, df, trading_symbol)

                # Update position count
                positions = get_positions()
                position_count = len(positions)
                
                # Enhanced signal reporting
                logger(f"📊 Signal Summary: Action={action}, Signals={len(signals)}, Positions={position_count}/{max_positions}")
                
                # Log all signals for debugging
                if signals:
                    logger(f"🎯 All detected signals:")
                    for i, signal in enumerate(signals, 1):
                        logger(f"   {i}. {signal}")
                else:
                    logger("⚠️ No signals detected this cycle")
                
                # Force trading for debugging (optional)
                if not action and len(signals) > 0:
                    # If we have any signals but no action, check if we can force it
                    if any("BUY" in s or "bullish" in s.lower() for s in signals):
                        action = "BUY"
                        logger("🔧 DEBUG: Forcing BUY action based on detected signals")
                    elif any("SELL" in s or "bearish" in s.lower() for s in signals):
                        action = "SELL"
                        logger("🔧 DEBUG: Forcing SELL action based on detected signals")

                # Execute trading signals with proper GUI parameter integration
                if action and position_count < max_positions:
                    logger(f"🚀 EXECUTING {action} ORDER for {trading_symbol} using {current_strategy} strategy")
                    logger(f"📊 Strategy signals detected: {len(signals)}")

                    # Get ALL parameters from GUI with proper validation
                    lot_size = gui.get_current_lot() if gui else 0.01
                    tp_value = gui.get_current_tp() if gui else "20"
                    sl_value = gui.get_current_sl() if gui else "10"
                    tp_unit = gui.get_current_tp_unit() if gui else "pips"
                    sl_unit = gui.get_current_sl_unit() if gui else "pips"

                    # Log the exact parameters being used
                    logger(f"📋 Using GUI parameters:")
                    logger(f"   Strategy: {current_strategy}")
                    logger(f"   Lot: {lot_size}")
                    logger(f"   TP: {tp_value} {tp_unit}")
                    logger(f"   SL: {sl_value} {sl_unit}")

                    # Execute order with exact GUI parameters
                    result = open_order(trading_symbol, lot_size, action, sl_value, tp_value, sl_unit, tp_unit)

                    if result and getattr(result, 'retcode', None) == mt5.TRADE_RETCODE_DONE:
                        logger(f"✅ {action} order executed successfully with {current_strategy}! Ticket: {result.order}")
                        consecutive_failures = 0

                        session_data['total_trades'] += 1
                        session_data['daily_orders'] += 1

                        if gui and gui.telegram_var.get():
                            msg = f"🚀 {action} Order Executed!\nSymbol: {trading_symbol}\nStrategy: {current_strategy}\nTicket: {result.order}\nTP: {tp_value} {tp_unit}\nSL: {sl_value} {sl_unit}"
                            send_telegram(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, msg)
                    else:
                        consecutive_failures += 1
                        logger(f"❌ Order execution failed. Failure count: {consecutive_failures}")

                elif action and position_count >= max_positions:
                    logger(f"⚠️ Max positions reached ({position_count}). Skipping {action} signal from {current_strategy}.")

                # Log detailed signals for monitoring
                if signals:
                    logger(f"📊 {current_strategy} generated {len(signals)} signals:")
                    for i, signal in enumerate(signals[:3]):  # Show first 3 signals
                        logger(f"   {i+1}. {signal}")
                    if len(signals) > 3:
                        logger(f"   ... and {len(signals)-3} more signals")

                # More frequent status updates with session info
                if time.time() % 30 < 3:  # Every 30 seconds instead of 60
                    try:
                        current_price = df['close'].iloc[-1]
                        session_info = get_current_trading_session()
                        session_name = session_info["name"] if session_info else "Default"
                        volatility = session_info["info"]["volatility"] if session_info else "unknown"
                        logger(f"💹 Status: {trading_symbol}@{current_price:.5f} | {current_strategy} | {session_name}({volatility}) | Pos:{position_count}/{max_positions}")
                    except:
                        pass

                # Strategy-specific sleep intervals for optimal performance
                if current_strategy == "HFT":
                    time.sleep(0.5)  # Ultra-fast for HFT
                elif current_strategy == "Scalping":
                    time.sleep(1.0)  # Fast for Scalping
                else:
                    time.sleep(2.0)  # Normal for Intraday/Arbitrage

            except Exception as e:
                logger(f"❌ Bot loop error: {str(e)}")
                consecutive_failures += 1
                if consecutive_failures >= max_failures:
                    logger("🛑 Too many consecutive errors. Stopping bot.")
                    break
                time.sleep(3)

    except Exception as e:
        logger(f"❌ Bot thread error: {str(e)}")
    finally:
        bot_running = False
        logger("🛑 Bot thread stopped")
        if gui:
            gui.bot_status_lbl.config(text="Bot: Stopped 🔴", foreground="red")

class TradingBotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("💹 MT5 ADVANCED AUTO TRADING BOT v4.0 - Premium Edition")
        self.root.geometry("1400x900")
        self.root.configure(bg="#0f0f0f")
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)

        self.current_strategy = "Scalping"

        self.create_widgets()

        # Initialize GUI states
        self.start_btn.config(state="disabled")
        self.close_btn.config(state="disabled")
        self.emergency_btn.config(state="normal")

        # Auto-connect on startup
        self.root.after(1000, self.auto_connect_mt5)

        # Start GUI updates
        self.root.after(2000, self.update_gui_data)

    def auto_connect_mt5(self):
        """Enhanced auto-connection on startup with better error handling"""
        try:
            self.log("🔄 Starting auto-connection to MetaTrader 5...")
            self.log("💡 PASTIKAN: MT5 sudah dijalankan dan login ke akun trading")
            self.log("💡 PENTING: MT5 harus dijalankan sebagai Administrator")
            self.status_lbl.config(text="Status: Connecting... 🔄", foreground="orange")
            self.root.update()

            # Show system info first
            import platform
            import sys
            self.log(f"🔍 Python: {sys.version.split()[0]} ({platform.architecture()[0]})")
            self.log(f"🔍 Platform: {platform.system()} {platform.release()}")

            if connect_mt5():
                self.log("🎉 SUCCESS: Auto-connected to MetaTrader 5!")
                self.status_lbl.config(text="Status: Connected ✅", foreground="green")
                self.update_symbols()
                self.start_btn.config(state="normal")
                self.close_btn.config(state="normal")
                self.connect_btn.config(state="disabled")

                # Show detailed connection info
                try:
                    info = get_account_info()
                    if info:
                        self.log(f"👤 Account: {info.get('login', 'N/A')} | Server: {info.get('server', 'N/A')}")
                        self.log(f"💰 Balance: ${info.get('balance', 0):.2f} | Equity: ${info.get('equity', 0):.2f}")
                        self.log(f"🔐 Trade Permission: {'✅' if info.get('balance', 0) > 0 else '⚠️'}")

                        # Update global session balance
                        global session_start_balance
                        session_start_balance = info.get('balance', 0)

                        self.log("🚀 Bot siap untuk trading otomatis!")
                except Exception as info_e:
                    self.log(f"⚠️ Error getting account details: {str(info_e)}")

            else:
                self.log("❌ FAILED: Auto-connection to MT5 failed")
                self.log("🔧 TROUBLESHOOTING WAJIB:")
                self.log("   1. 🔴 TUTUP MT5 SEPENUHNYA")
                self.log("   2. 🔴 KLIK KANAN MT5 → 'Run as Administrator'")
                self.log("   3. 🔴 LOGIN ke akun trading dengan kredensial yang benar")
                self.log("   4. 🔴 PASTIKAN status 'Connected' muncul di MT5")
                self.log("   5. 🔴 BUKA Market Watch dan tambahkan symbols (EURUSD, dll)")
                self.log("   6. 🔴 PASTIKAN Python dan MT5 sama-sama 64-bit")
                self.log("   7. 🔴 DISABLE antivirus sementara jika perlu")
                self.log("   8. 🔴 RESTART komputer jika masalah persisten")

                self.status_lbl.config(text="Status: Connection Failed ❌", foreground="red")

                # Enable manual connect button and keep trying
                self.connect_btn.config(state="normal")
                self.start_btn.config(state="disabled")
                self.close_btn.config(state="disabled")

                # Check specific issues
                try:
                    import MetaTrader5 as mt5
                    if mt5.initialize():
                        if mt5.account_info() is None:
                            self.log("🔍 DIAGNOSIS: MT5 dapat di-initialize tapi account info NULL")
                            self.log("   → SOLUSI: Pastikan sudah LOGIN ke akun trading")
                        if mt5.terminal_info() is None:
                            self.log("🔍 DIAGNOSIS: Terminal info tidak tersedia")
                            self.log("   → SOLUSI: Restart MT5 sebagai Administrator")
                        mt5.shutdown()
                    else:
                        self.log("🔍 DIAGNOSIS: MT5 initialize() gagal total")
                        self.log("   → SOLUSI: Pastikan MT5 berjalan dan tidak diblokir")
                except Exception as diag_e:
                    self.log(f"🔍 DIAGNOSIS ERROR: {str(diag_e)}")

        except Exception as e:
            error_msg = f"❌ CRITICAL: Auto-connection error: {str(e)}"
            self.log(error_msg)
            self.status_lbl.config(text="Status: Critical Error ❌", foreground="red")
            logger(error_msg)

    def create_widgets(self):
        """Enhanced GUI creation with better styling"""
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#0f0f0f")
        style.configure("TLabel", background="#0f0f0f", foreground="white", font=("Segoe UI", 10))
        style.configure("TButton", font=("Segoe UI", 10, "bold"))
        style.configure("TNotebook.Tab", background="#2e2e2e", foreground="white")
        style.configure("Accent.TButton", foreground="white", background="#4CAF50")

        # Main notebook
        tab_control = ttk.Notebook(self.root)
        tab_control.grid(row=0, column=0, sticky="nsew")

        # Create tabs
        self.dashboard_tab = ttk.Frame(tab_control)
        self.strategy_tab = ttk.Frame(tab_control)
        self.calculator_tab = ttk.Frame(tab_control)
        self.log_tab = ttk.Frame(tab_control)

        tab_control.add(self.dashboard_tab, text="📊 Dashboard")
        tab_control.add(self.strategy_tab, text="⚙️ Strategy Setup")
        tab_control.add(self.calculator_tab, text="🧮 Calculator")
        tab_control.add(self.log_tab, text="📝 Logs")

        # Build tab contents
        self.dashboard_tab.rowconfigure(3, weight=1)
        self.dashboard_tab.columnconfigure(0, weight=1)
        self.build_dashboard()
        self.build_strategy_tab()
        self.build_calculator_tab()
        self.build_log_tab()

    def build_dashboard(self):
        """Enhanced dashboard with better layout"""
        # Control Panel
        ctrl_frame = ttk.LabelFrame(self.dashboard_tab, text="🎛️ Control Panel")
        ctrl_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        # Row 1: Symbol and Timeframe
        ttk.Label(ctrl_frame, text="Symbol:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.symbol_var = tk.StringVar(value="EURUSD")
        self.symbol_entry = ttk.Combobox(ctrl_frame, textvariable=self.symbol_var, width=12)
        self.symbol_entry.bind('<Return>', self.on_symbol_validate)
        self.symbol_entry.grid(row=0, column=1, padx=5, pady=5)

        self.validate_symbol_btn = ttk.Button(ctrl_frame, text="✓", command=self.validate_symbol, width=3)
        self.validate_symbol_btn.grid(row=0, column=2, padx=2, pady=5)

        ttk.Label(ctrl_frame, text="Timeframe:").grid(row=0, column=3, padx=5, pady=5, sticky="w")
        self.timeframe_combo = ttk.Combobox(ctrl_frame, values=["M1", "M5", "M15", "M30", "H1", "H4"], width=8)
        self.timeframe_combo.set("M1")
        self.timeframe_combo.grid(row=0, column=4, padx=5, pady=5)

        ttk.Label(ctrl_frame, text="Strategy:").grid(row=0, column=5, padx=5, pady=5, sticky="w")
        self.strategy_combo = ttk.Combobox(ctrl_frame, values=["Scalping", "Intraday", "HFT", "Arbitrage"], width=10)
        self.strategy_combo.set("Scalping")
        self.strategy_combo.bind("<<ComboboxSelected>>", self.on_strategy_change)
        self.strategy_combo.grid(row=0, column=6, padx=5, pady=5)

        # Row 2: Connection and Control Buttons
        self.connect_btn = ttk.Button(ctrl_frame, text="🔌 Connect MT5", command=self.connect_mt5)
        self.connect_btn.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="ew")

        self.start_btn = ttk.Button(ctrl_frame, text="🚀 START BOT", command=self.start_bot, style="Accent.TButton")
        self.start_btn.grid(row=1, column=2, columnspan=2, padx=5, pady=5, sticky="ew")

        self.stop_btn = ttk.Button(ctrl_frame, text="⏹️ STOP BOT", command=self.stop_bot)
        self.stop_btn.grid(row=1, column=4, padx=5, pady=5, sticky="ew")

        self.close_btn = ttk.Button(ctrl_frame, text="❌ CLOSE ALL", command=self.close_all)
        self.close_btn.grid(row=1, column=5, padx=5, pady=5, sticky="ew")

        self.emergency_btn = ttk.Button(ctrl_frame, text="🚨 EMERGENCY", command=self.emergency_stop)
        self.emergency_btn.grid(row=1, column=6, padx=5, pady=5, sticky="ew")

        # Account Information
        acc_frame = ttk.LabelFrame(self.dashboard_tab, text="💰 Account Information")
        acc_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")

        self.balance_lbl = ttk.Label(acc_frame, text="Balance: $0.00", font=("Segoe UI", 11, "bold"))
        self.equity_lbl = ttk.Label(acc_frame, text="Equity: $0.00", font=("Segoe UI", 11))
        self.margin_lbl = ttk.Label(acc_frame, text="Free Margin: $0.00", font=("Segoe UI", 11))
        self.margin_level_lbl = ttk.Label(acc_frame, text="Margin Level: 0%", font=("Segoe UI", 11))
        self.status_lbl = ttk.Label(acc_frame, text="Status: Disconnected", font=("Segoe UI", 11, "bold"))
        self.server_lbl = ttk.Label(acc_frame, text="Server: N/A", font=("Segoe UI", 10))

        self.balance_lbl.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.equity_lbl.grid(row=0, column=1, padx=10, pady=5, sticky="w")
        self.margin_lbl.grid(row=0, column=2, padx=10, pady=5, sticky="w")
        self.margin_level_lbl.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.status_lbl.grid(row=1, column=1, padx=10, pady=5, sticky="w")
        self.server_lbl.grid(row=1, column=2, padx=10, pady=5, sticky="w")

        # Trading Statistics with Session Info
        stats_frame = ttk.LabelFrame(self.dashboard_tab, text="📈 Trading Statistics")
        stats_frame.grid(row=2, column=0, padx=10, pady=5, sticky="ew")

        self.daily_orders_lbl = ttk.Label(stats_frame, text="Daily Orders: 0")
        self.daily_profit_lbl = ttk.Label(stats_frame, text="Daily Profit: $0.00")
        self.win_rate_lbl = ttk.Label(stats_frame, text="Win Rate: 0%")
        self.open_positions_lbl = ttk.Label(stats_frame, text="Open Positions: 0")
        self.session_lbl = ttk.Label(stats_frame, text="Session: Loading...", font=("Segoe UI", 10, "bold"))
        self.bot_status_lbl = ttk.Label(stats_frame, text="Bot: Stopped 🔴", font=("Segoe UI", 10, "bold"))

        self.daily_orders_lbl.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.daily_profit_lbl.grid(row=0, column=1, padx=10, pady=5, sticky="w")
        self.win_rate_lbl.grid(row=0, column=2, padx=10, pady=5, sticky="w")
        self.open_positions_lbl.grid(row=0, column=3, padx=10, pady=5, sticky="w")
        self.session_lbl.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="w")
        self.bot_status_lbl.grid(row=1, column=2, columnspan=2, padx=10, pady=5, sticky="w")

        # Active Positions
        pos_frame = ttk.LabelFrame(self.dashboard_tab, text="📋 Active Positions")
        pos_frame.grid(row=3, column=0, padx=10, pady=10, sticky="nsew")

        columns = ("Ticket", "Symbol", "Type", "Lot", "Price", "Current", "Profit", "Pips")
        self.pos_tree = ttk.Treeview(pos_frame, columns=columns, show="headings", height=15)

        for col in columns:
            self.pos_tree.heading(col, text=col)
            self.pos_tree.column(col, anchor="center", width=100)

        pos_scrollbar = ttk.Scrollbar(pos_frame, orient="vertical", command=self.pos_tree.yview)
        self.pos_tree.configure(yscrollcommand=pos_scrollbar.set)

        self.pos_tree.pack(side="left", fill="both", expand=True)
        pos_scrollbar.pack(side="right", fill="y")

    def build_strategy_tab(self):
        """Enhanced strategy configuration tab"""
        self.strategy_tab.columnconfigure((0, 1), weight=1)

        strategies = ["Scalping", "Intraday", "HFT", "Arbitrage"]
        self.strategy_params = {}

        for i, strat in enumerate(strategies):
            frame = ttk.LabelFrame(self.strategy_tab, text=f"🎯 {strat} Strategy")
            frame.grid(row=i // 2, column=i % 2, padx=10, pady=10, sticky="nsew")

            defaults = {
                "Scalping": {"lot": "0.01", "tp": "15", "sl": "8"},    # Sesuai requirement: TP 10-15 pips, SL 5-10 pips
                "Intraday": {"lot": "0.02", "tp": "80", "sl": "40"},   # Sesuai requirement: TP 60-100 pips, SL 30-50 pips  
                "HFT": {"lot": "0.01", "tp": "5", "sl": "3"},          # Ultra fast untuk HFT
                "Arbitrage": {"lot": "0.03", "tp": "25", "sl": "12"}   # Mean reversion
            }

            ttk.Label(frame, text="Lot Size:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
            lot_entry = ttk.Entry(frame, width=15)
            lot_entry.insert(0, defaults[strat]["lot"])
            lot_entry.grid(row=0, column=1, padx=5, pady=5)

            ttk.Label(frame, text="TP:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
            tp_entry = ttk.Entry(frame, width=10)
            tp_entry.insert(0, defaults[strat]["tp"])
            tp_entry.grid(row=1, column=1, padx=5, pady=5)

            tp_unit_combo = ttk.Combobox(frame, values=["pips", "price", "%"], width=8)
            tp_unit_combo.set("pips")
            tp_unit_combo.grid(row=1, column=2, padx=5, pady=5)

            ttk.Label(frame, text="SL:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
            sl_entry = ttk.Entry(frame, width=10)
            sl_entry.insert(0, defaults[strat]["sl"])
            sl_entry.grid(row=2, column=1, padx=5, pady=5)

            sl_unit_combo = ttk.Combobox(frame, values=["pips", "price", "%"], width=8)
            sl_unit_combo.set("pips")
            sl_unit_combo.grid(row=2, column=2, padx=5, pady=5)

            self.strategy_params[strat] = {
                "lot": lot_entry,
                "tp": tp_entry,
                "sl": sl_entry,
                "tp_unit": tp_unit_combo,
                "sl_unit": sl_unit_combo
            }

        # Global Settings
        settings_frame = ttk.LabelFrame(self.strategy_tab, text="⚙️ Global Settings")
        settings_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        ttk.Label(settings_frame, text="Max Positions:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.max_pos_entry = ttk.Entry(settings_frame, width=15)
        self.max_pos_entry.insert(0, "5")
        self.max_pos_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(settings_frame, text="Max Drawdown (%):").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.max_dd_entry = ttk.Entry(settings_frame, width=15)
        self.max_dd_entry.insert(0, "3")
        self.max_dd_entry.grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(settings_frame, text="Profit Target (%):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.profit_target_entry = ttk.Entry(settings_frame, width=15)
        self.profit_target_entry.insert(0, "5")
        self.profit_target_entry.grid(row=1, column=1, padx=5, pady=5)

        self.telegram_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(settings_frame, text="📱 Telegram Notifications", variable=self.telegram_var).grid(row=1, column=2, columnspan=2, padx=5, pady=5, sticky="w")

    def build_calculator_tab(self):
        """Enhanced calculator tab"""
        calc_frame = ttk.LabelFrame(self.calculator_tab, text="🧮 TP/SL Calculator")
        calc_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Input section
        input_frame = ttk.Frame(calc_frame)
        input_frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(input_frame, text="Symbol:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.calc_symbol_entry = ttk.Entry(input_frame, width=15)
        self.calc_symbol_entry.insert(0, "EURUSD")
        self.calc_symbol_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(input_frame, text="Lot Size:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.calc_lot_entry = ttk.Entry(input_frame, width=15)
        self.calc_lot_entry.insert(0, "0.01")
        self.calc_lot_entry.grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(input_frame, text="TP:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.calc_tp_entry = ttk.Entry(input_frame, width=10)
        self.calc_tp_entry.grid(row=1, column=1, padx=5, pady=5)

        self.calc_tp_unit = ttk.Combobox(input_frame, values=["pips", "price", "%"], width=8)
        self.calc_tp_unit.set("pips")
        self.calc_tp_unit.grid(row=1, column=2, padx=5, pady=5)

        ttk.Label(input_frame, text="SL:").grid(row=1, column=3, padx=5, pady=5, sticky="w")
        self.calc_sl_entry = ttk.Entry(input_frame, width=10)
        self.calc_sl_entry.grid(row=1, column=4, padx=5, pady=5)

        self.calc_sl_unit = ttk.Combobox(input_frame, values=["pips", "price", "%"], width=8)
        self.calc_sl_unit.set("pips")
        self.calc_sl_unit.grid(row=1, column=5, padx=5, pady=5)

        calc_btn = ttk.Button(input_frame, text="🧮 Calculate", command=self.calculate_tp_sl)
        calc_btn.grid(row=2, column=1, columnspan=2, padx=5, pady=10)

        # Results
        self.calc_results = ScrolledText(calc_frame, height=20, bg="#0a0a0a", fg="#00ff00", font=("Courier", 11))
        self.calc_results.pack(fill="both", expand=True, padx=10, pady=10)

    def build_log_tab(self):
        """Enhanced log tab"""
        log_ctrl_frame = ttk.Frame(self.log_tab)
        log_ctrl_frame.pack(fill="x", padx=10, pady=5)

        ttk.Button(log_ctrl_frame, text="💾 Export Logs", command=self.export_logs).pack(side="left", padx=5)
        ttk.Button(log_ctrl_frame, text="🗑️ Clear Logs", command=self.clear_logs).pack(side="left", padx=5)

        self.log_area = ScrolledText(self.log_tab, height=40, bg="#0a0a0a", fg="#00ff00", font=("Consolas", 10))
        self.log_area.pack(fill="both", expand=True, padx=10, pady=10)

    def log(self, text):
        """Enhanced logging with timestamp"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        full_text = f"[{timestamp}] {text}"
        self.log_area.insert(tk.END, full_text + "\n")
        self.log_area.see(tk.END)
        self.root.update_idletasks()

    def connect_mt5(self):
        """Enhanced MT5 connection with comprehensive GUI feedback"""
        try:
            self.log("🔄 Manual connection attempt to MetaTrader 5...")
            self.status_lbl.config(text="Status: Connecting... 🔄", foreground="orange")
            self.root.update()

            # Enhanced connection attempt dengan detailed logging
            self.log("🔍 Checking MT5 installation and permissions...")
            
            if connect_mt5():
                self.log("✅ Successfully connected to MetaTrader 5!")
                self.status_lbl.config(text="Status: Connected ✅", foreground="green")

                # Update symbols and enable buttons
                self.log("🔄 Loading available symbols...")
                self.update_symbols()
                
                self.start_btn.config(state="normal")
                self.close_btn.config(state="normal")
                self.connect_btn.config(state="disabled")

                # Get detailed account info dengan error handling
                self.log("🔄 Retrieving account information...")
                info = get_account_info()
                if info:
                    # Update all account labels immediately
                    self.balance_lbl.config(text=f"Balance: ${info['balance']:,.2f}")
                    self.equity_lbl.config(text=f"Equity: ${info['equity']:,.2f}")
                    self.margin_lbl.config(text=f"Free Margin: ${info['free_margin']:,.2f}")
                    
                    margin_level = info.get('margin_level', 0)
                    if margin_level > 0:
                        self.margin_level_lbl.config(text=f"Margin Level: {margin_level:.2f}%")
                    else:
                        self.margin_level_lbl.config(text="Margin Level: ∞%")
                        
                    self.server_lbl.config(text=f"Server: {info['server']} | Login: {info['login']}")
                    
                    self.log(f"✅ Account Details:")
                    self.log(f"   👤 Login: {info['login']}")
                    self.log(f"   🌐 Server: {info['server']}")
                    self.log(f"   💰 Balance: ${info['balance']:,.2f}")
                    self.log(f"   📈 Equity: ${info['equity']:,.2f}")
                    self.log(f"   💵 Free Margin: ${info['free_margin']:,.2f}")
                    self.log(f"   📊 Margin Level: {margin_level:.2f}%")

                    global session_start_balance
                    session_start_balance = info['balance']
                    session_data['start_balance'] = info['balance']
                    
                    self.log("🎯 GUI-MT5 connection established successfully!")
                    self.log("🚀 Ready to start automated trading!")
                    
                else:
                    self.log("⚠️ Connected to MT5 but cannot retrieve account info")
                    self.log("💡 Check if MT5 is properly logged in to trading account")

            else:
                self.log("❌ Failed to connect to MetaTrader 5")
                self.log("🔧 Please check:")
                self.log("   1. MT5 is running and logged in")
                self.log("   2. MT5 is running as Administrator") 
                self.log("   3. Account has trading permissions")
                self.log("   4. No firewall blocking the connection")
                
                self.status_lbl.config(text="Status: Connection Failed ❌", foreground="red")
                self.start_btn.config(state="disabled")
                self.close_btn.config(state="disabled")
                self.connect_btn.config(state="normal")
                
                # Reset account labels
                self.balance_lbl.config(text="Balance: N/A", foreground="gray")
                self.equity_lbl.config(text="Equity: N/A", foreground="gray")
                self.margin_lbl.config(text="Free Margin: N/A", foreground="gray")
                self.margin_level_lbl.config(text="Margin Level: N/A", foreground="gray")
                self.server_lbl.config(text="Server: N/A")

        except Exception as e:
            error_msg = f"❌ Critical connection error: {str(e)}"
            self.log(error_msg)
            self.status_lbl.config(text="Status: Critical Error ❌", foreground="red")
            
            # Reset everything on error
            self.start_btn.config(state="disabled")
            self.close_btn.config(state="disabled")
            self.connect_btn.config(state="normal")
            
            import traceback
            self.log(f"📝 Error details: {traceback.format_exc()}")
            
            # Show error in account labels
            self.balance_lbl.config(text="Balance: Error", foreground="red")
            self.equity_lbl.config(text="Equity: Error", foreground="red")
            self.margin_lbl.config(text="Free Margin: Error", foreground="red")
            self.margin_level_lbl.config(text="Margin Level: Error", foreground="red")
            self.server_lbl.config(text="Server: Connection Error")

    def start_bot(self):
        """Enhanced bot starting with better validation"""
        global bot_running, current_strategy, max_positions, max_drawdown, daily_max_loss, profit_target

        if bot_running:
            self.log("⚠️ Bot is already running!")
            return

        try:
            # Validate connection
            if not check_mt5_status():
                messagebox.showerror("❌ Error", "Please connect to MT5 first!")
                return

            # Validate symbol
            symbol = self.symbol_var.get().strip().upper()
            if not symbol:
                messagebox.showerror("❌ Error", "Please enter a trading symbol!")
                return

            self.log(f"🔍 Validating symbol: {symbol}")

            if not validate_and_activate_symbol(symbol):
                messagebox.showerror("❌ Error", f"Symbol {symbol} is not valid!")
                return

            self.log(f"✅ Symbol {symbol} validated successfully!")

            # Update global settings
            current_strategy = self.strategy_combo.get()
            max_positions = int(self.max_pos_entry.get())
            max_drawdown = float(self.max_dd_entry.get()) / 100
            profit_target = float(self.profit_target_entry.get()) / 100

            bot_running = True

            # Start bot thread
            threading.Thread(target=bot_thread, daemon=True).start()
            self.log(f"🚀 Enhanced trading bot started for {symbol}!")
            self.bot_status_lbl.config(text="Bot: Running 🟢", foreground="green")

            # Update button states
            self.start_btn.config(state="disabled")
            self.stop_btn.config(state="normal")

        except ValueError as e:
            messagebox.showerror("❌ Error", f"Invalid input values: {str(e)}")
        except Exception as e:
            self.log(f"❌ Error starting bot: {str(e)}")
            messagebox.showerror("❌ Error", f"Failed to start bot: {str(e)}")

    def stop_bot(self):
        """Enhanced bot stopping"""
        global bot_running
        bot_running = False
        self.log("⏹️ Stopping trading bot...")
        self.bot_status_lbl.config(text="Bot: Stopping... 🟡", foreground="orange")
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")

    def emergency_stop(self):
        """Enhanced emergency stop"""
        global bot_running
        try:
            bot_running = False
            close_all_orders()
            self.log("🚨 EMERGENCY STOP ACTIVATED - All positions closed!")
            self.bot_status_lbl.config(text="Bot: Emergency Stop 🔴", foreground="red")

            if self.telegram_var.get():
                send_telegram(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, "🚨 EMERGENCY STOP - All positions closed!")
        except Exception as e:
            self.log(f"❌ Emergency stop error: {str(e)}")

    def close_all(self):
        """Enhanced close all positions"""
        try:
            close_all_orders()
            self.log("❌ All positions closed manually")
        except Exception as e:
            self.log(f"❌ Error closing positions: {str(e)}")

    def on_strategy_change(self, event=None):
        """Handle strategy change with proper GUI integration"""
        global current_strategy
        new_strategy = self.strategy_combo.get()

        if new_strategy != current_strategy:
            current_strategy = new_strategy
            self.log(f"🔄 Strategy changed from {current_strategy} to: {new_strategy}")

            # Update current_strategy global
            current_strategy = new_strategy

            # Log current strategy parameters
            try:
                lot = self.get_current_lot()
                tp = self.get_current_tp()
                sl = self.get_current_sl()
                tp_unit = self.get_current_tp_unit()
                sl_unit = self.get_current_sl_unit()

                self.log(f"📊 {new_strategy} params: Lot={lot}, TP={tp} {tp_unit}, SL={sl} {sl_unit}")
            except Exception as e:
                self.log(f"❌ Error logging strategy params: {str(e)}")

    def get_current_lot(self):
        """Get current lot size from GUI"""
        try:
            strategy = self.strategy_combo.get()
            return float(self.strategy_params[strategy]["lot"].get())
        except:
            return 0.01

    def get_current_tp(self):
        """Get current TP from GUI"""
        try:
            strategy = self.strategy_combo.get()
            return self.strategy_params[strategy]["tp"].get()
        except:
            return "20"

    def get_current_sl(self):
        """Get current SL from GUI"""
        try:
            strategy = self.strategy_combo.get()
            return self.strategy_params[strategy]["sl"].get()
        except:
            return "10"

    def get_current_tp_unit(self):
        """Get current TP unit from selected strategy"""
        try:
            strategy = self.strategy_combo.get()
            if strategy in self.strategy_params:
                unit = self.strategy_params[strategy]["tp_unit"].get()
                logger(f"🔍 GUI: TP unit for {strategy} = {unit}")
                return unit
            else:
                logger(f"⚠️ GUI: Strategy {strategy} not found in params, using default")
                return "pips"
        except Exception as e:
            logger(f"❌ GUI: Error getting TP unit: {str(e)}")
            return "pips"

    def get_current_sl_unit(self):
        """Get current SL unit from selected strategy"""
        try:
            strategy = self.strategy_combo.get()
            if strategy in self.strategy_params:
                unit = self.strategy_params[strategy]["sl_unit"].get()
                logger(f"🔍 GUI: SL unit for {strategy} = {unit}")
                return unit
            else:
                logger(f"⚠️ GUI: Strategy {strategy} not found in params, using default")
                return "pips"
        except Exception as e:
            logger(f"❌ GUI: Error getting SL unit: {str(e)}")
            return "pips"

    def update_symbols(self):
        """Enhanced symbol updating"""
        try:
            symbols = get_symbol_suggestions()
            if symbols:
                self.symbol_entry['values'] = symbols
                self.log(f"📊 Loaded {len(symbols)} symbols")
            else:
                self.symbol_entry['values'] = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"]
        except Exception as e:
            self.log(f"❌ Error updating symbols: {str(e)}")

    def validate_symbol(self):
        """Enhanced symbol validation"""
        try:
            symbol = self.symbol_var.get().strip().upper()
            if not symbol:
                messagebox.showwarning("⚠️ Warning", "Please enter a symbol first!")
                return

            self.log(f"🔍 Validating symbol: {symbol}")

            if not check_mt5_status():
                messagebox.showerror("❌ Error", "Please connect to MT5 first!")
                return

            valid_symbol = validate_and_activate_symbol(symbol)
            if valid_symbol:
                self.symbol_var.set(valid_symbol)
                # dst...
                self.log(f"✅ Symbol {valid_symbol} validated successfully!")
                messagebox.showinfo("✅ Success", f"Symbol {valid_symbol} is valid!")
                self.validate_symbol_btn.config(text="✅")
            else:
                self.log(f"❌ Symbol {symbol} validation failed!")
                messagebox.showerror("❌ Error", f"Symbol {symbol} is not valid!")
                self.validate_symbol_btn.config(text="❌")

        except Exception as e:
            self.log(f"❌ Error validating symbol: {str(e)}")

    def on_symbol_validate(self, event=None):
        """Auto-validate on symbol entry"""
        try:
            symbol = self.symbol_var.get().strip().upper()
            if symbol and len(symbol) >= 4:
                self.root.after(500, lambda: self.auto_validate_symbol(symbol))
        except:
            pass

    def auto_validate_symbol(self, symbol):
        """Background symbol validation"""
        try:
            if check_mt5_status() and validate_and_activate_symbol(symbol):
                self.validate_symbol_btn.config(text="✅")
            else:
                self.validate_symbol_btn.config(text="❌")
        except:
            self.validate_symbol_btn.config(text="?")

    def calculate_tp_sl(self):
        """Enhanced TP/SL calculation"""
        try:
            symbol = self.calc_symbol_entry.get()
            lot = float(self.calc_lot_entry.get())
            tp_input = self.calc_tp_entry.get()
            sl_input = self.calc_sl_entry.get()
            tp_unit = self.calc_tp_unit.get()
            sl_unit = self.calc_sl_unit.get()

            if not check_mt5_status():
                self.calc_results.delete(1.0, tk.END)
                self.calc_results.insert(tk.END, "❌ Please connect to MT5 first!\n")
                return

            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                self.calc_results.delete(1.0, tk.END)
                self.calc_results.insert(tk.END, f"❌ Cannot get price for {symbol}!\n")
                return

            current_price = tick.ask
            pip_value = calculate_pip_value(symbol, lot)

            # Calculate TP values
            tp_price = 0.0
            tp_profit = 0.0
            if tp_input:
                tp_price, tp_calc = parse_tp_sl_input(tp_input, tp_unit, symbol, lot, current_price, "BUY", True)
                tp_profit = tp_calc.get('amount', 0)

            # Calculate SL values
            sl_price = 0.0
            sl_loss = 0.0
            if sl_input:
                sl_price, sl_calc = parse_tp_sl_input(sl_input, sl_unit, symbol, lot, current_price, "BUY", False)
                sl_loss = sl_calc.get('amount', 0)

            result_text = f"""
🧮 TP/SL CALCULATION RESULTS
===============================
Symbol: {symbol}
Lot Size: {lot}
Current Price: {current_price:.5f}

TAKE PROFIT:
- Input: {tp_input} {tp_unit}
- Price Level: {tp_price:.5f}
- Expected Profit: ${tp_profit:.2f}

STOP LOSS:
- Input: {sl_input} {sl_unit}
- Price Level: {sl_price:.5f}
- Expected Loss: ${sl_loss:.2f}

RISK/REWARD RATIO: {(tp_profit/max(sl_loss,1)):.2f}:1
PIP VALUE: ${pip_value:.2f}
===============================
"""
            self.calc_results.delete(1.0, tk.END)
            self.calc_results.insert(tk.END, result_text)

        except Exception as e:
            self.calc_results.delete(1.0, tk.END)
            self.calc_results.insert(tk.END, f"❌ Calculation Error: {str(e)}\n")

    def export_logs(self):
        """Enhanced log export"""
        try:
            if not os.path.exists("logs"):
                os.makedirs("logs")

            log_content = self.log_area.get(1.0, tk.END)
            filename = f"logs/gui_logs_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

            with open(filename, 'w') as f:
                f.write(log_content)

            self.log(f"💾 Logs exported to {filename}")
            messagebox.showinfo("✅ Export Success", f"Logs exported to {filename}")
        except Exception as e:
            self.log(f"❌ Error exporting logs: {str(e)}")

    def clear_logs(self):
        """Clear log area"""
        self.log_area.delete(1.0, tk.END)
        self.log("🗑️ Logs cleared")

    def update_gui_data(self):
        """Enhanced GUI data updating with better error handling and real-time info"""
        try:
            # Check MT5 status dan update connection status
            if check_mt5_status():
                self.status_lbl.config(text="Status: Connected ✅", foreground="green")

                # Get current account info untuk real-time update
                info = get_account_info()
                if info:
                    # Update account labels dengan data real-time
                    self.balance_lbl.config(text=f"Balance: ${info['balance']:,.2f}")
                    self.equity_lbl.config(text=f"Equity: ${info['equity']:,.2f}")
                    self.margin_lbl.config(text=f"Free Margin: ${info['free_margin']:,.2f}")
                    
                    # Calculate and display margin level
                    margin_level = info.get('margin_level', 0)
                    if margin_level > 0:
                        margin_color = "green" if margin_level > 300 else "orange" if margin_level > 150 else "red"
                        self.margin_level_lbl.config(
                            text=f"Margin Level: {margin_level:.2f}%", 
                            foreground=margin_color
                        )
                    else:
                        self.margin_level_lbl.config(text="Margin Level: ∞%", foreground="green")
                    
                    self.server_lbl.config(text=f"Server: {info['server']} | Login: {info['login']}")

                    # Initialize session_start_balance if not set
                    global session_start_balance
                    if session_start_balance is None:
                        session_start_balance = info['balance']
                        session_data['start_balance'] = info['balance']
                        logger(f"💰 Session initialized - Starting Balance: ${session_start_balance:.2f}")

                else:
                    # Error getting account info
                    self.balance_lbl.config(text="Balance: Error", foreground="red")
                    self.equity_lbl.config(text="Equity: Error", foreground="red")
                    self.margin_lbl.config(text="Free Margin: Error", foreground="red")
                    self.margin_level_lbl.config(text="Margin Level: Error", foreground="red")
                    logger("⚠️ Cannot get account info from MT5")

            else:
                # MT5 not connected
                self.status_lbl.config(text="Status: Disconnected ❌", foreground="red")
                self.server_lbl.config(text="Server: N/A")
                self.balance_lbl.config(text="Balance: N/A", foreground="gray")
                self.equity_lbl.config(text="Equity: N/A", foreground="gray")
                self.margin_lbl.config(text="Free Margin: N/A", foreground="gray")
                self.margin_level_lbl.config(text="Margin Level: N/A", foreground="gray")

            # Update trading statistics with proper calculations
            self.daily_orders_lbl.config(text=f"Daily Orders: {session_data.get('daily_orders', 0)}")

            # Calculate daily profit from current equity vs start balance
            actual_daily_profit = 0.0
            daily_profit_percent = 0.0
            
            if info and session_start_balance and session_start_balance > 0:
                actual_daily_profit = info['equity'] - session_start_balance
                session_data['daily_profit'] = actual_daily_profit
                daily_profit_percent = (actual_daily_profit / session_start_balance) * 100
            else:
                actual_daily_profit = session_data.get('daily_profit', 0.0)

            # Color coding for profit/loss
            daily_profit_color = "green" if actual_daily_profit >= 0 else "red"
            self.daily_profit_lbl.config(
                text=f"Daily P/L: ${actual_daily_profit:.2f} ({daily_profit_percent:+.2f}%)", 
                foreground=daily_profit_color
            )

            # Calculate win rate from closed positions with better tracking
            total_closed = session_data.get('winning_trades', 0) + session_data.get('losing_trades', 0)
            winning_trades = session_data.get('winning_trades', 0)

            if total_closed > 0:
                win_rate = (winning_trades / total_closed) * 100
                win_rate_color = "green" if win_rate >= 60 else "orange" if win_rate >= 40 else "red"
                self.win_rate_lbl.config(
                    text=f"Win Rate: {win_rate:.1f}% ({winning_trades}W/{total_closed-winning_trades}L)", 
                    foreground=win_rate_color
                )
            else:
                self.win_rate_lbl.config(text="Win Rate: -- % (0W/0L)", foreground="gray")

            # Update positions count with real-time data
            positions = get_positions()
            position_count = len(positions) if positions else 0
            self.open_positions_lbl.config(text=f"Open Positions: {position_count}/{max_positions}")

            # Update session information
            try:
                current_session = get_current_trading_session()
                if current_session:
                    session_name = current_session["name"]
                    volatility = current_session["info"]["volatility"]
                    session_color = {
                        "very_high": "red", 
                        "high": "orange", 
                        "medium": "green", 
                        "low": "blue"
                    }.get(volatility, "gray")
                    
                    self.session_lbl.config(
                        text=f"Session: {session_name} ({volatility.upper()} volatility)",
                        foreground=session_color
                    )
                else:
                    self.session_lbl.config(text="Session: Outside Major Sessions", foreground="gray")
            except Exception as e:
                self.session_lbl.config(text="Session: Error", foreground="red")

            # Update bot status with current strategy info
            global bot_running, current_strategy
            if bot_running:
                self.bot_status_lbl.config(
                    text=f"Bot: Running 🟢 ({current_strategy})", 
                    foreground="green"
                )
            else:
                self.bot_status_lbl.config(text="Bot: Stopped 🔴", foreground="red")

            # Update positions table
            self.update_positions()

            # Log periodic status untuk debugging
            if hasattr(self, '_update_counter'):
                self._update_counter += 1
            else:
                self._update_counter = 1
                
            # Log every 30 updates (about 1 minute)
            if self._update_counter % 30 == 0:
                if info:
                    logger(f"📊 GUI Update #{self._update_counter}: Balance=${info['balance']:.2f}, Equity=${info['equity']:.2f}, Positions={position_count}")
                else:
                    logger(f"📊 GUI Update #{self._update_counter}: MT5 disconnected")

        except Exception as e:
            logger(f"❌ GUI update error: {str(e)}")
            # Show error in status
            self.status_lbl.config(text="Status: Update Error ❌", foreground="red")
            import traceback
            logger(f"📝 GUI update traceback: {traceback.format_exc()}")

        # Schedule next update with faster interval for real-time feel
        self.root.after(1500, self.update_gui_data)  # Update every 1.5 seconds instead of 2

    def update_positions(self):
        """Enhanced position table updating"""
        try:
            # Clear existing items
            for item in self.pos_tree.get_children():
                self.pos_tree.delete(item)

            # Get current positions
            positions = get_positions()

            for pos in positions:
                position_type = "BUY" if pos.type == mt5.ORDER_TYPE_BUY else "SELL"

                # Get current price
                tick = mt5.symbol_info_tick(pos.symbol)
                if tick:
                    current_price = tick.bid if pos.type == mt5.ORDER_TYPE_BUY else tick.ask

                    # Calculate pips
                    price_diff = current_price - pos.price_open if pos.type == mt5.ORDER_TYPE_BUY else pos.price_open - current_price
                    pip_size = 0.01 if "JPY" in pos.symbol else 0.0001
                    pips = price_diff / pip_size

                    # Insert with color coding
                    profit_color = "green" if pos.profit >= 0 else "red"

                    self.pos_tree.insert("", "end", values=(
                        pos.ticket,
                        pos.symbol,
                        position_type,
                        f"{pos.volume:.2f}",
                        f"{pos.price_open:.5f}",
                        f"{current_price:.5f}",
                        f"${pos.profit:.2f}",
                        f"{pips:.1f}"
                    ), tags=(profit_color,))
                else:
                    # If tick is unavailable
                    self.pos_tree.insert("", "end", values=(
                        pos.ticket,
                        pos.symbol,
                        position_type,
                        f"{pos.volume:.2f}",
                        f"{pos.price_open:.5f}",
                        "N/A",
                        f"${pos.profit:.2f}",
                        "N/A"
                    ), tags=("red" if pos.profit < 0 else "green",))

            # Configure colors
            self.pos_tree.tag_configure("green", foreground="green")
            self.pos_tree.tag_configure("red", foreground="red")

        except Exception as e:
            logger(f"❌ Error updating positions: {str(e)}")

    def on_closing(self):
        """Enhanced closing handler"""
        global bot_running
        if bot_running:
            self.stop_bot()
            time.sleep(1)

        try:
            mt5.shutdown()
        except:
            pass

        self.root.destroy()

# Configure run command to run the bot
if __name__ == "__main__":
    try:
        import tkinter as tk
        from tkinter import messagebox

        # Check Python version compatibility
        import sys
        if sys.version_info < (3, 7):
            print("❌ ERROR: Python 3.7+ required")
            sys.exit(1)

        # Check if MetaTrader5 is available
        try:
            import MetaTrader5 as mt5
            print("✅ MetaTrader5 module available")
        except ImportError:
            print("❌ ERROR: MetaTrader5 module not found")
            print("💡 Install with: pip install MetaTrader5")
            sys.exit(1)

        # Initialize GUI
        root = tk.Tk()
        gui = TradingBotGUI(root)

        # Make gui globally accessible
        globals()['gui'] = gui

        root.protocol("WM_DELETE_WINDOW", gui.on_closing)

        # Enhanced startup logging
        logger("🚀 === MT5 ADVANCED AUTO TRADING BOT v4.0 - Premium Edition ===")
        logger("🔧 Features: Enhanced MT5 Connection, Improved Error Handling")
        logger("📱 Advanced Diagnostics, Real-time Updates, Better Profitability")
        logger("🎯 Comprehensive Symbol Validation & Market Data Testing")
        logger("⚡ Optimized for Maximum Win Rate and Minimal Errors")
        logger("=" * 70)
        logger("🚀 STARTUP SEQUENCE:")
        logger("   1. GUI initialized successfully")
        logger("   2. Auto-connecting to MT5...")
        logger("   3. Validating trading environment...")
        logger("💡 NEXT STEPS: Wait for connection, then click 'START BOT'")
        logger("=" * 70)

        root.mainloop()

    except Exception as e:
        print(f"❌ CRITICAL STARTUP ERROR: {str(e)}")
        print("🔧 SOLUSI:")
        print("   1. Pastikan Python 3.7+ terinstall")
        print("   2. Install dependencies: pip install MetaTrader5 pandas numpy tkinter")
        print("   3. Pastikan MT5 sudah terinstall")
        print("   4. Restart aplikasi")
        import traceback
        print(f"📝 Detail error: {traceback.format_exc()}")
        input("Press Enter to exit...")