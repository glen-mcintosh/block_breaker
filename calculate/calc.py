"""Original experiments from calculate/calc.ipynb, in their original cell order.

Run from calculate.
Execution preserves the original capture, plotting, and file-writing behavior.
"""

def main():
    # Former notebook cell 1
    import numpy as np

    GRID_COLS = 8  # Adjust as needed

    test_grid = np.array([
        [1, 0, 1, 0, 0, 1, 0, 1],
        [1, 1, 1, 0, 0, 0, 0, 0],
        [1, 1, 1, 0, 1, 0, 1, 1],
        [0, 1, 0, 1, 0, 1, 0, 1],
        [1, 1, 0, 1, 1, 1, 1, 0],
        [1, 1, 1, 0, 1, 0, 0, 1],
        [1, 0, 1, 0, 1, 0, 0, 0],
        [1, 1, 0, 0, 0, 1, 0, 1]
    ], dtype=int)
    
    # test_grid = np.array([
    #     [0, 0, 0, 0, 0, 0, 0, 0],
    #     [0, 0, 0, 0, 0, 0, 0, 0],
    #     [0, 0, 0, 0, 0, 0, 0, 0],
    #     [0, 0, 0, 0, 0, 0, 0, 0],
    #     [0, 0, 0, 0, 0, 0, 0, 0],
    #     [0, 0, 0, 0, 0, 0, 0, 0],
    #     [0, 0, 0, 0, 0, 0, 0, 0],
    #     [0, 0, 0, 0, 0, 0, 0, 0]
    # ], dtype=int)

    shape1 = {"shape": np.array([[1, 1, 1], [1, 1, 1]])}

    shape2 = {"shape": np.array([[0, 1, 1], [1, 1, 0]])}

    shape3 = {"shape": np.array([[1, 0], [1, 1]])}



    print(test_grid)
    print('\n')  
    print(shape1["shape"])
    print('\n')
    print(shape2["shape"])
    print('\n')
    print(shape3["shape"])
    print('\n')



    # Former notebook cell 2
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

    # Helper function to place a shape on the board
    def place_shape(board, shape, row, col):
        h, w = shape.shape
        for i in range(h):
            for j in range(w):
                if shape[i, j] == 1:
                    board[row + i, col + j] = 1

    # Helper function to remove a shape from the board
    def remove_shape(board, shape, row, col):
        h, w = shape.shape
        for i in range(h):
            for j in range(w):
                if shape[i, j] == 1:
                    board[row + i, col + j] = 0

    # Backtracking solver
    def solve(board, shapes, shape_index, placements):
        if shape_index == len(shapes):
            return True, placements  # All shapes placed successfully
    
        shape = shapes[shape_index]["shape"]
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

    # Main function to find a solution
    def find_solution(board, shapes):
        # Create a copy of the board to avoid modifying the original
        board_copy = board.copy()
        shapes_list = shapes
        success, placements = solve(board_copy, shapes_list, 0, [])
    
        if success:
            print("Solution found:")
            for shape_idx, row, col in placements:
                print(f"Shape {shape_idx + 1} placed at (row: {row}, col: {col})")
            print("Final board state:")
            print(board_copy)
        else:
            print("No solution exists")
    
        return success, placements, board_copy

    # Run the solver
    success, placements, final_board = find_solution(test_grid, [shape1, shape2, shape3])


if __name__ == "__main__":
    main()
