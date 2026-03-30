/*
 * leap_client.c — LEAP2 C client implementation
 *
 * Dependencies: libcurl, cJSON (vendored)
 */

#include "leap_client.h"
#include "cJSON.h"

#include <curl/curl.h>
#include <math.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>


/* ── Internal types ── */

struct LEAPClient {
    char* server_url;
    char* student_id;
    char* experiment;
    char* trial;            /* nullable */
    char  base_url[512];    /* "{server_url}/exp/{experiment}" */
    char  last_error[512];
    CURL* curl;
    cJSON* functions;       /* cached discovery result, or NULL */
};

/* Dynamic buffer for curl responses */
typedef struct {
    char*  data;
    size_t len;
    size_t cap;
} Buffer;

static void buf_init(Buffer* b) {
    b->cap  = 1024;
    b->len  = 0;
    b->data = (char*)malloc(b->cap);
    if (b->data) b->data[0] = '\0';
}

static void buf_free(Buffer* b) {
    free(b->data);
    b->data = NULL;
    b->len = b->cap = 0;
}

static size_t write_cb(void* ptr, size_t size, size_t nmemb, void* userdata) {
    Buffer* b = (Buffer*)userdata;
    size_t bytes = size * nmemb;
    while (b->len + bytes + 1 > b->cap) {
        b->cap *= 2;
        char* tmp = (char*)realloc(b->data, b->cap);
        if (!tmp) return 0;
        b->data = tmp;
    }
    memcpy(b->data + b->len, ptr, bytes);
    b->len += bytes;
    b->data[b->len] = '\0';
    return bytes;
}


/* ── Internal helpers ── */

static void set_error(LEAPClient* c, const char* fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(c->last_error, sizeof(c->last_error), fmt, ap);
    va_end(ap);
}

static LEAPError map_http_error(LEAPClient* c, long status, const char* body) {
    const char* detail = "unknown";
    cJSON* json = cJSON_Parse(body);
    if (json) {
        cJSON* d = cJSON_GetObjectItemCaseSensitive(json, "detail");
        if (cJSON_IsString(d) && d->valuestring)
            detail = d->valuestring;
    }

    LEAPError err;
    if (status == 403) {
        set_error(c, "Student '%s' is not registered for experiment '%s'. "
                  "Register via the Admin UI or admin API.",
                  c->student_id, c->experiment);
        err = LEAP_ERR_NOT_REGISTERED;
    } else {
        set_error(c, "Server error (HTTP %ld): %s", status, detail);
        err = LEAP_ERR_SERVER;
    }

    cJSON_Delete(json);
    return err;
}

static LEAPError http_get(LEAPClient* c, const char* url, Buffer* resp) {
    buf_init(resp);
    curl_easy_reset(c->curl);
    curl_easy_setopt(c->curl, CURLOPT_URL, url);
    curl_easy_setopt(c->curl, CURLOPT_WRITEFUNCTION, write_cb);
    curl_easy_setopt(c->curl, CURLOPT_WRITEDATA, resp);
    curl_easy_setopt(c->curl, CURLOPT_TIMEOUT, 15L);
    curl_easy_setopt(c->curl, CURLOPT_FOLLOWLOCATION, 1L);

    CURLcode res = curl_easy_perform(c->curl);
    if (res != CURLE_OK) {
        set_error(c, "Network error: %s", curl_easy_strerror(res));
        buf_free(resp);
        return LEAP_ERR_NETWORK;
    }

    long status = 0;
    curl_easy_getinfo(c->curl, CURLINFO_RESPONSE_CODE, &status);
    if (status != 200) {
        LEAPError err = map_http_error(c, status, resp->data);
        buf_free(resp);
        return err;
    }
    return LEAP_OK;
}

static LEAPError http_post_json(LEAPClient* c, const char* url,
                                 const char* body, Buffer* resp) {
    buf_init(resp);
    curl_easy_reset(c->curl);
    curl_easy_setopt(c->curl, CURLOPT_URL, url);
    curl_easy_setopt(c->curl, CURLOPT_POSTFIELDS, body);
    curl_easy_setopt(c->curl, CURLOPT_WRITEFUNCTION, write_cb);
    curl_easy_setopt(c->curl, CURLOPT_WRITEDATA, resp);
    curl_easy_setopt(c->curl, CURLOPT_TIMEOUT, 15L);
    curl_easy_setopt(c->curl, CURLOPT_FOLLOWLOCATION, 1L);

    struct curl_slist* headers = NULL;
    headers = curl_slist_append(headers, "Content-Type: application/json");
    curl_easy_setopt(c->curl, CURLOPT_HTTPHEADER, headers);

    CURLcode res = curl_easy_perform(c->curl);
    curl_slist_free_all(headers);

    if (res != CURLE_OK) {
        set_error(c, "Network error: %s", curl_easy_strerror(res));
        buf_free(resp);
        return LEAP_ERR_NETWORK;
    }

    long status = 0;
    curl_easy_getinfo(c->curl, CURLINFO_RESPONSE_CODE, &status);
    if (status != 200) {
        LEAPError err = map_http_error(c, status, resp->data);
        buf_free(resp);
        return err;
    }
    return LEAP_OK;
}

