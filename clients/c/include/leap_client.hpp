/*
 * leap_client.hpp — Header-only C++17 wrapper for LEAP2
 *
 * RAII, exceptions, variadic templates, implicit result conversion.
 *
 * Quick start:
 *   leap::Client c("http://localhost:9000", "s001", "gradient-descent-2d");
 *   double r = c("df", 1.0, 2.0);
 *   auto df = c.func("df");
 *   double g = df(0.5, 0.0);
 */

#ifndef LEAP_CLIENT_HPP
#define LEAP_CLIENT_HPP

#include "leap_client.h"

#include <cmath>
#include <cstdlib>
#include <initializer_list>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace leap {

/* ── Exception ── */

struct Error : std::runtime_error {
    LEAPError code;
    Error(LEAPError c, const std::string& msg)
        : std::runtime_error(msg), code(c) {}
};

/* ── JSON serialization helpers ── */

namespace detail {

inline void append_json(std::ostringstream& os, double v)       { os << v; }
inline void append_json(std::ostringstream& os, float v)        { os << static_cast<double>(v); }
inline void append_json(std::ostringstream& os, int v)          { os << v; }
inline void append_json(std::ostringstream& os, long v)         { os << v; }
inline void append_json(std::ostringstream& os, long long v)    { os << v; }
inline void append_json(std::ostringstream& os, unsigned v)     { os << v; }
inline void append_json(std::ostringstream& os, bool v)         { os << (v ? "true" : "false"); }

inline void append_json(std::ostringstream& os, const char* v) {
    os << '"';
    for (const char* p = v; *p; ++p) {
        switch (*p) {
            case '"':  os << "\\\""; break;
            case '\\': os << "\\\\"; break;
            case '\n': os << "\\n";  break;
            case '\t': os << "\\t";  break;
            default:   os << *p;
        }
    }
    os << '"';
}

inline void append_json(std::ostringstream& os, const std::string& v) {
    append_json(os, v.c_str());
}

template<typename T>
void append_json(std::ostringstream& os, const std::vector<T>& v) {
    os << '[';
    for (size_t i = 0; i < v.size(); ++i) {
        if (i) os << ',';
        append_json(os, v[i]);
    }
    os << ']';
}

template<typename V>
void append_json(std::ostringstream& os, const std::map<std::string, V>& m) {
    os << '{';
    bool first = true;
    for (auto& [k, v] : m) {
        if (!first) os << ',';
        append_json(os, k);
        os << ':';
        append_json(os, v);
        first = false;
    }
    os << '}';
}

inline std::string build_args_json() { return "[]"; }

template<typename... Args>
std::string build_args_json(Args&&... args) {
    std::ostringstream os;
    os << '[';
    int n = 0;
    ((n++ ? (os << ',', 0) : 0, append_json(os, std::forward<Args>(args))), ...);
    os << ']';
    return os.str();
}

/* Simple JSON value extraction helpers (no full parser needed — values come
   from the C library which already validated the JSON). */

inline double parse_double(const std::string& json) {
    return std::strtod(json.c_str(), nullptr);
}

inline int parse_int(const std::string& json) {
    return static_cast<int>(std::strtol(json.c_str(), nullptr, 10));
}

inline bool parse_bool(const std::string& json) {
    return json == "true";
}

inline std::string parse_string(const std::string& json) {
    /* Strip surrounding quotes, unescape */
    if (json.size() >= 2 && json.front() == '"' && json.back() == '"') {
        std::string s;
        s.reserve(json.size() - 2);
        for (size_t i = 1; i + 1 < json.size(); ++i) {
            if (json[i] == '\\' && i + 2 < json.size()) {
                switch (json[i + 1]) {
                    case '"':  s += '"';  ++i; break;
                    case '\\': s += '\\'; ++i; break;
                    case 'n':  s += '\n'; ++i; break;
                    case 't':  s += '\t'; ++i; break;
                    default:   s += json[i]; break;
                }
            } else {
                s += json[i];
            }
        }
        return s;
    }
    return json; /* not a quoted string — return as-is */
}

/* Parse a JSON array of strings: ["a","b","c"] */
inline std::vector<std::string> parse_string_vector(const std::string& json) {
    std::vector<std::string> result;
    if (json.size() < 2 || json.front() != '[') return result;
    size_t i = 1;
    while (i < json.size()) {
        while (i < json.size() && (json[i] == ' ' || json[i] == ',' || json[i] == '\n')) ++i;
        if (i >= json.size() || json[i] == ']') break;
        if (json[i] == '"') {
            size_t start = i;
            ++i;
            while (i < json.size() && json[i] != '"') {
                if (json[i] == '\\') ++i; /* skip escaped char */
                ++i;
            }
            if (i < json.size()) ++i; /* closing quote */
            result.push_back(parse_string(json.substr(start, i - start)));
        } else {
            /* non-string element: skip to next comma or bracket */
            size_t start = i;
            while (i < json.size() && json[i] != ',' && json[i] != ']') ++i;
            result.push_back(json.substr(start, i - start));
        }
    }
    return result;
}

} // namespace detail


