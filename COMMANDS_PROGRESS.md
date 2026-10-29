# Command-by-command progress

Working through the commands in the order listed in `website/commands.json`. Record each command here as we review or change it.

## Current follow-up

The command/load audit and regression evidence are tracked in [LOAD_PROGRESS.md](LOAD_PROGRESS.md).
Load pass: **38 / 38 catalog entries audited; 91 tests passed against the disposable PostgreSQL cluster.**

## Discord Activity pilot

- Selected `/bollywood` as the first game for Pippo's shared Discord Activity. This is a planned port; the current command remains the running implementation until the Activity is built and verified.
- Preserve the existing Bollywood loop: movie title hangman, letter guesses, hint buttons, three shared game lives, repeated rounds from a shuffled movie deck, and solo/friends play. Keep the slash command as a direct launcher into the Activity.
- Next: design the Activity lobby/game screens and a server-authoritative session API around the existing Bollywood data and scoring behavior.

Clash friends lobbies expire without silently switching to a Pippo duel. The slash description is within Discord’s 100-character limit; full command-tree serialization is regression-tested. Bollywood/Hollywood masked titles now render below the art with high contrast, and guessed-letter reveals match the right characters.
All 14 games now share one mode screen: **Play solo** or **Play with friends**. This supersedes older solo-flag examples below.
`/laser` uses its original slow emoji edits, and FLAMES uses the six original local outcome images.
Routine guess feedback uses reactions and updates to the existing game message.
Clash uses the configured Meta Muse Spark Contributor model; a live structured-judgment smoke call succeeded. The user allowed Meta model-improvement data use, with standard routing mode set in `.env`.

## Progress

- Reviewed: 38 / 38
- Changed: 34
- `/play`: reviewed `cogs/play.py`; implementation is an interactive game picker that routes into existing game commands. No specific defect or requested change identified yet. No code change made.
- `/bollywood`: reviewed and fixed the game loop and hint interactions. Added eight Pippo-themed film-night scene assets, selected randomly for game art. Automated tests have not been run.
- `/hollywood`: filters out TV series, video games, and other non-movie records; adds an explicit full-title bonus shot with a clear cost for a miss; uses a random Pippo Hollywood scene from a new four-image set. Updated the catalog copy and preview image.
- `/plotster`: now runs a three-life game with three guesses per title, progressive keyword reveals, once-per-round costed hints, and faster/cleaner scoring. It uses a shuffled set of actual movies with clue data and four randomized Pippo detective scenes. Updated the website copy and preview.
- `/quizster`: rebuilt actor/movie/year questions to use verified metadata and shuffled, variable-length answer sets; fixed answer/life handling, no-answer continuation, majority skips, shared hints, streak bonuses, round recaps, and final standings. It supports Bollywood, Hollywood, and Mix, with four randomized Pippo quiz scenes and matching website copy.
- `/poster`: now uses a six-step reveal, three shared lives, timed reveals, fuzzy title matching, clarity-based points, and a three-title streak bonus that restores a life. It skips non-movie records and unavailable poster URLs, loads each poster once per round, and uses four randomized Pippo cinema scenes. Updated the website previews and play instructions.
- `/bingo`: restored the original 1–25 classroom tickets and turn loop while keeping private player-owned boards, recent-call updates, inactivity timeouts, and four randomized Pippo Bingo scenes. Players choose a number from their own ticket on their turn; every ticket marks it, and the first to five lines wins. Updated catalog copy and captioned preview.
- `/tictactoe`: kept turn-checked friend challenges and added Easy, Normal, and perfect Hard solo modes. The bot uses alpha-beta minimax for Normal/Hard, with Normal deliberately making an occasional weaker move. Start and result screens use four randomized Pippo game scenes; updated slash choices, catalog copy, and preview.
- `/memory`: serialized flips to prevent overlapping plays, made the eight pair faces unique, added clear turn/match/streak feedback, solo move-based stars, and four randomized Pippo Memory scenes. Updated the solo/friend instructions and website preview.
- `/flood`: corrected row/column territory accounting, ensured starting corners have distinct colors, added majority-or-full-board tie endings, and gave Pippo a largest-gain color strategy. Turns now serialize, color buttons preview tile gains, and four randomized Pippo territory scenes accompany the live board. Updated the website copy and preview.
- `/clash`: capped open duels at two distinct submissions, rejected late/solo conflicts, and clarified timeout behavior (one fighter faces Pippo; empty lobbies close once). Submissions remain hidden until the duel starts; arena/results now use four randomized Pippo scenes. The AI keeps its strict winner schema and visibly labelled random fallback; updated catalog copy and preview.
- `/npat`: replaced the placeholder with a six-player lobby and five timed rounds using unique random letters. Each player locks a private four-category card; unique valid answers earn 10 points, shared valid answers earn 5, and a complete card adds 5. The game reveals round-by-round scoring and a final leaderboard. Four new Pippo classroom scenes rotate randomly through rounds and results; the website card and preview now describe the live game.

