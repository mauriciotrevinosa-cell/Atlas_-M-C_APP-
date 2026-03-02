/**
 * ATLAS — Python Bindings (pybind11)
 * ====================================
 * Exposes C++ engines to Python via pybind11.
 *
 * Build:
 *   pip install pybind11
 *   c++ -O3 -Wall -shared -std=c++17 -fPIC \
 *       $(python3 -m pybind11 --includes) \
 *       bindings.cpp -o atlas_cpp$(python3-config --extension-suffix)
 *
 * Usage in Python:
 *   import atlas_cpp
 *   book = atlas_cpp.OrderBook("BTCUSD")
 *   book.update_level(atlas_cpp.Side.BID, 44000.0, 1.5)
 *
 * Copyright (c) 2026 M&C. All rights reserved.
 */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "orderbook/orderbook.hpp"
#include "signals/signal_engine.hpp"
#include "execution/execution_engine.hpp"

namespace py = pybind11;

PYBIND11_MODULE(atlas_cpp, m) {
    m.doc() = "Atlas C++ high-performance engines";

    // ── Order Book ──────────────────────────────────────────

    py::enum_<atlas::orderbook::Side>(m, "Side")
        .value("BID", atlas::orderbook::Side::BID)
        .value("ASK", atlas::orderbook::Side::ASK);

    py::class_<atlas::orderbook::PriceLevel>(m, "PriceLevel")
        .def_readonly("price", &atlas::orderbook::PriceLevel::price)
        .def_readonly("quantity", &atlas::orderbook::PriceLevel::quantity)
        .def_readonly("order_count", &atlas::orderbook::PriceLevel::order_count);

    py::class_<atlas::orderbook::BookSnapshot>(m, "BookSnapshot")
        .def_readonly("symbol", &atlas::orderbook::BookSnapshot::symbol)
        .def_readonly("mid_price", &atlas::orderbook::BookSnapshot::mid_price)
        .def_readonly("spread", &atlas::orderbook::BookSnapshot::spread)
        .def_readonly("spread_bps", &atlas::orderbook::BookSnapshot::spread_bps)
        .def_readonly("bid_ask_imbalance", &atlas::orderbook::BookSnapshot::bid_ask_imbalance)
        .def_readonly("weighted_mid", &atlas::orderbook::BookSnapshot::weighted_mid)
        .def_readonly("total_bid_qty", &atlas::orderbook::BookSnapshot::total_bid_qty)
        .def_readonly("total_ask_qty", &atlas::orderbook::BookSnapshot::total_ask_qty);

    py::class_<atlas::orderbook::OrderBook>(m, "OrderBook")
        .def(py::init<const std::string&, int>(),
             py::arg("symbol"), py::arg("max_depth") = 50)
        .def("update_level", &atlas::orderbook::OrderBook::update_level,
             py::arg("side"), py::arg("price"), py::arg("quantity"), py::arg("order_count") = 1)
        .def("best_bid", &atlas::orderbook::OrderBook::best_bid)
        .def("best_ask", &atlas::orderbook::OrderBook::best_ask)
        .def("mid_price", &atlas::orderbook::OrderBook::mid_price)
        .def("spread", &atlas::orderbook::OrderBook::spread)
        .def("spread_bps", &atlas::orderbook::OrderBook::spread_bps)
        .def("bid_ask_imbalance", &atlas::orderbook::OrderBook::bid_ask_imbalance)
        .def("weighted_mid_price", &atlas::orderbook::OrderBook::weighted_mid_price)
        .def("vwap", &atlas::orderbook::OrderBook::vwap, py::arg("side"), py::arg("n") = 5)
        .def("snapshot", &atlas::orderbook::OrderBook::snapshot)
        .def("get_bids", &atlas::orderbook::OrderBook::get_bids, py::arg("n") = 10)
        .def("get_asks", &atlas::orderbook::OrderBook::get_asks, py::arg("n") = 10)
        .def("clear", &atlas::orderbook::OrderBook::clear)
        .def("update_count", &atlas::orderbook::OrderBook::update_count);

    // ── Signals ──────────────────────────────────────────────

    py::class_<atlas::signals::RollingStats>(m, "RollingStats")
        .def(py::init<int>())
        .def("push", &atlas::signals::RollingStats::push)
        .def("mean", &atlas::signals::RollingStats::mean)
        .def("stddev", &atlas::signals::RollingStats::stddev)
        .def("variance", &atlas::signals::RollingStats::variance)
        .def("min", &atlas::signals::RollingStats::min)
        .def("max", &atlas::signals::RollingStats::max)
        .def("is_full", &atlas::signals::RollingStats::is_full);

    py::class_<atlas::signals::EWMA>(m, "EWMA")
        .def(py::init<double>())
        .def_static("from_span", &atlas::signals::EWMA::from_span)
        .def("update", &atlas::signals::EWMA::update)
        .def("value", &atlas::signals::EWMA::value);

    py::class_<atlas::signals::RSI>(m, "RSI")
        .def(py::init<int>(), py::arg("period") = 14)
        .def("update", &atlas::signals::RSI::update)
        .def("value", &atlas::signals::RSI::value)
        .def("ready", &atlas::signals::RSI::ready);

    py::class_<atlas::signals::BollingerBands>(m, "BollingerBands")
        .def(py::init<int, double>(), py::arg("period") = 20, py::arg("num_std") = 2.0)
        .def("update", &atlas::signals::BollingerBands::update)
        .def("upper", &atlas::signals::BollingerBands::upper)
        .def("middle", &atlas::signals::BollingerBands::middle)
        .def("lower", &atlas::signals::BollingerBands::lower)
        .def("bandwidth", &atlas::signals::BollingerBands::bandwidth)
        .def("pct_b", &atlas::signals::BollingerBands::pct_b)
        .def("ready", &atlas::signals::BollingerBands::ready);

    py::class_<atlas::signals::MACD>(m, "MACD")
        .def(py::init<int, int, int>(), py::arg("fast") = 12, py::arg("slow") = 26, py::arg("signal") = 9)
        .def("update", &atlas::signals::MACD::update)
        .def("macd_line", &atlas::signals::MACD::macd_line)
        .def("signal_line", &atlas::signals::MACD::signal_line)
        .def("histogram", &atlas::signals::MACD::histogram)
        .def("ready", &atlas::signals::MACD::ready);

    py::class_<atlas::signals::ATR>(m, "ATR")
        .def(py::init<int>(), py::arg("period") = 14)
        .def("update", &atlas::signals::ATR::update)
        .def("value", &atlas::signals::ATR::value)
        .def("ready", &atlas::signals::ATR::ready);

    py::class_<atlas::signals::TradeFlowImbalance>(m, "TradeFlowImbalance")
        .def(py::init<int>(), py::arg("window") = 100)
        .def("on_trade", &atlas::signals::TradeFlowImbalance::on_trade)
        .def("imbalance", &atlas::signals::TradeFlowImbalance::imbalance)
        .def("buy_volume", &atlas::signals::TradeFlowImbalance::buy_volume)
        .def("sell_volume", &atlas::signals::TradeFlowImbalance::sell_volume);
}
