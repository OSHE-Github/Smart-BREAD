import sys, time, array, cv2, numpy, threading, detect
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

#Sorting vars
sort = array.array("b", [0,0,0])
sortMap = array.array("b", [4, 5, 6])
heyimsortinere = 0
sortStartTime = 0

modelPath = ["models/MergedModelFP16.onnx"]

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
    CAN.Raw.write(0x1A3, 1, 1, 0, 0, 0)
    CAN.Raw.write(0x1A3, 1, 2, 0, 1, 0)
    CAN.Write.pwm(0x1A3, 0, 5000, 128)
    for i in range(3):
        CAN.Raw.write(0x1A3, 1, sortMap[i], 0, 0, 0)

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
    flagArr = array.array("b", [0, 1, 0, 0, 0, 0, 0, 0, 0]) #Boot, Home, Cam, Conveyor, Fault, Info, Confirm, Demo, and Detector init Flags in array form
    convArr = array.array("b", [0, 0, 0]) #Speed, Measured Speed, Direction
    confirmArr = array.array("b", [0,0]) #Confirm screen flag, left, right buttons
    constArr = array.array("b", [60]) #FPS
    demoArr = array.array("b", [0, 0, 0, 0, 0]) # d0+/- (0), d1 (1), d2 (2), blkdb (3), analog (4)

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
    global cam, ret, frame

    #Camera setup
    # 1. Force the V4L2 backend so OpenCV can directly control hardware exposure
    cam = cv2.VideoCapture(4, cv2.CAP_V4L2)

    # 2. Grab one frame first to start the camera hardware stream
    cam.read()
    time.sleep(0.1)

    # 3. Switch from Auto Exposure (3) to Manual Exposure (1)
    cam.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)

    cam.set(cv2.CAP_PROP_EXPOSURE, 600)      # Push exposure higher
    cam.set(cv2.CAP_PROP_GAIN, 120)          # Boost hardware sensor gain
    cam.set(cv2.CAP_PROP_BRIGHTNESS, 150)

    # 5. Flush 5 frames so the new manual exposure takes effect immediately
    for _ in range(5):
        cam.read()

    # Verify what the driver actually accepted
    print("Actual Auto Exposure:", cam.get(cv2.CAP_PROP_AUTO_EXPOSURE))
    print("Actual Exposure Value:", cam.get(cv2.CAP_PROP_EXPOSURE))

    if(memDebug):
        rss_memory = process.memory_info().rss
        print(f"Camera started!  Memory Usage: {rss_memory / (1024**2):.2f} MB")

    # ret, frame = cam.read()

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
                CAN.write(0x1A3, 3, 0, 0, 0, 128)
                pygame.quit()
                sys.exit()
    
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    CAN.write(0x1A3, 3, 0, 0, 0, 128)
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
            shutdown()

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                shutdown()

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
    if cam.isOpened():
        if ret and frame is not None:
            image = cv2topygame(dispFrame)

    #Display camera feed and other onscreen elements
    screen.blit(image, (((width-image.width)/2), ((height-image.height)/3)))
    cameraButton = screenElements.Button("Home", (int) (width - ButtonXScale - ButtonXScale/3), (int) (height - ButtonYScale - ButtonYScale/3), ButtonXScale, ButtonYScale, ButtonFontSize, WHITE, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR)

    #Handle events relating to the home screen, and only the home screen
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            shutdown()

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                shutdown()

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
            shutdown()

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                shutdown()

        if addSpeedButton.handle_event(event):
            convArr[0] = min(convArr[0] + 1, 100)
            CAN.write(0x1A3, 1, 0, 0, convArr[0], int(255.0*(int(convArr[0])/100.0)))


        if minusSpeedButton.handle_event(event):
            convArr[0] = max(convArr[0] - 1, 0)
            CAN.write(0x1A3, 1, 0, 0, convArr[0], int(255.0*(int(convArr[0])/100.0)))


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
            shutdown()
    
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                shutdown()

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
            shutdown()

    if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                shutdown()
            
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
                shutdown()
    
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    shutdown()

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
    d0t = font.render(f"{demoArr[0]}", True, BORDER_COLOR)
    d1t = font.render(f"{demoArr[1]}", True, BORDER_COLOR)
    d2t = font.render(f"{demoArr[2]}", True, BORDER_COLOR)
    blkdt = font.render(f"{demoArr[3]}, {demoArr[3]}, {demoArr[3]}, {demoArr[3]}", True, BORDER_COLOR)
    analogText = font.render(f"{demoArr[4]/10}", True, BORDER_COLOR)

    #Draw buttons
