import sys, time, array, cv2, numpy, threading
from tkinter import font
import pygame, gif_pygame
import os, psutil
import screenElements, CAN
from screenElements import drawBorders, evil_noise
from converters import cv2topygame

#Process time monitor
timeDebug = 1
start = 0
if timeDebug:
    start = time.perf_counter()

#Enable threading
multiThread = 0;
threadLiving = array.array("b", [0,0,0,0])

#Init memory monitor
memDebug = 1;
memDebugLoop = 0;
if(memDebug | memDebugLoop):
    process = psutil.Process(os.getpid())

if(memDebug):
    rss_memory = process.memory_info().rss
    print(f"Starting Memory Usage: {rss_memory / (1024**2):.2f} MB")

def init():
    #Global Variable Definitions
    global clock, objects
    global screen, width, height
    global ButtonXScale, ButtonYScale, ButtonFontSize, bordWidth
    global flagArr, convArr, constArr, numSorted, confirmArr, demoArr
    global BG_COLOR, BORDER_COLOR, TEXT_FIELD_COLOR, WHITE, BLACK, RED, NORMAL_COLOR, HOVER_COLOR, PRESS_COLOR

    # Initialize Pygame
    pygame.init()
    CAN.init()

    #Screen Vars
    clock = pygame.time.Clock()
    objects = []

    #Window Setup
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    pygame.display.set_caption("Bread HMI")
    width, height = pygame.display.get_surface().get_size()

    if(memDebug):
        rss_memory = process.memory_info().rss
        print(f"Window created!  Memory Usage: {rss_memory / (1024**2):.2f} MB")

    #Button Scale & Placement Grid Vars
    ButtonXScale = (int) ((width/4))
    ButtonYScale = (int) ((height/5))
    ButtonFontSize = (int) (ButtonYScale*0.4)

    bordWidth = height/50

    #Arrays of bytes
    flagArr = array.array("b", [0, 1, 0, 0, 0, 0, 0, 0]) #Boot, Home, Cam, Conveyor, Fault, Info, Confirm, Demo Flags in array form
    convArr = array.array("b", [0, 0, 0]) #Speed, Measured Speed, Direction
    confirmArr = array.array("b", [0,0]) #Confirm screen flag, left, right buttons
    constArr = array.array("b", [60]) #FPS
    demoArr = array.array("b", [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]) # first 8 are digital 0 or 1, and last 8 are analog 0 to 3.3

    #Conveyor Vars
    numSorted = 0

    #Colors
    BG_COLOR = (245, 245, 220)
    BORDER_COLOR = (98, 49, 8)
    TEXT_FIELD_COLOR= (210, 180, 140)
    WHITE = (255, 255, 255)
    BLACK = (0,0,0)
    RED = (255,0,0)
    NORMAL_COLOR = (117, 35, 0)
    HOVER_COLOR = (30, 100, 200)
    PRESS_COLOR = (0, 50, 75)

    if(memDebug):
        rss_memory = process.memory_info().rss
        print(f"Constants Created!  Memory Usage: {rss_memory / (1024**2):.2f} MB")

def camInit():
    #Global var definitions
    global cam

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

def graphicInit():
    #Global var init
    global boxY, boxWidth, boxHeight, ssBoxX, msBoxX, osBoxX
    global font
    global setSpeedLabel, mesSpeedLabel, objText
    global ssLabelX, ssLabelY, msLabelX, msLabelY, osLabelX, osLabelY
    global leftDirButton, minusSpeedButton, addSpeedButton, rightDirButton
    global osheLogo, owidth, oheight, bootAnim, bootAnimTimings, bootAnimLength

    #Image asset setup
    pygame.display.set_icon(pygame.image.load('assets/icon.png'))
    osheLogo = pygame.image.load("assets/OSHE Logo.png").convert_alpha()
    osheLogo = pygame.transform.scale(osheLogo, (width/5, height/4))
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

