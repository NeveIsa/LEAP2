/*
 * leap_client.h — C client for LEAP2
 *
 * Three layers of API:
 *   Layer 1: leap_call()         — full JSON in/out, kwargs, trial override
 *   Layer 2: leap_call_doubles() — typed convenience, no JSON needed
 *   Layer 3: LEAP() macro        — one-line variadic calls
 *
 * Quick start:
 *   LEAPClient* c = leap_create("http://localhost:9000", "s001", "my-lab", NULL);
 *   double r = LEAP(c, "df", 1.0, 2.0);
 *   printf("result = %f\n", r);
 *   leap_destroy(c);
 *
 * Requires: libcurl (-lcurl)
 */

#ifndef LEAP_CLIENT_H
#define LEAP_CLIENT_H

#include <math.h>   /* NAN */
#include <stdarg.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ── Opaque handle ── */
typedef struct LEAPClient LEAPClient;

/* ── Error codes ── */
typedef enum {
    LEAP_OK = 0,
    LEAP_ERR_NETWORK,        /* could not reach server */
    LEAP_ERR_SERVER,         /* server returned 4xx/5xx */
    LEAP_ERR_NOT_REGISTERED, /* 403 — student not registered */
    LEAP_ERR_PROTOCOL,       /* invalid JSON or missing fields */
    LEAP_ERR_INVALID_ARG,    /* bad argument to a client function */
} LEAPError;


/* ── Layer 1: Core (full control) ── */

LEAPClient* leap_create(const char* server_url, const char* student_id,
                         const char* experiment, const char* trial);
void        leap_destroy(LEAPClient* c);

/*
 * Full JSON RPC call.
 *   args_json   — JSON array, e.g. "[1.0, 2.0]" (required)
 *   kwargs_json — JSON object, e.g. "{\"lr\": 0.01}" or NULL
 *   trial       — per-call trial name override, or NULL
 *   result_json — receives malloc'd JSON string; caller must leap_free()
 */
LEAPError   leap_call(LEAPClient* c, const char* func_name,
                       const char* args_json, const char* kwargs_json,
                       const char* trial, char** result_json);

LEAPError   leap_list_functions(LEAPClient* c, char** json_out);
void        leap_help(LEAPClient* c);
LEAPError   leap_is_registered(LEAPClient* c, int* registered);
LEAPError   leap_fetch_logs(LEAPClient* c, int n, const char* order, char** json_out);

const char* leap_last_error(LEAPClient* c);
void        leap_free(void* ptr);


/* ── Layer 2: Typed convenience ── */

LEAPError   leap_call_doubles(LEAPClient* c, const char* func_name,
                               int argc, const double* args, double* result);
LEAPError   leap_call_ints(LEAPClient* c, const char* func_name,
                            int argc, const int* args, int* result);
/* Caller must leap_free(*result) */
LEAPError   leap_call_string(LEAPClient* c, const char* func_name,
                              const char* args_json, char** result);


/* ── Layer 3: Variadic one-liner ── */

/*
 * leap_calld — call with argc double arguments, return double result.
 * Returns NAN on error (check with isnan(); detail via leap_last_error()).
 */
double      leap_calld(LEAPClient* c, const char* func_name, int argc, ...);

/* LEAP() macro — auto-counts args so students never write argc. */
#define _LEAP_NARGS_(_8,_7,_6,_5,_4,_3,_2,_1,N,...) N
#define _LEAP_NARGS(...) _LEAP_NARGS_(__VA_ARGS__,8,7,6,5,4,3,2,1,0)
#define LEAP(client, func, ...) \
    leap_calld((client), (func), _LEAP_NARGS(__VA_ARGS__), __VA_ARGS__)

#ifdef __cplusplus
}
#endif

#endif /* LEAP_CLIENT_H */
