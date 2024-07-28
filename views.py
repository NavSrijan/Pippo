import discord
import ipdb
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

    def reset(self):
        self.hint_given = False
        self.random_letter_given = False
        self.synopsis_given = False

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
        await interaction.response.defer()
        ans_key = {"A": 0, "B": 1, "C": 2, "D": 3}
        view = self.view
        if interaction.user.id in view.people_playing:
            if view.users.get(interaction.user.id) is not None:
                msg = await interaction.followup.send("Haven't you already responded?", ephemeral=True)
                await asyncio.sleep(1)
                await msg.delete()
            else:
                msg = await interaction.followup.send("Your response has been submitted.", ephemeral=True)
                await asyncio.sleep(1)
                await msg.delete()
                view.users[interaction.user.id] = ans_key[self.label]
        else:
            msg = await interaction.followup.send("You are not in the game.", ephemeral=True)
            await asyncio.sleep(1)
            await msg.delete()
        #Check if all the users have responded
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

        for i in ["A", "B", "C", "D"]:
            self.add_item(QuizButton(i))

    async def on_timeout(self):
        self.disable_view()
        await self.response.edit(view=self)

    def disable_view(self):
        for child in self.children:
            child.disabled = True

    def reset(self):
        self.hint_given = False

    """async def compare_answers(self):
        for user_id, ans in self.users.items():
            if ans == self.quiz_obj.answer_index:
                self.people.get(user_id)[1]+=1
            else:
                self.people.get(user_id)[0]-=1
            if self.people.get(user_id)[0]==0:
                self.people_playing.remove(user_id)

        self.disable_view()
        await self.response.edit(view=self)
        self.stop()
        """
    async def compare_answers(self):
        for user_id, ans in self.users.items():
            if ans == self.quiz_obj.answer_index:
                self.people[user_id][1] += 1
            else:
                if self.people[user_id][0] > 0:  # Ensure lives are deducted only once
                    self.people[user_id][0] -= 1
                    if self.people[user_id][0] == 0:
                        self.people_playing.remove(user_id)

        self.disable_view()
        await self.response.edit(view=self)
        self.stop()

    @discord.ui.button(label='‎', style=discord.ButtonStyle.grey, row=1, disabled=True)
    async def placeholder1(self, interaction: discord.Interaction,
                    button: discord.ui.Button):
        pass

    @discord.ui.button(label='Hint', style=discord.ButtonStyle.green, row=1)
    async def green(self, interaction: discord.Interaction,
                    button: discord.ui.Button):
        await interaction.response.defer()
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
        if self.skips<0:
            await interaction.followup.send("You don't have any skips left.")
            return
        if interaction.user.id not in self.skipping_users:
            self.skipping_users.append(interaction.user.id)
        if len(self.skipping_users)>=round(len(self.people_playing)/2):
            await interaction.followup.send("Skipped.")
            self.stop()
            self.skips-=1
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
                for i in self.glob.players.values():
                    chnl = i.msg.channel
                    ### Turn etc string
                    i.global_cut.append(self.label)
                    total_lines = self.check_winner(i.number_list, i.global_cut)
                    emojis = [":regional_indicator_b:", ":regional_indicator_i: ", ":regional_indicator_n: ", ":regional_indicator_g: ", ":regional_indicator_o: "]
                    details_string = f"Current turn: <@{list(self.glob.players.keys())[self.glob.turn]}>\n<@{interaction.user.id}> played **{self.label}**\n\n{''.join(emojis[:total_lines])}"
                    await i.msg.edit(view=BingoView(self.glob, i), content=details_string)
                    
                    if total_lines>=5:
                        winners.append(i.id)

                winners = list(set(winners))
                for m in winners:
                    await chnl.send(f"<@{m}> WON!")
                if len(winners)!=0:
                    for i in self.glob.players.values():
                        await i.msg.edit(view=None, content="Game over!")

            else:
                await interaction.followup.send("It's not your turn.", ephemeral=True)

            #await self.player.msg.edit(view=BingoView(self.glob, self.player))
        else:
            await interaction.followup.send("Wait for everyone to start.", ephemeral=True)

