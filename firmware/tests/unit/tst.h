// Star Tracker — minimal test framework for the host tests (no external dependency).
#pragma once
#include <cmath>
#include <cstdio>
#include <functional>
#include <string>
#include <vector>
struct TstCase { const char *name; std::function<void()> fn; };
std::vector<TstCase> &tst_registry();
extern int tst_fail_count;
extern std::string tst_current;
struct TstReg { TstReg(const char *n, std::function<void()> f) { tst_registry().push_back({n, f}); } };
#define TST_CAT2(a, b) a##b
#define TST_CAT(a, b) TST_CAT2(a, b)
#define TEST(name) static void name(); static TstReg TST_CAT(reg_, name)(#name, name); static void name()
#define CHECK(c) do { if (!(c)) { tst_fail_count++; printf("    FAIL %s:%d  %s\n", __FILE__, __LINE__, #c); } } while (0)
#define CHECK_NEAR(a, b, tol) do { double _a = (a), _b = (b); if (!(std::fabs(_a - _b) <= (tol))) { tst_fail_count++; \
    printf("    FAIL %s:%d  %s = %.9g, expected %.9g +/- %g\n", __FILE__, __LINE__, #a, _a, _b, (double)(tol)); } } while (0)
#define NOTE(...) do { printf("    "); printf(__VA_ARGS__); printf("\n"); } while (0)
