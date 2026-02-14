# OpenClaw Cron Jobs Guide

## Overview

OpenClaw includes a built-in Gateway scheduler that enables your AI agents to execute scheduled tasks autonomously. With cron jobs, your bots can wake up at specific times, perform actions, and deliver results to chats without manual intervention.

## What We've Enabled

As of this update, all new VPS deployments automatically include cron job support with the following configuration:

```json
{
  "cron": {
    "enabled": true,
    "store": "~/.openclaw/cron/jobs.json",
    "maxConcurrentRuns": 1
  }
}
```

This means:
- ✅ Cron jobs are enabled by default
- ✅ Jobs persist across restarts at `~/.openclaw/cron/jobs.json`
- ✅ One job runs at a time (prevents resource conflicts)

## How to Use Cron Jobs

### Accessing Your VPS

To manage cron jobs, SSH into your droplet:

```bash
ssh root@<your-droplet-ip>
```

Then switch to the openclaw user:

```bash
su - openclaw -s /bin/bash
cd /var/lib/openclaw
```

### Essential Commands

**List all cron jobs:**
```bash
openclaw cron list
```

**Add a one-shot reminder:**
```bash
openclaw cron add --name "Meeting Reminder" \
  --at "2026-02-15T14:00:00Z" \
  --session main \
  --system-event "Reminder: Team meeting in 15 minutes!" \
  --wake now
```

**Add a daily morning briefing (isolated session):**
```bash
openclaw cron add --name "Morning Briefing" \
  --cron "0 7 * * *" \
  --tz "America/Los_Angeles" \
  --session isolated \
  --message "Summarize my calendar for today and check for important emails." \
  --announce \
  --channel telegram
```

**Add an interval-based job (every 30 minutes):**
```bash
openclaw cron add --name "Monitor Updates" \
  --every 1800000 \
  --session isolated \
  --message "Check for system updates and summarize any important changes."
```

**Run a job manually (for testing):**
```bash
openclaw cron run <job-id>
```

**View job execution history:**
```bash
openclaw cron runs --id <job-id> --limit 50
```

**Delete a cron job:**
```bash
openclaw cron remove <job-id>
```

## Schedule Types

### 1. One-Shot (`--at`)
Execute once at a specific timestamp (ISO 8601 format):
```bash
--at "2026-02-15T16:00:00Z"
```

### 2. Interval (`--every`)
Execute repeatedly at fixed intervals (milliseconds):
```bash
--every 3600000  # Every hour (60 * 60 * 1000 ms)
```

### 3. Cron Expression (`--cron`)
Traditional 5-field cron syntax with optional timezone:
```bash
--cron "0 9 * * *" --tz "America/New_York"  # Daily at 9 AM EST
--cron "*/30 * * * *"  # Every 30 minutes
--cron "0 0 * * 0"  # Weekly on Sunday at midnight
```

Cron format: `minute hour day-of-month month day-of-week`

## Session Types

### Main Session (`--session main`)
Injects a system event into your main conversation. Use for:
- Reminders and notifications
- Alerts that should appear in your active chat
- Time-sensitive prompts

Example:
```bash
--session main --system-event "Your daily standup starts in 5 minutes"
```

### Isolated Session (`--session isolated`)
Runs in a dedicated background session (`cron:<jobId>`). Use for:
- Research tasks
- Data gathering
- File organization
- Background processing

Example:
```bash
--session isolated --message "Research today's top tech news and summarize."
```

## Practical Use Cases

### 1. Daily News Briefing
```bash
openclaw cron add --name "Tech News" \
  --cron "0 8 * * *" --tz "America/Los_Angeles" \
  --session isolated \
  --message "Find and summarize the top 5 tech news stories from today." \
  --announce --channel telegram
```

### 2. Calendar Reminder
```bash
openclaw cron add --name "Standup Reminder" \
  --cron "0 9 * * 1-5" \
  --session main \
  --system-event "Daily standup in 10 minutes! 🚀" \
  --wake now
```

### 3. Server Health Check
```bash
openclaw cron add --name "Health Check" \
  --every 3600000 \
  --session isolated \
  --message "Check system status: disk usage, memory, and CPU load."
```

### 4. Weekly Report
```bash
openclaw cron add --name "Weekly Summary" \
  --cron "0 17 * * 5" --tz "UTC" \
  --session isolated \
  --message "Compile a weekly summary of all tasks completed this week." \
  --announce --channel telegram
```

### 5. Birthday Reminders
```bash
openclaw cron add --name "Birthday Alert" \
  --at "2026-03-15T09:00:00Z" \
  --session main \
  --system-event "🎂 It's Sarah's birthday today! Don't forget to wish her." \
  --wake now
```

## Important Notes

### Reliability
- Jobs persist in `~/.openclaw/cron/jobs.json` and survive system restarts
- Automatic exponential backoff on failures: 30s → 1m → 5m → 15m → 60m
- Backoff resets after successful execution

### Timezone Handling
Always specify timezone for cron expressions to avoid confusion:
```bash
--tz "America/New_York"    # EST/EDT
--tz "America/Los_Angeles" # PST/PDT
--tz "UTC"                 # Coordinated Universal Time
```

### Security
- Cron jobs run as the `openclaw` user (not root)
- All jobs inherit the security context of the OpenClaw service
- Gateway port (18789) remains localhost-only

### Resource Management
- Default `maxConcurrentRuns: 1` prevents resource conflicts
- Isolated sessions don't interfere with main chat
- Jobs timeout according to agent configuration

## Disabling Cron Jobs

If you need to disable cron functionality entirely, set:
```bash
export OPENCLAW_SKIP_CRON=1
```

Or modify `openclaw.json`:
```json
{
  "cron": {
    "enabled": false
  }
}
```

## Getting Help

For more details, run:
```bash
openclaw cron --help
openclaw cron add --help
```

## Future Deployments

All new bots deployed after this update will automatically have cron jobs enabled. Existing bots will need to be redeployed or manually updated to include the cron configuration in their `openclaw.json` file.
