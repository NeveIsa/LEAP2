# LEAP2 C/C++ Client

Call LEAP experiment functions from C or C++ as if they were local functions.

## Prerequisites

- **libcurl** development headers
  - Ubuntu/Debian: `sudo apt install libcurl4-openssl-dev`
  - macOS: `brew install curl` (or use system curl)
  - Fedora: `sudo dnf install libcurl-devel`

## Build

```bash
make            # builds libleap_client.a
make example    # C example
make example_cpp  # C++ example
```

Or with CMake:
```bash
cmake -B build && cmake --build build
```

## C Usage

```c
#include "leap_client.h"

LEAPClient* c = leap_create("http://localhost:9000", "s001", "my-lab", NULL);

// One-line calls — feels like a local function
double r = LEAP(c, "df", 1.0, 2.0);
double g = LEAP(c, "gradient", 0.5);

// Print available functions
leap_help(c);

leap_destroy(c);
```

The `LEAP()` macro takes doubles and returns a double. On error it returns `NAN` — check with `isnan()` and call `leap_last_error(c)` for details.

For string results, kwargs, or complex types, use `leap_call()` (Layer 1):

```c
char* result = NULL;
leap_call(c, "search", "[\"A\"]", "{\"depth\": 3}", NULL, &result);
printf("%s\n", result);
leap_free(result);
```

## C++ Usage

```cpp
#include "leap_client.hpp"

leap::Client c("http://localhost:9000", "s001", "my-lab");

// Feels like local function calls
double r = c("df", 1.0, 2.0);
std::string path = c("search", "A");

// Reusable function handle
auto df = c.func("df");
for (double x = 0; x < 10; x += 0.1)
    std::cout << df(x, 0.0).json() << "\n";

// Complex return types
auto neighbors = c("neighbors", "A").as<std::vector<std::string>>();
```

The C++ wrapper is header-only (`leap_client.hpp`), uses RAII, and throws `leap::Error` on failures.

## API Layers

| Layer | Function | Use case |
|-------|----------|----------|
| 3 | `LEAP(c, "f", args...)` | One-line numeric calls (C macro) |
| 3 | `c("f", args...)` | One-line calls (C++ operator) |
| 2 | `leap_call_doubles/ints/string` | Typed results without JSON |
| 1 | `leap_call(c, name, args_json, kwargs_json, trial, &result)` | Full control, JSON in/out |

## Dependencies

- **libcurl** — HTTP client (system package)
- **cJSON** — JSON parser (vendored in `src/`, MIT license)
