import discord
import random
import asyncio
from typing import List

from flood import Flood


class HintsView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=60)
        self.hint_given = False
        self.random_letter_given = False
        self.synopsis_given = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        owner_id = getattr(self, "author_id", None)
        if owner_id is not None and interaction.user.id != owner_id:
            await interaction.response.send_message("Only the player who started this solo game can use hints.", ephemeral=True)
            return False
        return True

    def reset(self):
        self.hint_given = False
        self.random_letter_given = False
        self.synopsis_given = False
        for child in self.children:
            child.disabled = False

    @discord.ui.button(label='Reveal Cast', style=discord.ButtonStyle.green)
    async def green(self, interaction: discord.Interaction,
                    button: discord.ui.Button):
        self.green.disabled = True
        if self.tries>1:
            await interaction.response.defer()
            await interaction.followup.send(self.hint)
            if self.hint_given is False:
                self.tries -= 1
                self.hint_given = True
        await self.out.edit(view=self)

    @discord.ui.button(label='Random Letter', style=discord.ButtonStyle.blurple)
    async def blue(self, interaction: discord.Interaction,
                    button: discord.ui.Button):
        self.blue.disabled = True
        if self.tries>3:
            await interaction.response.defer()
            await interaction.followup.send(f"Random Letter: **{self.random_letter}**")
            if self.random_letter_given is False:
                self.tries -= 2
                self.random_letter_given = True
        await self.out.edit(view=self)

    @discord.ui.button(label='Summary', style=discord.ButtonStyle.red)
    async def red(self, interaction: discord.Interaction,
                  button: discord.ui.Button):
        self.red.disabled = True
        if self.tries>5:
            await interaction.response.defer()
            await interaction.followup.send(f"Synopsis: **{self.synopsis}**")
            if self.synopsis_given is False:
                self.tries -= 5
                self.synopsis_given = True
        await self.out.edit(view=self)

class PlotsterView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=60)
        self.hint_given = False
        self.random_letter_given = False
        self.synopsis_given = False

    def reset(self):
        self.hint_given = False
        self.random_letter_given = False
        self.synopsis_given = False
        for child in self.children:
            child.disabled = False

    @discord.ui.button(label='Cast', style=discord.ButtonStyle.green)
    async def green(self, interaction: discord.Interaction,
                    button: discord.ui.Button):
        self.green.disabled=True
        await interaction.response.defer()
        await interaction.followup.send(self.cast)
        await self.out.edit(view=self)

    @discord.ui.button(label='Details', style=discord.ButtonStyle.blurple)
    async def blue(self, interaction: discord.Interaction,
                    button: discord.ui.Button):
        self.blue.disabled=True
        await interaction.response.defer()
        text = f"Rating: {self.movie['rating']}\nGenre: {self.movie['genre']}\nDuration: {self.movie['duration']}\nReleased: {self.movie['datePublished']}"
        await interaction.followup.send(text)
        await self.out.edit(view=self)

    @discord.ui.button(label='Synopsis', style=discord.ButtonStyle.red)
    async def red(self, interaction: discord.Interaction,
                  button: discord.ui.Button):
        self.red.disabled=True
        await interaction.response.defer()
        await interaction.followup.send(f"Synopsis: **{self.synopsis}**")
        await self.out.edit(view=self)



class QuizButton(discord.ui.Button):
    def __init__(self, label:str):
        super().__init__(style=discord.ButtonStyle.blurple, label=label)
        self.label = label

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if view.is_finished() or view.resolved:
            await interaction.response.send_message("This round is over.", ephemeral=True)
            return
        if interaction.user.id not in view.people_playing:
            await interaction.response.send_message("You are not in the game.", ephemeral=True)
            return
        if interaction.user.id in view.users:
            await interaction.response.send_message("You already answered this round.", ephemeral=True)
            return
        # Record the answer before awaiting network I/O so duplicate clicks cannot race.
        view.users[interaction.user.id] = {"A": 0, "B": 1, "C": 2, "D": 3}[self.label]
        await interaction.response.send_message("Your response has been submitted.", ephemeral=True)
        if len(view.users) == len(view.people_playing):
            await view.compare_answers()


