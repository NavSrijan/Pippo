
def flood_fill(self, start_x, start_y, target_color):
    # Dimensions of the grid
    grid = self.box_colors

    rows = len(grid)
    cols = len(grid[0])

    # Create a matrix to track visited positions
    visited = [[False for _ in range(cols)] for _ in range(rows)]

    # Helper function for recursive flood fill
    def fill(x, y):
        # Check if the current position is within bounds and has the target color
        if x < 0 or x >= cols or y < 0 or y >= rows or visited[y][x] or grid[y][x] != target_color:
            return

        # Mark the position as visited
        visited[y][x] = True

        # Recursively fill adjacent positions
        fill(x - 1, y)  # Left
        fill(x + 1, y)  # Right
        fill(x, y - 1)  # Up
        fill(x, y + 1)  # Down

    # Perform flood fill from the starting position
    fill(start_x, start_y)

    # Collect the adjacent positions of the same color
    adjacent_squares = []
    for y in range(rows):
        for x in range(cols):
            if visited[y][x]:
                adjacent_squares.append((x, y))

    return adjacent_squares
