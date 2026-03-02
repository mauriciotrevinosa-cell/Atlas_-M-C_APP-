/**
 * ATLAS — Execution Engine (C++)
 * ================================
 * Low-latency order execution algorithms.
 * TWAP, VWAP, and smart order routing.
 *
 * Copyright (c) 2026 M&C. All rights reserved.
 */

#pragma once

#include <chrono>
#include <cstdint>
#include <functional>
#include <string>
#include <vector>

namespace atlas {
namespace execution {

// ──────────────────────────────────────────────────────────────
// Order Types
// ──────────────────────────────────────────────────────────────

enum class OrderSide : uint8_t { BUY = 0, SELL = 1 };
enum class OrderType : uint8_t { MARKET = 0, LIMIT = 1, STOP = 2 };
enum class OrderStatus : uint8_t {
    PENDING = 0, ACTIVE = 1, PARTIAL = 2, FILLED = 3, CANCELLED = 4, REJECTED = 5
};

struct Order {
    uint64_t    id;
    std::string symbol;
    OrderSide   side;
    OrderType   type;
    double      quantity;
    double      filled_quantity;
    double      price;           // Limit price (0 for market)
    double      avg_fill_price;
    OrderStatus status;
    int64_t     created_ns;
    int64_t     updated_ns;

    double remaining() const { return quantity - filled_quantity; }
    bool is_done() const {
        return status == OrderStatus::FILLED ||
               status == OrderStatus::CANCELLED ||
               status == OrderStatus::REJECTED;
    }
};

struct Fill {
    uint64_t order_id;
    double   price;
    double   quantity;
    int64_t  timestamp_ns;
};

// Callback for order status updates
using FillCallback = std::function<void(const Fill&)>;

// ──────────────────────────────────────────────────────────────
// TWAP Executor
// ──────────────────────────────────────────────────────────────

class TWAPExecutor {
    /**
     * Time-Weighted Average Price execution.
     * Splits total order into equal time slices.
     */
public:
    TWAPExecutor(int n_slices, int64_t duration_ns)
        : n_slices_(n_slices),
          duration_ns_(duration_ns),
          slice_interval_ns_(duration_ns / n_slices),
          current_slice_(0),
          total_quantity_(0),
          filled_quantity_(0),
          start_time_ns_(0),
          active_(false) {}

    struct TWAPSlice {
        int     slice_index;
        double  target_quantity;
        double  filled_quantity;
        double  avg_price;
        int64_t scheduled_time_ns;
        bool    completed;
    };

    void start(double total_quantity, int64_t now_ns) {
        total_quantity_ = total_quantity;
        slice_qty_ = total_quantity / n_slices_;
        start_time_ns_ = now_ns;
        current_slice_ = 0;
        filled_quantity_ = 0;
        active_ = true;

        slices_.clear();
        for (int i = 0; i < n_slices_; ++i) {
            slices_.push_back({
                i,
                slice_qty_,
                0.0,
                0.0,
                start_time_ns_ + i * slice_interval_ns_,
                false
            });
        }
    }

    // Returns next slice to execute (if time has come), or nullptr
    TWAPSlice* next_slice(int64_t now_ns) {
        if (!active_ || current_slice_ >= n_slices_) return nullptr;

        auto& slice = slices_[current_slice_];
        if (now_ns >= slice.scheduled_time_ns && !slice.completed) {
            return &slice;
        }
        return nullptr;
    }

    void on_fill(double price, double quantity) {
        if (current_slice_ < n_slices_) {
            auto& slice = slices_[current_slice_];
            slice.filled_quantity += quantity;
            slice.avg_price = (slice.avg_price * (slice.filled_quantity - quantity) + price * quantity)
                              / slice.filled_quantity;

            if (slice.filled_quantity >= slice.target_quantity * 0.99) {
                slice.completed = true;
                ++current_slice_;
            }
        }
        filled_quantity_ += quantity;

        if (filled_quantity_ >= total_quantity_ * 0.99) {
            active_ = false;
        }
    }

