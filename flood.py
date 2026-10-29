from PIL import Image, ImageDraw
from io import BytesIO
from discord import File
import random

class Flood():

    def __init__(self, players: list):
        # Constants
        self.BOX_SIZE = 10  # Size of each box in pixels
        self.GRID_SIZE = 32 # Number of boxes in each row and column
        self.IMAGE_SIZE = self.BOX_SIZE * self.GRID_SIZE  # Size of the image
        # Define the colors
        self.colors = [
            (255, 0, 0),   # Red
            (0, 255, 0),   # Green
            (0, 0, 255),   # Blue
            (255, 255, 0), # Yellow
            (255, 0, 255)  # Magenta
        ]

        self.box_colors = []
        self.players = {}
        self.gen_image()
        end = self.GRID_SIZE - 1
        home_squares = {
            2: [(0, 0), (end, end)],
            3: [(0, 0), (0, end), (end, end)],
            4: [(0, 0), (0, end), (end, 0), (end, end)],
        }.get(len(players))
        if home_squares is None:
            raise ValueError("Flood supports two to four players.")

        used_colors = set()
        for player, home in zip(players, home_squares):
            row, column = home
            color = self.box_colors[row][column]
            if color in used_colors:
                color = random.choice([candidate for candidate in self.colors if candidate not in used_colors])
                self.box_colors[row][column] = color
            used_colors.add(color)
            self.players[player.id] = {"color": color, "total_pixels": 1, "home_square": home}
        self.update_image()

    def gen_image(self):
        self.box_colors = []
        # Create a new image with the desired size
        self.image = Image.new('RGB', (self.IMAGE_SIZE, self.IMAGE_SIZE))
        #random.seed(69)

        # Draw the grid of boxes on the image
        for i in range(self.GRID_SIZE):
            temp_ll = []
            for j in range(self.GRID_SIZE):
                box_color = random.choice(self.colors)
                temp_ll.append(box_color)

            self.box_colors.append(temp_ll)
        #self.draw_borders(border_boxes)
        #self.image.show()

    def update_image(self):
        self.image = Image.new('RGB', (self.IMAGE_SIZE, self.IMAGE_SIZE))
        draw = ImageDraw.Draw(self.image)

        for player in self.players.values():
            row, column = player["home_square"]
            color = self.box_colors[row][column]
            region = self.flood_fill(row, column, color)
            player["color"] = color
            player["total_pixels"] = len(region)

        for row in range(self.GRID_SIZE):
            for column in range(self.GRID_SIZE):
                left = column * self.BOX_SIZE
                top = row * self.BOX_SIZE
                right = left + self.BOX_SIZE - 1
                bottom = top + self.BOX_SIZE - 1
                draw.rectangle(
                    (left, top, right, bottom),
                    fill=self.box_colors[row][column],
                    outline=(34, 38, 52),
                )


    def return_image(self):
        with BytesIO() as output:
            self.image.save(output, format='PNG')
            output.seek(0)
            return File(output, filename='flood.png')

    def check_four_sides(self, x, y):
        colors = self.box_colors
        original_color = colors[x][y]
        edges = []

        j = 0
        for i in [(0, -1), (1, 0), (0, 1), (-1, 0)]:
            dx, dy = i
            if dx+x < 0 or dy+y < 0:
                edges.append(j)
                j+=1
                continue
            try:
                color = colors[x+dx][y+dy]
            except:
                edges.append(j)
            try:
                if color != original_color:
                    edges.append(j)
            except:
                pass
            j+=1
        return edges

    def flood_fill(self, start_row, start_column, target_color):
        """Return a four-direction connected region in row-column coordinates."""
        grid = self.box_colors
        rows = len(grid)
        cols = len(grid[0])

        visited = [[False for _ in range(cols)] for _ in range(rows)]
        region = []

        if start_row < 0 or start_row >= rows or start_column < 0 or start_column >= cols:
            return region
        if grid[start_row][start_column] != target_color:
            return region

        stack = [(start_row, start_column)]
        visited[start_row][start_column] = True

        while stack:
            row, column = stack.pop()
            region.append((row, column))
            for row_delta, column_delta in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                next_row = row + row_delta
                next_column = column + column_delta
                if 0 <= next_row < rows and 0 <= next_column < cols and not visited[next_row][next_column]:
                    if grid[next_row][next_column] == target_color:
                        visited[next_row][next_column] = True
                        stack.append((next_row, next_column))

        return region

    def replace_pixels(self, user_id, color_to_put):
        """Replace pixels of a player"""
        player = self.players[user_id]
        row, column = player['home_square']
        color = self.box_colors[row][column]
        region = self.flood_fill(row, column, color)
        for square_row, square_column in region:
            self.box_colors[square_row][square_column] = color_to_put
        self.update_image()

    def territory_gain(self, user_id, color_to_put):
        """Estimate how many cells a color would add to this player's region."""
        player = self.players[user_id]
        row, column = player["home_square"]
        original_grid = [line[:] for line in self.box_colors]
        old_size = player["total_pixels"]
        current_color = self.box_colors[row][column]
        owned = self.flood_fill(row, column, current_color)
        try:
            for square_row, square_column in owned:
                self.box_colors[square_row][square_column] = color_to_put
            new_size = len(self.flood_fill(row, column, color_to_put))
        finally:
            self.box_colors = original_grid
        return new_size - old_size

    def return_probable_buttons(self, user_id=None):
        """
        Returns the color of buttons which a user can have.
        It will **not** include, the color of the original pixels of the user,
        and **not** the color of the pixels of the opponent.
        """
        player_colors = {i['color'] for i in self.players.values()}
        choices = [color for color in self.colors if color not in player_colors]
        if user_id is None:
            return choices
        growth = {color: self.territory_gain(user_id, color) for color in choices}
        return sorted(choices, key=lambda color: growth[color], reverse=True)

    def get_percentages(self):
        """Return percentages"""
        percentages = []
        for i in self.players.keys():
            pixels = self.players[i]['total_pixels']
            perc = (pixels*100)/(self.GRID_SIZE**2)
            percentages.append(perc)

        return percentages


