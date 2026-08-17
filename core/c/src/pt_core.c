/*
 * pt_core.c — version and error strings.
 *
 * A face calls pt_api_version() at load and refuses politely on a MAJOR
 * mismatch instead of crashing against a core it was not built for. That one
 * check is what makes a GUI rebuild cheap and independent of the core.
 */

#include "pt_internal.h"

#define PT_STR2(x) #x
#define PT_STR(x)  PT_STR2(x)

unsigned pt_api_version(void)
{
    return ((unsigned)PT_API_VERSION_MAJOR << 16) | (unsigned)PT_API_VERSION_MINOR;
}

const char *pt_version_string(void)
{
    return PT_STR(PT_API_VERSION_MAJOR) "." PT_STR(PT_API_VERSION_MINOR) ".0";
}

const char *pt_strerror(pt_err e)
{
    switch (e) {
    case PT_OK:            return "ok";
    case PT_E_INVAL:       return "invalid argument";
    case PT_E_NOMEM:       return "out of memory";
    case PT_E_PARSE:       return "parse error";
    case PT_E_IO:          return "I/O error";
    case PT_E_NOTFOUND:    return "not found";
    case PT_E_UNSUPPORTED: return "unsupported in this build";
    case PT_E_TYPE:        return "wrong type";
    case PT_E_TRUNCATED:   return "buffer too small";
    }
    return "unknown error";
}
