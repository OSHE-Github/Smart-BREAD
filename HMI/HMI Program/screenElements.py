import pygame

#Button Class
class Button:
    def __init__(self, text, x, y, width, height, fontSize, textColor, normColor, downColor, hoverColor):
        self.text = text
        self.rect = pygame.Rect(x, y, width, height)
        self.current_color = normColor
        self.textColor = textColor
        self.normColor = normColor
        self.pressColor = downColor
        self.hoverColor = hoverColor
        
        #Setup font and text surface
        self.font = pygame.font.SysFont("Arial", fontSize)
        self.text_surf = self.font.render(self.text, True, self.textColor)
        
        #Center the text within the button's rectangle
        self.text_rect = self.text_surf.get_rect(center=self.rect.center)

    #Draw the button onscreen
    def draw(self, surface):
        pygame.draw.rect(surface, self.current_color, self.rect, border_radius=8)
        surface.blit(self.text_surf, self.text_rect)

    #Handle click events
    def handle_event(self, event):
        mouse_pos = pygame.mouse.get_pos()
        if self.rect.collidepoint(mouse_pos):
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.current_color = self.pressColor
                if self.rect.collidepoint(event.pos):
                    return True
            return False

    def update(self):
        mouse_pos = pygame.mouse.get_pos()
        if self.rect.collidepoint(mouse_pos):
            self.current_color = self.hoverColor
        else:
            self.current_color = self.normColor

def drawBorders(screen, BORDER_COLOR, width, height, bordWidth):
    pygame.draw.rect(screen, BORDER_COLOR, pygame.Rect(0, 0, width, bordWidth), border_radius=0)
    pygame.draw.rect(screen, BORDER_COLOR, pygame.Rect(0, height - bordWidth, width, bordWidth), border_radius=0)
    pygame.draw.rect(screen, BORDER_COLOR, pygame.Rect(0, 0, bordWidth, height), border_radius=0)
    pygame.draw.rect(screen, BORDER_COLOR, pygame.Rect(width - bordWidth, 0, bordWidth, height), border_radius=0)

def evil_noise():
    pygame.mixer.pre_init(44100, -16, 1, 1024)
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
