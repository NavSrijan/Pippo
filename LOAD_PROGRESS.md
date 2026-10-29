# Command reliability and load pass

Current follow-up to `COMMANDS_PROGRESS.md`. The first design pass remains recorded there; the decisions here supersede its older solo flags, laser dodge game, and routine guess replies.

## Requested behavior

- Every game uses one mode screen: **Play solo** / **Play with friends**. The same component serves direct commands and `/play`; movie filters and difficulty settings survive the selection. No public solo flags or positional booleans remain. NPAT is also available solo.
- `/laser` keeps the original 1.5-second emoji reveal through edits to the same message. Different users can run their own animations. A deleted animation closes cleanly.
- FLAMES retains its reveal and restores all six original `F/L/A/M/E/S` images as local attachments. Pippo art can accompany the outcome.
- Ordinary guessing feedback is a reaction or an edit to the current game post. Poster and Plotster do not send extra replies after misses or correct guesses. Unsolved-title reveals and final standings remain.
- A Clash friends lobby with fewer than two fighters expires without automatically switching to solo; only the shared Play solo button selects that mode.
- Clash retains OpenRouter, configurable model selection, authenticated structured requests, validation, and explicitly labelled offline fallback. The default reasoning model gets a bounded 2048-token allowance and low reasoning effort; response bodies are capped at 256 KiB.

## Review findings

| Finding | Resolution | Evidence |
| --- | --- | --- |
| Plotster fails on round two | Draw another movie when the initial validated movie has been consumed | `test_plotster_second_round_and_score_deposit` |
| Credential in untracked scratch script | Replaced the literal with `ANIMAL_API_KEY` environment lookup; no credential value printed during this pass | Static literal scan of Python sources; original key must be rotated by its owner if still active |
| Truncated animal downloads | Read bounded chunks through EOF, verify decoded format/dimensions away from the event loop, retry failures and retain same-breed fallback | Stream EOF/size tests and real PNG-to-JPEG photo-pipeline tests |
| Suggestion reply references deleted input | Send guidance without a reply reference; normal prefix replies also tolerate deleted inputs, and menu launches use ordinary sends | Suggestion and `PippoContext` tests |
| sudo loses Docker variables | Preserve the three named PostgreSQL variables across sudo; keep values out of command arguments | Launcher environment test |
| Running PostgreSQL skips sudo authorization | Authorize before role/database provisioning | Launcher authorization test |
| Copied website examples fail | Render HTML from current JSON and validate the shared mode flow; original captures retained | Catalog regeneration/idempotence and registration tests |

## Shared safeguards

- Movie year ranges reject dates beyond next year before any file work, preventing unbounded CSV scans from tying up a worker.
- Media/file work uses four worker threads and a per-loop admission gate. Poster/photo HTTP waits use asynchronous pooled connections, leaving workers for rendering and decoding.
- One application HTTP session: 32 connections globally, eight per host, bounded request/download limits, and closure at shutdown. Clash uses this client too.
- Prefix reads use a bounded 60-second cache, coalesce concurrent reads, and invalidate after an update. In-flight old reads cannot overwrite a newly configured prefix.
- Chat-guessing games share a channel reservation across commands, preventing the same guess from feeding multiple games. Reservations release on success, failure, and cancellation. Different channels/threads work independently; one owner can run two chat games across channels.
- Button/modal boards are isolated per message. Per-channel gates were replaced with per-member gates where commands already maintain private boards/lobbies, so different people can play alongside each other.
- Live menus are capped at 500 globally and eight per owner; finished menus release capacity on the next admission. A per-user command burst limit is eight invocations per ten seconds, including launches. Busy messages explain what to do.
- Character purchases conditionally debit and save in one transaction; duplicate clicks in one session charge once. Transfers lock accounts in a stable order. Movie score and coin awards now commit together.
- Existing coin balances migrate to `BIGINT` without loss. Ranking indexes match the three leaderboard queries. Leaderboard selection defers before database work and serializes edits.
- Late lobby actions and completed-board timeouts are guarded; Tic Tac Toe move/AI work serializes per board. Flood's redundant pixel-by-pixel initial image pass was removed.

## Per-command audit

All 38 catalog entries were inspected. Shared runtime changes apply to every command; the table records command-specific boundaries rather than adding features to already adequate commands.

