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
        #adj = self.flood_fill(0, 0, (255, 0, 0))
        #self.update_image(adj)
        x = self.GRID_SIZE-1
        if len(players)==2:
            home_squares = [[0, 0], [x, x]]
        elif len(players)==3:
            home_squares = [[0, 0], [x, 0], [x, x]]
        elif len(players)==4:
            home_squares = [[0, 0], [x, 0], [0, x], [x, x]]
        for i, j in enumerate(players):
            x = home_squares[i][0]
            y = home_squares[i][1]
            self.players[j.id] = {"color": self.box_colors[x][y], "total_pixels": 1, "home_square": home_squares[i]}

    def gen_image(self):
        # Create a new image with the desired size
        self.image = Image.new('RGB', (self.IMAGE_SIZE, self.IMAGE_SIZE))
        #random.seed(69)

        # Draw the grid of boxes on the image
        for i in range(self.GRID_SIZE):
            temp_ll = []
            for j in range(self.GRID_SIZE):
                box_color = random.choice(self.colors)
                temp_ll.append(box_color)
                for x in range(i * self.BOX_SIZE, (i + 1) * self.BOX_SIZE):
                    for y in range(j * self.BOX_SIZE, (j + 1) * self.BOX_SIZE):
                        #for k in self.get_coords((x, y)):
                        self.image.putpixel((x,y), box_color)

            self.box_colors.append(temp_ll)
        #self.draw_borders(border_boxes)
        #self.image.show()

    def update_image(self):
        try:
            # Create a new image with the desired size
            self.image = Image.new('RGB', (self.IMAGE_SIZE, self.IMAGE_SIZE))
            adj1 = self.flood_fill(0,0, self.box_colors[0][0])
            xxx = self.GRID_SIZE-1
            adj2 = self.flood_fill(xxx,xxx, self.box_colors[xxx][xxx])

            ids = []
            for i in self.players.keys():
                ids.append(i)

            self.players[ids[0]]["color"] = self.box_colors[0][0] 
            self.players[ids[0]]["total_pixels"] = len(adj1)

            self.players[ids[1]]["color"] = self.box_colors[xxx][xxx] 
            self.players[ids[1]]["total_pixels"] = len(adj2)

            # Draw the grid of boxes on the image
            for i in range(self.GRID_SIZE):
                for j in range(self.GRID_SIZE):
                    diffx1 = 0
                    diffy1 = 0
                    diffx2 = 0
                    diffy2 = 0
                    diff = 2
                    box_color = self.box_colors[i][j]
                    if (i,j) in adj1 or (i,j) in adj2:
                        edges = self.check_four_sides(i, j)
                        if len(edges) != 0:
                            if 0 in edges:
                                diffy2 = -diff
                            if 1 in edges:
                                diffx1 = diff
                            if 2 in edges:
                                diffx2 = diff
                            if 3 in edges:
                                diffy1 = -diff

                    for x in range((i * self.BOX_SIZE)-diffy1, ((i + 1) * self.BOX_SIZE)-diffx1):
                        for y in range((j * self.BOX_SIZE)-diffy2, ((j + 1) * self.BOX_SIZE)-diffx2):
                            self.image.putpixel((x, y), box_color)

        except Exception as e:
            print(e)


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

    def flood_fill(self, start_x, start_y, target_color):
        # Dimensions of the grid
        grid = self.box_colors
        rows = len(grid)
        cols = len(grid[0])

        visited = [[False for _ in range(cols)] for _ in range(rows)]
        adjacent_squares = []

        if start_y < 0 or start_y >= rows or start_x < 0 or start_x >= cols:
            return adjacent_squares
        if grid[start_y][start_x] != target_color:
            return adjacent_squares

        stack = [(start_x, start_y)]
        visited[start_y][start_x] = True

        while stack:
            cx, cy = stack.pop()
            adjacent_squares.append((cy, cx))
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < cols and 0 <= ny < rows and not visited[ny][nx]:
                    if grid[ny][nx] == target_color:
                        visited[ny][nx] = True
                        stack.append((nx, ny))

        return adjacent_squares

    def replace_pixels(self, user_id, color_to_put):
        """Replace pixels of a player"""
        player = self.players[user_id]
        x = player['home_square'][0]
        y = player['home_square'][1]

        color = self.box_colors[x][y]
        adj = self.flood_fill(x, y, color)
        for square in adj:
            self.box_colors[square[0]][square[1]] = color_to_put
        self.update_image()

    def return_probable_buttons(self):
        """
        Returns the color of buttons which a user can have.
        It will **not** include, the color of the original pixels of the user,
        and **not** the color of the pixels of the opponent.
        """
        player_colors = {i['color'] for i in self.players.values()}
        return [c for c in self.colors if c not in player_colors]

    def get_percentages(self):
        """Return percentages"""
        percentages = []
        for i in self.players.keys():
            pixels = self.players[i]['total_pixels']
            perc = (pixels*100)/(self.GRID_SIZE**2)
            percentages.append(perc)

        return percentages