static char* strdup_safe(const char* s) {
    if (!s) return NULL;
    size_t len = strlen(s);
    char* d = (char*)malloc(len + 1);
    if (d) memcpy(d, s, len + 1);
    return d;
}


/* ── Discovery (internal) ── */

static LEAPError discover(LEAPClient* c) {
    if (c->functions) return LEAP_OK;

    char url[600];
    snprintf(url, sizeof(url), "%s/functions", c->base_url);

    Buffer resp;
    LEAPError err = http_get(c, url, &resp);
    if (err != LEAP_OK) return err;

    c->functions = cJSON_Parse(resp.data);
    buf_free(&resp);

    if (!c->functions) {
        set_error(c, "Invalid JSON from /functions endpoint");
        return LEAP_ERR_PROTOCOL;
    }
    return LEAP_OK;
}


/* ── Lifecycle ── */

LEAPClient* leap_create(const char* server_url, const char* student_id,
                         const char* experiment, const char* trial) {
    if (!server_url || !student_id || !experiment) return NULL;

    LEAPClient* c = (LEAPClient*)calloc(1, sizeof(LEAPClient));
    if (!c) return NULL;

    c->server_url = strdup_safe(server_url);
    c->student_id = strdup_safe(student_id);
    c->experiment = strdup_safe(experiment);
    c->trial      = strdup_safe(trial);
    c->functions  = NULL;

    /* Strip trailing slash from server_url */
    size_t slen = strlen(c->server_url);
    while (slen > 0 && c->server_url[slen - 1] == '/')
        c->server_url[--slen] = '\0';

    snprintf(c->base_url, sizeof(c->base_url), "%s/exp/%s",
             c->server_url, c->experiment);

    c->curl = curl_easy_init();
    if (!c->curl) {
        leap_destroy(c);
        return NULL;
    }

    /* Eagerly discover functions (like Python/Julia clients) */
    discover(c);

    return c;
}

void leap_destroy(LEAPClient* c) {
    if (!c) return;
    if (c->curl) curl_easy_cleanup(c->curl);
    if (c->functions) cJSON_Delete(c->functions);
    free(c->server_url);
    free(c->student_id);
    free(c->experiment);
    free(c->trial);
    free(c);
}


/* ── Layer 1: Core RPC ── */

LEAPError leap_call(LEAPClient* c, const char* func_name,
                     const char* args_json, const char* kwargs_json,
                     const char* trial, char** result_json) {
    if (!c || !func_name) return LEAP_ERR_INVALID_ARG;
    if (result_json) *result_json = NULL;

    /* Build JSON payload */
    cJSON* payload = cJSON_CreateObject();
    cJSON_AddStringToObject(payload, "student_id", c->student_id);
    cJSON_AddStringToObject(payload, "func_name", func_name);

    /* Parse args array */
    cJSON* args = cJSON_Parse(args_json ? args_json : "[]");
    if (!args) {
        set_error(c, "Invalid args JSON: %s", args_json ? args_json : "(null)");
        cJSON_Delete(payload);
        return LEAP_ERR_INVALID_ARG;
    }
    cJSON_AddItemToObject(payload, "args", args);

    /* Optional kwargs */
    if (kwargs_json) {
        cJSON* kwargs = cJSON_Parse(kwargs_json);
        if (kwargs) {
            cJSON_AddItemToObject(payload, "kwargs", kwargs);
        }
    }

    /* Trial: per-call override > client default > null */
    const char* t = trial ? trial : c->trial;
    if (t) {
        cJSON_AddStringToObject(payload, "trial", t);
    } else {
        cJSON_AddNullToObject(payload, "trial");
    }

    char* body = cJSON_PrintUnformatted(payload);
    cJSON_Delete(payload);

    if (!body) {
        set_error(c, "Failed to serialize JSON payload");
        return LEAP_ERR_PROTOCOL;
    }

    /* POST to /call */
    char url[600];
    snprintf(url, sizeof(url), "%s/call", c->base_url);

    Buffer resp;
    LEAPError err = http_post_json(c, url, body, &resp);
    free(body);

    if (err != LEAP_OK) return err;

    /* Parse response */
    cJSON* json = cJSON_Parse(resp.data);
    buf_free(&resp);

    if (!json) {
        set_error(c, "Invalid JSON response for '%s'", func_name);
        return LEAP_ERR_PROTOCOL;
    }

    cJSON* result = cJSON_GetObjectItemCaseSensitive(json, "result");
    if (!result) {
        set_error(c, "Missing 'result' in response for '%s'", func_name);
        cJSON_Delete(json);
        return LEAP_ERR_PROTOCOL;
    }

    /* Serialize result back to JSON string */
    if (result_json) {
        *result_json = cJSON_PrintUnformatted(result);
    }

    cJSON_Delete(json);
    return LEAP_OK;
}

