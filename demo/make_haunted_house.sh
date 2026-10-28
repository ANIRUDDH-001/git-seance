#!/usr/bin/env bash
# Build a small git repository whose history is full of the departed.
# Usage: demo/make_haunted_house.sh [target-dir]   (default: ./haunted-house)
set -euo pipefail

target="${1:-haunted-house}"
rm -rf "$target"
mkdir -p "$target"
cd "$target"
git init -q -b main
git config user.name "Nobody" && git config user.email "nobody@example.com"
git config commit.gpgsign false

# commit "<author>" "<email>" "<iso date>" "<message>"
commit() {
  git add -A
  GIT_AUTHOR_NAME="$1" GIT_AUTHOR_EMAIL="$2" GIT_AUTHOR_DATE="$3" \
  GIT_COMMITTER_NAME="$1" GIT_COMMITTER_EMAIL="$2" GIT_COMMITTER_DATE="$3" \
    git commit -q -m "$4"
}

mkdir -p src lib legacy scripts payroll/src

# ---------------------------------------------------------------- 1999: the old world
cat > legacy/PAYROLL.cbl <<'EOF'
       IDENTIFICATION DIVISION.
       PROGRAM-ID. PAYROLL.
       AUTHOR. E. HALVORSEN.
      * RUNS EVERY FRIDAY AT 02:00. DO NOT TOUCH.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-EMPLOYEE.
          05 WS-NAME        PIC X(30).
          05 WS-HOURS       PIC 9(3)V99.
          05 WS-RATE        PIC 9(3)V99.
          05 WS-GROSS       PIC 9(6)V99.
       PROCEDURE DIVISION.
       MAIN-PARA.
           PERFORM READ-EMPLOYEE
           COMPUTE WS-GROSS = WS-HOURS * WS-RATE
      * TODO: OVERTIME AFTER 40 HOURS (ASKED FOR IN 1999)
           PERFORM WRITE-CHEQUE
           STOP RUN.
       READ-EMPLOYEE.
           ACCEPT WS-NAME.
           ACCEPT WS-HOURS.
           ACCEPT WS-RATE.
       WRITE-CHEQUE.
           DISPLAY "PAY " WS-NAME " THE SUM OF " WS-GROSS.
EOF
commit "Edna Halvorsen" "edna@example.com" "1999-03-15T09:12:00+00:00" "Initial payroll run for the Friday batch"

cat > src/y2k_patch.c <<'EOF'
#include <stdio.h>
#include <time.h>

/* Two-digit years roll over at midnight. This keeps the ledger sane. */
int fix_year(int yy) {
    /* FIXME: this window breaks again in 2050. Someone else's problem. */
    return yy < 50 ? 2000 + yy : 1900 + yy;
}

int main(void) {
    time_t now = time(NULL);
    struct tm *t = localtime(&now);
    printf("The year is %d. We survived.\n", fix_year(t->tm_year % 100));
    return 0;
}
EOF
commit "Edna Halvorsen" "edna@example.com" "1999-12-30T23:40:00+00:00" "Emergency Y2K patch for the ledger"

git rm -q src/y2k_patch.c
commit "Edna Halvorsen" "edna@example.com" "2000-01-02T08:05:00+00:00" "It worked. Nothing happened. Removing the Y2K patch."

# ---------------------------------------------------------------- 2015: the npm years
mkdir -p lib
cat > lib/leftpad.js <<'EOF'
module.exports = leftpad;

// Pads a string on the left. That's it. That's the whole package.
function leftpad (str, len, ch) {
  str = String(str);
  var i = -1;
  if (!ch && ch !== 0) ch = ' ';
  len = len - str.length;
  while (++i < len) {
    str = ch + str;
  }
  return str;
}
EOF
commit "Kai Moreno" "kai@example.com" "2015-06-02T14:00:00+00:00" "Vendor leftpad so we never depend on the internet again"