class QuizsterView(discord.ui.View):

    def __init__(self, quiz_obj, timeout=60):
        super().__init__(timeout=timeout)
        self.hint_given = False
        self.quiz_obj = quiz_obj
        self.movie = quiz_obj.movie
        self.cast = f"Cast: **{self.movie['actors']}**"
        self.synopsis = self.movie['description']
        synopsis = f"Synopsis: **{self.synopsis}**"
        cast = self.cast
        details = f"Rating: {self.movie['rating']}\nGenre: {self.movie['genre']}\nDuration: {self.movie['duration']}\nReleased: {self.movie['datePublished']}"
        self.hint_text =  quiz_obj.hint
        self.users = {}
        self.skipping_users = []
        self.resolved = False
        self.skipped = False

        for i in ["A", "B", "C", "D"]:
            self.add_item(QuizButton(i))

    async def on_timeout(self):
        await self.compare_answers()

    def disable_view(self):
        for child in self.children:
            child.disabled = True

    def reset(self):
        self.hint_given = False

    async def compare_answers(self):
        if self.resolved:
            return
        self.resolved = True
        for user_id in list(self.people_playing):
            if self.users.get(user_id) == self.quiz_obj.answer_index:
                self.people[user_id][1] += 1
            else:
                self.people[user_id][0] = max(0, self.people[user_id][0] - 1)
                if self.people[user_id][0] == 0:
                    self.people_playing.remove(user_id)
        self.disable_view()
        self.stop()
        await self.response.edit(view=self)

    @discord.ui.button(label='‎', style=discord.ButtonStyle.grey, row=1, disabled=True)
    async def placeholder1(self, interaction: discord.Interaction,
                    button: discord.ui.Button):
        pass

    @discord.ui.button(label='Hint', style=discord.ButtonStyle.green, row=1)
    async def green(self, interaction: discord.Interaction,
                    button: discord.ui.Button):
        await interaction.response.defer()
        if interaction.user.id not in self.people_playing:
            await interaction.followup.send("You are not playing this quiz.", ephemeral=True)
            return
        if self.hints>0:
            if not self.hint_given:
                self.hint_given = True
                self.hints-=1
            await interaction.followup.send(self.hint_text)
        else:
            await interaction.followup.send("You don't have any hints left.")

    @discord.ui.button(label='Skip', style=discord.ButtonStyle.red, row=1)
    async def red(self, interaction: discord.Interaction,
                    button: discord.ui.Button):
        await interaction.response.defer()
        if interaction.user.id not in self.people_playing:
            await interaction.followup.send("You are not playing this quiz.", ephemeral=True)
            return
        if self.resolved:
            return
        if self.skips <= 0:
            await interaction.followup.send("You don't have any skips left.")
            return
        if interaction.user.id not in self.skipping_users:
            self.skipping_users.append(interaction.user.id)
        if len(self.skipping_users)>=round(len(self.people_playing)/2):
            self.resolved = True
            self.skipped = True
            self.skips -= 1
            self.disable_view()
            self.stop()
            await self.response.edit(view=self)
            await interaction.followup.send("Skipped.")
        else:
            await interaction.followup.send(f"Votes to skip: {len(self.skipping_users)}/{round(len(self.people_playing)/2)}")

    @discord.ui.button(label='‎', style=discord.ButtonStyle.grey, row=1, disabled=True)
    async def placeholder2(self, interaction: discord.Interaction,
                    button: discord.ui.Button):
        pass


# Bingo Views

class BingoButton(discord.ui.Button):
    def __init__(self, glob, player, label:str, row, disabled=False, style=discord.ButtonStyle.green):
        super().__init__(style=style, label=label, row=row, disabled=disabled)
        self.label = label
        self.player = player
        self.glob = glob #Global object

    def check_winner(self, ll, cut):
        total_lines = 0

        # checking columns
        for i in ll:
            if len(set(i) & set(cut))==5:
                total_lines+=1

        # checking rows
        for i in range(len(ll)):
            if len(set([x[i] for x in ll]) & set(cut))==5:
                total_lines+=1

        # getting diagonals
        d1 = []
        for i in range(len(ll)):
            d1.append(ll[i][i])
        d2 = []
        for i in range(len(ll)):
            d2.append(ll[i][-i-1])

        # Checking diagonals
        if len(set(d1) & set(cut))==5:
                total_lines+=1
        if len(set(d2) & set(cut))==5:
                total_lines+=1

        return total_lines

    def increase_turn(self):
        self.glob.turn+=1
        if self.glob.turn>=len(self.glob.players):
            self.glob.turn = 0


    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if self.glob.everyone_started:
            # IMPLEMENT TURN SYSTEM
            if list(self.glob.players.keys()).index(interaction.user.id) == self.glob.turn:
                self.increase_turn()
                self.player.cut.append(self.label)
                winners = []
                channel = interaction.channel or (getattr(self.glob, 'out', None) and self.glob.out.channel)
                for i in self.glob.players.values():
                    i.global_cut.append(self.label)
                    total_lines = self.check_winner(i.number_list, i.global_cut)
                    emojis = [":regional_indicator_b:", ":regional_indicator_i: ", ":regional_indicator_n: ", ":regional_indicator_g: ", ":regional_indicator_o: "]
                    details_string = f"Current turn: <@{list(self.glob.players.keys())[self.glob.turn]}>\n<@{interaction.user.id}> played **{self.label}**\n\n{''.join(emojis[:total_lines])}"
                    if i.msg:
                        try:
                            if getattr(self.glob, 'bot_user_id', None) and i.id == self.glob.bot_user_id:
                                await i.msg.edit(view=None, content=details_string)
                            else:
                                await i.msg.edit(view=BingoView(self.glob, i), content=details_string)
                        except Exception:
                            pass
                    
                    if total_lines>=5:
                        winners.append(i.id)

                winners = list(set(winners))
                for m in winners:
                    winner_tag = "🤖 Pippo" if (getattr(self.glob, 'bot_user_id', None) and m == self.glob.bot_user_id) else f"<@{m}>"
                    if channel:
                        await channel.send(f"{winner_tag} WON!")
                if len(winners)!=0:
                    for i in self.glob.players.values():
                        if getattr(i, "view", None):
                            i.view.stop()
                        if i.msg:
                            try:
                                await i.msg.edit(view=None, content="Game over!")
                            except Exception:
                                pass
                    return

                # Check if next turn is the bot's turn
                bot_turn_id = list(self.glob.players.keys())[self.glob.turn]
                if getattr(self.glob, 'bot_user_id', None) == bot_turn_id:
                    bot_player = self.glob.players[bot_turn_id]
                    uncut = [
                        n for row in bot_player.number_list for n in row
                        if n not in bot_player.cut and n not in bot_player.global_cut
                    ]
                    if uncut:
                        bot_label = random.choice(uncut)
                        self.increase_turn()
                        bot_player.cut.append(bot_label)
                        bot_winners = []
                        for i in self.glob.players.values():
                            i.global_cut.append(bot_label)
                            total_lines = self.check_winner(i.number_list, i.global_cut)
                            emojis = [":regional_indicator_b:", ":regional_indicator_i: ", ":regional_indicator_n: ", ":regional_indicator_g: ", ":regional_indicator_o: "]
                            details_string = f"Current turn: <@{list(self.glob.players.keys())[self.glob.turn]}>\n🤖 **Pippo** played **{bot_label}**\n\n{''.join(emojis[:total_lines])}"
                            if i.msg:
                                try:
                                    if getattr(self.glob, 'bot_user_id', None) and i.id == self.glob.bot_user_id:
                                        await i.msg.edit(view=None, content=details_string)
                                    else:
                                        await i.msg.edit(view=BingoView(self.glob, i), content=details_string)
                                except Exception:
                                    pass
                            if total_lines >= 5:
                                bot_winners.append(i.id)

                        bot_winners = list(set(bot_winners))
                        for m in bot_winners:
                            winner_tag = "🤖 Pippo" if (getattr(self.glob, 'bot_user_id', None) and m == self.glob.bot_user_id) else f"<@{m}>"
                            if channel:
                                await channel.send(f"{winner_tag} WON!")
                        if len(bot_winners) != 0:
                            for i in self.glob.players.values():
                                if getattr(i, "view", None):
                                    i.view.stop()
                                if i.msg:
                                    try:
                                        await i.msg.edit(view=None, content="Game over!")
                                    except Exception:
                                        pass

            else:
                await interaction.followup.send("It's not your turn.", ephemeral=True)

            #await self.player.msg.edit(view=BingoView(self.glob, self.player))
        else:
            await interaction.followup.send("Wait for everyone to start.", ephemeral=True)

