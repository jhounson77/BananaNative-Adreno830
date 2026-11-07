// NPLN (nn::npln, Nintendo's network platform library: the client of the online services, statically linked into
// the Switch 2 sdk module together with its gRPC-over-libcurl stack). On the host it has neither Nintendo's
// backend nor a network path to one, and the library does not degrade into a Result a game could handle:
// The Legend of Zelda: Ocarina of Time's boot got as far as its NPLN setup (the _npln: romfs mount, the
// nn.npln.Worker / nn.npln.Callback / npln-grpc executor / Porter / LibcurlGc threads up) and aborted 0.3 s in
// with a bare nn::diag abort - no message, no file, Result 0, the VAbortImpl call at sdk+0xb8fe8 under a caller
// that left no named frame - the library's own assert, not a checked call. So none of it runs: every non-weak
// import of a _ZN2nn4npln symbol is bound at load time (loader.c bind_sym) to one of the host's named stubs
// instead of the sdk module's definition. A stub returns 0 - the SDK's success Result, false for the Is* getters,
// null for a pointer - and logs the symbol once per name here, then each function's first call (UNIMPL, with
// x0-x2), so a boot that needs more than the zero answers stops at one of those calls, readably, and the log
// names the functions whose real answers are wanted. Data symbols stay with the sdk module's own zero-initialized
// definitions: a stub's instruction bytes read as data would not do.
// Platform limit: the cause (no Nintendo NPLN backend on the host) is where it cannot be fixed; per-function HLE
// replaces the stubs as the calls that need them show up in the logs.
#include "hle.h"
#include <string.h>

uint64_t resolve_import(module_t *m, const char *name);   // hle.c: the named stubs (return 0, UNIMPL on the first call)

#define NPLN_PREFIX "_ZN2nn4npln"
#define NPLN_LISTED 96

// The stub for a module's import of a _ZN2nn4npln symbol: 1 with *out = the stub's address, 0 when the name is
// not one of NPLN's. Bind-time (the load holds no other threads), so the once-per-name list needs no lock
int dm_npln_import(const char *module, const char *name, uint64_t *out) {
    if (strncmp(name, NPLN_PREFIX, sizeof NPLN_PREFIX - 1)) return 0;
    *out = resolve_import(NULL, name);
    static const char *listed[NPLN_LISTED]; static unsigned nlisted, nover;
    for (unsigned i = 0; i < nlisted && i < NPLN_LISTED; i++) if (!strcmp(listed[i], name)) return 1;
    if (nlisted < NPLN_LISTED) { listed[nlisted++] = name; LOG("[npln] %s imports %s → host stub (returns 0; the NPLN library does not run)", module, name); }
    else if (!nover++) LOG("[RED] [npln] %s imports more than %d _ZN2nn4npln symbols; the rest take the same stubs unlisted", module, NPLN_LISTED);
    return 1;
}