- `/onewordstory`: rebuilt as a rotating-turn story game for up to six players, with an eight-word solo option, short per-turn timers, host-controlled early finish, inactivity stops, and surprise letter/length/ending twist cards worth bonus points. Each valid word earns a point; the final story includes the contributor scoreboard and randomized Pippo storybook art. Updated the lobby, catalog copy, and preview.
- `/ship`: made scores pair-specific and repeatable using both identities, with rerolls deriving a fresh reading for the same pair. Replaced custom-server heart emojis with a portable meter and Pippo verdict; rerolls remain limited to three for the starter. Avatar collages render at higher quality and fail independently of the reading. Four generated Pippo matchmaker scenes rotate as thumbnails; updated catalog and preview.
- `/flames`: corrected shared-letter counting and the circular elimination cursor, then turned the one-shot answer into a five-step interactive reveal. Names and mentions are normalized safely, random pairings skip bots, and four local Pippo classroom scenes rotate during the reveal. Replaced remote image URLs and updated the website card and preview.
- `/laser`: restored the original 1.5-second emoji reveal through edits to one message. Different players can run independent animations; deleting the animation stops it cleanly.
- `/cartoon`: filters incomplete character records, shows a random character and show, and adds five invoker-only spins without repeating a draw. Four Pippo cartoon-show scenes rotate as captioned thumbnails. Updated the card and preview.
- `/cartoonme`: resolves shop-selected identities by both show and character, keeps the user-ID-based default stable, filters missing-image and exact duplicate records, and adds randomized captioned Pippo art. Updated its catalog copy and preview.
- `/8ball`: keeps the 20 classic answer choices, shows the asked question with Pippo's verdict, and allows three owner-only shakes; consecutive readings cannot repeat the same response. Four randomized Pippo fortune-teller scenes include live text captions. Updated catalog copy and preview.
- `/what`: replaced the raw three-definition code block with an owner-only Previous/Next browser for up to 12 unique community definitions. Each card shows a cleaned definition, example, contributor, and vote totals; API query encoding, response validation, timeout handling, mention suppression, and length limits are in place. Four Pippo dictionary scenes rotate with word/page captions. Updated catalog copy and preview.
- `/kiss`: replaced forced, randomly scripted physical-kiss narration and remote GIFs with an invite the recipient can accept or pass; requests quietly expire after 60 seconds. The no-target option remains as a randomized friendly air-kiss. Self and bot targets get clear guidance. Four randomized Pippo greeting scenes carry dynamic captions. Updated the catalog and preview.
- `/dog`: turned the one-photo drop into an invoker-only four-photo Pup Parade with unique photos, three extra fetches, and progress feedback. Photos are validated as small, supported-format images from TheDogAPI hosts, then receive a readable caption overlay; four Pippo dog-park scenes rotate as thumbnails. No fixed-image fallback remains if the live feed is unavailable. Updated the catalog and preview.
- `/cat`: added the matching four-photo Cat Parade using the same bounded image validation, no-repeat carousel, invoker-only controls, and dynamic captions as `/dog`. Added four randomized Pippo cat-scene thumbnails and updated the catalog/preview.
- `/woof`: expanded the one-question quiz into five distinct breed-photo rounds with a cumulative score. Friends mode lets the whole chat guess once per round; wrong choices are eliminated in place and a correct guess advances the shared quiz. Solo mode stays owner-only and moves on after a miss. The same message shows round results and the final leaderboard, while photo downloads remain bounded, validated, and matched to each answer.
- `/meow`: uses the same five-round solo/friends loop with distinct cat breeds, in-place guess feedback, scoring, timeout cleanup, and a final leaderboard. Updated both catalog descriptions to explain the longer game.
- `/breedme`: keeps the stable per-profile breed match and friend lookup. It now shows the breed's actual lifespan range instead of a derived human-age number, fetches a verified breed-specific photo with a local breed-image fallback, captions the photo, and adds Pippo art. Updated the catalog description and preview.
## `/poster` review findings