if multiThread:
    init()
    camThread = threading.Thread(target = camInit)
    graphicThread = threading.Thread(target = graphicInit)

    camThread.start()
    graphicThread.start()
    CAN.init()

    threadLiving[0] = camThread.is_alive()
    threadLiving[1] = graphicThread.is_alive()

    while True:
        if not threadLiving[0]:
            camThread.join()
            graphicThread.join()
            break

        if not threadLiving[1]:
            graphicThread.join()
            camThread.join()
            break

        threadLiving[0] = camThread.is_alive()
        threadLiving[1] = graphicThread.is_alive()

if not multiThread:
    init()
    camInit()
    graphicInit()
    CAN.init()

def BootScreen(): #Screen elements for boot animation (As well as nessecary CAN checks
    global flagArr

    screen.fill(BG_COLOR)
    drawBorders(screen, BORDER_COLOR, width, height, bordWidth)

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
    drawBorders(screen, BORDER_COLOR, width, height, bordWidth)
    cameraButton = screenElements.Button("Camera", (int) (0 + ButtonXScale/3), (int) (height - ButtonYScale - ButtonYScale/3), ButtonXScale, ButtonYScale, ButtonFontSize, WHITE, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR)
    conveyorButton = screenElements.Button("Conveyor", (int) (width - ButtonXScale - ButtonXScale/3), (int) (height - ButtonYScale - ButtonYScale/3), ButtonXScale, ButtonYScale, ButtonFontSize, WHITE, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR)
    infoButton = screenElements.Button("Info", (int) (width/2 - ButtonXScale/2), (int) (height - ButtonYScale - ButtonYScale/3), ButtonXScale, ButtonYScale, ButtonFontSize, WHITE, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR)
    demoButton = screenElements.Button("Demo", (int) (width/2 - ButtonXScale/2), (int) (height - 3 * ButtonYScale), ButtonXScale, ButtonYScale, ButtonFontSize, WHITE, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR)

    cameraButton.update()
    conveyorButton.update()
    infoButton.update()
    demoButton.update()

    for event in pygame.event.get(): #Handle events relating to the home screen, and only the home screen
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()

        if cameraButton.handle_event(event):
            flagArr[2] = 1

        if conveyorButton.handle_event(event):
            flagArr[3] = 1

        if infoButton.handle_event(event):
            flagArr[5] = 1

        if demoButton.handle_event(event):
            flagArr[7] = 1

    cameraButton.draw(screen)
    conveyorButton.draw(screen)
    infoButton.draw(screen)
    demoButton.draw(screen)

    #Update frame buffer
    pygame.display.update()
    clock.tick(constArr[0])
    
def CamScreen(): #Screen for elements of the camera view screen
    global cam
    global flagArr

    screen.fill(BG_COLOR)
    drawBorders(screen, BORDER_COLOR, width, height, bordWidth)

    #Read and convert camera feed
    ret, frame = cam.read()
    if ret and frame is not None:
        image = cv2topygame(frame)

    #Display camera feed and other onscreen elements
    screen.blit(image, (((width-image.width)/2), ((height-image.height)/3)))
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

        if cameraButton.handle_event(event):
            flagArr[2] = 0

    cameraButton.draw(screen)

    #Update frame buffer
    pygame.display.update()
    clock.tick(constArr[0])