class BingoView(discord.ui.View):

    def __init__(self, glob, player, timeout=60):
        super().__init__(timeout=timeout)
        self.player = player
        self.glob = glob

        self.populate_buttons()

    def populate_buttons(self):
        ll = self.player.number_list
        for i in range(len(ll)):
            for j in ll[i]:
                num =  j
                if str(num) in self.player.cut or str(num) in self.player.global_cut:
                    num = "X"
                    self.add_item(BingoButton(self.glob, self.player, num, row=i, disabled=True, style=discord.ButtonStyle.red))
                    continue
                self.add_item(BingoButton(self.glob, self.player, num, row=i, disabled=False))

class BingoStartView(discord.ui.View):

    def __init__(self, players, timeout=60):
        super().__init__(timeout=timeout)
        self.players = players
        self.turn = 0

    @discord.ui.button(label='Start', style=discord.ButtonStyle.green)
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

        self.everyone_started = True
        desc = "Not started: "
        for i in self.players.values():
            if i.started==False:
                self.everyone_started = False
                desc += f"<@{i.id}> "

        if self.everyone_started:
            self.clear_items()
            await self.out.edit(content="The game has begun.", view=self)
        else:
            await self.out.edit(content=desc)


# Tic Tac Toe

# Defines a custom button that contains the logic of the game.
# The ['TicTacToe'] bit is for type hinting purposes to tell your IDE or linter
# what the type of `self.view` is. It is not required.
class TicTacToeButton(discord.ui.Button['TicTacToe']):
    def __init__(self, x: int, y: int):
        # A label is required, but we don't need one so a zero-width space is used
        # The row parameter tells the View which row to place the button under.
        # A View can only contain up to 5 rows -- each row can only have 5 buttons.
        # Since a Tic Tac Toe grid is 3x3 that means we have 3 rows and 3 columns.
        super().__init__(style=discord.ButtonStyle.secondary, label='\u200b', row=y)
        self.x = x
        self.y = y

    # This function is called whenever this particular button is pressed
    # This is part of the "meat" of the game logic
    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: TicTacToe = self.view
        state = view.board[self.y][self.x]
        if state in (view.X, view.O):
            return

        if view.current_player == view.X:
            self.style = discord.ButtonStyle.danger
            self.label = 'X'
            self.disabled = True
            view.board[self.y][self.x] = view.X
            view.current_player = view.O
            content = "It is now O's turn"
        else:
            self.style = discord.ButtonStyle.success
            self.label = 'O'
            self.disabled = True
            view.board[self.y][self.x] = view.O
            view.current_player = view.X
            content = "It is now X's turn"

        winner = view.check_board_winner()
        if winner is not None:
            if winner == view.X:
                content = 'X won!'
            elif winner == view.O:
                content = 'O won!'
            else:
                content = "It's a tie!"

            for child in view.children:
                child.disabled = True

            view.stop()

        await interaction.response.edit_message(content=content, view=view)


# This is our actual board View
class TicTacToeView(discord.ui.View):
    # This tells the IDE or linter that all our children will be TicTacToeButtons
    # This is not required
    children: List[TicTacToeButton]
    X = -1
    O = 1
    Tie = 2

    def __init__(self):
        super().__init__()
        self.current_player = self.X
        self.board = [
            [0, 0, 0],
            [0, 0, 0],
            [0, 0, 0],
        ]

        # Our board is made up of 3 by 3 TicTacToeButtons
        # The TicTacToeButton maintains the callbacks and helps steer
        # the actual game.
        for x in range(3):
            for y in range(3):
                self.add_item(TicTacToeButton(x, y))

    # This method checks for the board winner -- it is used by the TicTacToeButton
    def check_board_winner(self):
        for across in self.board:
            value = sum(across)
            if value == 3:
                return self.O
            elif value == -3:
                return self.X

        # Check vertical
        for line in range(3):
            value = self.board[0][line] + self.board[1][line] + self.board[2][line]
            if value == 3:
                return self.O
            elif value == -3:
                return self.X

        # Check diagonals
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

        # If we're here, we need to check if a tie was made
        if all(i != 0 for row in self.board for i in row):
            return self.Tie

        return None

# Help View

class HelpView(discord.ui.View):

    def __init__(self, timeout=60):
        super().__init__(timeout=timeout)
        server_url="https://discord.gg/ugcEEd8pAP"
        self.add_item(discord.ui.Button(label='Server', url=server_url))
        vote_url="https://top.gg/bot/1066895131485163570/vote"
        self.add_item(discord.ui.Button(label='Vote', url=vote_url))


# BreedGuessView