1. **Round flow:** wrong guesses and timeouts move through six clarity steps; missing all six costs one of three shared lives and reveals the title.
2. **Scoring:** earlier answers earn more. Three consecutive poster wins by one player award two bonus points and restore a shared life, up to three.
3. **Movie/poster handling:** only movie records with poster URLs enter the deck. Each poster downloads once and is reused for all reveals. Unavailable URLs are skipped; titles accept punctuation/case variants and close typos.
4. **Art and catalog:** four new Pippo cinema scenes rotate through the start and end screens. The website card, preview, example, and instructions match the game rules.
5. **Leaderboard follow-up:** score deposits still use the existing Bollywood score table; review the shared Bollywood/Hollywood/poster totals when `/leaderboard` is reached.

## `/bingo` review findings

1. **Cards and rules:** each player receives a shuffled ticket containing each number from 1 to 25 once. Five completed rows, columns, or diagonals win; there is no free center.
2. **Turn loop:** the player whose turn it is selects one uncalled number from their own ticket; every ticket marks that number and the turn advances. Solo Pippo chooses a random uncalled number from its own ticket.
3. **Game lifecycle:** boards are private and owner-checked. Multiplayer waits until all board messages are delivered before opening play. Calls serialize behind a lock; inactivity skips turns and eventually closes an abandoned game.
4. **Art and catalog:** four Pippo Bingo scenes rotate through start and result screens with the current title/status captioned over the art. The website card, example, copy, and preview describe the original 1–25 classroom loop.

## `/tictactoe` review findings

1. **Turn and win rules:** the 3×3 board detects rows, columns, diagonals, and full-board draws. Player ownership and turn are checked before a move; invalid clicks receive an ephemeral explanation.
2. **Solo play:** Easy chooses a random legal square. Normal uses optimal play most turns with a 24% chance of a weaker move; Hard uses alpha-beta minimax and cannot lose. The default Normal mode keeps Pippo beatable while still blocking and taking wins.
3. **Friend matches:** an invite is private to the challenged player, allows either side to decline, and expires after one minute. Accepted games are restricted to the two players and time out after two minutes of inactivity.
4. **Art and catalog:** four Pippo tic-tac-toe scenes rotate through game start and result screens. Catalog copy reflects the available difficulties and the updated preview uses Pippo art.

## `/memory` review findings

1. **Board integrity:** the previous face list contained duplicates, so some games could deal more than two copies of the same face. The deck now samples eight distinct faces and duplicates each exactly once.
2. **Turn loop:** the board lock and turn token serialize clicks, prevent stale interactions from acting after a miss, and preserve the rule that a match keeps your turn while a miss passes it. Match streaks and turn changes are now explicit.
3. **Scoring and finish:** solo mode counts pair attempts and awards one to three stars based on moves; head-to-head mode scores pairs and reports winner or tie. Games end cleanly on all pairs or timeout.
4. **Art and catalog:** four Pippo Memory scenes rotate through start and result screens. The copy explains the turn rules and solo star score.

## `/flood` review findings

1. **Territory integrity:** the old generation could give both corners the same color, letting connected areas overlap. Starting territories now have distinct colors, row/column coordinates are consistent, and image rendering follows the same grid.
2. **Loop and strategy:** turn-token checks reject stale clicks. Buttons show expected territory gain; Pippo picks a best-gain color and breaks ties randomly. A player wins above 50%; a full even board is a draw.
3. **Visuals and state:** the bot has four randomized Flood scenes. Both the board and art attachment update together, and the embed reports each player's territory percentage and whose turn it is.
4. **Catalog:** card and detail copy describe the majority condition and Pippo's move strategy; the preview uses the new art.