def ConveyorScreen(): #Screen for elements of the conveyor control screen
    global convArr
    global confirmArr
    global flagArr
    global numSorted

    #Draw background elements
    screen.fill(BG_COLOR)
    drawBorders(screen, BORDER_COLOR, width, height, bordWidth)

    #Define text to display
    font = pygame.font.SysFont('Arial', (int) (ButtonFontSize/2))
    speedText = font.render(f"{convArr[0]}%", True, BORDER_COLOR)
    measSpeedText = font.render(f"{convArr[1]}%", True, BORDER_COLOR)
    sortedCount = font.render(f"{numSorted}", True, BORDER_COLOR)
    dirText = font.render(f"Direction: {'Left' if convArr[2] == 0 else 'Right'}", True, BORDER_COLOR)

    #Draw detail boxes onscreen
    pygame.draw.rect(screen, TEXT_FIELD_COLOR, pygame.Rect(ssBoxX, boxY, boxWidth, boxHeight), border_radius=0) #Set speed box
    pygame.draw.rect(screen, TEXT_FIELD_COLOR, pygame.Rect(msBoxX, boxY, boxWidth, boxHeight), border_radius=0) #Meas speed box
    pygame.draw.rect(screen, TEXT_FIELD_COLOR, pygame.Rect(osBoxX, boxY, boxWidth, boxHeight), border_radius=0) #Object count box

    #Draw text onscreen
    screen.blit(setSpeedLabel, (ssLabelX, ssLabelY))
    screen.blit(mesSpeedLabel, (msLabelX, msLabelY))
    screen.blit(objText, (osLabelX, osLabelY))
    screen.blit(dirText, (width/2 - dirText.width/2, boxY + boxHeight + dirText.height/6))

    #Draw changing text onscreen
    screen.blit(speedText, (ssBoxX + boxWidth/2 - speedText.width/2, boxY + speedText.height/6))
    screen.blit(measSpeedText, (msBoxX + boxWidth/2 - measSpeedText.width/2, boxY + measSpeedText.height/6))
    screen.blit(sortedCount, (osBoxX + boxWidth/2 - sortedCount.width/2, boxY + sortedCount.height/6))

    #Home button to go back to home menu
    homeButton = screenElements.Button("Home", (int) (0 + ButtonXScale/3), (int) (height - ButtonYScale - ButtonYScale/3), ButtonXScale, ButtonYScale, ButtonFontSize, WHITE, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR)

    leftDirButton.update()
    minusSpeedButton.update()
    addSpeedButton.update()
    rightDirButton.update()
    homeButton.update()

    #Event handlers for all of the buttons
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()

        if addSpeedButton.handle_event(event):
            convArr[0] = min(convArr[0] + 1, 100)

        if minusSpeedButton.handle_event(event):
            convArr[0] = max(convArr[0] - 1, 0)

        if leftDirButton.handle_event(event):
            if convArr[2] == 1:
                confirmArr[0] = 1
                flagArr[6] = 1

        if rightDirButton.handle_event(event):
                if convArr[2] == 0:
                    confirmArr[1] = 1
                    flagArr[6] = 1
            #print(CAN.read(0x1A3, 0, 1, 0, 0))

        if homeButton.handle_event(event):
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
    clock.tick(constArr[0])

def ConfirmScreen(): #Screen for conveyor direction confirmation
    global flagArr
    global convArr
    global confirmArr


    screen.fill(BG_COLOR)
    drawBorders(screen, BORDER_COLOR, width, height, bordWidth)
    font = pygame.font.SysFont('Arial', (int) (ButtonFontSize/1.5))
    text = font.render("Are you sure you want to change the direction of the conveyor?", True, BORDER_COLOR)
    screen.blit(text, ((int) (((width-text.width)/2)), (int) (((height-text.height)/2) - text.height/2)))

    yConfButton = screenElements.Button("Yes", (int) (width - 3.25*ButtonXScale), (int) (height/2 + ButtonYScale/3), ButtonXScale, ButtonYScale, ButtonFontSize, WHITE, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR)
    nConfButton = screenElements.Button("No", (int) (width - 1.75*ButtonXScale), (int) (height/2 + ButtonYScale/3), ButtonXScale, ButtonYScale, ButtonFontSize, WHITE, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR)

    yConfButton.update()
    nConfButton.update()

    #Event handlers for all of the buttons
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
    
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()

        if yConfButton.handle_event(event):
            if confirmArr[0] == 1:
                convArr[2] = 0
                confirmArr[0] = 0
            if confirmArr[1] == 1:
                convArr[2] = 1
                confirmArr[1] = 0
            flagArr[6] = 0

        if nConfButton.handle_event(event):
            confirmArr[0] = 0
            confirmArr[1] = 0
            flagArr[6] = 0

    yConfButton.draw(screen)
    nConfButton.draw(screen)

    #Update frame buffer
    pygame.display.update()
    clock.tick(constArr[0])

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
    clock.tick(constArr[0])

