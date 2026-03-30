/*
 * example.cpp — LEAP2 C++ client usage example
 *
 * Build:  make example_cpp
 * Run:    ./example_cpp
 */

#include "leap_client.hpp"
#include <iostream>

int main() {
    try {
        leap::Client c("http://localhost:9000", "s001", "gradient-descent-2d");
        c.help();
        std::cout << "\n";

        /* Feels like calling local functions */
        double r = c("df", 1.0, 2.0);
        std::cout << "df(1.0, 2.0) = " << r << "\n";

        /* Reusable function handle */
        auto df = c.func("df");
        for (double x = 0; x < 3; x += 1.0) {
            double val = df(x, 0.0);
            std::cout << "df(" << x << ", 0) = " << val << "\n";
        }

        /* Full JSON call for complex cases */
        auto result = c.call("f", "[1.0, 2.0]");
        std::cout << "f(1.0, 2.0) = " << result.json() << "\n";

        /* Registration check */
        std::cout << "Registered: " << (c.is_registered() ? "yes" : "no") << "\n";

    } catch (const leap::Error& e) {
        std::cerr << "LEAP error: " << e.what() << "\n";
        return 1;
    }
    return 0;
}
