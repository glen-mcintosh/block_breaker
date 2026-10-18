from ppadb.client import Client
import torch
from block_lib import model, get_board, get_shapes, get_single_shape, print_board, print_shape, print_shapes_inline

from calc import find_solution

def main():

    adb = Client(host="127.0.0.1", port=5037)
    devices = adb.devices()

    if len(devices) == 0:
        print("No devices")

    device = devices[0]
    image = device.screencap()

    with open("screen.png", "wb") as f:
        f.write(image)

    board = get_board(image)

    print("Current Grid State:")
    print_board(board)

    model.load_state_dict(torch.load("shape_classifier.pth"))
    model.eval()

    print("Current shapes to play:")
    pic_left, pic_center, pic_right = get_shapes(image)

    shape_left = get_single_shape(pic_left, model)
    
    shape_center = get_single_shape(pic_center, model)
    shape_right = get_single_shape(pic_right, model)
    
    
    print_shapes_inline(shape_left, shape_center, shape_right)
    
    success, placements, final_board = find_solution(board, shape_left, shape_center, shape_right)
    # print(board)
    
    print(success)
    print(placements)
    print(final_board)    

if __name__ == "__main__":
    main()
