# Friday Training: Linux for Data Engineering

> Status: Draft  
> Level: Beginner  
> Applies to: Linux / Bash / Batch / Operations  
> Data scale: Local fixture; production implications identified  
> Example status: Walkthrough complete; execution pending  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

Linux is underneath much of the data-engineering world: servers, containers, Spark workers, Kafka brokers, databases, schedulers, and cloud virtual machines. A data engineer need not become a full-time Linux administrator, but must be able to navigate data safely, automate repeatable work, and investigate failed jobs.

The terminal is not only a fallback when VS Code lacks a feature. VS Code is usually better for authoring and reviewing code; the shell is often better for:

- working on remote machines over SSH;
- composing small tools into a repeatable inspection;
- checking permissions, disk, processes, services, and logs;
- running the same operation locally, in CI, and on a server; and
- automating non-interactive work.

This resembles using `./gradlew test` even when Android Studio has a test button: the command is explicit, repeatable, and usable by CI. The analogy stops where the shell directly manages operating-system resources and combines unrelated programs through text streams.

This guide focuses on filesystems, permissions, `grep`/`awk`/`sed`, processes, cron, shell automation, and operational logs. It is not a catalog of every Linux command, an advanced administration guide, or a replacement for Python, SQL, or a workflow orchestrator.

## Learning objectives

After completing this guide, you should be able to:

- navigate a Linux filesystem and measure file and disk usage;
- explain file ownership and read, write, and execute permissions;
- inspect line-oriented data and logs with `grep`, `awk`, and `sed`;
- find, observe, and terminate a process safely;
- schedule a small recurring job with cron and identify cron's limitations;
- write a Bash wrapper that fails visibly and publishes output atomically; and
- follow operational logs from a symptom to a likely cause.

## Prerequisites and environment

The walkthroughs assume Bash on Linux. On Windows, use WSL 2 with a Linux distribution; run these paths and commands inside WSL, not PowerShell.

```bash
uname -a
printf 'shell=%s\n' "$SHELL"
pwd
```

Examples use a learning directory under the current user's home and require no `sudo`.

## Mental model: commands transform streams

```text
stdin (0) ---> command ---> stdout (1)
                   |
                   +-----> stderr (2)
```

- **stdin** supplies input.
- **stdout** carries the requested result.
- **stderr** carries diagnostics.
- Exit status `0` normally means success; nonzero means failure.

| Operator | Meaning | Example |
| --- | --- | --- |
| `|` | Send stdout into another command | `grep ERROR app.log | wc -l` |
| `>` / `>>` | Replace / append a file with stdout | `command >> run.log` |
| `2>` | Send stderr to a file | `command 2> errors.log` |
| `2>&1` | Send stderr to stdout's destination | `command > run.log 2>&1` |
| `&&` | Continue only after success | `validate && publish` |

Pipeline data and pipeline status are different contracts. A command may emit rows yet still exit nonzero because it could not complete correctly.

## Running example: an hourly order feed

A partner delivers pipe-delimited orders. Each record is one order. The file in `incoming/` is the authoritative received copy; summaries in `published/` are derived and rebuildable.

```bash
mkdir -p ~/linux-data-lab/{incoming,work,published,logs,archive}
cd ~/linux-data-lab

printf '%s\n' \
  'order_id|event_time|region|amount_cents|status' \
  'o-1001|2026-09-11T13:00:04Z|west|1299|PAID' \
  'o-1002|2026-09-11T13:04:32Z|east|2500|PAID' \
  'o-1003|2026-09-11T13:05:10Z|west|500|DECLINED' \
  'BROKEN|not-a-timestamp|west||PAID' \
  > incoming/orders-2026-09-11-13.psv

printf '%s\n' \
  '2026-09-11T13:00:01Z level=INFO run_id=run-42 event=start file=orders-2026-09-11-13.psv' \
  '2026-09-11T13:00:02Z level=INFO run_id=run-42 event=accepted order_id=o-1001' \
  '2026-09-11T13:00:03Z level=ERROR run_id=run-42 event=rejected line=5 reason=missing_amount' \
  '2026-09-11T13:00:04Z level=INFO run_id=run-42 event=complete accepted=3 rejected=1' \
  > logs/orders-pipeline.log
```

The fixture is deliberately tiny. These tools scan text line by line and are excellent for sampling and incidents, not replacements for a distributed engine over terabytes.