class BingoView(discord.ui.View):

    def __init__(self, glob, player, timeout=60):
        super().__init__(timeout=timeout)
        previous = getattr(player, "view", None)
        if previous is not None:
            previous.stop()
        self.player = player
        self.glob = glob
        player.view = self

        self.populate_buttons()

    def populate_buttons(self):
        ll = self.player.number_list
        for i in range(len(ll)):
            for j in ll[i]:
                num =  j
                if str(num) in self.player.cut or str(num) in self.player.global_cut:
                    num = "X"
                    self.add_item(BingoButton(self.glob, self.player, num, row=i, disabled=True, style=discord.ButtonStyle.red))
                else:
                    self.add_item(BingoButton(self.glob, self.player, num, row=i, disabled=False))

    async def on_timeout(self):
        if getattr(self.player, "view", None) is not self:
            return
        for child in self.children:
            child.disabled = True
        if self.player.msg:
            try:
                await self.player.msg.edit(content="⏱️ Your Bingo board expired after inactivity. Start another game with `/play`.", view=self)
            except Exception:
                pass

class BingoStartView(discord.ui.View):

    def __init__(self, players, bot_user_id=None, timeout=60):
        super().__init__(timeout=timeout)
        self.players = players
        self.bot_user_id = bot_user_id
        self.turn = 0

    @discord.ui.button(label='Get my board', style=discord.ButtonStyle.green)
    async def start_button(self, interaction:discord.Interaction, button:discord.ui.Button):
        await interaction.response.defer()
        # Checking if the person is in the list or not.
        try:
            player = self.players[interaction.user.id]
        except:
            await interaction.followup.send("You're not in the game?", ephemeral=True)
            return 
             
        if player.started:
            await interaction.followup.send("You have already started, wait for others to start.", ephemeral=True)
        else:
            player.started = True
            details_string = f"Current turn: <@{list(self.players.keys())[0]}>"
            msg = await interaction.followup.send(view=BingoView(self, player), content=details_string, ephemeral=True)
            player.msg = msg

        if self.bot_user_id and self.bot_user_id in self.players:
            bot_player = self.players[self.bot_user_id]
            bot_player.started = True
            bot_player.msg = self.out

        self.everyone_started = True
        desc = "Waiting for board: "
        for i in self.players.values():
            if i.started==False:
                self.everyone_started = False
                desc += f"<@{i.id}> "

        if self.everyone_started:
            self.clear_items()
            self.stop()
            await self.out.edit(content="The game has begun.", view=self)
        else:
            await self.out.edit(content=desc)

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if getattr(self, "out", None):
            try:
                await self.out.edit(content="⏱️ Bingo start lobby expired. Run `/play` to start another game.", view=self)
            except Exception:
                pass


# Challenge Invite View for 1v1 duels
class GameLobbyView(discord.ui.View):
    """Reusable button lobby for games with more than one participant."""

    def __init__(self, owner_id: int, owner_name: str, game_name: str, timeout=45, max_players=10):
        super().__init__(timeout=timeout)
        self.owner_id = owner_id
        self.owner_name = owner_name
        self.game_name = game_name
        self.max_players = max_players
        self.joined_ids = [owner_id]
        self.started = False
        self.message = None

    def render(self):
        mentions = ", ".join(f"<@{user_id}>" for user_id in self.joined_ids)
        return (
            f"🎮 **{self.game_name} lobby**\n"
            f"Players ({len(self.joined_ids)}/{self.max_players}): {mentions}\n"
            "Press **Join** to play, then the host presses **Start**. "
            "Use the solo option when starting a game to play alone."
        )

    @discord.ui.button(label="Join", style=discord.ButtonStyle.success, emoji="🙋")
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.bot:
            await interaction.response.send_message("Bots cannot join this lobby.", ephemeral=True)
            return
        if interaction.user.id not in self.joined_ids:
            if len(self.joined_ids) >= self.max_players:
                await interaction.response.send_message("This lobby is full.", ephemeral=True)
                return
            self.joined_ids.append(interaction.user.id)
        await interaction.response.edit_message(content=self.render(), view=self)

    @discord.ui.button(label="Start", style=discord.ButtonStyle.primary, emoji="▶️")
    async def start(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("Only the host can start this game.", ephemeral=True)
            return
        if len(self.joined_ids) < 2:
            await interaction.response.send_message(
                "Invite at least one player, or choose solo when starting the game.", ephemeral=True
            )
            return
        self.started = True
        self.stop()
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content=f"✅ {self.game_name} is starting!", view=self)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger, emoji="✖️")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("Only the host can cancel this lobby.", ephemeral=True)
            return
        self.stop()
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content=f"{self.game_name} lobby cancelled.", view=self)

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            try:
                await self.message.edit(content=f"⏱️ {self.game_name} lobby expired. Start a new game when you're ready.", view=self)
            except Exception:
                pass


