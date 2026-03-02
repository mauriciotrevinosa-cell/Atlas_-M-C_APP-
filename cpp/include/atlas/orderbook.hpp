/**
 * ATLAS — High Performance Order Book Engine
 * ============================================
 * L2 Order Book with nanosecond-level processing.
 * Designed for HFT signal generation and market microstructure analysis.
 *
 * Features:
 * - Price-level aggregated order book (L2)
 * - O(log n) insert/cancel/modify
 * - Real-time mid price, spread, imbalance, VWAP
 * - Snapshot export for Python integration
 *
 * Copyright (c) 2026 M&C. All rights reserved.
 */

#pragma once

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <map>
#include <string>
#include <vector>

namespace atlas {
namespace orderbook {

// ──────────────────────────────────────────────────────────────
// Types
// ──────────────────────────────────────────────────────────────

enum class Side : uint8_t { BID = 0, ASK = 1 };

struct PriceLevel {
    double price;
    double quantity;
    int    order_count;
    int64_t timestamp_ns;  // Last update timestamp (nanoseconds)
};

struct BookSnapshot {
    std::string symbol;
    int64_t     timestamp_ns;
    double      mid_price;
    double      spread;
    double      spread_bps;
    double      bid_ask_imbalance;  // -1 (all asks) to +1 (all bids)
    double      weighted_mid;       // Volume-weighted mid price
    double      vwap_bid_5;         // VWAP of top 5 bid levels
    double      vwap_ask_5;         // VWAP of top 5 ask levels
    double      total_bid_qty;
    double      total_ask_qty;
    int         bid_levels;
    int         ask_levels;
};

struct TradeEvent {
    int64_t timestamp_ns;
    double  price;
    double  quantity;
    Side    aggressor;  // Who initiated: BID = buyer aggressive, ASK = seller aggressive
};

// ──────────────────────────────────────────────────────────────
// Order Book
// ──────────────────────────────────────────────────────────────

class OrderBook {
public:
    explicit OrderBook(const std::string& symbol, int max_depth = 50)
        : symbol_(symbol), max_depth_(max_depth) {}

    // --- Core Operations (hot path) ---

    void update_level(Side side, double price, double quantity, int order_count = 1) {
        auto& book = (side == Side::BID) ? bids_ : asks_;

        if (quantity <= 0.0) {
            // Remove level
            book.erase(price);
        } else {
            book[price] = {price, quantity, order_count, now_ns()};
        }

        // Trim depth
        trim(side);
        ++update_count_;
    }

    void clear_side(Side side) {
        if (side == Side::BID) bids_.clear();
        else asks_.clear();
    }

    void clear() {
        bids_.clear();
        asks_.clear();
    }

    // --- Market Data Queries (hot path) ---

    double best_bid() const {
        return bids_.empty() ? 0.0 : bids_.rbegin()->first;
    }

    double best_ask() const {
        return asks_.empty() ? 0.0 : asks_.begin()->first;
    }

    double mid_price() const {
        double bb = best_bid(), ba = best_ask();
        return (bb > 0 && ba > 0) ? (bb + ba) / 2.0 : 0.0;
    }

    double spread() const {
        return best_ask() - best_bid();
    }

    double spread_bps() const {
        double mid = mid_price();
        return (mid > 0) ? (spread() / mid) * 10000.0 : 0.0;
    }

    double bid_ask_imbalance() const {
        double bid_qty = top_n_quantity(Side::BID, 5);
        double ask_qty = top_n_quantity(Side::ASK, 5);
        double total = bid_qty + ask_qty;
        return (total > 0) ? (bid_qty - ask_qty) / total : 0.0;
    }

    double weighted_mid_price() const {
        double bb = best_bid(), ba = best_ask();
        if (bb <= 0 || ba <= 0) return mid_price();

        double bq = bids_.rbegin()->second.quantity;
        double aq = asks_.begin()->second.quantity;
        double total = bq + aq;
        return (total > 0) ? (bb * aq + ba * bq) / total : mid_price();
    }

    // VWAP of top N levels
    double vwap(Side side, int n = 5) const {
        const auto& book = (side == Side::BID) ? bids_ : asks_;
        double sum_pq = 0.0, sum_q = 0.0;
        int count = 0;

        if (side == Side::BID) {
            for (auto it = book.rbegin(); it != book.rend() && count < n; ++it, ++count) {
                sum_pq += it->second.price * it->second.quantity;
                sum_q += it->second.quantity;
            }
        } else {
            for (auto it = book.begin(); it != book.end() && count < n; ++it, ++count) {
                sum_pq += it->second.price * it->second.quantity;
                sum_q += it->second.quantity;
            }
        }
        return (sum_q > 0) ? sum_pq / sum_q : 0.0;
    }

    // --- Snapshot (for Python export) ---

    BookSnapshot snapshot() const {
        return {
            symbol_,
            now_ns(),
            mid_price(),
            spread(),
            spread_bps(),
            bid_ask_imbalance(),
            weighted_mid_price(),
            vwap(Side::BID, 5),
            vwap(Side::ASK, 5),
            total_quantity(Side::BID),
            total_quantity(Side::ASK),
            static_cast<int>(bids_.size()),
            static_cast<int>(asks_.size()),
        };
    }

    // --- Level Access ---

    std::vector<PriceLevel> get_bids(int n = 10) const {
        std::vector<PriceLevel> result;
        int count = 0;
        for (auto it = bids_.rbegin(); it != bids_.rend() && count < n; ++it, ++count) {
            result.push_back(it->second);
        }
        return result;
    }

    std::vector<PriceLevel> get_asks(int n = 10) const {
        std::vector<PriceLevel> result;
        int count = 0;
        for (auto it = asks_.begin(); it != asks_.end() && count < n; ++it, ++count) {
            result.push_back(it->second);
        }
        return result;
    }

    // --- Stats ---

    uint64_t update_count() const { return update_count_; }
    const std::string& symbol() const { return symbol_; }

private:
    std::string symbol_;
    int max_depth_;
    uint64_t update_count_ = 0;

    // Bids: sorted ascending (highest = rbegin)
    // Asks: sorted ascending (lowest = begin)
    std::map<double, PriceLevel> bids_;
    std::map<double, PriceLevel> asks_;

    void trim(Side side) {
        auto& book = (side == Side::BID) ? bids_ : asks_;
        while (static_cast<int>(book.size()) > max_depth_) {
            if (side == Side::BID) {
                book.erase(book.begin());  // Remove worst bid (lowest)
            } else {
                auto it = book.end();
                --it;
                book.erase(it);  // Remove worst ask (highest)
            }
        }
    }

    double top_n_quantity(Side side, int n) const {
        const auto& book = (side == Side::BID) ? bids_ : asks_;
        double total = 0.0;
        int count = 0;

        if (side == Side::BID) {
            for (auto it = book.rbegin(); it != book.rend() && count < n; ++it, ++count)
                total += it->second.quantity;
        } else {
            for (auto it = book.begin(); it != book.end() && count < n; ++it, ++count)
                total += it->second.quantity;
        }
        return total;
    }

    double total_quantity(Side side) const {
        const auto& book = (side == Side::BID) ? bids_ : asks_;
        double total = 0.0;
        for (const auto& [_, level] : book) total += level.quantity;
        return total;
    }

    static int64_t now_ns() {
        return std::chrono::duration_cast<std::chrono::nanoseconds>(
            std::chrono::high_resolution_clock::now().time_since_epoch()
        ).count();
    }
};

}  // namespace orderbook
}  // namespace atlas