## Filesystem

Linux has one directory tree rooted at `/`. Absolute paths start with `/`; relative paths are resolved from `pwd`.

| Path | Meaning for a data engineer | Why w/ Example |
| --- | --- | --- |
| `/` | Root of the filesystem, not the user's workspace | Needed to access all system files when trying to inspect or modify system-wide configurations |
| `~` or `/home/<user>` | Current user's home | Personal workspace and configuration files, including scripts and local data |
| `/etc` | Host and service configuration | Central location for system and service settings, including network and authentication configurations when you'd need to update something like user accounts or service parameters |
| `/var/log` | Traditional host and service logs | Central location for log files, useful for troubleshooting and auditing system and service behavior |
| `/tmp` | Temporary data; persistence is not guaranteed | Suitable for short-lived files, inspect things like temporary logs or intermediate data |
| `/mnt` | Common mount point for other filesystems | Used to access additional storage devices, useful for mounting external drives or network filesystems |
| `.` / `..` | Current directory / parent directory | Navigate relative to the current location, select current or parent directories |

### Commands and when to use them

| Goal | Command | Why it matters |
| --- | --- | --- |
| Locate yourself | `pwd` | Verify relative-path resolution |
| List metadata | `ls -lah` | See hidden files, owners, modes, and sizes |
| Navigate | `cd path`, `cd ..` | Move without changing data |
| Make a layout | `mkdir -p path` | Repeatably create parent directories |
| Preview | `head -n 5 file`, `tail -n 20 file` | Check headers and recent log records |
| Measure a file | `wc -l file`, `wc -c file` | Quick volume sanity checks |
| Find paths | `find path -type f -name '*.psv'` | Discover files or partitions |
| Path usage | `du -sh path` | Find large datasets |
| Disk capacity | `df -h path` | Check the filesystem holding a path |
| Identify format | `file path` | Detect text, compression, or binary data |
| Copy / move | `cp source dest`, `mv source dest` | Derive a copy or relocate/rename |

### Walkthrough: inspect a delivery

```bash
cd ~/linux-data-lab
pwd
ls -lah incoming 
head -n 3 incoming/orders-2026-09-11-13.psv
wc -l incoming/orders-2026-09-11-13.psv
du -sh incoming
df -h incoming
find incoming -type f -name 'orders-*.psv' -print
```

`head` previews the first few lines of a file, useful for quickly inspecting headers or initial records. `wc -l` counts the number of lines in a file, which helps verify the expected number of records. `du -sh` shows the disk usage of a directory or file in a human-readable format, and `df -h` displays the available disk space on the filesystem containing the path. `find` helps locate specific files based on patterns and criteria. `-type f` restricts the search to regular files. `-name 'pattern'` matches filenames against the specified pattern. `-print` outputs the matching paths to the terminal.

`wc -l` should report five physical lines: one header and four records. `du` reports space used by the path; `df` reports remaining capacity on its filesystem. Existence does not prove completeness—a producer may still be writing the file.

Publish through a candidate file in the destination filesystem:

```bash
printf '%s\n' 'region|paid_orders|amount_cents' > published/.summary.tmp
mv published/.summary.tmp published/summary.psv
```

A same-filesystem rename is atomic: consumers see the old name or new name, not a partially written file. This does not make a multi-file dataset transactional, and a move across filesystems may become copy-then-delete.

`rm -r` recursively removes a tree and usually has no undo. Preview retention targets before an authorized deletion:

```bash
find archive -type f -mtime +30 -print
```

Do not learn deletion by pasting broad wildcards into `rm`.

## Permissions and ownership

```text
-rw-r----- 1 pipeline analytics 418 Sep 11 13:05 orders.psv
             owner    group
```

The first character is the type (`-` file or `d` directory). The next nine are three `rwx` groups for owner, group, and others.

| Permission | Regular file | Directory |
| --- | --- | --- |
| `r` | Read bytes | List entry names |
| `w` | Change bytes | Create, rename, or delete entries |
| `x` | Execute | Traverse/access entries through it |

Directory permissions are subtle: deletion is mainly controlled by the containing directory, not the file's write bit. Ownership and access are also separate. An owner can normally change a file's mode after removing their own read/write access.

```bash
ls -ld incoming incoming/orders-2026-09-11-13.psv
id
chmod u+x script.sh
chmod 640 data.psv
chmod 750 pipeline-directory
chown pipeline:analytics data.psv  # normally requires elevated authority
umask
```

