"""Mount Google Drive on a Colab session from the command line (google-colab-cli 0.7.5 or later; 0.7.4 fails with 'mount failed').

Usage: python -m porky.drivemount SESSION FLAG LOG
`colab drivemount` prints a Google authorization link, then waits for Enter. This opens the link in the user's own browser, waits
for FLAG to exist (created once the user has clicked « Autoriser » and seen « Please close this tab »), then sends Enter. Without
the flag after 30 min, it stops the command without sending Enter. Exits 0 only if Colab printed 'Mounted at'.
One authorization per new machine: a relaunch at night waits for the click.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import time

CLI = os.environ.get("PORKY_COLAB", os.path.expanduser("~/.local/bin/colab"))
WAIT_S = 1800


def main() -> int:
    session, flag, log = sys.argv[1:4]
    p = subprocess.Popen([CLI, "--auth=adc", "drivemount", "-s", session], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True, bufsize=1)
    opened = mounted = False
    with open(log, "w") as out:
        for line in p.stdout:
            out.write(line)
            out.flush()
            mounted = mounted or "Mounted at" in line
            m = re.search(r"https://accounts\.google\.com/\S+", line)
            if m and not opened:
                subprocess.run(["open", m.group(0)])  # the link goes to the user's own browser only
                opened = True
                # The "Press Enter" prompt has no newline: wait for the go-ahead right after the link.
                t0 = time.time()
                while not os.path.exists(flag) and time.time() - t0 < WAIT_S:
                    time.sleep(2)
                if not os.path.exists(flag):
                    p.kill()
                    out.write("\nNO GO-AHEAD: stopped without pressing Enter\n")
                    return 2
                p.stdin.write("\n")
                p.stdin.flush()
        p.wait()
        out.write(f"\nEXIT {p.returncode} mounted={mounted}\n")
    return 0 if mounted else 1


if __name__ == "__main__":
    sys.exit(main())
