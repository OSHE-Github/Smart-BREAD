import sys, time, array
from tkinter import font
import pygame, gif_pygame
import screenElements, CAN
import cv2
import os, psutil #For memory monitoring


#Init memory monitor
memDebug = 1;
memDebugLoop = 0;
if(memDebug | memDebugLoop):
    process = psutil.Process(os.getpid())

if(memDebug):
    rss_memory = process.memory_info().rss
    print(f"Starting Memory Usage: {rss_memory / (1024**2):.2f} MB")



# Initialize Pygame
pygame.init()

#Screen Vars
clock = pygame.time.Clock()
objects = []

#Arrays of bytes
flagArr = array.array("b", [0, 1, 0, 0, 0, 1]) #Boot, Home, Cam, Conveyor, Fault, and Info Flags in array form
convArr = array.array("b", [0, 0, 0]) #Speed, Measured Speed, Direction
constArray = array.array("b", [60]) #FPS, bDiv,

#Conveyor Vars
numSorted = 0

#Window Setup
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
pygame.display.set_caption("Bread HMI")
width, height = pygame.display.get_surface().get_size()

if(memDebug):
    rss_memory = process.memory_info().rss
    print(f"Window created!  Memory Usage: {rss_memory / (1024**2):.2f} MB")

#Image asset setup
pygame.display.set_icon(pygame.image.load('assets/icon.png'))
osheLogo = pygame.image.load("assets/OSHE Logo.png").convert_alpha()
osheLogo = pygame.transform.scale(osheLogo, (osheLogo.width/10, osheLogo.height/10))
owidth = osheLogo.width; oheight = osheLogo.height

#Boot animation setup
bootAnim = gif_pygame.load("assets/boot_test_delete_later.gif")
bootAnimTimings = bootAnim.get_durations()
bootAnimLength = 0;

#Calculate boot animation total length.
for i in bootAnimTimings:
    bootAnimLength = bootAnimLength + i

if(memDebug):
    rss_memory = process.memory_info().rss
    print(f"Assets loaded! Memory Usage: {rss_memory / (1024**2):.2f} MB")

#Button Scale & Placement Grid Vars
ButtonXScale = (int) ((width/4))
ButtonYScale = (int) ((height/5))
ButtonFontSize = (int) (ButtonYScale*0.4)

bordWidth = height/50

#Colors
BG_COLOR = (245, 245, 220)
BORDER_COLOR = (98, 49, 8)
TEXT_FIELD_COLOR= (210, 180, 140)
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

if(memDebug):
    rss_memory = process.memory_info().rss
    print(f"Camera started!  Memory Usage: {rss_memory / (1024**2):.2f} MB")

#Static graphic setup
boxY = bordWidth*5; boxWidth = width/12; boxHeight = height/16;
ssBoxX = bordWidth*7; msBoxX = width/2 - width/24; osBoxX = width - bordWidth*14

#Static text setup
font = pygame.font.SysFont('Arial', (int) (ButtonFontSize/2))
setSpeedLabel = font.render("Set Speed", True, BORDER_COLOR) #Set speed label text

ssLabelX = (int) (ssBoxX + boxWidth/2 - setSpeedLabel.width/2) #Set speed label X precalc
ssLabelY = (int) (boxY - setSpeedLabel.height - setSpeedLabel.height/6) #Set speed label Y precalc

mesSpeedLabel = font.render("Measured Speed", True, BORDER_COLOR) #Measured speed label text
msLabelX = (int) (width/2 - mesSpeedLabel.width/2)
msLabelY = ssLabelY

objText = font.render("Objects Sorted", True, BORDER_COLOR) #Sorted object count label text
osLabelX = osBoxX + boxWidth/2 - objText.width/2
osLabelY = ssLabelY

#Belt Controls
leftDirButton = screenElements.Button("Left", (int) (0  + 0.125 * ButtonXScale), (int) (height - 2.25 * ButtonYScale), ButtonXScale * 0.75, (int) (ButtonYScale*0.66), ButtonFontSize, WHITE, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR)
minusSpeedButton = screenElements.Button("-", (int) (0 + 1 * ButtonXScale + 0.125 * ButtonXScale), (int) (height - 2.25 * ButtonYScale), ButtonXScale * 0.75, (int) (ButtonYScale*0.66), ButtonFontSize, WHITE, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR)
addSpeedButton = screenElements.Button("+", (int) (0 + 2 * ButtonXScale + 0.125 * ButtonXScale), (int) (height - 2.25 * ButtonYScale), ButtonXScale * 0.75, (int) (ButtonYScale*0.66), ButtonFontSize, WHITE, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR)
rightDirButton = screenElements.Button("Right", (int) (0 + 3 * ButtonXScale + 0.125 * ButtonXScale), (int) (height - 2.25* ButtonYScale), ButtonXScale * 0.75, (int) (ButtonYScale*0.66), ButtonFontSize, WHITE, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR)