## `/clash` review findings

1. **Lobby:** only two distinct creations can enter an open duel. Late submissions are rejected; a solo Pippo selection cannot silently discard another player's creation.
2. **Timeouts:** an empty lobby closes without sending a duplicate cancellation. One timely submission proceeds against Pippo, matching the timeout status.
3. **Judging:** OpenRouter receives the creations as JSON data, validates a strict 1-or-2 winner schema, and falls back to a random, clearly labelled result if judging is unavailable.
4. **Art and catalog:** four Pippo arena scenes rotate through the lobby, duel, and verdict. The command card and preview reflect friend and solo play.

## `/npat` review findings

1. **Round loop:** the host opens a lobby for up to six players; five distinct letters are drawn from a common alphabet, and each round gives players 45 seconds to lock Name, Place, Animal, and Thing answers together.
2. **Scoring:** the starting letter is checked automatically. Unique answers are worth 10, shared answers 5 each, wrong-letter or blank answers 0, and four valid answers earn a 5-point perfect-card bonus. Category meaning remains an honour-system rule.
3. **Reveal and finish:** cards stay private until the round closes, then each answer and its points are revealed. Scores accumulate across rounds and the finish screen shows ties and the full standings. Only the first submission from each participant counts.
4. **Art and catalog:** four generated Pippo classroom scenes are chosen randomly for each round/reveal; the website status, rules, and preview now match the implementation.

## `/onewordstory` review findings

1. **Turn order:** multiplayer uses a six-player join/start lobby, then rotates one-word turns for four laps. Solo mode keeps the author as the only contributor for eight turns.
2. **Twists and scoring:** every four accepted words, the next player draws a checkable starting-letter, minimum-length, or final-letter challenge for two bonus points. Each accepted word is worth one Story Point.
3. **Session controls:** turns have fixed deadlines; missed turns pass, and the story closes when everyone misses consecutively. The host can end early with the configured prefix plus `end`; channel and player checks ignore bots and off-turn words. Story words are length-capped and final mentions are disabled.
4. **Result and art:** final text, Story Points, ties/MVP, and one of four generated Pippo storybook scenes appear together. The command card, example, and preview now match solo and group play.

## `/ship` review findings

1. **Pair selection:** supports two names or members, one supplied partner, or a random non-bot server partner; falls back to Pippo outside a populated server. Usernames are escaped and no mentions are sent.
2. **Readings:** a stable, order-independent pair identity produces the initial 0–100 score, so different pairings receive different readings while the same pair keeps its result. Each reroll includes its reading number to produce a fresh score. The meter has ten hearts and each score gets a Pippo verdict with an explicit for-fun note.
3. **Rerolls and visuals:** the starter can reroll the same pair in place three times; rapid concurrent clicks are serialized. Member avatars remain in the collage when available, with four random Pippo matchmaker thumbnails for every reading.
4. **Catalog:** description and preview explain pair-specific readings and same-pair rerolls.

## `/flames` review findings

1. **Name matching:** compares alphabetic characters case-insensitively and cancels each shared letter once. The former implementation kept the right count but restarted elimination from the first letter every pass.
2. **Reveal:** the six FLAMES letters are removed in a circular count, continuing at the next position after each removal. The starter can reveal one burn at a time; the final letter displays its relationship result.
3. **Pairing and safety:** supports names, cached/fetched member mentions, or a random non-bot server member with Pippo as the fallback. Names are escaped and result embeds do not ping users.
4. **Art and catalog:** four generated classroom scenes rotate through the five-step reveal. The remote image links are gone; the website copy and preview show the interactive result.

## User corrections during the command overhaul

