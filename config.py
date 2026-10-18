import numpy as np


cell_points = [
    (142, 665),  # (Row 1, Col 1)
    (213, 629),  # (Row 1, Col 2)
    (351, 629),  # (Row 1, Col 3)
    (471, 629),  # (Row 1, Col 4)
    (586, 629),  # (Row 1, Col 5)
    (706, 629),  # (Row 1, Col 6)
    (831, 634),  # (Row 1, Col 7)
    (937, 634),  # (Row 1, Col 8)

    (133, 763),  # (Row 2, Col 1)
    (235, 763),  # (Row 2, Col 2)
    (337, 763),  # (Row 2, Col 3)
    (484, 763),  # (Row 2, Col 4)
    (604, 763),  # (Row 2, Col 5)
    (724, 763),  # (Row 2, Col 6)
    (831, 763),  # (Row 2, Col 7)
    (960, 771),  # (Row 2, Col 8)

    (124, 882),  # (Row 3, Col 1)
    (257, 887),  # (Row 3, Col 2)
    (360, 869),  # (Row 3, Col 3)
    (475, 882),  # (Row 3, Col 4)
    (604, 887),  # (Row 3, Col 5)
    (715, 887),  # (Row 3, Col 6)
    (835, 882),  # (Row 3, Col 7)
    (960, 882),  # (Row 3, Col 8)

    (137, 998),  # (Row 4, Col 1)
    (244, 1007), # (Row 4, Col 2)
    (377, 1007), # (Row 4, Col 3)
    (480, 993),  # (Row 4, Col 4)
    (586, 993),  # (Row 4, Col 5)
    (706, 998),  # (Row 4, Col 6)
    (840, 998),  # (Row 4, Col 7)
    (960, 998),  # (Row 4, Col 8)

    (142, 1109), # (Row 5, Col 1)
    (235, 1109), # (Row 5, Col 2)
    (337, 1109), # (Row 5, Col 3)
    (466, 1109), # (Row 5, Col 4)
    (582, 1109), # (Row 5, Col 5)
    (706, 1113), # (Row 5, Col 6)
    (822, 1113), # (Row 5, Col 7)
    (951, 1113), # (Row 5, Col 8)

    (124, 1237), # (Row 6, Col 1)
    (248, 1237), # (Row 6, Col 2)
    (337, 1237), # (Row 6, Col 3)
    (457, 1237), # (Row 6, Col 4)
    (600, 1237), # (Row 6, Col 5)
    (720, 1237), # (Row 6, Col 6)
    (831, 1237), # (Row 6, Col 7)
    (977, 1233), # (Row 6, Col 8)

    (111, 1348), # (Row 7, Col 1)
    (257, 1353), # (Row 7, Col 2)
    (373, 1353), # (Row 7, Col 3)
    (471, 1353), # (Row 7, Col 4)
    (604, 1353), # (Row 7, Col 5)
    (720, 1353), # (Row 7, Col 6)
    (840, 1353), # (Row 7, Col 7)
    (955, 1353), # (Row 7, Col 8)

    (133, 1486), # (Row 8, Col 1)
    (231, 1481), # (Row 8, Col 2)
    (337, 1481), # (Row 8, Col 3)
    (466, 1477), # (Row 8, Col 4)
    (577, 1477), # (Row 8, Col 5)
    (728, 1468), # (Row 8, Col 6)
    (835, 1463), # (Row 8, Col 7)
    (964, 1468)  # (Row 8, Col 8)
]