/* ── Result — wraps a JSON string with implicit conversions ── */

class Result {
    std::string json_;
public:
    explicit Result(std::string json) : json_(std::move(json)) {}

    operator double()      const { return detail::parse_double(json_); }
    operator float()       const { return static_cast<float>(detail::parse_double(json_)); }
    operator int()         const { return detail::parse_int(json_); }
    operator long()        const { return static_cast<long>(std::strtol(json_.c_str(), nullptr, 10)); }
    operator bool()        const { return detail::parse_bool(json_); }
    operator std::string() const { return detail::parse_string(json_); }

    /* Explicit conversion for complex types */
    template<typename T> T as() const;

    const std::string& json() const { return json_; }
};

/* Specializations */
template<> inline std::vector<std::string> Result::as<std::vector<std::string>>() const {
    return detail::parse_string_vector(json_);
}
template<> inline double      Result::as<double>()      const { return detail::parse_double(json_); }
template<> inline int         Result::as<int>()         const { return detail::parse_int(json_); }
template<> inline std::string Result::as<std::string>() const { return detail::parse_string(json_); }


/* Forward declarations */
class Client;

/* ── Func — reusable function handle ── */

class Func {
    LEAPClient* c_;
    std::string name_;
    friend class Client;
    Func(LEAPClient* c, std::string name) : c_(c), name_(std::move(name)) {}
public:
    template<typename... Args>
    Result operator()(Args&&... args) const {
        std::string args_json = detail::build_args_json(std::forward<Args>(args)...);
        char* result = nullptr;
        LEAPError err = leap_call(c_, name_.c_str(), args_json.c_str(),
                                   nullptr, nullptr, &result);
        if (err != LEAP_OK) {
            throw Error(err, leap_last_error(c_));
        }
        std::string r(result);
        leap_free(result);
        return Result(std::move(r));
    }
};


/* ── Client ── */

class Client {
    LEAPClient* c_;

    void check(LEAPError err) {
        if (err != LEAP_OK) throw Error(err, leap_last_error(c_));
    }

public:
    Client(const std::string& url, const std::string& sid,
           const std::string& exp, const std::string& trial = "")
        : c_(leap_create(url.c_str(), sid.c_str(), exp.c_str(),
                          trial.empty() ? nullptr : trial.c_str())) {
        if (!c_) throw Error(LEAP_ERR_INVALID_ARG, "Failed to create LEAP client");
    }

    ~Client() { if (c_) leap_destroy(c_); }

    /* Non-copyable */
    Client(const Client&) = delete;
    Client& operator=(const Client&) = delete;

    /* Movable */
    Client(Client&& o) noexcept : c_(o.c_) { o.c_ = nullptr; }
    Client& operator=(Client&& o) noexcept {
        if (this != &o) { if (c_) leap_destroy(c_); c_ = o.c_; o.c_ = nullptr; }
        return *this;
    }

    /* Direct variadic call: double r = c("df", 1.0, 2.0); */
    template<typename... Args>
    Result operator()(const std::string& func_name, Args&&... args) {
        std::string args_json = detail::build_args_json(std::forward<Args>(args)...);
        char* result = nullptr;
        check(leap_call(c_, func_name.c_str(), args_json.c_str(),
                         nullptr, nullptr, &result));
        std::string r(result);
        leap_free(result);
        return Result(std::move(r));
    }

    /* Bind a reusable function handle */
    Func func(const std::string& name) { return Func(c_, name); }

    /* Full JSON call for complex cases (kwargs, trial override) */
    Result call(const std::string& func_name,
                const std::string& args_json = "[]",
                const std::string& kwargs_json = "",
                const std::string& trial = "") {
        char* result = nullptr;
        check(leap_call(c_, func_name.c_str(), args_json.c_str(),
                         kwargs_json.empty() ? nullptr : kwargs_json.c_str(),
                         trial.empty() ? nullptr : trial.c_str(), &result));
        std::string r(result);
        leap_free(result);
        return Result(std::move(r));
    }

    void help() { leap_help(c_); }

    bool is_registered() {
        int reg = 0;
        check(leap_is_registered(c_, &reg));
        return reg != 0;
    }

    std::string fetch_logs(int n = 100, const std::string& order = "latest") {
        char* json = nullptr;
        check(leap_fetch_logs(c_, n, order.c_str(), &json));
        std::string r(json);
        leap_free(json);
        return r;
    }
};

} // namespace leap

#endif /* LEAP_CLIENT_HPP */