1. **Text on generated game art:** generated Pippo scenes now receive readable, dynamic title and subtitle overlays when attached. Movie puzzle posters remain unobstructed so the answer stays guessable; Bollywood's puzzle lettering remains overlaid on its scene.
2. **`/poster` response feedback:** every wrong guess gets an immediate ❌ reaction and a short reply before the next clearer poster. Correct guesses get a ✅ reaction plus the score/streak result.
3. **`/bingo` classroom loop:** restored the original shuffled 1–25 tickets with no free center or 75-ball B-I-N-G-O columns. On their turn, each player selects a number from their ticket; every ticket marks it, and five completed lines still win. Pippo chooses randomly from its own remaining ticket numbers.
4. **`/cartoon` data/art:** the dataset has 359 rows, four without image URLs, and a few duplicate character names across shows. Roulette excludes rows without usable HTTP(S) image URLs and displays the show alongside the character. External image reachability is not live-verified.
5. **`/cartoonme` identity:** the saved identity now matches `(show_name, cartoon_character)`, so a duplicate name from another show cannot replace the shop selection. Users without a shop choice still receive the same deterministic identity for their Discord ID. Missing or exact duplicate records do not enter the lookup pool.
6. **`/8ball` interaction:** the asker can reveal up to three more readings without repeating the last result. Other members receive an ephemeral explanation; each reading updates the question, answer, and captioned Pippo art together.
7. **Missing feedback item:** the user's numbered point 4 arrived blank; awaiting its details.

## `/what` review findings

1. **Lookup and API handling:** encodes phrases as query parameters, caps input, validates response shape, catches timeout/network/JSON errors, and gives a clear no-result or temporary-outage response.
2. **Definition browser:** one result per card with cleaned community definition, example, author, and vote totals. Up to 12 unique definitions are navigable with Previous/Next controls; only the command author can turn pages.
3. **Content handling:** user and API supplied text has mentions disabled and markdown escaped; definition/example/title lengths fit Discord limits. Urban Dictionary's community content may still contain mature language, reflected in the catalog.
4. **Art and catalog:** four generated Pippo dictionary scenes rotate randomly and receive readable word/page captions. The catalog preview and instructions describe the interactive browser.

## `/kiss` review findings

1. **Consent and response:** a member target receives Accept and Pass buttons; only that recipient can choose. No response closes quietly after 60 seconds, and a refusal gets a light, non-pressuring response.
2. **Air-kiss option:** leaving the target blank posts one of four playful air-kiss lines without putting another member on the spot.
3. **Input and mentions:** self-targets and bot targets receive actionable guidance. Usernames are markdown-escaped and messages disable mentions.
4. **Art and catalog:** removed external romance GIFs in favor of four randomized Pippo greeting illustrations with dynamic captions. The catalog now describes the consent-based request and air-kiss option.

## `/dog` review findings

1. **Photo flow:** starts a four-photo carousel; the invoker can fetch three more photos from the same message. Duplicate URLs are skipped, controls are owner-only, and the button expires after two minutes.
2. **Photo validation:** requires HTTPS TheDogAPI image hosts, checks redirects/content type/status, caps download size and pixel count, and accepts only JPEG, PNG, or WebP before decoding.
3. **Captions and feedback:** each actual dog photo gets a rendered Pup Parade/photo-count caption; changing photos updates the embed and Pippo thumbnail. Failures return a clear retry message without falling back to a stale fixed photo.
4. **Art and catalog:** four Pippo dog-park scenes rotate as captioned thumbnails. The catalog now describes the photo carousel and new Pippo artwork.

## `/cat` review findings

1. **Photo flow:** four unique cat photos appear in a carousel. Only the invoker can request up to three more; interactions serialize, and controls disable after the fourth photo or on timeout.
2. **Photo validation:** requests HTTPS TheCatAPI hosts, verifies redirects/content type/status, enforces an 8 MiB download cap and 20-megapixel limit, and decodes only JPEG, PNG, or WebP.
3. **Captions and feedback:** the selected real cat photo receives a readable Pippo/position overlay; changing photos updates the image, rotating Pippo art, status, and remaining count. Feed failures are reported clearly without a stale fixed fallback.
4. **Art and catalog:** four Pippo cat scenes rotate as captioned thumbnails. Website card, detail, example, and preview describe the four-photo Cat Parade.

## Runtime setup

