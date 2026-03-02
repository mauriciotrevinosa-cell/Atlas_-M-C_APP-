/**
 * ATLAS — Signal Compute Engine (C++)
 * =====================================
 * High-performance signal computation for latency-critical paths.
 * Computes technical indicators, microstructure signals, and
 * rolling statistics in tight loops.
 *
 * Copyright (c) 2026 M&C. All rights reserved.
 */

#pragma once

#include <algorithm>
#include <cmath>
#include <deque>
#include <numeric>
#include <vector>

namespace atlas {
namespace signals {

// ──────────────────────────────────────────────────────────────
// Rolling Statistics (O(1) per update using online algorithms)
// ──────────────────────────────────────────────────────────────

class RollingStats {
public:
    explicit RollingStats(int window) : window_(window) {}

    void push(double value) {
        buffer_.push_back(value);
        if (static_cast<int>(buffer_.size()) > window_) {
            buffer_.pop_front();
        }
    }

    double mean() const {
        if (buffer_.empty()) return 0.0;
        double sum = std::accumulate(buffer_.begin(), buffer_.end(), 0.0);
        return sum / buffer_.size();
    }

    double variance() const {
        if (buffer_.size() < 2) return 0.0;
        double m = mean();
        double sq_sum = 0.0;
        for (double v : buffer_) sq_sum += (v - m) * (v - m);
        return sq_sum / (buffer_.size() - 1);
    }

    double stddev() const { return std::sqrt(variance()); }

    double min() const {
        return buffer_.empty() ? 0.0 : *std::min_element(buffer_.begin(), buffer_.end());
    }

    double max() const {
        return buffer_.empty() ? 0.0 : *std::max_element(buffer_.begin(), buffer_.end());
    }

    int count() const { return static_cast<int>(buffer_.size()); }
    bool is_full() const { return static_cast<int>(buffer_.size()) >= window_; }

private:
    int window_;
    std::deque<double> buffer_;
};


// ──────────────────────────────────────────────────────────────
// EWMA (Exponentially Weighted Moving Average)
// ──────────────────────────────────────────────────────────────

class EWMA {
public:
    explicit EWMA(double alpha) : alpha_(alpha), value_(0.0), initialized_(false) {}

    // Construct from span: alpha = 2/(span+1)
    static EWMA from_span(int span) {
        return EWMA(2.0 / (span + 1));
    }

    void update(double new_value) {
        if (!initialized_) {
            value_ = new_value;
            initialized_ = true;
        } else {
            value_ = alpha_ * new_value + (1.0 - alpha_) * value_;
        }
    }

    double value() const { return value_; }
    bool initialized() const { return initialized_; }

private:
    double alpha_;
    double value_;
    bool initialized_;
};


// ──────────────────────────────────────────────────────────────
// Technical Indicators (streaming / O(1) per bar)
// ──────────────────────────────────────────────────────────────

class RSI {
    /**
     * Relative Strength Index (streaming).
     * Uses EWMA of gains/losses for smoothing.
     */
public:
    explicit RSI(int period = 14)
        : period_(period), avg_gain_(1.0 / period), avg_loss_(1.0 / period),
          prev_close_(0.0), count_(0) {}

    void update(double close) {
        if (count_ > 0) {
            double change = close - prev_close_;
            double gain = (change > 0) ? change : 0.0;
            double loss = (change < 0) ? -change : 0.0;

            if (count_ < period_) {
                gain_sum_ += gain;
                loss_sum_ += loss;
                if (count_ == period_ - 1) {
                    avg_gain_.update(gain_sum_ / period_);
                    avg_loss_.update(loss_sum_ / period_);
                }
            } else {
                avg_gain_.update(gain);
                avg_loss_.update(loss);
            }
        }
        prev_close_ = close;
        ++count_;
    }

    double value() const {
        if (count_ < period_) return 50.0;  // Default neutral
        double ag = avg_gain_.value();
        double al = avg_loss_.value();
        if (al == 0.0) return 100.0;
        double rs = ag / al;
        return 100.0 - (100.0 / (1.0 + rs));
    }

