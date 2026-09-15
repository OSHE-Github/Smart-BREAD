import sys, time, array
import pygame, gif_pygame
import screenElements
import cv2

# Initialize Pygame
pygame.init()

#Screen Vars
clock = pygame.time.Clock()
fps = 60
objects = []
GUIScale = (int) (1)

#Screen Flags
BootFlag = 0
HomeFlag = 1
CamFlag = 0
ConveyorFlag = 0
FaultFlag = 0

#Conveyor Vars
Speed = 0
Direction = 0

#Window Setup
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN) #Fullscreen
pygame.display.set_caption("Bread HMI")
pygame.display.set_icon(pygame.image.load('assets/icon.png'))
bootAnim = gif_pygame.load("assets/boot_test_delete_later.gif")
width, height = pygame.display.get_surface().get_size()
bootAnimTimings = bootAnim.get_durations()
bootAnimLength = 0;
pygame.mixer.pre_init(44100, -16, 1, 1024)
pygame.init()

#Calculate boot animation total length.
for i in bootAnimTimings:
    bootAnimLength = bootAnimLength + i

#Button Scale & Placement Grid Vars
ButtonXScale = (int) ((width/8)*GUIScale)
ButtonYScale = (int) ((height/10)*GUIScale)
ButtonFontSize = (int) (ButtonYScale*0.4)

GridCellWidth = width/6
GridCellHeight = height/6

#Colors
BG_COLOR = (30, 30, 40)
WHITE = (255, 255, 255)
BLACK = (0,0,0)
RED = (255,0,0)
NORMAL_COLOR = (50, 150, 250)
HOVER_COLOR = (30, 100, 200)
PRESS_COLOR = (0, 50, 75)

#Camera setup
cam = cv2.VideoCapture(0)
if not cam.isOpened():
    print("Error: Webcam could not be opened.")
    sys.exit()

cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

if cam.isOpened():
    # Read one dummy frame to prime the matrix buffer completely
    success, _ = cam.read()
    print(f"Camera verified. OS Backend connected to index {0}. Working: {success}")
else:
    print("fuck")

#Make button
font = pygame.font.SysFont('Arial', ButtonFontSize)

#Make text
font = pygame.font.SysFont('Arial', 30)
text = font.render("Oooo, a button!", True, WHITE)

#End of init, start rendering
initTime = time.perf_counter()

def BootScreen(): #Screen elements for boot animation (As well as nessecary CAN checks
    print("hi")

def HomeScreen(): #Screen for elements of the home screen
    screen.fill(BG_COLOR)
    screen.blit(text, ((int) ((width/8)*GUIScale), (int) ((height/10)*GUIScale)-40))
    cameraButton = screenElements.Button("Camera", (int) (0 + ButtonXScale), (int) (height - ButtonYScale - ButtonYScale/3), ButtonXScale, ButtonYScale, ButtonFontSize, WHITE, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR)
    cameraButton.draw(screen)
    
    for event in pygame.event.get(): #Handle events relating to the home screen, and only the home screen
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
            
        if cameraButton.handle_event(event, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR):
            global CamFlag
            CamFlag = 1

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()

    #Update frame buffer
    pygame.display.update()
    clock.tick(fps)
    
def CamScreen(): #Screen for elements of the camera view screen
    screen.fill(BG_COLOR)
    global cam

    #Read and convert camera feed
    ret, frame = cam.read()
    if ret and frame is not None:
        image = cv2topygame(frame)

    #Display camera feed and other onscreen elements
    screen.blit(image, (((width-image.width)/2), ((height-image.height)/2)))
    cameraButton = screenElements.Button("Home", (int) (width - ButtonXScale - ButtonXScale), (int) (height - ButtonYScale - ButtonYScale/3), ButtonXScale, ButtonYScale, ButtonFontSize, WHITE, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR)
    cameraButton.draw(screen)

    #Handle events relating to the home screen, and only the home screen
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if cameraButton.handle_event(event, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR):
            global CamFlag
            CamFlag = 0

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()

    #Update frame buffer
    pygame.display.update()
    clock.tick(fps)

def ConveyorScreen(): #Screen for elements of the conveyor control screen
    print("hi")

    for event in pygame.event.get(): #Handle events relating to the home screen, and only the home screen
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()

    #Update frame buffer
    pygame.display.update()
    clock.tick(fps)

def FaultScreen(): #Screen for elements of the fault screen
    screen.fill(RED)
    font = pygame.font.SysFont('Arial', 60)
    text = font.render("A FAULT HAS OCCURED", True, WHITE)
    screen.blit(text, ((int) (((width-text.width)/2)), (int) (((height-text.height)/2) - text.height/2)))
    text = font.render("PLEASE DIAGNOSE AND RESTART", True, WHITE)
    screen.blit(text, ((int) (((width-text.width)/2)), (int) (((height-text.height)/2) + text.height/2)))
    
    evil_noise()  #Play 440Hz for 1500ms
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
            
    #Update frame buffer        
    pygame.display.update()
    clock.tick(fps)
    
def evil_noise():
    sample_rate = 44100
    period = int(sample_rate / 440)

    #Build one full wavelength cycle (half high amplitude, half low)
    amplitude = 2**15 - 1  # Max for 16-bit signed int
    samples = array.array("h", [0] * period)
    for i in range(period):
        samples[i] = amplitude if i < period / 2 else -amplitude

    #Turn the cycle into a Sound object
    sound = pygame.mixer.Sound(buffer=samples)
    sound.set_volume(0.125)

    #Loop the short buffer sound to fill the requested duration
    sound.play(loops=-1)
    pygame.delay(1000)
    sound.stop()

def cv2topygame(opencv_image):
    # Ensure a valid matrix array exists before running transformations
    if opencv_image is None or not hasattr(opencv_image, 'shape') or opencv_image.size == 0:
        return None

    try:
        # 1. Convert native BGR color matrix to RGB
        rgb_image = cv2.cvtColor(opencv_image, cv2.COLOR_BGR2RGB)

        # 2. Swap axis 0 and 1 because OpenCV maps (Height, Width) and Pygame expects (Width, Height)
        pygame_image = rgb_image.swapaxes(0, 1)

        # 3. Create surface direct from memory buffer
        return pygame.surfarray.make_surface(pygame_image)
    except Exception as e:
        print(f"Error converting frame: {e}")
        return None

#Main Game Loop
while True:
    while(BootFlag): #Render boot animation
        screen.fill(BLACK)
        bootAnim.render(screen, ((int) ((width-bootAnim.width)/2), (int) ((height-bootAnim.height)/2)))
        currentTime = time.perf_counter()
    
        #Check if boot animation has finished running
        if(currentTime - initTime > bootAnimLength):
            BootFlag = 0
            
        #Update frame buffer        
        pygame.display.update()
        clock.tick(fps)
        
    #First and foremost check if there is a fault flag raised, and intentionally catch the entire program if there is.
    while(FaultFlag):
        FaultScreen()
    
    #Camera screen rendering
    if(CamFlag):
        CamScreen()
        continue
        
    if(ConveyorFlag):
        ConveyorScreen()
        continue

    #Home screen rendering
    if(HomeFlag):
        HomeScreen()
        continue
