"""Original experiments from shape_mapping/shape_mapping.ipynb, in their original cell order.

Run from shape_mapping.
Execution preserves the original capture, plotting, and file-writing behavior.
"""

def main():
    # Former notebook cell 1



    # Former notebook cell 2
    ang_2_left_down = {"shape": {(1, 1), (0, 1)}}
    ang_2_left_up = {"shape": {(0, 1), (1, 1)}}
    ang_2_right_down = {"shape": {(1, 1), (1, 0)}}
    ang_2_right_up = {"shape": {(1, 0), (1, 1)}}
    ang_3_left_down = {"shape": {(1, 1, 1), (0, 0, 1), (0, 0, 1)}}
    ang_3_left_up = {"shape": {(0, 0, 1), (0, 0, 1), (1, 1, 1)}}
    ang_3_right_down = {"shape": {(1, 1, 1), (1, 0, 0), (1, 0, 0)}}
    ang_3_right_up = {"shape": {(1, 0, 0), (1, 0, 0), (1, 1, 1)}}
    l_1 = {"shape": {(1, 0), (1, 0), (1, 1)}}
    l_2 = {"shape": {(0, 1), (0, 1), (1, 1)}}
    l_3 = {"shape": {(1, 1), (1, 0), (1, 0)}}
    l_4 = {"shape": {(1, 1), (0, 1), (0, 1)}}
    line_2_h = {"shape": {(1, 1)}}
    line_2_v = {"shape": {(1), (1)}}
    line_3_h = {"shape": {(1, 1, 1)}}
    line_3_v = {"shape": {(1), (1), (1)}}
    line_4_h = {"shape": {(1, 1, 1, 1)}}
    line_4_v = {"shape": {(1), (1), (1), (1)}}
    line_5_h = {"shape": {(1, 1, 1, 1, 1)}}
    line_5_v = {"shape": {(1), (1), (1), (1), (1)}}
    l_inv_1 = {"shape": {(1, 1, 1), (1, 0, 0)}}
    l_inv_2 = {"shape": {(1, 1, 1), (0, 0, 1)}}
    l_inv_3 = {"shape": {(1, 0, 0), (1, 1, 1)}}
    l_inv_4 = {"shape": {(0, 0, 1), (1, 1, 1)}}
    rec_3x2_h = {"shape": {(1, 1, 1), (1, 1, 1)}}
    rec_3x2_v = {"shape": {(1, 1), (1, 1), (1, 1)}}
    sla_left_2 = {"shape": {(1, 0), (0, 1)}}
    sla_left_3 = {"shape": {(1, 0, 0), (0, 1, 0), (0, 0, 1)}}
    sla_right_2 = {"shape": {(0, 1), (1, 0)}}
    sla_right_3 = {"shape": {(0, 0, 1), (0, 1, 0), (1, 0, 0)}}
    square_2 = {"shape": {(1, 1), (1, 1)}}
    square_3 = {"shape": {(1, 1, 1), (1, 1, 1), (1, 1, 1)}}
    t_down = {"shape": {(1, 1, 1), (0, 1, 0)}}
    t_left = {"shape": {(0, 1), (1, 1), (0, 1)}}
    t_right = {"shape": {(1, 0), (1, 1), (1, 0)}}
    t_up = {"shape": {(0, 1, 0), (1, 1, 1)}}
    zig_1 = {"shape": {(0, 1), (1, 1), (1, 0)}}
    zig_2 = {"shape": {(1, 0), (1, 1), (0, 1)}}
    zig_3 = {"shape": {(0, 1, 1), (1, 1, 0)}}
    zig_4= {"shape": {(1, 1, 0), (0, 1, 1)}}
    zz_single = {"shape": {(1)}}


    shape_classes = [
        ang_2_left_down, 
        ang_2_left_up, 
        ang_2_right_down, 
        ang_2_right_up, 
        ang_3_left_down, 
        ang_3_left_up, 
        ang_3_right_down, 
        ang_3_right_up, 
        l_1, 
        l_2, 
        l_3, 
        l_4, 
        l_inv_1, 
        l_inv_2, 
        l_inv_3, 
        l_inv_4, 
        line_2_h, 
        line_2_v, 
        line_3_h, 
        line_3_v, 
        line_4_h, 
        line_4_v, 
        line_5_h, 
        line_5_v, 
        rec_3x2_h, 
        rec_3x2_v, 
        sla_left_2, 
        sla_left_3, 
        sla_right_2, 
        sla_right_3, 
        square_2, 
        square_3, 
        t_down, 
        t_left, 
        t_right, 
        t_up, 
        zig_1, 
        zig_2, 
        zig_3, 
        zig_4, 
        zz_single
    ]


    # Former notebook cell 3
    def print_shape(shape_dict):
        if not isinstance(shape_dict, dict):
            raise TypeError(f"Expected a dictionary but got {type(shape_dict)}: {shape_dict}")

        shape_set = shape_dict["shape"]

        # Convert set to list and sort for ordered display
        shape_list = sorted(shape_set)

        # Print shape grid
        for row in shape_list:
            print(" ".join(str(cell) for cell in row))

    # Example Shape Dictionary
    zig_4 = {"shape": {(1, 1), (0, 1)}}  

    # Ensure `shape_left` is a dictionary, not a string
    shape_left = zig_4  # Should reference the dictionary, NOT "zig_4"

    # Print Debugging Info
    print(f"DEBUG: shape_left = {l_inv_3}")
    print_shape(l_inv_3)





    # Former notebook cell 4
    # ang_2_left_down = {"shape": {(1, 1), (0, 1)}}
    # ang_2_left_up = {"shape": {(0, 1), (1, 1)}}
    # ang_2_right_down = {"shape": {(1, 1), (1, 0)}}
    # ang_2_right_up = {"shape": {(1, 0), (1, 1)}}
    # ang_3_left_down = {"shape": {(1, 1, 1), (0, 0, 1), (0, 0, 1)}}
    # ang_3_left_up = {"shape": {(0, 0, 1), (0, 0, 1), (1, 1, 1)}}
    # ang_3_right_down = {"shape": {(1, 1, 1), (1, 0, 0), (1, 0, 0)}}
    # ang_3_right_up = {"shape": {(1, 0, 0), (1, 0, 0), (1, 1, 1)}}
    # l_1 = {"shape": {(1, 0), (1, 0), (1, 1)}}
    # l_2 = {"shape": {(0, 1), (0, 1), (1, 1)}}
    # l_3 = {"shape": {(1, 1), (1, 0), (1, 0)}}
    # l_4 = {"shape": {(1, 1), (0, 1), (0, 1)}}
    # line_2_h = {"shape": {(1, 1)}}
    # line_2_v = {"shape": {(1), (1)}}
    # line_3_h = {"shape": {(1, 1, 1)}}
    # line_3_v = {"shape": {(1), (1), (1)}}
    # line_4_h = {"shape": {(1, 1, 1, 1)}}
    # line_4_v = {"shape": {(1), (1), (1), (1)}}
    # line_5_h = {"shape": {(1, 1, 1, 1, 1)}}
    # line_5_v = {"shape": {(1), (1), (1), (1), (1)}}
    # l_inv_1 = {"shape": {(1, 1, 1), (1, 0, 0)}}
    # l_inv_2 = {"shape": {(1, 1, 1), (0, 0, 1)}}
    # l_inv_3 = {"shape": {(1, 0, 0), (1, 1, 1)}}
    # l_inv_4 = {"shape": {(0, 0, 1), (1, 1, 1)}}
    # rec_3x2_h = {"shape": {(1, 1, 1), (1, 1, 1)}}
    # rec_3x2_v = {"shape": {(1, 1), (1, 1), (1, 1)}}
    # sla_left_2 = {"shape": {(1, 0), (0, 1)}}
    # sla_left_3 = {"shape": {(1, 0, 0), (0, 1, 0), (0, 0, 1)}}
    # sla_right_2 = {"shape": {(0, 1), (1, 0)}}
    # sla_right_3 = {"shape": {(0, 0, 1), (0, 1, 0), (1, 0, 0)}}
    # square_2 = {"shape": {(1, 1), (1, 1)}}
    # square_3 = {"shape": {(1, 1, 1), (1, 1, 1), (1, 1, 1)}}
    # t_down = {"shape": {(1, 1, 1), (0, 1, 0)}}
    # t_left = {"shape": {(0, 1), (1, 1), (0, 1)}}
    # t_right = {"shape": {(1, 0), (1, 1), (1, 0)}}
    # t_up = {"shape": {(0, 1, 0), (1, 1, 1)}}
    # zig_1 = {"shape": {(0, 1), (1, 1), (1, 0)}}
    # zig_2 = {"shape": {(1, 0), (1, 1), (0, 1)}}
    # zig_3 = {"shape": {(0, 1, 1), (1, 1, 0)}}
    # zig_4= {"shape": {(1, 1, 0), (0, 1, 1)}}
    # zz_single = {"shape": {(1)}}


if __name__ == "__main__":
    main()