- Added `./run.sh` to load `.env`, create `.venv` if needed, install runtime dependencies, prepare PostgreSQL and apply `schema.sql`, then start the bot.
- Added a final database-pool preflight using the same `database_options()` as the bot. It retries transient connection failures for 15 seconds and reports the host/port plus likely failure category without printing credentials; Discord login is skipped if the configured database is still unreachable.
- When the local PostgreSQL service or Docker needs administrator rights, the database helper requests sudo in an interactive terminal. It tries both `systemctl` and `service` to start a local PostgreSQL service, then uses its Docker fallback with a persistent PostgreSQL 18 container. Remote database configuration is used as-is and must already have an accessible database and schema permissions.
- `bash -n run.sh` passes. Database preparation and live Discord startup remain unverified because they require the user's local PostgreSQL or Docker access and Discord credentials. In the current restricted environment, PostgreSQL is not listening and systemd/Docker access is blocked.

## `/bollywood` review findings

1. **Fixed:** the game now grants the three lives described in its instructions.
2. **Fixed:** letter guesses are normalized and tracked as sets, so casing cannot duplicate a letter or finish a title early. Duplicate guesses get a repeat marker without consuming a try.
3. **Fixed:** unaffordable hints receive an ephemeral explanation and leave the button available. A random-letter hint now reveals a remaining letter in the puzzle and refreshes the image.
4. **Gameplay and art:** rounds use a shuffled movie deck to avoid repeats until the available titles have been used. The game shows remaining lives, tries, and missed letters. Start, round, and game-over images randomly use one of eight new Pippo-themed film-night illustrations in `imgs/bollywood_scenes/`.

## `/hollywood` review findings

1. **Content:** Hollywood data contains TV series and other media types alongside movies. This command now offers only records marked `Movie`.
2. **Gameplay:** a deliberate `title: <answer>` shot can solve a round for 3 individual points. A wrong title shot costs 2 tries; ordinary chat text is ignored, and letter guesses keep their existing scoring.
3. **Art and catalog:** four new Pippo Hollywood scenes are chosen randomly for the start, puzzle, and game-over art. Puzzle lettering uses a light, readable color on the dark studio scenes. The website catalog now describes the real round rules and uses branded game art.
4. **Follow-up for `/leaderboard`:** Hollywood and Bollywood currently share the `bollywood_points` table and leaderboard option. Review whether the leaderboard should split those modes when that command is reached.

## `/plotster` review findings

1. **Clues:** the old game showed the full synopsis immediately and did not attach its advertised hint buttons. It now starts with two title-safe keywords, reveals another after each miss, and offers cast, film details, or plot summary at point costs.
2. **Loop and scoring:** players get three guesses per title and three game lives. Correct titles earn up to six points based on remaining guesses and hints used. Timeouts and skips cost one life, and the game continues until lives run out or players exit.
3. **Movie pool:** only movies with usable clue data are selected; the last remaining title is no longer discarded at the deck rollover. User-facing titles and clues are HTML-unescaped.
4. **Art and shared code:** four new Pippo detective scenes are selected randomly for each stage. The shared movie picker excludes non-movies and supplies `/quizster` with actor/year metadata for questions.

## Queue

1. `play` — reviewed — catalog: live
2. `bollywood` — reviewed — catalog: live
3. `hollywood` — reviewed — catalog: live
4. `plotster` — reviewed — catalog: live
5. `quizster` — reviewed and overhauled — catalog: live
6. `poster` — reviewed and overhauled — catalog: live
7. `bingo` — reviewed and overhauled — catalog: live
8. `tictactoe` — reviewed and overhauled — catalog: live
9. `memory` — reviewed and overhauled — catalog: live
10. `flood` — reviewed and overhauled — catalog: live
11. `clash` — reviewed and overhauled — catalog: live
12. `npat` — reviewed and overhauled — catalog: live
13. `onewordstory` — reviewed and overhauled — catalog: live
14. `ship` — reviewed and overhauled — catalog: live
15. `flames` — reviewed and overhauled — catalog: live
16. `laser` — reviewed and overhauled — catalog: live
17. `cartoon` — reviewed and overhauled — catalog: live
18. `cartoonme` — reviewed and overhauled — catalog: live
19. `8ball` — reviewed and overhauled — catalog: live
20. `what` — reviewed and overhauled — catalog: live
21. `kiss` — reviewed and overhauled — catalog: live
22. `dog` — reviewed and overhauled — catalog: live
23. `cat` — reviewed and overhauled — catalog: live
24. `woof` — reviewed and overhauled — catalog: live
25. `meow` — reviewed and overhauled — catalog: live
26. `breedme` — reviewed and overhauled — catalog: live
27. `meowme` — reviewed and overhauled — catalog: live
28. `balance` — reviewed — catalog: live
29. `send_coins` — reviewed and overhauled — catalog: live
30. `shop` — reviewed — catalog: live
31. `shop character` — reviewed and overhauled — catalog: live
32. `leaderboard` — reviewed and overhauled — catalog: live
33. `help` — reviewed — catalog: live
34. `ping` — reviewed and overhauled — catalog: live
35. `change_prefix` — reviewed and overhauled — catalog: live
36. `suggest` — reviewed and overhauled — catalog: live
37. `signup` — reviewed and overhauled — catalog: live
38. `signup greetings` — reviewed and overhauled — catalog: live