if(memDebug):
    rss_memory = process.memory_info().rss
    print(f"Static elements loaded!  Memory Usage: {rss_memory / (1024**2):.2f} MB")


#Misc Setup
pygame.mixer.pre_init(44100, -16, 1, 1024)


def BootScreen(): #Screen elements for boot animation (As well as nessecary CAN checks
    global flagArr

    screen.fill(BG_COLOR)
    drawBorders()

    font = pygame.font.SysFont('Arial', 30)
    bread = font.render("Smart BREAD", True, BLACK)
    booting = font.render("Booting...", True, BLACK)
    screen.blit(bread, ((int) (((width - bread.get_width())/2)), (int) ((height/2)+osheLogo.get_height()/2)))
    screen.blit(booting, ((int) (((width - booting.get_width())/2)), (int) ((height/2)+osheLogo.get_height()+booting.get_height())))
    screen.blit(osheLogo, ((width - owidth)/2, (height - oheight)/2))

    for event in pygame.event.get(): #Handle events relating to the boot screen, and only the boot screen
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
    
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()

def HomeScreen(): #Screen for elements of the home screen
    global flagArr

    font = pygame.font.SysFont('Arial', 30)
    screen.fill(BG_COLOR)
    drawBorders()
    cameraButton = screenElements.Button("Camera", (int) (0 + ButtonXScale/3), (int) (height - ButtonYScale - ButtonYScale/3), ButtonXScale, ButtonYScale, ButtonFontSize, WHITE, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR)
    conveyorButton = screenElements.Button("Conveyor", (int) (width - ButtonXScale - ButtonXScale/3), (int) (height - ButtonYScale - ButtonYScale/3), ButtonXScale, ButtonYScale, ButtonFontSize, WHITE, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR)
    infoButton = screenElements.Button("Info", (int) (width/2 - ButtonXScale/2), (int) (height - ButtonYScale - ButtonYScale/3), ButtonXScale, ButtonYScale, ButtonFontSize, WHITE, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR)


    for event in pygame.event.get(): #Handle events relating to the home screen, and only the home screen
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()

        if cameraButton.handle_event(event, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR):
            flagArr[2] = 1

        if conveyorButton.handle_event(event, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR):
            flagArr[3] = 1

        if infoButton.handle_event(event, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR):
            flagArr[5] = 1

    cameraButton.draw(screen)
    conveyorButton.draw(screen)
    infoButton.draw(screen)

    #Update frame buffer
    pygame.display.update()
    clock.tick(constArray[0])
    
def CamScreen(): #Screen for elements of the camera view screen
    global cam
    global flagArr

    screen.fill(BG_COLOR)
    drawBorders()

    #Read and convert camera feed
    ret, frame = cam.read()
    if ret and frame is not None:
        image = cv2topygame(frame)

    #Display camera feed and other onscreen elements
    screen.blit(image, (((width-image.width)/2), ((height-image.height)/2)))
    cameraButton = screenElements.Button("Home", (int) (width - ButtonXScale - ButtonXScale/3), (int) (height - ButtonYScale - ButtonYScale/3), ButtonXScale, ButtonYScale, ButtonFontSize, WHITE, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR)

    #Handle events relating to the home screen, and only the home screen
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()

        if cameraButton.handle_event(event, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR):
            flagArr[2] = 0

    cameraButton.draw(screen)

    #Update frame buffer
    pygame.display.update()
    clock.tick(constArray[0])