LEAPError leap_list_functions(LEAPClient* c, char** json_out) {
    if (!c || !json_out) return LEAP_ERR_INVALID_ARG;
    *json_out = NULL;

    LEAPError err = discover(c);
    if (err != LEAP_OK) return err;

    *json_out = cJSON_PrintUnformatted(c->functions);
    return LEAP_OK;
}

void leap_help(LEAPClient* c) {
    if (!c) return;
    if (discover(c) != LEAP_OK) {
        printf("Error discovering functions: %s\n", c->last_error);
        return;
    }

    printf("LEAP Client — %s/exp/%s\n", c->server_url, c->experiment);
    printf("Student: %s\n\n", c->student_id);
    printf("Available functions:\n");

    cJSON* func = NULL;
    cJSON_ArrayForEach(func, c->functions) {
        const char* name = func->string;
        cJSON* sig = cJSON_GetObjectItemCaseSensitive(func, "signature");
        cJSON* doc = cJSON_GetObjectItemCaseSensitive(func, "doc");
        cJSON* nolog = cJSON_GetObjectItemCaseSensitive(func, "nolog");
        cJSON* noreg = cJSON_GetObjectItemCaseSensitive(func, "noregcheck");
        cJSON* admin = cJSON_GetObjectItemCaseSensitive(func, "adminonly");

        printf("  %s%s", name, (sig && cJSON_IsString(sig)) ? sig->valuestring : "()");

        /* Badges */
        int has_badge = 0;
        if (nolog && cJSON_IsTrue(nolog))   { printf("%s@nolog", has_badge ? ", " : "  ["); has_badge = 1; }
        if (noreg && cJSON_IsTrue(noreg))   { printf("%s@noregcheck", has_badge ? ", " : "  ["); has_badge = 1; }
        if (admin && cJSON_IsTrue(admin))   { printf("%s@adminonly", has_badge ? ", " : "  ["); has_badge = 1; }
        if (has_badge) printf("]");
        printf("\n");

        if (doc && cJSON_IsString(doc) && doc->valuestring[0]) {
            /* Print each line of docstring indented */
            const char* p = doc->valuestring;
            while (*p) {
                printf("      ");
                while (*p && *p != '\n') { putchar(*p); p++; }
                putchar('\n');
                if (*p == '\n') p++;
            }
        }
    }
}

LEAPError leap_is_registered(LEAPClient* c, int* registered) {
    if (!c || !registered) return LEAP_ERR_INVALID_ARG;
    *registered = 0;

    /* URL-encode student_id into query */
    char url[700];
    char* encoded = curl_easy_escape(c->curl, c->student_id, 0);
    snprintf(url, sizeof(url), "%s/is-registered?student_id=%s",
             c->base_url, encoded);
    curl_free(encoded);

    Buffer resp;
    LEAPError err = http_get(c, url, &resp);
    if (err != LEAP_OK) return err;

    cJSON* json = cJSON_Parse(resp.data);
    buf_free(&resp);
    if (!json) {
        set_error(c, "Invalid JSON from /is-registered");
        return LEAP_ERR_PROTOCOL;
    }

    cJSON* reg = cJSON_GetObjectItemCaseSensitive(json, "registered");
    if (reg && cJSON_IsBool(reg)) {
        *registered = cJSON_IsTrue(reg) ? 1 : 0;
    }

    cJSON_Delete(json);
    return LEAP_OK;
}