class ChallengeInviteView(discord.ui.View):
    def __init__(self, challenger: discord.Member, opponent: discord.Member, game_name: str = "Game", timeout=60):
        super().__init__(timeout=timeout)
        self.challenger = challenger
        self.opponent = opponent
        self.game_name = game_name
        self.accepted = None
        self.message = None

    @discord.ui.button(label="Accept ⚔️", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.opponent.id:
            await interaction.response.send_message("Only the challenged opponent can accept!", ephemeral=True)
            return
        self.accepted = True
        self.stop()
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(content=f"⚔️ **{self.opponent.display_name}** accepted the challenge from **{self.challenger.display_name}**!", view=self)

    @discord.ui.button(label="Decline ❌", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.opponent.id and interaction.user.id != self.challenger.id:
            await interaction.response.send_message("You cannot decline this challenge!", ephemeral=True)
            return
        self.accepted = False
        self.stop()
        for item in self.children:
            item.disabled = True
        decliner = "Challenge cancelled." if interaction.user.id == self.challenger.id else f"**{self.opponent.display_name}** declined the challenge."
        await interaction.response.edit_message(content=decliner, view=self)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if hasattr(self, 'message') and self.message:
            try:
                await self.message.edit(content="⏱️ Challenge timed out.", view=self)
            except Exception:
                pass


# Tic Tac Toe
class TicTacToeButton(discord.ui.Button['TicTacToeView']):
    def __init__(self, x: int, y: int):
        super().__init__(style=discord.ButtonStyle.secondary, label='\u200b', row=y)
        self.x = x
        self.y = y

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: TicTacToeView = self.view
        state = view.board[self.y][self.x]
        if state in (view.X, view.O):
            return

        # Player validation
        if view.vs_bot:
            if interaction.user != view.player_x:
                await interaction.response.send_message("Only you can play in this solo match!", ephemeral=True)
                return
        elif view.player_x and view.player_o:
            if interaction.user not in (view.player_x, view.player_o):
                await interaction.response.send_message("This game is between other players!", ephemeral=True)
                return
            if view.current_player == view.X and interaction.user != view.player_x:
                await interaction.response.send_message("It is Player X's turn!", ephemeral=True)
                return
            if view.current_player == view.O and interaction.user != view.player_o:
                await interaction.response.send_message("It is Player O's turn!", ephemeral=True)
                return
        elif view.player_x and not view.player_o:
            if view.current_player == view.X and interaction.user != view.player_x:
                await interaction.response.send_message("Only Player X can play the first move!", ephemeral=True)
                return
            if view.current_player == view.O:
                if interaction.user == view.player_x:
                    await interaction.response.send_message("Waiting for another player to play O!", ephemeral=True)
                    return
                view.player_o = interaction.user

        if view.current_player == view.X:
            self.style = discord.ButtonStyle.danger
            self.label = 'X'
            self.disabled = True
            view.board[self.y][self.x] = view.X
            view.current_player = view.O
            o_name = "Pippo 🤖" if view.vs_bot else (view.player_o.mention if view.player_o else "O")
            content = f"It is now {o_name}'s turn (O)"
        else:
            self.style = discord.ButtonStyle.success
            self.label = 'O'
            self.disabled = True
            view.board[self.y][self.x] = view.O
            view.current_player = view.X
            x_name = view.player_x.mention if view.player_x else "X"
            content = f"It is now {x_name}'s turn (X)"

        winner = view.check_board_winner()
        if winner is not None:
            if winner == view.X:
                winner_name = view.player_x.mention if view.player_x else "X"
                content = f"🏆 **{winner_name}** won! Run `/play` to start another game."
            elif winner == view.O:
                winner_name = "Pippo 🤖" if view.vs_bot else (view.player_o.mention if view.player_o else "O")
                content = f"🏆 **{winner_name}** won! Run `/play` to start another game."
            else:
                content = "🤝 It's a tie! Run `/play` to start another game."

            for child in view.children:
                child.disabled = True
            view.stop()
        elif view.vs_bot and view.current_player == view.O:
            # Bot AI plays its turn
            view.bot_move()
            bot_winner = view.check_board_winner()
            if bot_winner is not None:
                if bot_winner == view.O:
                    content = "🤖 **Pippo** won! Run `/play` to start another game."
                elif bot_winner == view.Tie:
                    content = "🤝 It's a tie! Run `/play` to start another game."
                for child in view.children:
                    child.disabled = True
                view.stop()
            else:
                content = f"It is now {view.player_x.mention}'s turn (X)!"

        await interaction.response.edit_message(content=content, view=view)


class TicTacToeView(discord.ui.View):
    children: List[TicTacToeButton]
    X = -1
    O = 1
    Tie = 2

    def __init__(self, player_x: discord.Member = None, player_o: discord.Member = None, vs_bot: bool = False, timeout=120):
        super().__init__(timeout=timeout)
        self.player_x = player_x
        self.player_o = player_o
        self.vs_bot = vs_bot
        self.current_player = self.X
        self.message = None
        self.board = [
            [0, 0, 0],
            [0, 0, 0],
            [0, 0, 0],
        ]

        for x in range(3):
            for y in range(3):
                self.add_item(TicTacToeButton(x, y))

    def _apply_bot_cell(self, r, c):
        self.board[r][c] = self.O
        for btn in self.children:
            if btn.x == c and btn.y == r:
                btn.label = 'O'
                btn.style = discord.ButtonStyle.success
                btn.disabled = True
                break
        self.current_player = self.X

    def bot_move(self):
        # 1. Winning move
        for r in range(3):
            for c in range(3):
                if self.board[r][c] == 0:
                    self.board[r][c] = self.O
                    if self.check_board_winner() == self.O:
                        self._apply_bot_cell(r, c)
                        return
                    self.board[r][c] = 0

        # 2. Block move
        for r in range(3):
            for c in range(3):
                if self.board[r][c] == 0:
                    self.board[r][c] = self.X
                    if self.check_board_winner() == self.X:
                        self._apply_bot_cell(r, c)
                        return
                    self.board[r][c] = 0

        # 3. Center
        if self.board[1][1] == 0:
            self._apply_bot_cell(1, 1)
            return

        # 4. Corners
        corners = [(0, 0), (0, 2), (2, 0), (2, 2)]
        random.shuffle(corners)
        for r, c in corners:
            if self.board[r][c] == 0:
                self._apply_bot_cell(r, c)
                return

        # 5. Any free cell
        empty = [(r, c) for r in range(3) for c in range(3) if self.board[r][c] == 0]
        if empty:
            r, c = random.choice(empty)
            self._apply_bot_cell(r, c)

    def check_board_winner(self):
        for across in self.board:
            value = sum(across)
            if value == 3:
                return self.O
            elif value == -3:
                return self.X

        for line in range(3):
            value = self.board[0][line] + self.board[1][line] + self.board[2][line]
            if value == 3:
                return self.O
            elif value == -3:
                return self.X

        diag = self.board[0][2] + self.board[1][1] + self.board[2][0]
        if diag == 3:
            return self.O
        elif diag == -3:
            return self.X

        diag = self.board[0][0] + self.board[1][1] + self.board[2][2]
        if diag == 3:
            return self.O
        elif diag == -3:
            return self.X

        if all(i != 0 for row in self.board for i in row):
            return self.Tie

        return None

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if hasattr(self, 'message') and self.message:
            try:
                await self.message.edit(content="⏱️ Tic Tac Toe ended after inactivity. Run `/play` to start another game.", view=self)
            except Exception:
                pass


# Modern Interactive Help Views
class HelpCategorySelect(discord.ui.Select):
    def __init__(self, bot, prefix="."):
        self.bot = bot
        self.prefix = prefix
        options = [
            discord.SelectOption(label="Home", emoji="🏠", description="Overview & category guide", value="home", default=True),
            discord.SelectOption(label="Games & Trivia", emoji="🎮", description="Bollywood, Bingo, TicTacToe, Flood, Memory, Clash", value="games"),
            discord.SelectOption(label="Economy & Shop", emoji="🪙", description="Coins, balances, transfers, and cartoon shop", value="economy"),
            discord.SelectOption(label="Fun & Social", emoji="🎉", description="Ship, Flames, Cartoons, 8Ball, Urban Dictionary", value="fun"),
            discord.SelectOption(label="Animals", emoji="🐾", description="Dogs, Cats, Meow/Woof trivia, and Breed Matchers", value="animals"),
            discord.SelectOption(label="Settings & Utility", emoji="⚙️", description="Prefix, Leaderboard, Greetings, Suggestions", value="settings"),
        ]
        super().__init__(placeholder="Select a category to browse...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if self.view.author_id and interaction.user.id != self.view.author_id:
            await interaction.response.send_message("Only the user who requested this help menu can browse categories.", ephemeral=True)
            return

        choice = self.values[0]
        for option in self.options:
            option.default = (option.value == choice)

        embed = self.view.generate_embed(choice)
        await interaction.response.edit_message(embed=embed, view=self.view)


class HelpView(discord.ui.View):
    CATEGORY_COGS = {
        "games": {"Games"},
        "economy": {"Economy", "Shop"},
        "fun": {"Fun", "Actions"},
        "animals": {"Animals"},
        "settings": {"Settings", "Schedules", "Help", "Play", "Info"},
    }

    def __init__(self, bot=None, author_id=None, prefix=".", timeout=120):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.author_id = author_id
        self.prefix = prefix
        self.message = None

        if self.bot:
            self.add_item(HelpCategorySelect(self.bot, prefix=self.prefix))

        server_url = "https://discord.gg/ugcEEd8pAP"
        self.add_item(discord.ui.Button(label='Support Server', emoji='💬', url=server_url))
        vote_url = "https://top.gg/bot/1066895131485163570/vote"
        self.add_item(discord.ui.Button(label='Vote on Top.gg', emoji='⭐', url=vote_url))

    def generate_embed(self, category: str) -> discord.Embed:
        category_info = {
            "games": ("🎮 Games & Trivia", "Movie games, trivia, and party games.", discord.Color.gold()),
            "economy": ("🪙 Economy & Shop", "Balances, coin transfers, and shop commands.", discord.Color.green()),
            "fun": ("🎉 Fun & Social", "Social games and pop-culture commands.", discord.Color.magenta()),
            "animals": ("🐾 Animals", "Pet photos, breed quizzes, and breed matchers.", discord.Color.teal()),
            "settings": ("⚙️ Settings & Utilities", "Server setup, leaderboards, and feedback.", discord.Color.blue()),
        }
        if category in category_info:
            title, description, color = category_info[category]
            emb = discord.Embed(title=title, description=description, color=color)
            commands = []
            if self.bot:
                commands = [
                    command for command in self.bot.walk_commands()
                    if not command.hidden and command.cog_name in self.CATEGORY_COGS[category]
                ]
            for command in sorted(commands, key=lambda item: item.name):
                prefix_command = f"{self.prefix}{command.qualified_name}"
                slash_command = f"/{command.qualified_name}"
                summary = command.short_doc or command.help or "No description available."
                if command.name in {"bollywood", "hollywood", "plotster", "quizster", "poster"}:
                    summary += " Use `solo: True` (prefix) or enable `solo` (slash) to play alone."
                elif command.name in {"bingo", "flood", "clash", "woof", "meow", "onewordstory"}:
                    summary += " For prefix commands, append `true` to play solo; for slash commands, enable `solo`."
                emb.add_field(
                    name=f"`{prefix_command}` · `{slash_command}`",
                    value=summary[:1024],
                    inline=False,
                )
            if not commands:
                emb.description += "\nNo commands are available in this category right now."
            return emb

        if category == "home":
            emb = discord.Embed(
                title="👋 Welcome to Pippo!",
                description=(
                    "Pick a category from the menu to see available commands.\n\n"
                    f"For an interactive game menu, run `/play` or `{self.prefix}play`. "
                    f"You can also use slash commands or the `{self.prefix}` prefix."
                ),
                color=discord.Color.gold(),
            )
            category_titles = {
                "games": "🎮 Games & Trivia",
                "economy": "🪙 Economy & Shop",
                "fun": "🎉 Fun & Social",
                "animals": "🐾 Animals",
                "settings": "⚙️ Settings & Utilities",
            }
            for key, title in category_titles.items():
                available = (
                    [command for command in self.bot.walk_commands()
                     if not command.hidden and command.cog_name in self.CATEGORY_COGS[key]]
                    if self.bot else []
                )
                emb.add_field(name=title, value=f"{len(available)} commands · select the category for details.", inline=False)
            emb.set_footer(text="Use /help <command> or the prefix help command for a command’s details.")
            return emb

        return discord.Embed(title="Help", description="Choose a category from the menu above.", color=discord.Color.gold())

    async def on_timeout(self):
        for child in self.children:
            if isinstance(child, discord.ui.Select):
                child.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except Exception:
                pass


# BreedGuessView
class BreedGuessButton(discord.ui.Button):
    def __init__(self, label: str, view, answer=False, row=1, disabled=False, style=discord.ButtonStyle.grey):
        super().__init__(style=style, label=label, row=row, disabled=disabled)
        self.label = label
        self.answer = answer

    async def callback(self, interaction: discord.Interaction):
        if self.view.author_id is not None and interaction.user.id != self.view.author_id:
            await interaction.response.send_message("Only the person who started this quiz can answer.", ephemeral=True)
            return
        await interaction.response.defer()
        for i in self.view.children:
            i.disabled = True
            if getattr(i, 'answer', False) is True:
                i.style = discord.ButtonStyle.green

        if self.answer is False:
            self.style = discord.ButtonStyle.red
            feedback = f"❌ **{interaction.user.display_name}** guessed **{self.label}**, which is incorrect! The correct breed was **{self.view.answer}**."
        else:
            feedback = f"🎉 **{interaction.user.display_name}** guessed correctly! It's a **{self.label}**!"

        self.view.stop()
        await self.view.out.edit(view=self.view)
        await interaction.followup.send(feedback)


class BreedGuessView(discord.ui.View):
    def __init__(self, answer, breeds, timeout=60, author_id=None):
        super().__init__(timeout=timeout)
        self.answer = answer
        self.author_id = author_id
        self.out = None
        for i in breeds:
            ans = (i == answer)
            self.add_item(BreedGuessButton(i, self, answer=ans))

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
            if getattr(child, 'answer', False):
                child.style = discord.ButtonStyle.green
        if self.out:
            try:
                await self.out.edit(view=self)
            except Exception:
                pass


# MemoryView

class MemoryButton(discord.ui.Button):
    def __init__(self, label:str, row, disabled=False, style=discord.ButtonStyle.grey):
        super().__init__(style=style, label=label, row=row, disabled=disabled)
        self.revealed = False

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if interaction.user.id != self.view.players[self.view.turn].id:
            await interaction.followup.send("Not really your turn, is it?", ephemeral=True)
            return
        if self in self.view.temp_clicked or self.revealed:
            await interaction.followup.send("You cannot select the same card twice!", ephemeral=True)
            return
        self.view.temp_clicked.append(self)
        if len(self.view.temp_clicked) == 1:
            self.label = self.view.emojis[self.view.children.index(self)]
            self.style = discord.ButtonStyle.blurple
            await self.view.out.edit(view=self.view)
        else:
            self.view.moves += 1
            btn2 = self.view.temp_clicked[1]
            emoji_index = self.view.children.index(btn2)
            self.label = self.view.emojis[self.view.children.index(self)]

            if self.view.temp_clicked[0].label == self.view.emojis[emoji_index]:
                self.view.scores[self.view.turn] += 1
                self.view.pairs_found += 1
                self.view.revealed += self.view.temp_clicked
                for i in self.view.temp_clicked:
                    i.revealed = True
                    i.style = discord.ButtonStyle.green
                    i.label = self.view.emojis[self.view.children.index(i)]
                    i.disabled = True

                if self.view.is_solo:
                    if self.view.check_winner() is True:
                        content = f"🏆 **Victory!** {self.view.players[0].mention} matched all 8 pairs in **{self.view.moves}** moves. Run `/play` to play again."
                        for i in self.view.children:
                            i.disabled = True
                        self.view.stop()
                    else:
                        content = f"🃏 **Solo Memory Challenge**\nMatched: **{self.view.pairs_found}/8** pairs | Moves: **{self.view.moves}**"
                else:
                    if self.view.check_winner() is True:
                        if self.view.scores[0] == self.view.scores[1]:
                            content = f"🤝 It's a tie at **{self.view.scores[0]}** pairs each. Run `/play` to play again."
                        else:
                            winner = self.view.scores.index(max(self.view.scores))
                            content = f"🏆 {self.view.players[winner].mention} has won with **{self.view.scores[winner]}** pairs! Run `/play` to play again."
                        for i in self.view.children:
                            i.disabled = True
                        self.view.stop()
                    else:
                        content = f":arrow_forward: {self.view.players[0].mention}:{self.view.scores[0]}\n:arrow_forward: {self.view.players[1].mention}:{self.view.scores[1]}\n"

                self.view.temp_clicked = []
                await self.view.out.edit(content=content, view=self.view)
            else:
                for i in self.view.children:
                    i.disabled = True
                for i in self.view.temp_clicked:
                    i.disabled = True
                    i.style = discord.ButtonStyle.red
                await self.view.out.edit(view=self.view)
                await asyncio.sleep(1)
                for i in self.view.children:
                    i.disabled = i.revealed 
                    i.label = "‎ "
                    i.style = discord.ButtonStyle.grey
                    if i.revealed:
                        i.label = self.view.emojis[self.view.children.index(i)]
                        i.style = discord.ButtonStyle.green

                if not self.view.is_solo:
                    self.view.change_turn()
                    content = f":arrow_forward: {self.view.players[0].mention}:{self.view.scores[0]}\n:arrow_forward: {self.view.players[1].mention}:{self.view.scores[1]}\n{self.view.players[self.view.turn].mention}'s turn"
                else:
                    content = f"🃏 **Solo Memory Challenge**\nMatched: **{self.view.pairs_found}/8** pairs | Moves: **{self.view.moves}**"

                self.view.temp_clicked = []
                await self.view.out.edit(content=content, view=self.view)


class MemoryView(discord.ui.View):

    def __init__(self, user1, user2=None):
        super().__init__(timeout=90)
        self.is_solo = (user2 is None)
        self.players = [user1] if self.is_solo else [user1, user2]
        self.turn = 0
        self.buttons_list = []
        self.temp_clicked = []
        self.revealed = []
        self.out = None
        self.scores = [0] if self.is_solo else [0, 0]
        self.moves = 0
        self.pairs_found = 0

        emojis = [
            "😭", "😔", "😡", "😏", "😋", "🤤", "😋", "😘", "😟", "🤓", "😎", "🤩", "😣", "😿", "😙", "😁",
            "😗", "😐", "😮", "😈", "🤡", "👉", "😼", "😾", "😺", "🤜", "💪", "🙌", "😛", "👩‍🦱", "👁️",
            "👇", "🦷", "👨‍🌾", "🕵️‍♀️", "👷‍♀️", "👮‍♂️", "💂", "👨‍🌾", "🦻", "💆‍♀️", "🤷‍♂️", "👶", "🙇‍♂️",
            "🙍‍♂️", "👛", "🩴", "👗", "👒", "🦺", "👛", "🦇", "🐒", "🦋", "🐡", "🦟", "🐸", "🦶", "🥀",
            "🎋", "🐲", "🥗", "🍑", "🍈", "🥑", "🥔", "🥯", "🥕", "🍆", "⚾", "⚽", "🏀"
        ]

        emojis = random.sample(emojis, 8)
        emojis += emojis
        random.shuffle(emojis)
        self.emojis = emojis

        self.populate_buttons()
        
    def populate_buttons(self):
        if len(self.buttons_list) == 0:
            row_change = 0
            row = 0
            for i in range(16):
                label = "‎ "
                if row_change%4==0:
                    row+=1
                btn = MemoryButton(label, row)
                self.add_item(btn)
                row_change+=1
        else:
            row_change = 0
            row = 0
            for i in self.buttons_list:
                if i.revealed is True:
                    label = ""
                else:
                    label = "‎ "

    def change_turn(self):
        self.turn+=1
        if self.turn==len(self.players):
            self.turn = 0

    def check_winner(self):
        """Check if someone has won"""
        if len(self.revealed) == 16:
            return True
        else:
            return False

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.out:
            try:
                await self.out.edit(content="⏱️ Memory Match ended after inactivity. Run `/play` to start another game.", view=self)
            except Exception:
                pass


# FloodView 

class FloodButton(discord.ui.Button):
    def __init__(self, label:str, row=0, disabled=False, style=discord.ButtonStyle.grey, emoji=None, color=None):
        super().__init__(style=style, label=label, row=row, disabled=disabled)
        self.color = color
        if emoji:
            self.emoji = emoji

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()

        # Check if the correct user has pressed the button
        if self.view.players[self.view.turn] != interaction.user:
            await interaction.followup.send("Its not really your turn, is it?", ephemeral=True)
            return

        colors = {"red": (255, 0, 0),
                "green": (0, 255, 0),
                "blue": (0, 0, 255),
                "yellow": (255, 255, 0),
                "magenta": (255, 0, 255)
                }


        self.view.flood.replace_pixels(interaction.user.id, colors[self.color])
        self.view.change_turn()

        self.view.clear_items()
        self.view.populate_buttons()

        if await self.view.check_winner() is True:
            return

        if getattr(self.view, 'vs_bot', False):
            # Bot AI turn
            probable = self.view.flood.return_probable_buttons()
            if probable:
                bot_color = probable[0]
                self.view.flood.replace_pixels(self.view.bot.user.id, bot_color)
            self.view.change_turn()
            self.view.clear_items()
            self.view.populate_buttons()
            if await self.view.check_winner() is True:
                return

        await self.view.update_msg(embed=self.view.return_embed(), file=self.view.flood.return_image())

class FloodView(discord.ui.View):

    def __init__(self, user1, emojis):
        super().__init__(timeout=60)
        self.players = [user1]
        self.emojis = emojis
        self.turn = 0
        self.vs_bot = False
        self.bot = None
        self.colors = {
            (255, 0, 0): "red",   # Red
            (0, 255, 0): "green",   # Green
            (0, 0, 255): "blue",   # Blue
            (255, 255, 0): "yellow", # Yellow
            (255, 0, 255): "magenta"  # Magenta
        }

    def populate_buttons(self):
        probable_buttons = self.flood.return_probable_buttons()
        for i in probable_buttons:
            btn = FloodButton(self.colors[i], color=self.colors[i], emoji=self.emojis[self.colors[i]])
            self.add_item(btn)

    async def update_msg(self, embed=None, file=None):
        await self.out.edit(view=self, embed=embed, attachments=[file])

    def change_turn(self):
        self.turn+=1
        if self.turn==len(self.players):
            self.turn = 0

    async def check_winner(self):
        percentages = self.flood.get_percentages()
        for i, j in enumerate(percentages):
            if j>50:
                self.stop()
                self.clear_items()
                winner = self.players[i]
                winner_title = f"{winner.name} WON!" if hasattr(winner, 'name') else "Pippo WON!"
                embed = discord.Embed(title=winner_title, color=discord.Color.green())
                embed.description = "Run `/play` to start another Flood game."
                image_url = "attachment://flood.png"
                embed.set_image(url=image_url) # image file needs to be sent with the message separately
                await self.update_msg(embed=embed, file=self.flood.return_image())
                return True
        return False

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if getattr(self, "out", None):
            try:
                await self.out.edit(content="⏱️ Flood ended after inactivity. Run `/play` to start another game.", view=self)
            except Exception:
                pass

    def return_embed(self):
        """Return the required embed"""
        percentages = self.flood.get_percentages()

        current_turn = f"{self.players[self.turn].mention}'s turn"
        p2_name = getattr(self.players[1], 'name', 'Pippo')
        percentages_str = f"{self.emojis['top_left']} {self.players[0].mention}: {round(percentages[0])}%\n{self.emojis['bottom_right']} {self.players[1].mention}: {round(percentages[1])}%"
        embed = discord.Embed(title=f"{self.players[0].name} v/s {p2_name}",
                              description=f"{current_turn}\n\n{percentages_str}",
                              color=discord.Color.blue())
        image_url = "attachment://flood.png"
        embed.set_image(url=image_url)

        return embed

    @discord.ui.button(label='Accept the challenge!', style=discord.ButtonStyle.green)
    async def start(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()

        if len(self.players) == 1:
            if interaction.user != self.players[0]:
                self.players.append(interaction.user)
                self.flood = Flood(self.players)
                self.clear_items()
                self.populate_buttons()
                await self.update_msg(embed=self.return_embed(), file=self.flood.return_image())
            else:
                await interaction.followup.send("You cannot accept your own challenge!", ephemeral=True)
        else:
            await interaction.followup.send("This match already has two players!", ephemeral=True)

    @discord.ui.button(label='Play vs Pippo 🤖', style=discord.ButtonStyle.blurple)
    async def play_bot(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if interaction.user != self.players[0]:
            await interaction.followup.send("Only the challenger can start single player mode!", ephemeral=True)
            return

        bot_player = self.bot.user
        self.players.append(bot_player)
        self.vs_bot = True
        self.flood = Flood(self.players)
        self.clear_items()
        self.populate_buttons()
        await self.update_msg(embed=self.return_embed(), file=self.flood.return_image())


# GuessTheMovie

class GuessTheMovieButton(discord.ui.Button):
    def __init__(self, label:str, correct="", row=0, disabled=False, style=discord.ButtonStyle.grey):
        super().__init__(style=style, label=label, row=row, disabled=disabled)
        self.correct = correct

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()

        if self.correct == self.label:
            self.style = discord.ButtonStyle.green
            for i in self.view.children:
                i.disabled = True
        else:
            self.style = discord.ButtonStyle.red
            for i in self.view.children:
                i.disabled = True
                if i.label == self.correct:
                    i.style = discord.ButtonStyle.green

        await self.view.update_msg()

class GuessTheMovieView(discord.ui.View):

    def __init__(self, movie, other):
        super().__init__(timeout=60)
        self.populate_buttons(movie, other)

    def populate_buttons(self, movie, other):
        other.append(movie)
        random.shuffle(other)
        for i in other:
            btn = GuessTheMovieButton(i, correct=movie)
            self.add_item(btn)

    async def update_msg(self):
        await self.out.edit(view=self)


class ShipButton(discord.ui.Button):
    def __init__(self, label:str, style=discord.ButtonStyle.grey, disabled=False):
        super().__init__(style=style, label=label, disabled=disabled)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.disabled = True
        self.style = discord.ButtonStyle.red
        #disable button in the old message
        await self.view.update_msg()
        await self.view.ctx.invoke(self.view.bot.get_command("ship"))

class ShipView(discord.ui.View):

    def __init__(self, bot, ctx):
        super().__init__(timeout=120)
        self.bot = bot
        self.ctx = ctx
        
        self.add_item(ShipButton("Ship Again", style=discord.ButtonStyle.green))

    async def update_msg(self):
        await self.out.edit(view=self)
