import cv2, pygame

def cv2topygame(image):
    #Check if the image is even valid before trying
    if image is None or not hasattr(image, 'shape') or image.size == 0:
        return None

    #Convert image from cv2 to pygame for display
    try:
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pygame_image = rgb_image.swapaxes(0, 1)
        return pygame.surfarray.make_surface(pygame_image)
    except Exception as e:
        print(f"Error converting frame: {e}")
        return None