    // Performance metrics
    double participation_rate(double market_volume) const {
        return (market_volume > 0) ? filled_quantity_ / market_volume : 0.0;
    }

    double avg_fill_price() const {
        double sum_pq = 0.0, sum_q = 0.0;
        for (const auto& s : slices_) {
            sum_pq += s.avg_price * s.filled_quantity;
            sum_q += s.filled_quantity;
        }
        return (sum_q > 0) ? sum_pq / sum_q : 0.0;
    }

    double completion_pct() const {
        return (total_quantity_ > 0) ? filled_quantity_ / total_quantity_ : 0.0;
    }

    bool is_active() const { return active_; }
    int current_slice() const { return current_slice_; }
    int total_slices() const { return n_slices_; }

private:
    int n_slices_;
    int64_t duration_ns_;
    int64_t slice_interval_ns_;
    int current_slice_;
    double total_quantity_;
    double filled_quantity_;
    double slice_qty_;
    int64_t start_time_ns_;
    bool active_;
    std::vector<TWAPSlice> slices_;
};


// ──────────────────────────────────────────────────────────────
// VWAP Executor
// ──────────────────────────────────────────────────────────────

class VWAPExecutor {
    /**
     * Volume-Weighted Average Price execution.
     * Slices weighted by historical volume profile.
     */
public:
    VWAPExecutor(const std::vector<double>& volume_profile, int64_t duration_ns)
        : duration_ns_(duration_ns),
          current_slice_(0),
          total_quantity_(0),
          filled_quantity_(0),
          active_(false)
    {
        // Normalize profile
        double sum = 0.0;
        for (double v : volume_profile) sum += v;
        for (double v : volume_profile) {
            profile_.push_back((sum > 0) ? v / sum : 1.0 / volume_profile.size());
        }
        n_slices_ = static_cast<int>(profile_.size());
        slice_interval_ns_ = (n_slices_ > 0) ? duration_ns / n_slices_ : duration_ns;
    }

    void start(double total_quantity, int64_t now_ns) {
        total_quantity_ = total_quantity;
        start_time_ns_ = now_ns;
        current_slice_ = 0;
        filled_quantity_ = 0;
        active_ = true;

        // Compute target per slice based on volume profile
        slice_targets_.clear();
        for (int i = 0; i < n_slices_; ++i) {
            slice_targets_.push_back(total_quantity * profile_[i]);
        }
    }

    double current_slice_target() const {
        if (current_slice_ < n_slices_)
            return slice_targets_[current_slice_];
        return 0.0;
    }

    void advance_slice() {
        if (current_slice_ < n_slices_) ++current_slice_;
        if (current_slice_ >= n_slices_) active_ = false;
    }

    void on_fill(double quantity) {
        filled_quantity_ += quantity;
    }

    bool is_active() const { return active_; }
    double completion_pct() const {
        return (total_quantity_ > 0) ? filled_quantity_ / total_quantity_ : 0.0;
    }

private:
    std::vector<double> profile_;
    std::vector<double> slice_targets_;
    int n_slices_;
    int64_t duration_ns_;
    int64_t slice_interval_ns_;
    int current_slice_;
    double total_quantity_;
    double filled_quantity_;
    int64_t start_time_ns_ = 0;
    bool active_;
};


// ──────────────────────────────────────────────────────────────
// Execution Monitor (tracks slippage, fill rates, latency)
// ──────────────────────────────────────────────────────────────

struct ExecutionMetrics {
    double avg_fill_price;
    double arrival_price;        // Price when order was submitted
    double implementation_shortfall;  // Slippage vs arrival
    double slippage_bps;
    int    total_fills;
    double total_quantity;
    int64_t total_latency_ns;
    int64_t avg_latency_ns;
};

}  // namespace execution
}  // namespace atlas
