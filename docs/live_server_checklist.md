# UMS Lite: Live Server Checklist

Use this checklist to perform a manual dry run of the tournament lifecycle before going live.

## Pre-Flight
- [ ] Ensure `.env` is configured and the bot is online.
- [ ] Confirm the bot role has standard message sending and embed rendering permissions in your target channel.
- [ ] Confirm you (the tester) have `Manage Server` permissions to access the Admin Control Panel.

## Tournament Creation & Registration
- [ ] Execute `/ums`. Verify you see the **Admin Control Panel**.
- [ ] Click **Create Tournament**.
- [ ] Click **Open Registration**.
- [ ] Verify a persistent **Public Tournament Panel** message appears in the channel.
- [ ] Have 2–3 dummy users click **Join** on the public panel. Verify the entrant count ticks up.
- [ ] Have a user click **Leave**. Verify the entrant count ticks down.
- [ ] Click **Close Registration** in the Admin Control Panel. Verify the public panel buttons disappear.

## Bracket Generation
- [ ] Click **Generate & Start** in the Admin Control Panel.
- [ ] Verify the shared, persistent **Match Cards** appear in the channel immediately.
- [ ] Verify the public panel updates its status to "The tournament is currently underway!".

## Match Execution
- [ ] Have Player 1 click **I Won** on their Match Card.
- [ ] Verify the Match Card color changes to orange (Awaiting Confirmation).
- [ ] Have Player 2 click **I Lost** (which confirms Player 1's win).
- [ ] Verify the Match Card color changes to green (Resolved) and displays the winner.
- [ ] If a downstream match is waiting for this winner, verify the downstream Match Card automatically updates with the winner's name.

## Dispute Handling & Admin Override
- [ ] For another Match Card, have Player 1 and Player 2 both click **I Won**.
- [ ] Verify the Match Card color changes to red (Disputed) and displays both conflicting reports.
- [ ] Open the `/ums` Admin Control Panel. Verify the disputed match is explicitly flagged under "⚠️ Disputed Matches".
- [ ] On the shared Match Card, verify you (as an Admin) can see the **🛡️ Force P1 Win** and **🛡️ Force P2 Win** buttons.
- [ ] Click one of the Force buttons. Verify the match resolves and the dispute buttons disappear.

## Tournament Completion
- [ ] Resolve the final match in the bracket.
- [ ] Verify the Public Tournament Panel updates to display "**The tournament is COMPLETE!**" and lists the final winner.
- [ ] Execute `/ums` and verify the Admin Control Panel now shows no active tournaments, and lists your finished tournament under "Recent History".

## Recovery Edge Cases
- [ ] **Public Panel Recovery:** Delete the persistent Public Tournament Panel message in Discord. Then type `/ums` and click the **Refresh** button on the Admin Control Panel. Verify the public panel is recreated instantly.
- [ ] **Bot Restart Recovery:** Stop the bot process (`Ctrl+C`) and start it again. Verify the bot logs `Startup UI reconciliation completed successfully` and all active Match Cards/Panels remain interactive.