| Command | Current behavior / concurrency decision |
| --- | --- |
| play | Shared mode buttons; single-use launch; ordinary send context; normal command checks/hooks; no reward for merely opening a game mode picker |
| bollywood | Original letter loop; fresh hint view per title; ignore unrelated chat; shared text-channel reservation; bounded rendering |
| hollywood | Same reservation/hint isolation; title-shot reaction without duplicate text |
| plotster | Second-round fix; private per-game deck/scoring; clue edits and reactions; scores deposited on exit |
| quizster | Per-round participant/answer state; once-only resolution; per-message buttons; offloaded data/question/art work |
| poster | Complete asynchronous bounded download; decoded source reused across reveals; reactions; independent text-channel reservation |
| bingo | Original classroom 1–25 cards/five-line rule; private player boards; serialized number calls; per-owner lobby gate; independent games for different hosts |
| tictactoe | Shared mode selection; opponent selection for friends; locked board updates and worker-based AI; terminal result protected from timeout |
| memory | Shared mode selection; per-board flip lock and state; inactivity cleanup preserves finished result |
| flood | Shared mode selection; no second solo path inside the lobby; serialized turn tokens; independent boards; cheaper initial rendering |
| clash | Shared mode selection; no second visible solo button; locked two-entry submissions; pooled OpenRouter judging; private creations until arena |
| npat | Added to common picker; solo uses existing five-round/modal loop; per-round submission lock and participant checks |
| onewordstory | Shared mode selection; one text game per channel; bounded turns/timeouts; wrong-word reaction instead of extra reply |
| ship | Per-owner reroll lock; same pair retained; avatar rendering offloaded; no shared avatar files |
| flames | Original local outcome images restored; per-owner reveal lock; image work offloaded |
| laser | Slow same-message emoji edit animation restored; per-member overlap guard and deleted-message handling |
| cartoon | Per-owner roulette lock and independent seen set; initial and repeat rendering offloaded |
| cartoonme | Stable/saved identity; read-only profile lookup; isolated artwork and safe reply |
| 8ball | Per-owner shake lock; initial and repeat rendering offloaded; complete multi-word questions retained |
| what | Pooled bounded-time HTTP request; complete multi-word phrases; clipped definitions; per-owner pagination lock; rendering offloaded |
| kiss | Recipient-controlled decision state; offloaded initial/result/timeout rendering; independent requests |
| dog | Four-photo per-owner carousel; pooled HTTP, bounded full-body reading, validated image, safe reply |
| cat | Same photo safeguards with independent cat state |
| woof | Five distinct photo rounds; shared solo/friends mode; public scores in friends mode; per-round locks and timeout cleanup; bounded validated photo pipeline |
| meow | Same five-round solo/friends loop and score handling for cats |
| breedme | Stable user match; cached source data; same-breed fallback; pooled photo client; offloaded image work |
| meowme | Stable cat match with the same safeguards |
| balance | Read-only account display, missing account returns zero; no unnecessary gameplay change |
| send_coins | Validates amount/target; transaction locks ordered; migrated storage can accept larger accumulated balances |
| shop | Entry point retained; generated catalog synced |
| shop character | Conditional debit/save transaction; owner lock and single-use purchase; stale page clicks clamped; duplicate names removed |
| leaderboard | Accurate shared movie category; indexed stable ordering; null records excluded; immediate defer and serialized category changes |
| help | Shared-mode instructions replace solo syntax; requester-owned category navigation; qualified subcommand names retain all words |
| ping | Separates gateway heartbeat from initial send duration; asynchronous in-place edit |
| change_prefix | Manage Server gate; reset/validation; immediate prefix-cache invalidation |
| suggest | Private slash form; prefix guidance uses send after deletion; forwarded embeds disable mentions |
| signup | Actionable preference entry point; no unnecessary change to scheduling |
| signup greetings | Atomic replacement of four flags; explicit all-off unsubscribe; daily Asia/Kolkata tasks start once and cancel on unload |

## Verification

