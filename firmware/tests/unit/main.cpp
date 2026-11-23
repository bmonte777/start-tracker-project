// Star Tracker — host test runner. Prints one line per test and a summary; exit code = number of failed tests.
#include "tst.h"
std::vector<TstCase> &tst_registry() { static std::vector<TstCase> r; return r; }
int tst_fail_count = 0;
std::string tst_current;
int main(int argc, char **argv)
{
    int failed = 0, passed = 0;
    std::string only = argc > 1 ? argv[1] : "";
    for (auto &t : tst_registry()) {
        if (!only.empty() && std::string(t.name).find(only) == std::string::npos) continue;
        int before = tst_fail_count;
        printf("%s\n", t.name);
        t.fn();
        bool ok = tst_fail_count == before;
        printf("  %s\n", ok ? "PASS" : "FAIL");
        (ok ? passed : failed)++;
    }
    printf("\n%d passed, %d failed\n", passed, failed);
    return failed;
}
