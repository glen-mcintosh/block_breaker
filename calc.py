from config import shape_classes



def can_place(board, shape, row, col):
    h, w = shape.shape
    # Check if shape fits within board boundaries
    if row + h > board.shape[0] or col + w > board.shape[1]:
        return False
    # Check if shape's 1s align with 0s on the board
    for i in range(h):
        for j in range(w):
            if shape[i, j] == 1 and board[row + i, col + j] == 1:
                return False
    return True

def place_shape(board, shape, row, col):
    h, w = shape.shape
    for i in range(h):
        for j in range(w):
            if shape[i, j] == 1:
                board[row + i, col + j] = 1

def remove_shape(board, shape, row, col):
    h, w = shape.shape
    for i in range(h):
        for j in range(w):
            if shape[i, j] == 1:
                board[row + i, col + j] = 0

def solve(board, shapes, shape_index, placements):
    if shape_index == len(shapes):
        return True, placements  # All shapes placed successfully
    
    shape = shapes[shape_index]  # Get the shape (string or NumPy array)
    
    # Convert string to NumPy array if necessary
    if isinstance(shape, str):
        if shape in shape_classes:
            shape = shape_classes[shape]["shape"]
        else:
            raise ValueError(f"Unknown shape name: {shape}. Ensure it exists in shape_classes.")
    elif not isinstance(shape, np.ndarray):
        raise ValueError(f"Shape must be a string name or NumPy array, got: {type(shape)}")
    
    h, w = shape.shape
    
    # Try all possible positions for the current shape
    for row in range(board.shape[0] - h + 1):
        for col in range(board.shape[1] - w + 1):
            if can_place(board, shape, row, col):
                # Place the shape
                place_shape(board, shape, row, col)
                placements.append((shape_index, row, col))
                # Recurse to place the next shape
                success, result = solve(board, shapes, shape_index + 1, placements)
                if success:
                    return True, result
                # Backtrack: remove the shape and try the next position
                remove_shape(board, shape, row, col)
                placements.pop()
    
    return False, []

def find_solution(board, shape_left, shape_center, shape_right):
    # Create a copy of the board to avoid modifying the original
    board_copy = board.copy()
    # Create a list of shapes (may be strings)
    shapes_list = [shape_left, shape_center, shape_right]
    success, placements = solve(board_copy, shapes_list, 0, [])
    
    return success, placements, board_copy