`ls -l` shows detailed information about files, including permissions, ownership, size, and modification time. `-ld` shows information about the directory itself rather than its contents. `id` displays the current user's identity and group memberships. `chmod` changes file permissions, `chown` changes ownership, and `umask` sets default permission masks for newly created files.

Numeric modes add `r=4`, `w=2`, and `x=1` for each identity class: `chmod r=4,w=2,x=1` = `chmod 7` (read+write+execute) for the corresponding identity class. `chmod 3` would correspond to `w+x` (write+execute) for the identity class.

`u`, `g`, and `o` refer to the user (owner), group, and others, respectively, when specifying permissions with `chmod`. `chmod u+r` adds read permission for the user, `chmod g-w` removes write permission for the group, and `chmod o+x` adds execute permission for others.

| Mode | Typical intent |
| --- | --- |
| `600` | Private read/write file, such as a credential |
| `640` | Owner writes; approved group reads |
| `700` | Private executable or directory |
| `750` | Owner manages; approved group reads/traverses |
| `755` | Publicly readable/traversable executable content |

Avoid `chmod 777`; it lets every local user mutate the path and hides an ownership-design problem. `sudo` is not a routine permission repair—root can bypass many checks and may create root-owned outputs that later jobs cannot use.

### Walkthrough: least privilege

```bash
cd ~/linux-data-lab
ls -l incoming/orders-2026-09-11-13.psv
chmod go-rwx incoming/orders-2026-09-11-13.psv
chmod u+rw incoming/orders-2026-09-11-13.psv
ls -l incoming/orders-2026-09-11-13.psv
```

In production, a service account might own incoming files and an `analytics` group might read published data. Interactive users should not mutate immutable raw data. Protect parent directories too, and never put secrets in scripts, command arguments, or logs; arguments may be visible in process listings. Process listings are accessible via commands like `ps` and can reveal sensitive information.

## `grep`, `awk`, and `sed`

- `grep` selects lines matching a pattern.
- `awk` splits records into fields and computes/formats results.
- `sed` selects or substitutes line-oriented text.

They suit logs and simple delimiters. They are not correct parsers for quoted CSV, nested JSON, Parquet, or Avro. `awk -F','` misreads a quoted CSV field that contains a comma; use Python's `csv` module or another format-aware tool.

Example:
```csv
order_id,customer_name,order_date,amount_cents,status
1,"Doe, John",2026-09-11,1299,PAID
2,"Jones, Jane",2026-09-11,1500,PAID
3,"Johnson, Bob",2026-09-11,1000,PENDING
4,"Brown, Alice",2026-09-11,0,REJECTED
```

`awk -F',' '{print NF}' example.csv` -> prints the number of fields in each row. Unfortunately, it will miscount fields if a CSV field contains a comma within quotes. Use a CSV-aware parser for accurate field counts.

```python
import csv

with open('example.csv', newline='') as csvfile:
    reader = csv.reader(csvfile)
    for row in reader:
        print(len(row))
```

### `grep`: select relevant lines

```bash
grep 'level=ERROR' logs/orders-pipeline.log
grep -nE 'level=(ERROR|WARN)' logs/orders-pipeline.log
grep -i 'missing_amount' logs/orders-pipeline.log
grep -v 'level=INFO' logs/orders-pipeline.log
grep -r --include='*.log' 'run_id=run-42' logs
grep -c 'event=rejected' logs/orders-pipeline.log
```

Options: `-n` line numbers, `-i` ignore case, `-v` invert (select non-matching lines), `-r` recurse, `-c` count, and `-E` extended regex. Quote patterns so the shell does not interpret them.

| Extended regex | Meaning |
| --- | --- |
| `^ERROR` / `complete$` | Text at start / end of line |
| `[0-9]+` | One or more ASCII digits |
| `ERROR|WARN` | Either alternative |
| `[^|]+` | Characters other than `|` |

Regex recognizes text shape, not semantic validity. A timestamp-shaped string may still be an impossible date.

### `awk`: fields and aggregates

With `-F'|'`, `$1` through `$5` are fields, `$0` is the record, and `NR` is its line number.