    bool ready() const { return count_ >= period_; }

private:
    int period_;
    EWMA avg_gain_;
    EWMA avg_loss_;
    double prev_close_;
    int count_;
    double gain_sum_ = 0.0;
    double loss_sum_ = 0.0;
};


class BollingerBands {
public:
    explicit BollingerBands(int period = 20, double num_std = 2.0)
        : stats_(period), num_std_(num_std) {}

    void update(double close) {
        stats_.push(close);
    }

    double upper() const { return stats_.mean() + num_std_ * stats_.stddev(); }
    double middle() const { return stats_.mean(); }
    double lower() const { return stats_.mean() - num_std_ * stats_.stddev(); }
    double bandwidth() const {
        double m = middle();
        return (m > 0) ? (upper() - lower()) / m : 0.0;
    }
    double pct_b(double close) const {
        double range = upper() - lower();
        return (range > 0) ? (close - lower()) / range : 0.5;
    }
    bool ready() const { return stats_.is_full(); }

private:
    RollingStats stats_;
    double num_std_;
};


class MACD {
public:
    MACD(int fast = 12, int slow = 26, int signal = 9)
        : fast_ema_(EWMA::from_span(fast)),
          slow_ema_(EWMA::from_span(slow)),
          signal_ema_(EWMA::from_span(signal)),
          count_(0), slow_period_(slow) {}

    void update(double close) {
        fast_ema_.update(close);
        slow_ema_.update(close);
        ++count_;

        if (count_ >= slow_period_) {
            double macd_line = fast_ema_.value() - slow_ema_.value();
            signal_ema_.update(macd_line);
        }
    }

    double macd_line() const { return fast_ema_.value() - slow_ema_.value(); }
    double signal_line() const { return signal_ema_.value(); }
    double histogram() const { return macd_line() - signal_line(); }
    bool ready() const { return count_ >= slow_period_; }

private:
    EWMA fast_ema_;
    EWMA slow_ema_;
    EWMA signal_ema_;
    int count_;
    int slow_period_;
};


class ATR {
    /**
     * Average True Range (streaming).
     */
public:
    explicit ATR(int period = 14) : period_(period), atr_ema_(1.0 / period), count_(0) {}

    void update(double high, double low, double close) {
        if (count_ > 0) {
            double tr = std::max({
                high - low,
                std::abs(high - prev_close_),
                std::abs(low - prev_close_)
            });
            atr_ema_.update(tr);
        }
        prev_close_ = close;
        ++count_;
    }

    double value() const { return atr_ema_.value(); }
    bool ready() const { return count_ > period_; }

private:
    int period_;
    EWMA atr_ema_;
    double prev_close_ = 0.0;
    int count_;
};


// ──────────────────────────────────────────────────────────────
// Microstructure Signals
// ──────────────────────────────────────────────────────────────

class TradeFlowImbalance {
    /**
     * Track buy/sell volume imbalance over rolling window.
     * Positive = more aggressive buying, negative = more selling.
     */
public:
    explicit TradeFlowImbalance(int window = 100)
        : window_(window) {}

    void on_trade(double quantity, bool is_buy) {
        double signed_qty = is_buy ? quantity : -quantity;
        buffer_.push_back(signed_qty);
        if (static_cast<int>(buffer_.size()) > window_) {
            buffer_.pop_front();
        }
    }

    double imbalance() const {
        if (buffer_.empty()) return 0.0;
        double sum = std::accumulate(buffer_.begin(), buffer_.end(), 0.0);
        double abs_sum = 0.0;
        for (double v : buffer_) abs_sum += std::abs(v);
        return (abs_sum > 0) ? sum / abs_sum : 0.0;
    }

    double buy_volume() const {
        double total = 0.0;
        for (double v : buffer_) if (v > 0) total += v;
        return total;
    }

    double sell_volume() const {
        double total = 0.0;
        for (double v : buffer_) if (v < 0) total += std::abs(v);
        return total;
    }

private:
    int window_;
    std::deque<double> buffer_;
};


// ──────────────────────────────────────────────────────────────
// Signal Aggregator (combines multiple signals)
// ──────────────────────────────────────────────────────────────

struct SignalSnapshot {
    double rsi;
    double macd_histogram;
    double bb_pct_b;
    double bb_bandwidth;
    double atr;
    double trade_flow_imbalance;
    double book_imbalance;
    double mid_price;
    double spread_bps;
};

}  // namespace signals
}  // namespace atlas
