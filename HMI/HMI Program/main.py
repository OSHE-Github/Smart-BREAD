import sys, time, array
import pygame, gif_pygame
import screenElements

# Initialize Pygame
pygame.init()

#Screen Vars
clock = pygame.time.Clock()
fps = 60
objects = []
GUIScale = (int) (1)

#Screen Flags
BootFlag = 1
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

#Make button
font = pygame.font.SysFont('Arial', ButtonFontSize)
test_button = screenElements.Button("Click Me!", 200, 150, ButtonXScale, ButtonYScale, ButtonFontSize, WHITE, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR)

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
    test_button.draw(screen)
    
    for event in pygame.event.get(): #Handle events relating to the home screen, and only the home screen
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
            
        if test_button.handle_event(event, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR):
            print("Test Button!")
    
def CamScreen(): #Screen for elements of the camera view screen
    print("hi")

def ConveyorScreen(): #Screen for elements of the conveyor control screen
    print("hi")

def FaultScreen(): ##Screen for elements of the fault screen
    screen.fill(RED)
    font = pygame.font.SysFont('Arial', 60)
    text = font.render("A FAULT HAS OCCURED", True, WHITE)
    screen.blit(text, ((int) (((width-text.width)/2)), (int) (((height-text.height)/2) - text.height/2)))
    text = font.render("PLEASE DIAGNOSE AND RESTART", True, WHITE)
    screen.blit(text, ((int) (((width-text.width)/2)), (int) (((height-text.height)/2) + text.height/2)))
    
    play_square_tone(440, 1500)  # Play 440Hz for 1500ms
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
            
    #Update frame buffer        
    pygame.display.update()
    clock.tick(fps)
    
def play_square_tone(frequency, duration_ms):
    sample_rate = 44100
    period = int(sample_rate / frequency)

    # Build one full wavelength cycle (half high amplitude, half low)
    amplitude = 2**15 - 1  # Max for 16-bit signed int
    samples = array.array("h", [0] * period)
    for i in range(period):
        samples[i] = amplitude if i < period / 2 else -amplitude

    # Turn the cycle into a Sound object
    sound = pygame.mixer.Sound(buffer=samples)
    sound.set_volume(0.125)

    # Loop the short buffer sound to fill the requested duration
    sound.play(loops=-1)
    pygame.time.delay(duration_ms)
    sound.stop()

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
        
    #Home screen rendering
    if(HomeFlag):
        HomeScreen()
    
    #Camera screen rendering
    if(CamFlag):
        CamScreen()
        
    if(ConveyorFlag):
        ConveyorScreen()
    
    #Update frame buffer        
    pygame.display.update()
    clock.tick(fps)