```bash
awk -F'|' '
  NR > 1 && $5 == "PAID" {count += 1; cents += $4}
  END {printf "paid_orders=%d amount_cents=%d\n", count, cents}
' incoming/orders-2026-09-11-13.psv

# NR > 1 skips the header row.
# $5 == "PAID" filters for paid orders.
# count and cents accumulate the number and total amount of paid orders.
# END, stop block executes after all input is processed and prints the final accumulated counts of paid orders and their total amount in cents. 

awk -F'|' 'NR > 1 && ($2 !~ /Z$/ || $4 !~ /^[0-9]+$/) {print NR ":" $0}' \
  incoming/orders-2026-09-11-13.psv

# NR > 1 skips the header row.
# $2 !~ /Z$/ filters for invalid order IDs.
# $4 !~ /^[0-9]+$/ filters for non-numeric amounts.
# The print statement outputs the line number and the full record for any malformed rows.
```

The aggregate should report two paid orders and 3,799 cents. The second command identifies the malformed record. These are smoke checks, not a complete data contract: they do not prove key uniqueness, valid calendar time, completeness, accepted statuses, or safe numeric bounds.

### `sed`: preview transformations

```bash
sed -n '1,3p' incoming/orders-2026-09-11-13.psv
# Print the first three lines of the file.

sed 's/|DECLINED$/|REJECTED/' incoming/orders-2026-09-11-13.psv
# Replace the status DECLINED with REJECTED at the end of the line.

sed '/^BROKEN|/d' incoming/orders-2026-09-11-13.psv
# Delete lines starting with BROKEN|.
```

These print to stdout without changing the input. Avoid `sed -i` on immutable raw data; write a candidate, validate it, and publish under a new path. `sed -i` would edit in place, which is not recommended for raw data.

### Walkthrough: investigate one run

```bash
grep 'run_id=run-42' logs/orders-pipeline.log
grep 'run_id=run-42' logs/orders-pipeline.log | grep 'level=ERROR'
grep 'run_id=run-42' logs/orders-pipeline.log | awk '{print $2, $4, $6}'
grep -c 'event=rejected' logs/orders-pipeline.log
```

This narrows from all run events to errors, selected fields, and a rejection count. For repeated or large analysis, ingest logs into a governed table rather than continually scanning host files.

## Processes and services

A **process** is one running program with a PID. A **service** is a long-running application managed by a supervisor, commonly systemd. A Spark driver, Python batch, JVM, database, and shell script are processes; PostgreSQL or Docker may also be configured as services.

| Goal | Command |
| --- | --- |
| Current shell's processes | `ps` |
| All processes/resources | `ps aux` |
| Find commands by pattern | `pgrep -a -f 'pattern'` |
| Inspect one process | `ps -p PID -o pid,ppid,stat,%cpu,%mem,etime,cmd` |
| Live CPU/memory | `top` |
| Host memory / load | `free -h`, `uptime` |
| Process open files | `lsof -p PID` when installed/authorized |

`ps aux | grep python` can match `grep` and unrelated users. Prefer a specific `pgrep` pattern and inspect owner/full command before signaling anything.

### Shell jobs and temporary background work

```bash
sleep 300 &
jobs
fg %1
# Ctrl+C interrupts the foreground process.
```

`&` backgrounds a job. `Ctrl+Z` suspends it; `bg` resumes it; `fg` foregrounds it. `jobs` only knows jobs in the current shell. If you want all jobs across all shells, you need to inspect processes with `ps` or `pgrep`.

`nohup command > logs/job.log 2>&1 &` may survive logout but supplies no schedule, retry policy, dependencies, health check, ownership, or centralized history. It is for temporary experiments, not production orchestration.

### Terminate gracefully

```bash
pgrep -a -f 'sleep 300'
kill PID       # SIGTERM: request graceful shutdown
ps -p PID      # verify the result
```

Use `kill -9 PID` (`SIGKILL`) only if graceful termination fails and impact is understood. It cannot be handled, so a job may leave partial output or stale locks. `pkill` may affect multiple matches; preview with `pgrep -a` first.

### Services with systemd

```bash
systemctl status postgresql
systemctl is-active postgresql
sudo systemctl restart postgresql
journalctl -u postgresql -n 50 --no-pager
journalctl -u postgresql -f
```

`systemctl` reports lifecycle state; `journalctl` shows what the service logged. Shared-state changes require authorization. Do not restart a production service merely because one client job failed. Some WSL/container environments do not run systemd; use that environment's supervisor instead.

## Cron