- Full suite against a disposable PostgreSQL 18 cluster under `/tmp`; each database test uses a separate temporary schema. Latest result: **95 passed** in **3.97 seconds**. Deprecation warnings originate in the installed Discord library.
- Actual pooled-client HTTP checks against a local server: 80 concurrent judgments respect the eight-per-host connection cap. Chunked results read through EOF; rate limits, oversized bodies, malformed judgments, and missing fields use the labelled fallback, and a subsequent valid game still succeeds. No external provider request was made.
- Cancelled media commands retain admission until their underlying threads finish; undelivered owned attachments are closed.
- Real database checks: 100 competing purchases cannot overspend; failed character saving rolls back its charge; 300 opposing transfers preserve total coins; 200 score updates preserve totals; 100 combined score/coin awards stay consistent; large credits work; the old integer balance migrates intact.
- 30 independent breed boards with four simultaneous answers each resolve once. Twenty identical Tic Tac Toe clicks produce one human move and one bot move. A hundred prefix requests share one read. Forty command invocations mix success/failure and then cancellation without retaining reservations.
- All 38 catalog entries register; all 14 games show identical mode buttons and preserve movie options. Duplicate mode clicks launch once. Catalog generation is idempotent.
- Local media burst: **80/80 renders completed in 1.294 seconds**, at most **four workers**. Event-loop delay: **p95 6.52 ms**, maximum **11.14 ms** on this machine. These are local CPU/file results, not end-to-end Discord throughput guarantees.

Reproduce:

```bash
.venv/bin/python -m pytest -q
TEST_DATABASE_URL='postgresql://USER@HOST:PORT/DISPOSABLE_DB' .venv/bin/python -m pytest -q
.venv/bin/python scripts/load_check.py --jobs 80
.venv/bin/python scripts/render_catalog.py
```

`TEST_DATABASE_URL` must name a disposable local test database where schema creation is permitted. Omit it to skip the PostgreSQL integration tests. Automated tests fake Discord/provider delivery; they do not send server messages or DMs or run system database provisioning/Docker operations. Separately, one real OpenRouter smoke request was made as described below. Live Discord traffic, Discord rate limits, and sustained deployment-host load still need a deployment soak check.

## Bollywood/Hollywood image text layout

- The masked movie title now sits in a dedicated navy strip with a gold edge below the artwork; the illustration is never painted over. Text is centered, wrapped, and uses consistent high-contrast colors with a dependable sans bold font.
- Fixed guessed-letter matching: revealed letters are selected by the guessed character itself, not by the next character in the title.
- Game captions now use a dynamically sized navy-and-gold panel below the artwork, so long subtitles remain visible without obscuring Pippo.
- Regression tests cover exact masks, the isolated title and caption panels, contrast, and full game flow.
- Full PostgreSQL-backed suite: **93 passed** in **3.89 seconds**.

## `/ship` pair scoring

- The score now derives from a stable, order-independent identity for both participants. Repeating the same pair gives the same baseline score; a different pair gets its own score. Each owner-only reroll includes its reroll number to generate a new reading for that pair.
- Added regression coverage for pair specificity, order independence, and reroll variation.
- Full PostgreSQL-backed suite: **95 passed** in **3.97 seconds**.

## `/woof` and `/meow` multiplayer rounds

- Both quizzes now use five distinct breed-photo rounds with a cumulative leaderboard and one updated game post. Friends mode lets chat members guess once per round; wrong choices turn red and are removed, while correct guesses award a point and advance the round. Solo mode remains starter-only and moves to the next photo after a miss.
- Interaction coverage checks multiple rounds, cumulative scoring, shared wrong-answer elimination, and one-shot legacy behavior.
- Full PostgreSQL-backed suite: **95 passed** in **3.97 seconds**.

## Discord command sync regression

- Shortened the Clash slash-command description to fit Discord’s 100-character maximum.
- Serialized the complete registered application-command tree locally and checked every command/option description; none exceed 100 characters. Added this as a regression test.
- Full PostgreSQL-backed suite after the fix: **90 passed**.

## OpenRouter and remaining live checks

- `.env` is configured with `OPENROUTER_MODEL=meta/muse-spark-1.3-contributor` and `OPENROUTER_PRIVACY_MODE=standard`. The existing API key was preserved and never printed.
- The user explicitly chose to allow Meta to use prompts and outputs for model improvement. Standard mode removes only the data collection and ZDR provider filters; required structured output remains. Strict mode remains the default for other deployments.
- A live one-request Clash smoke check returned a valid structured judgment from the selected model. It used two fictional test creations; no real Discord users or messages were involved.
- The complete suite now passes: **89 tests**, including disposable PostgreSQL integration tests. No tests were skipped.
- A real Discord connection, multiplayer gameplay, and sustained deployment-host soak test remain unverified. They need the bot running in its Discord deployment; local checks do not prove Discord gateway or platform rate-limit behavior.

Restart with `./run.sh` to apply the schema changes, load the new code, and synchronize the shared-mode command definitions.