## Art refresh follow-up

- Regenerated all 21 existing command scene folders and the generated catalog previews using the canonical mascot reference and a quieter editorial look; added dedicated four-scene sets for `/woof` and `/meow`. Actual command captures remain intact. Outfits may vary while Pippo's face, helmet, and overall identity stay recognizable.
- Added a captioned Pippo Treasury catalog preview for `/balance`; its original capture remains intact.
- Added a captioned Pippo sharing scene as the `/send_coins` catalog preview; its prior capture remains intact.
- Added separate captioned Pippo previews for `/shop` and `/shop character`; their prior captures remain intact.
- Added a captioned Pippo Hall of Fame leaderboard preview; the previous capture remains intact.
- Added a captioned Pippo Help Desk preview; the previous menu capture remains intact.
- Added a captioned Pippo online-status preview; the previous capture remains intact.
- Added a captioned Pippo prefix settings preview; the previous capture remains intact.
- Added a captioned Pippo feedback preview; the prior help capture remains intact.
- Added separate captioned Pippo greeting previews for the signup group and its preference command; prior captures remain intact.

## `/breedme` review findings

1. **Stable match:** the same Discord profile gets the same breed; the optional member argument still checks a friend.
2. **Breed details:** show the dataset's lifespan range directly; don't convert a breed's years into a purported human age.
3. **Photo:** request an image for the selected breed, validate and caption it, and fall back to that same breed's bundled image if the feed fails. The result still posts if no photo can be loaded.
4. **Art and catalog:** a Pippo dog-scene thumbnail accompanies the result; the catalog description and preview describe the stable match and information shown.

## `/meowme` review findings

1. **Stable match:** the selected cat breed is deterministic for the chosen Discord profile; the optional member argument still supports matching a friend.
2. **Breed details:** show the breed's temperament and source lifespan range directly, avoiding an unsupported human-age conversion.
3. **Photo:** request a photo for the selected breed, validate and caption it, and use the dataset's image as a same-breed fallback. The text match still posts if no image is available.
4. **Art and catalog:** Pippo cat art accompanies the result; the catalog copy and generated preview describe the stable breed match and its details. The prior command capture remains preserved.

## `/balance` review findings

1. **Balance source:** the command reads the caller's virtual coin balance from `points.coins`, the same field used by the shop and Coin Wealth leaderboard.
2. **Missing account:** the database accessor returns a zero balance for users without a row, so first-time users can check their balance without an error.
3. **Presentation:** displays the balance with thousands separators and the caller's avatar. No command logic change was needed; the catalog copy now describes the actual behavior and uses a generated Pippo Treasury preview while preserving the old capture.

## `/send_coins` review findings

1. **Validation:** rejects zero/negative amounts, self-transfers, and bot recipients. Added a clear upper bound matching the signed PostgreSQL `INT` column to prevent oversized requests from failing inside the database driver.
2. **Atomicity:** the database transfer creates missing balance rows, locks both accounts in a stable order, and debits only when the sender has enough coins; this prevents concurrent transfers from overspending.
3. **Feedback and catalog:** failures are private, successful transfers confirm the amount and members, and the catalog now describes the validation and uses generated Pippo sharing art while retaining its previous capture.

## `/shop` review findings

1. **Command scope:** `/shop` is the entry point that directs users to its available subcommand, `/shop character`; catalog copy now reflects that behavior.
2. **Catalog:** added a captioned Pippo shop preview while preserving the prior help capture. No root-command logic change was needed.