def ConveyorScreen(): #Screen for elements of the conveyor control screen
    global convArr
    global numSorted

    #Draw background elements
    screen.fill(BG_COLOR)
    drawBorders()

    #Define text to display
    font = pygame.font.SysFont('Arial', (int) (ButtonFontSize/2))
    speedText = font.render(f"{convArr[0]}", True, BORDER_COLOR)
    measSpeedText = font.render(f"{convArr[1]}", True, BORDER_COLOR)
    sortedCount = font.render(f"{numSorted}", True, BORDER_COLOR)

    #Draw detail boxes onscreen
    pygame.draw.rect(screen, TEXT_FIELD_COLOR, pygame.Rect(ssBoxX, boxY, boxWidth, boxHeight), border_radius=0) #Set speed box
    pygame.draw.rect(screen, TEXT_FIELD_COLOR, pygame.Rect(msBoxX, boxY, boxWidth, boxHeight), border_radius=0) #Meas speed box
    pygame.draw.rect(screen, TEXT_FIELD_COLOR, pygame.Rect(osBoxX, boxY, boxWidth, boxHeight), border_radius=0) #Object count box

    #Draw text onscreen
    screen.blit(setSpeedLabel, (ssLabelX, ssLabelY))
    screen.blit(mesSpeedLabel, (msLabelX, msLabelY))
    screen.blit(objText, (osLabelX, osLabelY))

    #Draw changing text onscreen
    screen.blit(speedText, (ssBoxX + boxWidth/2 - speedText.width/2, boxY + speedText.height/6))
    screen.blit(measSpeedText, (msBoxX + boxWidth/2 - measSpeedText.width/2, boxY + measSpeedText.height/6))
    screen.blit(sortedCount, (osBoxX + boxWidth/2 - sortedCount.width/2, boxY + sortedCount.height/6))




    #Home button to go back to home menu
    homeButton = screenElements.Button("Home", (int) (0 + ButtonXScale/3), (int) (height - ButtonYScale - ButtonYScale/3), ButtonXScale, ButtonYScale, ButtonFontSize, WHITE, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR)



    #Event handlers for all of the buttons
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()

        if addSpeedButton.handle_event(event, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR):
            if convArr[0] < 100:
                convArr[0] = convArr[0] + 1
            else:
                convArr[0] = 100

        if minusSpeedButton.handle_event(event, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR):
            if convArr[0] > 0:
                convArr[0] = convArr[0] - 1
            else:
                convArr[0] = 0

        if leftDirButton.handle_event(event, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR):
            convArr[2] = -1

        if rightDirButton.handle_event(event, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR):
            convArr[2] = 1

        if homeButton.handle_event(event, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR):
            global ConveyorFlag
            flagArr[3] = 0

    #Draw the buttons to the screen
    leftDirButton.draw(screen)
    minusSpeedButton.draw(screen)
    addSpeedButton.draw(screen)
    rightDirButton.draw(screen)
    homeButton.draw(screen)

    #Load the OSHE logo to the bottom right of the screen
    screen.blit(osheLogo, (width - bordWidth - owidth*1.1, height - bordWidth - oheight*1.1))
    bootAnim.render(screen, ((int) ((width-bootAnim.width)/2), (int) ((height-bootAnim.height)/3)))

    #Update frame buffer
    pygame.display.update()
    clock.tick(constArray[0])

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

    if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()
            
    #Update frame buffer        
    pygame.display.update()
    clock.tick(constArray[0])

def InfoScreen():
    global flagArr

    screen.fill(BG_COLOR)
    drawBorders()

    homeButton = screenElements.Button("Home", (int) (width - ButtonXScale - ButtonXScale/3), (int) (height - ButtonYScale - ButtonYScale/3), ButtonXScale, ButtonYScale, ButtonFontSize, WHITE, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR)


    for event in pygame.event.get(): #Handle events relating to the boot screen, and only the boot screen
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
    
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()

            if homeButton.handle_event(event, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR):
                flagArr[5] = 0

    homeButton.draw(screen)

    #Update frame buffer
    pygame.display.update()
    clock.tick(constArray[0])
    
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
    #Check if the image is even valid before trying
    if opencv_image is None or not hasattr(opencv_image, 'shape') or opencv_image.size == 0:
        return None

    #Convert image from cv2 to pygame for display
    try:
        rgb_image = cv2.cvtColor(opencv_image, cv2.COLOR_BGR2RGB)
        pygame_image = rgb_image.swapaxes(0, 1)
        return pygame.surfarray.make_surface(pygame_image)
    except Exception as e:
        print(f"Error converting frame: {e}")
        return None

def drawBorders():
    pygame.draw.rect(screen, BORDER_COLOR, pygame.Rect(0, 0, width, bordWidth), border_radius=0)
    pygame.draw.rect(screen, BORDER_COLOR, pygame.Rect(0, height - bordWidth, width, bordWidth), border_radius=0)
    pygame.draw.rect(screen, BORDER_COLOR, pygame.Rect(0, 0, bordWidth, height), border_radius=0)
    pygame.draw.rect(screen, BORDER_COLOR, pygame.Rect(width - bordWidth, 0, bordWidth, height), border_radius=0)

#End of init, start rendering
initTime = time.perf_counter()

#Main Game Loop
while True:
    while(flagArr[0]): #Render boot animation
        #screen.fill(BLACK)
        #bootAnim.render(screen, ((int) ((width-bootAnim.width)/2), (int) ((height-bootAnim.height)/2)))
        BootScreen()
        currentTime = time.perf_counter()
    
        #Check if boot animation has finished running
        if(currentTime - initTime > bootAnimLength):
            flagArr[0] = 0
            
        #Update frame buffer        
        pygame.display.update()
        clock.tick(constArray[0])
        
    if(memDebugLoop):
        rss_memory = process.memory_info().rss
        print(f"Current Process Memory Usage: {rss_memory / (1024**2):.2f} MB")

    #First check if there is a fault flag raised, and intentionally catch the entire program if there is.
    while(flagArr[4]):
        FaultScreen()
    
    #Camera screen rendering
    if(flagArr[2]):
        CamScreen()
        continue
        
    if(flagArr[3]):
        ConveyorScreen()
        continue

    #Home screen rendering
    if(flagArr[1]):
        HomeScreen()
        continue

    #Info screen rendering
    if(flagArr[5]):
        InfoScreen()
        continue