# digitalsPins 1 and 2 need a toggle button (whats happening already), digital 0 needs the speed +/-, want a blkdigital write for 7,6,5,4, 
# analog have a button write out 8 different voltages 0 to 3.3 (store between 0 and 495). Replace current analog buttons with one that does all at once.
# 
    d0bPlus = screenElements.Button("Digital 0 +", (int) (0.125 * ButtonXScale), (int) (height - 4 * ButtonYScale), ButtonXScale * 0.75, (int) (ButtonYScale*0.66), ButtonFontSize, WHITE, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR)
    d0bMinus = screenElements.Button("Digital 0 -", (int) (1.125 * ButtonXScale), (int) (height - 4 * ButtonYScale), ButtonXScale * 0.75, (int) (ButtonYScale*0.66), ButtonFontSize, WHITE, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR)
    d1b = screenElements.Button("Digital 1", (int) (2.125 * ButtonXScale), (int) (height - 4 * ButtonYScale), ButtonXScale * 0.75, (int) (ButtonYScale*0.66), ButtonFontSize, WHITE, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR)
    d2b = screenElements.Button("Digital 2", (int) (3.125 * ButtonXScale), (int) (height - 4 * ButtonYScale), ButtonXScale * 0.75, (int) (ButtonYScale*0.66), ButtonFontSize, WHITE, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR)
    blkdb = screenElements.Button("Bulk Digital", (int) (width/2 - ButtonXScale/2), (int) (height -  2.5 * ButtonYScale), ButtonXScale, (int) (ButtonYScale*0.66), ButtonFontSize, WHITE, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR)
    analogButton = screenElements.Button("Analog", (int) (width/2 - ButtonXScale/2), (int) (height - 1 * ButtonYScale), ButtonXScale, (int) (ButtonYScale*0.66), ButtonFontSize, WHITE, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR)

    homeButton = screenElements.Button("Home", (int) (width/2 - ButtonXScale), (int) (height - 5 * ButtonYScale), 2*ButtonXScale, ButtonYScale/4, (int) (ButtonFontSize/2), WHITE, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR)

    #Draw changing text onscreen
    screen.blit(d0t, ((int) ((1 * ButtonXScale) - d0t.width/2), (int) (height - 4.25 * ButtonYScale - d0t.height/2)))
    screen.blit(d1t, ((int) ((2.5 * ButtonXScale) - d1t.width/2), (int) (height - 4.25 * ButtonYScale - d1t.height/2)))
    screen.blit(d2t, ((int) ((3.5 * ButtonXScale) - d2t.width/2), (int) (height - 4.25 * ButtonYScale - d2t.height/2)))
    screen.blit(blkdt, ((int) (width/2 - blkdt.width/2), (int) (height - 2.75 * ButtonYScale - blkdt.height/2)))
    screen.blit(analogText, ((int) (width/2 - analogText.width/2), (int) (height - 1.25 * ButtonYScale - analogText.height/2)))

    #Update buttons
    d0bPlus.update(); d0bMinus.update(); d1b.update(); d2b.update(); blkdb.update(); analogButton.update();
    homeButton.update()

    #Event handlers for all of the buttons
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            shutdown()

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                shutdown()

        # Digital 0 increment speed up and down (copied from conveyor screen)
        if d0bPlus.handle_event(event):
            demoArr[0] = min(demoArr[0] + 1, 100)
            CAN.write(0x1A3, 1, 0, 0, demoArr[0], int(255.0*(int(demoArr[0])/100.0)))

        if d0bMinus.handle_event(event):
            demoArr[0] = max(demoArr[0] - 1, 0)
            CAN.write(0x1A3, 1, 0, 0, demoArr[0], int(255.0*(int(demoArr[0])/100.0)))

        # Digital 1 and 2 toggle between 1 and 0
        if d1b.handle_event(event):
            demoArr[1] = not demoArr[1]
            CAN.write(0x1A3, 1, 1, 0, demoArr[1], 0)


        if d2b.handle_event(event):
            demoArr[2] = not demoArr[2] 
            CAN.write(0x1A3, 1, 2, 0, demoArr[2], 0)

        # blkdigital toggle for pins 4,5,6,7)
        if blkdb.handle_event(event):
            demoArr[3] = not demoArr[3]
            CAN.write(0x1A3, 2, 3, 0b0000000000111 , 0, 0) #data is zeroes until you get the thing you want whatever that means, 0) #that sort of stuff for pins)


        # Analog button writes 8 different voltages (0 to 3.3V, stored 0 to 495) to the analog pin, 
        if analogButton.handle_event(event):
            CAN.write(0x1A3, 2, 8, 0, 4, 0)
            CAN.write(0x1A3, 2, 8, 0, 8, 0)
            CAN.write(0x1A3, 2, 8, 0, 12, 0)
            CAN.write(0x1A3, 2, 8, 0, 16, 0)
            CAN.write(0x1A3, 2, 8, 0, 20, 0)
            CAN.write(0x1A3, 2, 8, 0, 24, 0)
            CAN.write(0x1A3, 2, 8, 0, 28, 0)


        #Home method
        if homeButton.handle_event(event):
            flagArr[7] = 0

    #Draw the buttons to the screen
    d0bPlus.draw(screen); d0bMinus.draw(screen); d1b.draw(screen); d2b.draw(screen); blkdb.draw(screen); analogButton.draw(screen)
    homeButton.draw(screen)
    
    #Update frame buffer
    pygame.display.update()
    clock.tick(constArr[0])

def shutdown():
    CAN.Raw.write(0x1A3, 3, 0, 0, 0, 128)
    CAN.Raw.write(0x1A3, 1, 1, 0, 1, 0)

    for i in range(3):
        CAN.Raw.write(0x1A3, 1, sortMap[i], 0, 0, 0)

    pygame.quit()
    sys.exit()

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

    if cam.isOpened():
        ret, frame = cam.read()
        if ret and frame is not None:
            if flagArr[8] == 0:
                flagArr[8] = detect.init(frame, modelPath)

            if not heyimsortinere:
                crossFlag, _, dispFrame = detect.findobj(frame)
                if crossFlag != -1:

                    if crossFlag == 0:
                        crossFlag = 1
                    elif crossFlag == 1:
                        crossFlag = 0

                    print(crossFlag)
                    sort[crossFlag] = sort[crossFlag] == 0
                    CAN.Raw.write(0x1A3, 1, sortMap[crossFlag], 0, sort[crossFlag], 0)
                    heyimsortinere = 1
                    sortStartTime = time.perf_counter()
            else:
                dispFrame = frame

    if heyimsortinere:
        presentTime = time.perf_counter()
        print(presentTime - sortStartTime)
        if (presentTime - sortStartTime) > 10:
            sort[crossFlag] = sort[crossFlag] == 0
            CAN.Raw.write(0x1A3, 1, sortMap[crossFlag], 0, sort[crossFlag], 0)
            heyimsortinere = 0

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