Cron starts commands at wall-clock times. It suits small independent host-local jobs but knows nothing about datasets, upstream dependencies, backfills, data intervals, or distributed retries.

```text
minute hour day-of-month month day-of-week command
   0    *       *          *        *       run hourly
  30    2       *          *        *       run daily at 02:30
```

minute (0-59)
hour (0-23)
day-of-month (1-31)
month (1-12)
day-of-week (0-7, 0 or 7 is Sunday)

```bash
crontab -l   # list this user's entries
crontab -e   # edit this user's entries
```

Avoid `crontab -r`; it removes the user's entire crontab.

### A safer cron entry

```cron
SHELL=/bin/bash
PATH=/usr/local/bin:/usr/bin:/bin

5 * * * * /usr/bin/flock -n /tmp/orders-pipeline.lock /home/evan/linux-data-lab/bin/run-orders.sh >> /home/evan/linux-data-lab/logs/cron.log 2>&1
```

Adapt the user and paths (/home/evan). This runs hourly at minute five, uses absolute paths, captures stdout/stderr, uses Linux `flock` against overlap, and keeps logic in a version-controlled script. `flock` ensures that only one instance of the job runs at a time, preventing concurrent execution. Then it outputs `>>` to the specified log file and `2>&1` redirects stderr to the same log file.

Adapt the username and paths (home/evan/) for the target machine. This job runs hourly at minute five. It uses absolute paths and invokes a version-controlled script rather than embedding application logic in the crontab. `flock -n` ensures that only one instance runs at a time. `>>` appends stdout (expected output) to cron.log, and `2>&1` redirects stderr (errors and warnings) to the same log.

- `flock -n` attempts to acquire an exclusive lock and does not wait if another invocation holds it. If the lock is unavailable, this invocation exits immediately—so it prevents overlap by skipping that run.
- stderr (errors and warnings) are not captured by `>>`; you need to use `2>&1` to redirect them.
  - `>>` appends to a file, rather than overwriting it `>`.
  - `1>` represents stdout, and `2>` represents stderr. `&1` redirects stderr to the same destination as stdout.
  - if you wanted to send stdout and stderr to separate files, you could use `1>stdout.log 2>stderr.log`.

Before relying on cron, answer:

- Which time zone does the host use, including daylight-saving behavior?
- How is a missed run after downtime recovered?
- Is rerunning the same input safe?
- Where are history, failure alerts, and bounded logs retained?
- Who owns retries, timeouts, backfills, and stale locks?

Use a workflow orchestrator when work requires dependencies, retries, backfills, concurrency controls, centralized metadata, or alerts. Cron launches a command; it does not prove the expected data arrived or consumers received correct output.
- Apache Airflow and Prefect are popular workflow orchestrators

## Shell automation

Explore interactively; write a script when work must be repeatable, reviewed, scheduled, or handed to another engineer.

### Bounded batch wrapper

Create `~/linux-data-lab/bin`, then save this as `bin/run-orders.sh`:

Before reading the wrapper, distinguish assignment, expansion, and invocation:

| Intent | Bash syntax | Meaning |
| --- | --- | --- |
| Assign a variable | `BASE_DIR="${HOME}/linux-data-lab"` | There must be no spaces around `=`. With spaces, Bash tries to run `BASE_DIR` as a command. |
| Make an assigned variable immutable | `readonly BASE_DIR="..."` | `readonly` is a Bash builtin that marks the variable read-only after assigning it. |
| Expand a variable | `"$BASE_DIR"` or `"${BASE_DIR}"` | `$` asks Bash for the variable's value. Braces make the variable name boundary explicit. Prefer double quotes so the result remains one argument even if it contains spaces or wildcard characters. |
| Define a function | `cleanup() { commands; }` | This defines the function but does not run it. The `;` separates the final command from `}` when both are on one line. A newline can be used instead. |
| Call a function | `cleanup` | Commands and functions are invoked by name: do not add `$` or parentheses. |

Whitespace is syntax in Bash because it separates a command from its arguments. `rm -f -- "$candidate"` calls `rm` with three arguments: `-f`, `--`, and the expanded candidate path. Assignment is the important exception: `name=value` has no spaces around `=`. Tests require spaces because `[[`, `!`, `-r`, `"$INPUT"`, and `]]` are separate syntax tokens: `[[ ! -r "$INPUT" ]]`.