## `/shop character` review findings

1. **Browsing:** users choose a show, then one of its characters. Show lists paginate in Discord's 25-option limit, the current dataset stays within that limit per show, and shop views only respond to their owner.
2. **Purchase integrity:** the former balance-read followed by separate deduction could let simultaneous purchases overspend and could charge a user even if saving the character failed. Replaced it with one database transaction that conditionally debits 1,000 coins and saves the show/character together; failures roll back without charging.
3. **Feedback:** the dropdown displays the 1,000-coin price, and purchase success or insufficient funds ends the interaction with a clear result.
4. **Catalog:** updated the detail to describe the actual purchase and added generated Pippo character-shop art; preserved the prior capture.

## `/leaderboard` review findings

1. **Modes:** the interactive selector shows the top ten Bollywood, Plotster, and coin rankings. Bollywood, Hollywood, and Poster all currently write to the same historical score table, which has no mode field; relabelled that selector as shared Movie Games and disclosed the combined totals rather than implying a Bollywood-only ranking.
2. **Input and ordering:** the slash argument now offers the three supported categories as choices, while prefix input remains supported. Equal scores use ascending user ID for stable ordering.
3. **Feedback and art:** empty boards and database errors already produce explicit messages, and the view disables after timeout. Updated the catalog explanation and added Pippo leaderboard art while preserving the old capture.

## `/help` review findings

1. **Active implementation:** `bot.py` loads `cogs/help.py`; the older `cogs/help2.py` file is not registered. The active command offers category browsing and details for a specific command or alias.
2. **Interaction behavior:** help categories are requester-only, the select disables on timeout, and prefix lookup falls back to the default dot prefix when needed.
3. **Catalog:** the active menu matches the website description. Added a captioned Pippo Help Desk preview while keeping the existing menu capture.

## `/ping` review findings

1. **Metrics:** the old “Pong! N ms” value measured only the time to send the initial message, so it wasn't a Discord gateway latency. The command now reports gateway heartbeat latency and initial command response time separately.
2. **Response:** the command still edits its initial reply in place, so it works in both prefix and slash-command contexts without posting a second message.
3. **Catalog:** clarified the two metrics and added Pippo online-status art while preserving the old capture.

## `/change_prefix` review findings

1. **Access:** the command is restricted to members with Manage Server permission and only works in a server.
2. **Validation and reset:** it now rejects empty, whitespace-containing, and over-10-character prefixes, escapes the displayed value, and supports `reset` or `default` to restore `.` immediately.
3. **Catalog:** updated usage and permission/reset details and added Pippo settings art while preserving the old capture.

## `/suggest` review findings

1. **Privacy:** the prefix form previously asked users to type feedback into a public channel and relied on best-effort deletion afterward. Prefix use now deletes the command where permissions allow and directs the user to the private slash form; it never forwards prefix text.
2. **Delivery:** slash invocations open a modal or accept private interaction text, then DM the developer. Forwarded embeds disable mentions to prevent user-entered text from pinging anyone.
3. **Catalog:** the example now uses `/suggest` and the description clarifies private delivery; added Pippo feedback art while preserving the earlier capture.

## `/signup` review findings

1. **Entry point:** `/signup` previously returned “Not a valid command.” It now directs users to the greeting preference command in both prefix and slash forms.
2. **Preferences:** all four greeting schedules are daily DMs in India time. The preference command replaces the complete selection; the response now lists enabled times or clearly confirms that all greetings are off.
3. **Catalog:** clarified the opt-in DM behavior, India schedule, and all-off unsubscribe behavior. Added generated Pippo greeting art while retaining the prior captures.

## `/signup greetings` review findings

1. **Scheduling:** the four opt-in DM tasks run at 6:00 AM, 1:00 PM, 5:00 PM, and 10:00 PM Asia/Kolkata time; startup waits for the Discord client to be ready and unload cancels the loops.
2. **Preference state:** each submission replaces all four flags. The response now confirms the selected times or states that all greetings are off, so submitting unchecked options is an explicit unsubscribe.
3. **Catalog:** documented the available times, India timezone, all-off behavior, and generated Pippo greeting art; preserved the old help capture.