LEAPError leap_fetch_logs(LEAPClient* c, int n, const char* order, char** json_out) {
    if (!c || !json_out) return LEAP_ERR_INVALID_ARG;
    *json_out = NULL;

    char* encoded_sid = curl_easy_escape(c->curl, c->student_id, 0);
    char url[700];
    snprintf(url, sizeof(url), "%s/logs?student_id=%s&n=%d&order=%s",
             c->base_url, encoded_sid, n > 0 ? n : 100,
             (order && order[0]) ? order : "latest");
    curl_free(encoded_sid);

    Buffer resp;
    LEAPError err = http_get(c, url, &resp);
    if (err != LEAP_OK) return err;

    /* Return the raw JSON (contains {"logs": [...]}) */
    *json_out = resp.data;
    /* Don't free resp.data — caller owns it via leap_free() */
    return LEAP_OK;
}

const char* leap_last_error(LEAPClient* c) {
    if (!c) return "null client";
    return c->last_error;
}

void leap_free(void* ptr) {
    free(ptr);
}


/* ── Layer 2: Typed convenience ── */

LEAPError leap_call_doubles(LEAPClient* c, const char* func_name,
                             int argc, const double* args, double* result) {
    if (!c || !func_name || !result) return LEAP_ERR_INVALID_ARG;

    /* Build JSON args array */
    cJSON* arr = cJSON_CreateArray();
    for (int i = 0; i < argc; i++) {
        cJSON_AddItemToArray(arr, cJSON_CreateNumber(args[i]));
    }
    char* args_json = cJSON_PrintUnformatted(arr);
    cJSON_Delete(arr);

    char* result_json = NULL;
    LEAPError err = leap_call(c, func_name, args_json, NULL, NULL, &result_json);
    free(args_json);

    if (err != LEAP_OK) return err;

    /* Parse result as double */
    cJSON* val = cJSON_Parse(result_json);
    free(result_json);

    if (!val || !cJSON_IsNumber(val)) {
        set_error(c, "Expected numeric result from '%s', got: %s",
                  func_name, result_json ? result_json : "(null)");
        cJSON_Delete(val);
        return LEAP_ERR_PROTOCOL;
    }

    *result = val->valuedouble;
    cJSON_Delete(val);
    return LEAP_OK;
}

LEAPError leap_call_ints(LEAPClient* c, const char* func_name,
                          int argc, const int* args, int* result) {
    if (!c || !func_name || !result) return LEAP_ERR_INVALID_ARG;

    cJSON* arr = cJSON_CreateArray();
    for (int i = 0; i < argc; i++) {
        cJSON_AddItemToArray(arr, cJSON_CreateNumber(args[i]));
    }
    char* args_json = cJSON_PrintUnformatted(arr);
    cJSON_Delete(arr);

    char* result_json = NULL;
    LEAPError err = leap_call(c, func_name, args_json, NULL, NULL, &result_json);
    free(args_json);

    if (err != LEAP_OK) return err;

    cJSON* val = cJSON_Parse(result_json);
    free(result_json);

    if (!val || !cJSON_IsNumber(val)) {
        set_error(c, "Expected integer result from '%s'", func_name);
        cJSON_Delete(val);
        return LEAP_ERR_PROTOCOL;
    }

    *result = val->valueint;
    cJSON_Delete(val);
    return LEAP_OK;
}

LEAPError leap_call_string(LEAPClient* c, const char* func_name,
                            const char* args_json, char** result) {
    if (!c || !func_name || !result) return LEAP_ERR_INVALID_ARG;
    *result = NULL;

    char* result_json = NULL;
    LEAPError err = leap_call(c, func_name, args_json, NULL, NULL, &result_json);
    if (err != LEAP_OK) return err;

    cJSON* val = cJSON_Parse(result_json);
    free(result_json);

    if (!val) {
        set_error(c, "Invalid JSON result from '%s'", func_name);
        return LEAP_ERR_PROTOCOL;
    }

    if (cJSON_IsString(val)) {
        *result = strdup_safe(val->valuestring);
    } else {
        /* For non-string results, return the JSON representation */
        *result = cJSON_PrintUnformatted(val);
    }

    cJSON_Delete(val);
    return LEAP_OK;
}


/* ── Layer 3: Variadic one-liner ── */

double leap_calld(LEAPClient* c, const char* func_name, int argc, ...) {
    if (!c || !func_name || argc < 0 || argc > 8) return NAN;

    double args[8];
    va_list ap;
    va_start(ap, argc);
    for (int i = 0; i < argc; i++) {
        args[i] = va_arg(ap, double);
    }
    va_end(ap);

    double result;
    LEAPError err = leap_call_doubles(c, func_name, argc, args, &result);
    if (err != LEAP_OK) return NAN;
    return result;
}