shape_classes = {
    "ang_2_left_down": {"shape": np.array([[1, 1], [0, 1]])},
    "ang_2_left_up": {"shape": np.array([[0, 1], [1, 1]])},
    "ang_2_right_down": {"shape": np.array([[1, 1], [1, 0]])},
    "ang_2_right_up": {"shape": np.array([[1, 0], [1, 1]])},
    "ang_3_left_down": {"shape": np.array([[1, 1, 1], [0, 0, 1], [0, 0, 1]])},
    "ang_3_left_up": {"shape": np.array([[0, 0, 1], [0, 0, 1], [1, 1, 1]])},
    "ang_3_right_down": {"shape": np.array([[1, 1, 1], [1, 0, 0], [1, 0, 0]])},
    "ang_3_right_up": {"shape": np.array([[1, 0, 0], [1, 0, 0], [1, 1, 1]])},
    "l_1": {"shape": np.array([[1, 0], [1, 0], [1, 1]])},
    "l_2": {"shape": np.array([[0, 1], [0, 1], [1, 1]])},
    "l_3": {"shape": np.array([[1, 1], [1, 0], [1, 0]])},
    "l_4": {"shape": np.array([[1, 1], [0, 1], [0, 1]])},
    "line_2_h": {"shape": np.array([[1, 1]])},
    "line_2_v": {"shape": np.array([[1], [1]])},
    "line_3_h": {"shape": np.array([[1, 1, 1]])},
    "line_3_v": {"shape": np.array([[1], [1], [1]])},
    "line_4_h": {"shape": np.array([[1, 1, 1, 1]])},
    "line_4_v": {"shape": np.array([[1], [1], [1], [1]])},
    "line_5_h": {"shape": np.array([[1, 1, 1, 1, 1]])},
    "line_5_v": {"shape": np.array([[1], [1], [1], [1], [1]])},
    "l_inv_1": {"shape": np.array([[1, 1, 1], [1, 0, 0]])},
    "l_inv_2": {"shape": np.array([[1, 1, 1], [0, 0, 1]])},
    "l_inv_3": {"shape": np.array([[1, 0, 0], [1, 1, 1]])},
    "l_inv_4": {"shape": np.array([[0, 0, 1], [1, 1, 1]])},
    "rec_3x2_h": {"shape": np.array([[1, 1, 1], [1, 1, 1]])},
    "rec_3x2_v": {"shape": np.array([[1, 1], [1, 1], [1, 1]])},
    "sla_left_2": {"shape": np.array([[1, 0], [0, 1]])},
    "sla_left_3": {"shape": np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]])},
    "sla_right_2": {"shape": np.array([[0, 1], [1, 0]])},
    "sla_right_3": {"shape": np.array([[0, 0, 1], [0, 1, 0], [1, 0, 0]])},
    "square_2": {"shape": np.array([[1, 1], [1, 1]])},
    "square_3": {"shape": np.array([[1, 1, 1], [1, 1, 1], [1, 1, 1]])},
    "t_down": {"shape": np.array([[1, 1, 1], [0, 1, 0]])},
    "t_left": {"shape": np.array([[0, 1], [1, 1], [0, 1]])},
    "t_right": {"shape": np.array([[1, 0], [1, 1], [1, 0]])},
    "t_up": {"shape": np.array([[0, 1, 0], [1, 1, 1]])},
    "zig_1": {"shape": np.array([[0, 1], [1, 1], [1, 0]])},
    "zig_2": {"shape": np.array([[1, 0], [1, 1], [0, 1]])},
    "zig_3": {"shape": np.array([[0, 1, 1], [1, 1, 0]])},
    "zig_4": {"shape": np.array([[1, 1, 0], [0, 1, 1]])},
    "zz_single": {"shape": np.array([[1]])}
}


class_labels = [
    "ang_2_left_down",
    "ang_2_left_up",
    "ang_2_right_down",
    "ang_2_right_up",
    "ang_3_left_down",
    "ang_3_left_up",
    "ang_3_right_down",
    "ang_3_right_up",
    "l_1",
    "l_2",
    "l_3",
    "l_4",
    "l_inv_1",
    "l_inv_2",
    "l_inv_3",
    "l_inv_4",
    "line_2_h",
    "line_2_v",
    "line_3_h",
    "line_3_v",
    "line_4_h",
    "line_4_v",
    "line_5_h",
    "line_5_v",
    "rec_3x2_h",
    "rec_3x2_v",
    "sla_left_2",
    "sla_left_3",
    "sla_right_2",
    "sla_right_3",
    "square_2",
    "square_3",
    "t_down",
    "t_left",
    "t_right",
    "t_up",
    "zig_1",
    "zig_2",
    "zig_3",
    "zig_4",
    "zz_single",
]