import pygame

#Button Class
class Button:
    def __init__(self, text, x, y, width, height, fontSize, textColor, normColor, downColor, hoverColor):
        self.text = text
        self.rect = pygame.Rect(x, y, width, height)
        self.current_color = normColor
        
        #Setup font and text surface
        self.font = pygame.font.SysFont("Arial", fontSize)
        self.text_surf = self.font.render(self.text, True, textColor)
        
        #Center the text within the button's rectangle
        self.text_rect = self.text_surf.get_rect(center=self.rect.center)

    #Draw the button onscreen
    def draw(self, surface):
        pygame.draw.rect(surface, self.current_color, self.rect, border_radius=8)
        surface.blit(self.text_surf, self.text_rect)

    #Handle hover/click events
    def handle_event(self, event, normColor, downColor, hoverColor):
        mouse_pos = pygame.mouse.get_pos()
        if self.rect.collidepoint(mouse_pos):
            self.current_color = hoverColor
        else:
            self.current_color = normColor

        #Check if we're clicking or not
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.current_color = downColor
            if self.rect.collidepoint(event.pos):
                return True
        return False