def InfoScreen():
    global flagArr

    screen.fill(BG_COLOR)
    drawBorders(screen, BORDER_COLOR, width, height, bordWidth)

    font = pygame.font.SysFont('Arial', 60)
    text = font.render(" Smart-BREAD " \
    "\n https://github.com/OSHE-Github/Smart-BREAD " \
    "\n An Open Source Hardware Enterprise project " \
    "\n Michigan Technological University " \
    "\n Houghton, Michigan " \
    "\n This program is lisecensed under:" \
    "\n GNU Free Documentation License", True, BORDER_COLOR)
    screen.blit(text, ((int) (((width-text.width)/10)), (int) (((height-text.height)/10))))


    homeButton = screenElements.Button("Home", (int) (width - ButtonXScale - ButtonXScale/3), (int) (height - ButtonYScale - ButtonYScale/3), ButtonXScale, ButtonYScale, ButtonFontSize, WHITE, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR)


    for event in pygame.event.get(): #Handle events relating to the boot screen, and only the boot screen
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
    
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()

            if homeButton.handle_event(event):
                flagArr[5] = 0

    homeButton.draw(screen)

    #Update frame buffer
    pygame.display.update()
    clock.tick(constArr[0])

def DemoScreen():
    global flagArr
    global numSorted
    global demoArr

    #Draw background elements
    screen.fill(BG_COLOR)

    #Define text to display
    font = pygame.font.SysFont('Arial', (int) (ButtonFontSize/2))
    d1t = font.render(f"{demoArr[0]}", True, BORDER_COLOR); d2t = font.render(f"{demoArr[1]}", True, BORDER_COLOR); d3t = font.render(f"{demoArr[2]}", True, BORDER_COLOR); d4t = font.render(f"{demoArr[3]}", True, BORDER_COLOR);
    d5t = font.render(f"{demoArr[4]}", True, BORDER_COLOR); d6t = font.render(f"{demoArr[5]}", True, BORDER_COLOR); d7t = font.render(f"{demoArr[6]}", True, BORDER_COLOR); d8t = font.render(f"{demoArr[7]}", True, BORDER_COLOR);
    a1t = font.render(f"{demoArr[8]/10}", True, BORDER_COLOR); a2t = font.render(f"{demoArr[9]/10}", True, BORDER_COLOR); a3t = font.render(f"{demoArr[10]/10}", True, BORDER_COLOR); a4t = font.render(f"{demoArr[11]/10}", True, BORDER_COLOR);
    a5t = font.render(f"{demoArr[12]/10}", True, BORDER_COLOR); a6t = font.render(f"{demoArr[13]/10}", True, BORDER_COLOR); a7t = font.render(f"{demoArr[14]/10}", True, BORDER_COLOR); a8t = font.render(f"{demoArr[15]/10}", True, BORDER_COLOR);

    #Draw buttons
    d1b = screenElements.Button("Digital 1", (int) (0 + 0 * ButtonXScale + 0.125 * ButtonXScale), (int) (height - 4.25 * ButtonYScale), ButtonXScale * 0.75, (int) (ButtonYScale*0.5), ButtonFontSize, WHITE, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR)
    d2b = screenElements.Button("Digital 2", (int) (0 + 1 * ButtonXScale + 0.125 * ButtonXScale), (int) (height - 4.25 * ButtonYScale), ButtonXScale * 0.75, (int) (ButtonYScale*0.5), ButtonFontSize, WHITE, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR)
    d3b = screenElements.Button("Digital 3", (int) (0 + 2 * ButtonXScale + 0.125 * ButtonXScale), (int) (height - 4.25 * ButtonYScale), ButtonXScale * 0.75, (int) (ButtonYScale*0.5), ButtonFontSize, WHITE, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR)
    d4b = screenElements.Button("Digital 4", (int) (0 + 3 * ButtonXScale + 0.125 * ButtonXScale), (int) (height - 4.25 * ButtonYScale), ButtonXScale * 0.75, (int) (ButtonYScale*0.5), ButtonFontSize, WHITE, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR)
    
    d5b = screenElements.Button("Digital 5", (int) (0 + 0 * ButtonXScale + 0.125 * ButtonXScale), (int) (height - 3 * ButtonYScale), ButtonXScale * 0.75, (int) (ButtonYScale*0.5), ButtonFontSize, WHITE, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR)
    d6b = screenElements.Button("Digital 6", (int) (0 + 1 * ButtonXScale + 0.125 * ButtonXScale), (int) (height - 3 * ButtonYScale), ButtonXScale * 0.75, (int) (ButtonYScale*0.5), ButtonFontSize, WHITE, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR)
    d7b = screenElements.Button("Digital 7", (int) (0 + 2 * ButtonXScale + 0.125 * ButtonXScale), (int) (height - 3 * ButtonYScale), ButtonXScale * 0.75, (int) (ButtonYScale*0.5), ButtonFontSize, WHITE, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR)
    d8b = screenElements.Button("Digital 8", (int) (0 + 3 * ButtonXScale + 0.125 * ButtonXScale), (int) (height - 3 * ButtonYScale), ButtonXScale * 0.75, (int) (ButtonYScale*0.5), ButtonFontSize, WHITE, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR)
   
    a1b = screenElements.Button("Analog 1", (int) (0 + 0 * ButtonXScale + 0.125 * ButtonXScale), (int) (height - 1.75 * ButtonYScale), ButtonXScale * 0.75, (int) (ButtonYScale*0.5), ButtonFontSize, WHITE, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR)
    a2b = screenElements.Button("Analog 2", (int) (0 + 1 * ButtonXScale + 0.125 * ButtonXScale), (int) (height - 1.75 * ButtonYScale), ButtonXScale * 0.75, (int) (ButtonYScale*0.5), ButtonFontSize, WHITE, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR)
    a3b = screenElements.Button("Analog 3", (int) (0 + 2 * ButtonXScale + 0.125 * ButtonXScale), (int) (height - 1.75 * ButtonYScale), ButtonXScale * 0.75, (int) (ButtonYScale*0.5), ButtonFontSize, WHITE, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR)
    a4b = screenElements.Button("Analog 4", (int) (0 + 3 * ButtonXScale + 0.125 * ButtonXScale), (int) (height - 1.75 * ButtonYScale), ButtonXScale * 0.75, (int) (ButtonYScale*0.5), ButtonFontSize, WHITE, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR)
   
    a5b = screenElements.Button("Analog 5", (int) (0 + 0 * ButtonXScale + 0.125 * ButtonXScale), (int) (height - .5 * ButtonYScale), ButtonXScale * 0.75, (int) (ButtonYScale*0.5), ButtonFontSize, WHITE, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR)
    a6b = screenElements.Button("Analog 6", (int) (0 + 1 * ButtonXScale + 0.125 * ButtonXScale), (int) (height - .5 * ButtonYScale), ButtonXScale * 0.75, (int) (ButtonYScale*0.5), ButtonFontSize, WHITE, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR)
    a7b = screenElements.Button("Analog 7", (int) (0 + 2 * ButtonXScale + 0.125 * ButtonXScale), (int) (height - .5 * ButtonYScale), ButtonXScale * 0.75, (int) (ButtonYScale*0.5), ButtonFontSize, WHITE, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR)
    a8b = screenElements.Button("Analog 8", (int) (0 + 3 * ButtonXScale + 0.125 * ButtonXScale), (int) (height - .5 * ButtonYScale), ButtonXScale * 0.75, (int) (ButtonYScale*0.5), ButtonFontSize, WHITE, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR)

    homeButton = screenElements.Button("Home", (int) (width - 3*ButtonXScale), (int) (height - 5*ButtonYScale), 2*ButtonXScale, ButtonYScale/4, (int) (ButtonFontSize/2), WHITE, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR)

    #Draw changing text onscreen
    screen.blit(d1t, ((int) (0 * ButtonXScale + 0.5 * ButtonXScale - d1t.width/2), (int) (height - 4.5 * ButtonYScale - d1t.height/2)))
    screen.blit(d2t, ((int) (1 * ButtonXScale + 0.5 * ButtonXScale - d2t.width/2), (int) (height - 4.5 * ButtonYScale - d2t.height/2)))
    screen.blit(d3t, ((int) (2 * ButtonXScale + 0.5 * ButtonXScale - d3t.width/2), (int) (height - 4.5 * ButtonYScale - d3t.height/2)))
    screen.blit(d4t, ((int) (3 * ButtonXScale + 0.5 * ButtonXScale - d4t.width/2), (int) (height - 4.5 * ButtonYScale - d4t.height/2)))
    screen.blit(d5t, ((int) (0 * ButtonXScale + 0.5 * ButtonXScale - d5t.width/2), (int) (height - 3.25 * ButtonYScale - d5t.height/2)))
    screen.blit(d6t, ((int) (1 * ButtonXScale + 0.5 * ButtonXScale - d6t.width/2), (int) (height - 3.25 * ButtonYScale - d6t.height/2)))
    screen.blit(d7t, ((int) (2 * ButtonXScale + 0.5 * ButtonXScale - d7t.width/2), (int) (height - 3.25 * ButtonYScale - d7t.height/2)))
    screen.blit(d8t, ((int) (3 * ButtonXScale + 0.5 * ButtonXScale - d8t.width/2), (int) (height - 3.25 * ButtonYScale - d8t.height/2)))
    screen.blit(a1t, ((int) (0 * ButtonXScale + 0.5 * ButtonXScale - a1t.width/2), (int) (height - 2 * ButtonYScale - a1t.height/2)))
    screen.blit(a2t, ((int) (1 * ButtonXScale + 0.5 * ButtonXScale - a2t.width/2), (int) (height - 2 * ButtonYScale - a2t.height/2)))
    screen.blit(a3t, ((int) (2 * ButtonXScale + 0.5 * ButtonXScale - a3t.width/2), (int) (height - 2 * ButtonYScale - a3t.height/2)))
    screen.blit(a4t, ((int) (3 * ButtonXScale + 0.5 * ButtonXScale - a4t.width/2), (int) (height - 2 * ButtonYScale - a4t.height/2)))
    screen.blit(a5t, ((int) (0 * ButtonXScale + 0.5 * ButtonXScale - a5t.width/2), (int) (height - .75 * ButtonYScale - a5t.height/2)))
    screen.blit(a6t, ((int) (1 * ButtonXScale + 0.5 * ButtonXScale - a6t.width/2), (int) (height - .75 * ButtonYScale - a6t.height/2)))
    screen.blit(a7t, ((int) (2 * ButtonXScale + 0.5 * ButtonXScale - a7t.width/2), (int) (height - .75 * ButtonYScale - a7t.height/2)))
    screen.blit(a8t, ((int) (3 * ButtonXScale + 0.5 * ButtonXScale - a8t.width/2), (int) (height - .75 * ButtonYScale - a8t.height/2)))

    #Update buttons
    d1b.update(); d2b.update(); d3b.update(); d4b.update(); d5b.update(); d6b.update(); d7b.update(); d8b.update()
    a1b.update(); a2b.update(); a3b.update(); a4b.update(); a5b.update(); a6b.update(); a7b.update(); a8b.update()
    homeButton.update()

    #Event handlers for all of the buttons
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()

        #Digital buttons will flip-flop between 1 and 0
        if d1b.handle_event(event):
            demoArr[0] = not demoArr[0]

        if d2b.handle_event(event):
            demoArr[1] = not demoArr[1] 

        if d3b.handle_event(event):
            demoArr[2] = not demoArr[2]

        if d4b.handle_event(event):
            demoArr[3] = not demoArr[3]

        if d5b.handle_event(event):
            demoArr[4] = not demoArr[4]

        if d6b.handle_event(event):
            demoArr[5] = not demoArr[5]

        if d7b.handle_event(event):
            demoArr[6] = not demoArr[6]

        if d8b.handle_event(event):
            demoArr[7] = not demoArr[7]

        #Analog buttons will increment by 0.1 from 0 to 33, and then loop. When sending or interpreting, make sure to divide by 10.
        # encountered a float modification error when using decimals to loop.
        if a1b.handle_event(event):
            if demoArr[8] < 33:
                demoArr[8] += 1
            else:
                demoArr[8] = 0

        if a2b.handle_event(event):
            if demoArr[9] < 33:
                demoArr[9] += 1
            else:
                demoArr[9] = 0

        if a3b.handle_event(event):
            if demoArr[10] < 33:
                demoArr[10] += 1
            else:
                demoArr[10] = 0

        if a4b.handle_event(event):
            if demoArr[11] < 33:
                demoArr[11] += 1
            else:
                demoArr[11] = 0

        if a5b.handle_event(event):
            if demoArr[12] < 33:
                demoArr[12] += 1
            else:
                demoArr[12] = 0

        if a6b.handle_event(event):
            if demoArr[13] < 33:
                demoArr[13] += 1
            else:
                demoArr[13] = 0

        if a7b.handle_event(event):
            if demoArr[14] < 33:
                demoArr[14] += 1
            else:
                demoArr[14] = 0

        if a8b.handle_event(event):
            if demoArr[15] < 33:
                demoArr[15] += 1
            else:
                demoArr[15] = 0

        #Home method
        if homeButton.handle_event(event):
            flagArr[7] = 0

    #Draw the buttons to the screen
    d1b.draw(screen); d2b.draw(screen); d3b.draw(screen); d4b.draw(screen); d5b.draw(screen); d6b.draw(screen); d7b.draw(screen); d8b.draw(screen)
    a1b.draw(screen); a2b.draw(screen); a3b.draw(screen); a4b.draw(screen); a5b.draw(screen); a6b.draw(screen); a7b.draw(screen); a8b.draw(screen)
    homeButton.draw(screen)
    
    #Update frame buffer
    pygame.display.update()
    clock.tick(constArr[0])

#End of init, start rendering
initTime = time.perf_counter()
if timeDebug:
    print(f"Loading time = {round((initTime - start)*1000, 2)}ms")

#Main Loop
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
        clock.tick(constArr[0])
        
    if(memDebugLoop):
        rss_memory = process.memory_info().rss
        print(f"Current Process Memory Usage: {rss_memory / (1024**2):.2f} MB")

    #First check if there is a fault flag raised, and intentionally catch the entire program if there is.
    while(flagArr[4]):
        FaultScreen()

    #Confirm screen rendering
    if(flagArr[6]):
        ConfirmScreen()
        continue

    #Camera screen rendering
    if(flagArr[2]):
        CamScreen()
        continue

    #Conveyor screen rendering
    if(flagArr[3]):
        ConveyorScreen()
        continue

    #Info screen rendering
    if(flagArr[5]):
        InfoScreen()
        continue

    #Demo screen rendering
    if(flagArr[7]):
        DemoScreen()
        continue

    #Home screen rendering
    if(flagArr[1]):
        HomeScreen()
        continue

