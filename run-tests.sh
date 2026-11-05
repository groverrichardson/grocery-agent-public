#!/bin/sh
# Runs every test on made-up data. Touches no store, no Reminders list and no real order history.
set -e
cd "$(dirname "$0")"
export PYTHONDONTWRITEBYTECODE=1
python3 test_feedback.py
python3 tests/test_sample_run.py
node tests/test_add_walmart.js
if ADD_WALMART_SCRIPT=tests/fixtures/add_walmart.before-fix.js node tests/test_add_walmart.js >/dev/null; then
  echo "FAIL the old add script should fail the regression test"; exit 1
fi
echo "pass the old add script still fails the regression test"
echo "ALL TESTS PASSED"
