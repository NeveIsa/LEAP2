/*
 * example.c — LEAP2 C client usage example
 *
 * Build:  make example
 * Run:    ./example
 */

#include "leap_client.h"
#include <math.h>
#include <stdio.h>

int main(void) {
    LEAPClient* c = leap_create("http://localhost:9000", "s001",
                                 "gradient-descent-2d", NULL);
    if (!c) {
        fprintf(stderr, "Failed to create client\n");
        return 1;
    }

    /* Print available functions */
    leap_help(c);
    printf("\n");

    /* Layer 3: one-line calls via LEAP() macro */
    double r = LEAP(c, "df", 1.0, 2.0);
    if (!isnan(r)) {
        printf("df(1.0, 2.0) = %f\n", r);
    } else {
        printf("Error: %s\n", leap_last_error(c));
    }

    /* Layer 2: typed convenience */
    double args[] = {0.5, 0.5};
    double grad;
    LEAPError err = leap_call_doubles(c, "df", 2, args, &grad);
    if (err == LEAP_OK) {
        printf("df(0.5, 0.5) = %f\n", grad);
    }

    /* Layer 1: full JSON call with kwargs */
    char* json_result = NULL;
    err = leap_call(c, "f", "[1.0, 2.0]", NULL, NULL, &json_result);
    if (err == LEAP_OK) {
        printf("f(1.0, 2.0) = %s\n", json_result);
        leap_free(json_result);
    }

    /* Check registration */
    int registered = 0;
    if (leap_is_registered(c, &registered) == LEAP_OK) {
        printf("Registered: %s\n", registered ? "yes" : "no");
    }

    leap_destroy(c);
    return 0;
}
