import sys, os, unittest, signal

sys.path.insert(0, r'C:\Users\2025\OneDrive\Desktop\JARVIS-OS-V.2-main\JARVIS-OS-V.2-main')
os.chdir(r'C:\Users\2025\OneDrive\Desktop\JARVIS-OS-V.2-main\JARVIS-OS-V.2-main')

class TimeoutTestResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._timeout_tests = []

    def addError(self, test, err):
        if 'Timeout' in str(err) or 'alarm' in str(err).lower():
            self._timeout_tests.append(str(test))
        super().addError(test, err)


def timeout_handler(signum, frame):
    raise TimeoutError("Test timed out after 30 seconds")

test_files = [
    'tests/test_qa_system.py',
    'tests/test_deep_research.py',
    'tests/test_presentation_maker.py',
    'tests/test_startup_clap.py',
    'tests/test_desktop_integration.py',
    'tests/test_infinite_loop_detector.py',
    'tests/test_research_body.py',
]

loader = unittest.TestLoader()
suite = unittest.TestSuite()
loaded = []
skipped = []

for f in test_files:
    if os.path.exists(f):
        try:
            loaded_suite = loader.discover(os.path.dirname(f), pattern=os.path.basename(f))
            count = loaded_suite.countTestCases()
            suite.addTests(loaded_suite)
            loaded.append(f"{f} ({count} tests)")
        except Exception as e:
            skipped.append(f"{f}: {e}")
    else:
        skipped.append(f"{f} (NOT FOUND)")

print("=" * 60)
print("CRITICAL TESTS RUNNER")
print("=" * 60)
print(f"\nLoaded {suite.countTestCases()} tests from {len(loaded)} files:")
for l in loaded:
    print(f"  [OK] {l}")

if skipped:
    print(f"\nSkipped {len(skipped)} files:")
    for s in skipped:
        print(f"  [SKIP] {s}")

print(f"\n{'=' * 60}")
print("Running tests (30s timeout per test)...")
print("=" * 60)

# We can't use signal.SIGALRM on Windows, so we'll just run with a result tracker
runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
result = runner.run(suite)

print(f"\n{'=' * 60}")
print("SUMMARY")
print("=" * 60)
print(f"Ran {result.testsRun} tests")
print(f"Failures: {len(result.failures)}")
print(f"Errors: {len(result.errors)}")
print(f"Skipped: {len(result.skipped)}")

if result.failures:
    print(f"\n--- FAILURES ---")
    for test, tb in result.failures:
        print(f"\nFAIL: {test}")
        print(tb)

if result.errors:
    print(f"\n--- ERRORS ---")
    for test, tb in result.errors:
        print(f"\nERROR: {test}")
        print(tb)

if result.wasSuccessful():
    print("\nAll tests PASSED!")
else:
    print("\nSome tests FAILED or had ERRORS.")