git rm -q lib/leftpad.js
commit "Priya Raman" "priya@example.com" "2016-03-23T10:30:00+00:00" "Replace leftpad with String.prototype.padStart"

# ---------------------------------------------------------------- 2017: the fax machine
mkdir -p src
cat > src/fax_gateway.py <<'EOF'
"""Send invoices by fax, because the Hargrove account insists."""

import smtplib
import time
from email.message import EmailMessage

FAX_RELAY = "fax-relay.internal"


def send_fax(number, pdf_bytes, retries=3):
    msg = EmailMessage()
    msg["To"] = f"{number}@{FAX_RELAY}"
    msg["Subject"] = "Invoice"
    msg.add_attachment(pdf_bytes, maintype="application", subtype="pdf")
    for attempt in range(retries):
        try:
            with smtplib.SMTP(FAX_RELAY) as relay:
                relay.send_message(msg)
            return True
        except OSError:
            time.sleep(2 ** attempt)
    return False
EOF
commit "Marguerite Okafor" "marguerite@example.com" "2017-02-14T11:00:00+00:00" "Add fax gateway for the Hargrove account"

cat >> src/fax_gateway.py <<'EOF'


def send_cover_page(number, note):
    # TODO: support colour faxes (Hargrove asked twice)
    # HACK: the relay drops pages over 20, so we warn instead of splitting
    return send_fax(number, note.encode("latin-1"))
EOF
commit "Marguerite Okafor" "marguerite@example.com" "2017-05-09T16:20:00+00:00" "Fax cover pages, with a note to Hargrove"

sed -i 's/retries=3/retries=5/' src/fax_gateway.py
commit "Tomás Ibarra" "tomas@example.com" "2019-11-28T09:45:00+00:00" "Fax relay is flaky on holidays: retry 5 times"

# a file that is merely renamed is reincarnated, not dead
cat > src/utils.py <<'EOF'
def chunks(seq, n):
    return [seq[i:i + n] for i in range(0, len(seq), n)]
EOF
commit "Tomás Ibarra" "tomas@example.com" "2020-04-01T12:00:00+00:00" "Add chunking helper"
git mv src/utils.py src/helpers.py
commit "Tomás Ibarra" "tomas@example.com" "2020-04-02T12:00:00+00:00" "Rename utils to helpers"

# ---------------------------------------------------------------- 2021: Friday deploys
mkdir -p scripts
cat > scripts/deploy_friday.sh <<'EOF'
#!/bin/sh
# Ship it. What could go wrong at 17:55 on a Friday?
set -e
git pull --rebase
./build.sh
rsync -a dist/ prod:/srv/app/
echo "Deployed. Have a great weekend!"
EOF
commit "Jules Carter" "jules@example.com" "2021-10-29T17:50:00+00:00" "Add a one-command Friday deploy"

git rm -q scripts/deploy_friday.sh
commit "Priya Raman" "priya@example.com" "2021-11-01T09:00:00+00:00" "Remove Friday deploy script. See incident #666. We do not speak of that weekend."

# ---------------------------------------------------------------- 2023-24: the great cleanup
cat > payroll/src/lib.rs <<'EOF'
pub fn gross(hours: f64, rate: f64) -> f64 {
    let overtime = (hours - 40.0).max(0.0);
    (hours - overtime) * rate + overtime * rate * 1.5
}
EOF
git rm -q legacy/PAYROLL.cbl
commit "Dev Patel" "dev@example.com" "2023-09-08T15:00:00+00:00" "Migrate payroll from COBOL to Rust. Overtime finally works. Thank you, Edna."

git rm -q src/fax_gateway.py
commit "Dev Patel" "dev@example.com" "2024-07-19T10:10:00+00:00" "Remove fax support. Hargrove went paperless; the last fax was sent in March 2021."

echo "Built $(pwd): $(git rev-list --count HEAD) commits. Try: git seance graveyard"