A newline normally ends a command. A semicolon ends a command on the same line, so these function definitions are equivalent:

```bash
cleanup() { rm -f -- "$candidate"; }

cleanup() {
  rm -f -- "$candidate"
}
```

The same symbols can mean different things in nested languages. In the Bash parts of this script, `$1` is the function or script's first argument, `${name}` expands a variable, `$(command)` captures a command's stdout, `$$` is the current shell's process ID, and `$?` is the most recent command's exit status. Inside the single-quoted `awk` program, however, `$3`, `$4`, and `$5` mean fields three, four, and five of the current input record; Bash does not expand them because single quotes pass that program text to `awk` literally.
`BEGIN`, `END`, and `for (region in orders)` are also `awk`, not Bash. `BEGIN` runs once before input records are read. The `for` loop visits the keys in awk's `orders` associative array; `region` is assigned each key rather than declared with a separate type. `END` runs once after input processing finishes, and this program deliberately calls `exit 2` from that block when it rejected records. Bash closes its own constructs differently: `if` ends with `fi`, while functions and command groups end with `}`. `EXIT` in `trap cleanup EXIT` is a Bash trap condition meaning “when this shell exits”; it is not the end of a function or script.

```bash
#!/usr/bin/env bash

# Fail on many unhandled command errors (-e), unset expansions (-u), and failed pipeline stages (pipefail).
# -E makes an ERR trap inheritable, although this script defines only an EXIT trap.
set -Eeuo pipefail

# use readonly variables to prevent accidental modification of important paths and identifiers.
# define path variables for input, output, and base directory.
readonly BASE_DIR="${HOME}/linux-data-lab"
readonly INPUT="${1:-${BASE_DIR}/incoming/orders-2026-09-11-13.psv}"
readonly OUTPUT="${BASE_DIR}/published/paid-summary.psv"
readonly RUN_ID="orders-$(date -u +%Y%m%dT%H%M%SZ)-$$"

# Create the candidate in the publication directory so the final rename stays on one filesystem.
# Consumers continue seeing the old output until the complete candidate is renamed over it.
candidate="$(mktemp "${BASE_DIR}/published/.paid-summary.XXXXXX")"
# Define cleanup; the semicolon terminates rm because the closing brace is on the same line.
cleanup() { rm -f -- "$candidate"; }
# Register cleanup for shell exit; this names the function but does not call it now.
# The cleanup is harmless after a successful mv because the old candidate path no longer exists.
trap cleanup EXIT

log() {
  # Function arguments are local positional parameters: $1 and $2 are level and event.
  local level="$1" event="$2"
  # Remove the first two arguments; $* below expands the remaining message arguments.
  shift 2
  printf '%s level=%s run_id=%s event=%s %s\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$level" "$RUN_ID" "$event" "$*"
}

if [[ ! -r "$INPUT" ]]; then
  log ERROR input_unreadable "path=$INPUT" >&2
  exit 66
fi

log INFO start "input=$INPUT"

{
  # This is a Bash command group. Its combined stdout is redirected to the candidate below.
  printf '%s\n' 'region|paid_orders|amount_cents'
  # The single quotes protect the embedded awk program from Bash expansion.
  awk -F'|' '
    BEGIN { OFS="|" }
    NR == 1 {next}
    NF != 5 || $4 !~ /^[0-9]+$/ {rejected += 1; next}
    $5 == "PAID" {orders[$3] += 1; cents[$3] += $4}
    END {
      for (region in orders) print region, orders[region], cents[region]
      if (rejected > 0) {
        print "rejected_records=" rejected > "/dev/stderr"
        exit 2
      }
    }
  ' "$INPUT" | sort
} > "$candidate"

test -s "$candidate"
mv -f -- "$candidate" "$OUTPUT"
log INFO complete "output=$OUTPUT rows=$(wc -l < "$OUTPUT")"
```

Some expansions in the wrapper combine these rules:

- `${1:-default}` means “use the first argument when it is set and nonempty; otherwise use `default`.” Here it lets the caller override the input path safely even with `set -u` enabled.
- `$(date ...)` is command substitution: Bash runs `date` and inserts its stdout into `RUN_ID`.
- `$$` adds this Bash process's ID to `RUN_ID`; it is useful for correlation but is not a globally unique durable identifier.
- `"$*"` expands all remaining function arguments as one string. This logger intentionally uses it for a human-readable message; use `"$@"` when each argument must remain a separate argument.
- `$(wc -l < "$OUTPUT")` sends the file to `wc` through stdin, captures the resulting line count, and inserts it into the log message.
- `>&2` on the `log` call sends that call's stdout to stderr. `exit 66` then terminates the script with a nonzero status.
- `trap cleanup EXIT` runs `cleanup` for ordinary shell exit and exits caused by the script's handled errors. No cleanup mechanism can run after `SIGKILL`, a kernel crash, or power loss, which is one reason the candidate has a recognizable temporary name.

Run it:

```bash
mkdir -p ~/linux-data-lab/bin
chmod 700 ~/linux-data-lab/bin/run-orders.sh
bash -n ~/linux-data-lab/bin/run-orders.sh
~/linux-data-lab/bin/run-orders.sh
printf 'exit_status=%s\n' "$?"
```

`mkdir -p` creates the directory and does not fail if it already exists. `chmod 700` gives only the owner read, write, and execute permissions. `bash -n` parses the script without executing it. The next line invokes the executable script through its shebang. Finally, `$?` must be read immediately because every subsequent command replaces the saved exit status.

The malformed fixture intentionally causes a nonzero exit before publication. That is correct: do not silently publish a result that excluded unknown bad data.

### Why it is shaped this way

- `set -Eeuo pipefail` exposes many command, variable, and pipeline failures; it helps but does not make arbitrary Bash automatically safe.
- Quoted variables prevent whitespace/wildcard expansion changing arguments.
- `mktemp` avoids predictable temporary-name collisions.
- `trap` cleans the candidate after success, error, or handled termination.
- Validation precedes `mv`, so consumers do not see a partial candidate.
- UTC timestamps and `run_id` correlate events.
- Nonzero status lets cron, systemd, CI, or an orchestrator detect failure.

This local example remains incomplete: it does not lock inputs, prove producer completion, deduplicate IDs, reconcile source totals, retain rejected records, or make multi-file publication atomic. Those are production extensions, not reasons to hide invalid input.

If installed, run `shellcheck bin/run-orders.sh` for additional static analysis.

## Operational logs

Logs explain discrete events. They complement **metrics** (numeric behavior over time), **traces** (work across services), and **lineage** (datasets and transformations).

A useful event has a UTC timestamp, severity, stable event name, run/batch/data identifier, outcome, bounded counts, and actionable failure reason. Never log tokens, credentials, or unnecessary personal data. A rejected record may be sensitive; log a safe identifier and place authorized detail in protected quarantine storage.

### File logs and journal

```bash
tail -n 50 logs/orders-pipeline.log
tail -f logs/orders-pipeline.log
grep 'level=ERROR' logs/orders-pipeline.log
grep 'run_id=run-42' logs/orders-pipeline.log

journalctl -u SERVICE --since '1 hour ago' --no-pager
journalctl -u SERVICE -p err -n 100 --no-pager
journalctl -b -p err --no-pager
```

`tail -f` follows appends until `Ctrl+C`. Logs need retention and rotation; an unbounded debug log can fill the disk a pipeline needs for temporary data.

### Incident walkthrough: hourly output is missing

1. Confirm the expected output and timestamp:

   ```bash
   ls -lah --time-style=long-iso published
   ```

2. Check whether input arrived, is nonempty, and appears complete:

   ```bash
   find incoming -maxdepth 1 -type f -name 'orders-*.psv' -print
   wc -l incoming/orders-2026-09-11-13.psv
   tail -n 2 incoming/orders-2026-09-11-13.psv
   ```

3. Inspect run logs:

   ```bash
   tail -n 100 logs/cron.log
   grep -E 'level=(ERROR|WARN)|rejected_records' logs/cron.log
   ```

4. Determine whether a process is still running:

   ```bash
   pgrep -a -f 'run-orders.sh'
   ps -p PID -o pid,ppid,stat,%cpu,%mem,etime,cmd
   ```

5. Check host constraints:

   ```bash
   df -h ~/linux-data-lab
   free -h
   uptime
   ```

6. Reproduce with the exact input safely, fix the cause, rerun idempotently, and verify output contents and consumer recovery.

Do not begin by restarting services or killing processes. First distinguish missing input, bad data, permissions, code, scheduling, resource exhaustion, and dependency failures. A restart can erase evidence and repeat a non-idempotent write.

## Common pitfalls

