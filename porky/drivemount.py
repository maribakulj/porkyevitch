# Mount Drive on a Colab session from the CLI: open the authorization link in the browser, wait for a go-ahead flag, press Enter.
import os, re, subprocess, sys, time
session, flag, log = sys.argv[1], sys.argv[2], sys.argv[3]
p = subprocess.Popen([os.path.expanduser("~/.local/bin/colab"), "--auth=adc", "drivemount", "-s", session],
                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
opened = False
out = open(log, "w")
for line in p.stdout:
    out.write(line); out.flush()
    m = re.search(r"https://accounts\.google\.com/\S+", line)
    if m and not opened:
        subprocess.run(["open", m.group(0)])  # the link goes to the user's own browser only
        opened = True
        # The "Press Enter" prompt has no newline, so act right after the link: wait for the go-ahead, then press Enter.
        t0 = time.time()
        while not os.path.exists(flag) and time.time() - t0 < 1800:
            time.sleep(2)
        p.stdin.write("\n"); p.stdin.flush()
p.wait()
out.write(f"\nEXIT {p.returncode}\n"); out.close()
