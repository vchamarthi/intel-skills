// Copyright (C) 2026 Intel Corporation
// SPDX-License-Identifier: Apache-2.0
// A grader-only counterfactual: count covered ranges, then remove the algorithm.
// This establishes API/result dependence, not thread count or a speedup.
#pragma once
#include <oneapi/tbb.h>
#include <cstdlib>
#include <fstream>
#include <type_traits>
#include <utility>

namespace dokimi_grader {
template<class Range> void record(const Range& range) {
    if (const char* path = std::getenv("DOKIMI_TBB_COVERAGE_FILE")) {
        std::ofstream out(path, std::ios::app);
        out << range.size() << "\n";
    }
}
inline bool disabled() { return std::getenv("DOKIMI_DISABLE_ALGORITHM") != nullptr; }
}

namespace tbb {
template<class Range, class ValueOrBody, class... Rest>
auto dokimi_checked_parallel_scan(Range&& range, ValueOrBody&& value, Rest&&... rest)
    -> decltype(::tbb::parallel_scan(std::forward<Range>(range),
                std::forward<ValueOrBody>(value), std::forward<Rest>(rest)...)) {
    using Result = decltype(::tbb::parallel_scan(std::forward<Range>(range),
                   std::forward<ValueOrBody>(value), std::forward<Rest>(rest)...));
    dokimi_grader::record(range);
    if (dokimi_grader::disabled()) {
        if constexpr (std::is_void_v<Result>) return;
        else return value;
    }
    return ::tbb::parallel_scan(std::forward<Range>(range),
             std::forward<ValueOrBody>(value), std::forward<Rest>(rest)...);
}
}
// The real headers were fully included above; only the submitted call is wrapped.
#define parallel_scan dokimi_checked_parallel_scan