| Pitfall | Safer approach |
| --- | --- |
| Unquoted variable such as `rm $path` | Quote it and validate the resolved scope |
| `chmod 777` | Design owner/group access and least privilege |
| Parsing general CSV with `awk -F','` | Use a CSV-aware parser |
| Editing raw input with `sed -i` | Write and validate derived data |
| Writing directly to the final name | Candidate plus atomic rename |
| `command &` as production scheduling | Cron for simple work; otherwise supervisor/orchestrator |
| `kill -9` first | Request `SIGTERM`, observe, then escalate if necessary |
| Relative paths in cron | Set environment and use absolute paths |
| No overlap control | Idempotency plus concurrency control/locking |
| Logging complete bad records | Safe identifiers plus protected quarantine |
| Treating existence as completeness | Producer-side atomic publication/completion protocol |

## Choosing the right tool

| Need | Prefer |
| --- | --- |
| Edit/review a script or configuration | VS Code |
| Inspect a remote host, permission, process, disk, or live log | Linux shell |
| Search a few text logs once | `grep`, then `awk`/`sed` if needed |
| Correctly parse structured data | Format-aware library or query engine |
| Run a small independent host-local schedule | Cron |
| Supervise a long-running host service | systemd/platform supervisor |
| Coordinate dependencies, retries, backfills, and metadata | Workflow orchestrator |
| Exceed one machine's practical resources | Distributed engine |

The dividing line is the required contract: interactivity, reproducibility, structure awareness, scale, scheduling, supervision, or recovery.

## Compact command reference

| Area | Commands to remember first |
| --- | --- |
| Filesystem | `pwd`, `ls -lah`, `cd`, `mkdir -p`, `head`, `tail`, `wc`, `find`, `du -sh`, `df -h` |
| Permissions | `ls -l`, `id`, `chmod`, `chown`, `umask` |
| Text | `grep -nE`, `awk -F`, `sed -n`, `sort`, `uniq -c` |
| Processes | `ps`, `pgrep -a`, `top`, `free -h`, `uptime`, `kill` |
| Shell jobs | `&`, `jobs`, `bg`, `fg`, `Ctrl+C`, `Ctrl+Z` |
| Services/logs | `systemctl status`, `journalctl -u`, `tail -f` |
| Scheduling | `crontab -l`, `crontab -e` |
| Checks/help | `bash -n`, `shellcheck`, `man`, `COMMAND --help` |

## Knowledge check

1. Why can a user sometimes delete a read-only file? What permissions matter?
2. Predict `grep 'run_id=run-42' file | grep 'level=ERROR'` before running it.
3. Why is `awk -F','` unsafe as a general CSV parser?
4. A job receives `SIGKILL` while publishing. What could a consumer observe, and how does candidate-plus-rename help?
5. A command works interactively but fails in cron. Which environment, path, permission, working-directory, and logging checks come first?
6. Diagnose a missing hourly dataset without restarting or deleting anything.
7. Extend the wrapper to quarantine invalid rows without logging their contents.

## Key takeaways

- Use the shell for direct host access, composition, repeatability, automation, and operational visibility—not only when the IDE lacks a button.
- Treat paths, permissions, streams, and exit statuses as explicit interfaces.
- Use text tools for line-oriented inspection and format-aware tools when structure and correctness matter.
- Inspect a process and its evidence before signaling it; prefer graceful exit.
- Cron launches simple work; orchestration owns dependencies, retry, backfill, and richer operational history.
- Validate before publishing, and expose failure through nonzero statuses and correlatable, privacy-safe logs.

## Resources

- `man bash`, `help set`, and `help trap`
- `man 7 path_resolution`, `man chmod`, and `man 2 rename`
- `man grep`, `man awk`, and `man sed`
- `man ps`, `man 7 signal`, and `man systemctl`
- `man crontab`, `man 5 crontab`, and `man flock`
- `man journalctl`

Local manual pages match the installed utilities and are the first reference for exact options.

## Completion checklist

- [x] Highlighted Linux topics and IDE/shell boundary explained
- [x] Connected data-engineering walkthrough included
- [x] Ownership, failure, atomic publication, security, and logs addressed
- [x] Local-versus-production scale boundary stated
- [ ] Walkthrough executed in Linux/WSL and exact output recorded
- [ ] Cron overlap control exercised in a disposable environment
- [ ] Failure and recovery walkthrough completed by the learner