class BreedGuessButton(discord.ui.Button):

    def __init__(self, label:str, view, answer=False, row=1, disabled=False, style=discord.ButtonStyle.grey):
        super().__init__(style=style, label=label, row=row, disabled=disabled)
        self.label = label
        self.answer=answer
        #self.view = view

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        for i in self.view.children:
            i.disabled=True
            if i.answer is True:
                i.style = discord.ButtonStyle.green

        if self.answer is False:
            self.style = discord.ButtonStyle.red
        await self.view.out.edit(view=self.view)


class BreedGuessView(discord.ui.View):

    def __init__(self, answer, breeds, timeout=60):
        super().__init__(timeout=timeout)
        ans=False
        for i in breeds:
            ans = False
            if i == answer:
                ans=True
            self.add_item(BreedGuessButton(i, self, answer=ans))


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
        self.view.temp_clicked.append(self)
        if len(self.view.temp_clicked) == 1:
            self.label = self.view.emojis[self.view.children.index(self)]
            self.style = discord.ButtonStyle.blurple
        else:
            btn2 = self.view.temp_clicked[1]
            emoji_index = self.view.children.index(btn2)
            if self.view.temp_clicked[0].label == self.view.emojis[emoji_index]:
                self.view.scores[self.view.turn]+=1
                self.view.revealed+= self.view.temp_clicked
                for i in self.view.temp_clicked:
                    i.revealed = True
                    i.style = discord.ButtonStyle.green
                    i.label = self.view.emojis[self.view.children.index(i)]
                    i.disabled = True
            else:
                for i in self.view.children:
                    i.disabled = True
                for i in self.view.temp_clicked:
                    i.disabled = True
                    i.style = discord.ButtonStyle.red
                self.label = self.view.emojis[self.view.children.index(self)]
                await self.view.out.edit(view=self.view)
                await asyncio.sleep(1)
                for i in self.view.children:
                    i.disabled = i.revealed 
                    i.label = "‎ "
                    i.style = discord.ButtonStyle.grey
                    if i.revealed:
                        i.label = self.view.emojis[self.view.children.index(i)]
                        i.style = discord.ButtonStyle.green

                self.view.change_turn()
                await self.view.out.edit(content=f"{self.view.players[self.view.turn].mention}'s turn", view=self.view)

            if self.view.check_winner() is True:
                winner = self.view.scores.index(max(self.view.scores))
                await self.view.out.reply(f"{self.view.players[winner].mention} has won!")

            self.view.temp_clicked = []
            
        content = f":arrow_forward: {self.view.players[0].mention}:{self.view.scores[0]}\n:arrow_forward: {self.view.players[1].mention}:{self.view.scores[1]}\n"
        await self.view.out.edit(content=content, view=self.view)


class MemoryView(discord.ui.View):

    def __init__(self, user1, user2):
        super().__init__(timeout=60)
        self.players = [user1, user2]
        self.turn = 0
        self.buttons_list = []
        self.temp_clicked = []
        self.revealed = []
        self.scores = [0, 0]

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
        
        await self.view.update_msg(embed=self.view.return_embed(), file=self.view.flood.return_image())

class FloodView(discord.ui.View):

    def __init__(self, user1, emojis):
        super().__init__(timeout=60)
        self.players = [user1]
        self.emojis = emojis
        self.turn = 0
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
                self.clear_items()
                winner = self.players[i]
                embed = discord.Embed(title=f"{winner.name} WON!")
                image_url = "attachment://flood.png"
                embed.set_image(url=image_url) # image file needs to be sent with the message separately
                await self.update_msg(embed=embed, file=self.flood.return_image())
                return True
        return False

    def return_embed(self):
        """Return the requiered embed"""
        percentages = self.flood.get_percentages()

        current_turn = f"{self.players[self.turn].mention}'s turn'"
        percentages = f"{self.emojis['top_left']}{self.players[0].mention}: {round(percentages[0])}%\n{self.emojis['bottom_right']}{self.players[1].mention}: {round(percentages[1])}%"
        embed = discord.Embed(title=f"{self.players[0].name} v/s {self.players[1].name}", 
                              description=f"{current_turn}\n\n{percentages}")
        image_url = "attachment://flood.png"
        embed.set_image(url=image_url) # image file needs to be sent with the message separately

        return embed

    @discord.ui.button(label='Accept the challenge!', style=discord.ButtonStyle.green)
    async def start(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()

        if interaction.user!= self.players[0]:
            self.players.append(interaction.user)
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

