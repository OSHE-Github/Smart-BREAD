import threading, pygame, sys, screenElements

# Initialize Pygame
pygame.init()

#Var Setup
clock = pygame.time.Clock()
fps = 60
objects = []
GUIScale = (int) (1)

#Window Setup
#screen = pygame.display.set_mode((1600, 900)) #Windowed for testing
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN) #Fullscreen
pygame.display.set_caption("Bread HMI")
pygame.display.set_icon(pygame.image.load('assets/icon.png'))
width, height = pygame.display.get_surface().get_size()

#Button Scale & Placement Grid Vars
ButtonXScale = (int) ((width/8)*GUIScale)
ButtonYScale = (int) ((height/10)*GUIScale)
ButtonFontSize = (int) (ButtonYScale*0.4)

GridCellWidth = width/6
GridCellHeight = height/6

# Colors
BG_COLOR = (30, 30, 40)
WHITE = (255, 255, 255)
NORMAL_COLOR = (50, 150, 250)
HOVER_COLOR = (30, 100, 200)
PRESS_COLOR = (0, 50, 75)

#Make button
font = pygame.font.SysFont('Arial', ButtonFontSize)
test_button = screenElements.Button("Click Me!", 200, 150, ButtonXScale, ButtonYScale, ButtonFontSize, WHITE, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR)

#Make text
font = pygame.font.SysFont('Arial', 30)
text = font.render("Oooo, a button!", True, (255, 255, 255))

#Main Game Loop
while True:
    #Screen elements to render
    screen.fill(BG_COLOR)
    screen.blit(text, ((int) ((width/8)*GUIScale), (int) ((height/10)*GUIScale)-40))
    test_button.draw(screen)

    
    # Event handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
            
        #Test button action
        if test_button.handle_event(event, NORMAL_COLOR, PRESS_COLOR, HOVER_COLOR):
            print("Test Button!")
            
    #Update frame buffer        
    pygame.display.update()
    clock.tick(fps)

