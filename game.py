"""Some simple skeleton code for a pygame game/animation

This skeleton sets up a basic 800x600 window, an event loop, and a
redraw timer to redraw at 30 frames per second.
"""
from __future__ import division
import math
import random
import sys
import os
import pygame


# Some useful functions used in more than one class
def distance(p, q):
    """Return the distance between points p and q"""
    return math.sqrt((p[0]-q[0])**2 + (p[1]-q[1])**2)

def load_font(filename, size):
    """Load a font from the fonts directory"""
    return pygame.font.Font(os.path.join('fonts', filename), size)

def load_image(filename, alpha):
    """Load an image with the given filename from the images directory"""
    img = pygame.image.load(os.path.join('images', filename))
    if alpha:
        img = img.convert_alpha()
    else:
        img = img.convert()
    return img


def load_sound(filename):
    """Load a sound with the given filename from the sounds directory"""
    return pygame.mixer.Sound(os.path.join('sounds', filename))


def draw_centered(surface1, surface2, position):
    """Draw surface1 onto surface2 with center at position"""
    rect = surface1.get_rect()
    rect = rect.move(position[0]-rect.width//2, position[1]-rect.height//2)
    surface2.blit(surface1, rect)


def crop_image(img, width, height):
    """Crop an image around its center"""
    assert(img.get_width() >= width and img.get_height() >= height)
    img2 = pygame.Surface((width, height))
    rect = img.get_rect()
    rect = rect.move(-(rect.width-width)//2, -(rect.height-height)//2)
    img2.blit(img, rect)
    return img2
    

# Classes used within the game
class GameObject(object):
    """All game objects have a position and an image"""
    def __init__(self, position, image):
        self.image = image
        self.position = list(position[:])

    def draw_on(self, screen):
        draw_centered(self.image, screen, self.position)

    def size(self):
        return max(self.image.get_height(), self.image.get_width())


class Ant(GameObject):
    """Initial speed of Ant"""
    START_SPEED = 5
    ROT = math.pi/75   # rotation constant

    """An ant is the main character in our game"""
    def __init__(self, position):
        super(Ant, self).__init__(position, load_image('ant-game.png', True))
        self.speed = Ant.START_SPEED
        self.direction = 0
        self.images = [load_image('ant-game-%d.png' % i, True) 
                        for i in range(3) ]
        self.image_index = 1

    def choose_food(self, food):
        """Select a food item from the collection food"""
        # find the closest food item
        dmin = 10**15
        for f in food:
            d = distance(self.position, f.position)
            if d < dmin:
                self.target = f
                dmin = d

    def move(self):
        # Turn a little towards our target
        a = self.position
        b = self.target.position
        v = b[0]-a[0], b[1]-a[1]  # vector from a to b
        n = math.sqrt(v[0]**2 + v[1]**2) # length of v (also called norm)
        uv = v[0]/n, v[1]/n # unit vector pointing from a to b
        theta = math.atan2(uv[1], uv[0]) # between -pi and pi
        
        # hackey code -- use % instead
        while self.direction > math.pi:
            self.direction -= 2*math.pi
        while self.direction < -math.pi:
            self.direction += 2*math.pi

        turn = theta - self.direction

        if turn > math.pi:
            turn = -2*math.pi + turn
        if turn < -math.pi:
            turn = 2*math.pi - turn


        turn = min(self.speed*Ant.ROT, turn)
        turn = max(-self.speed*Ant.ROT, turn)

        self.direction += turn

        # Take a step forward in the current direction
        self.image_index = (self.image_index + 1) % 3
        self.position[0] += math.cos(self.direction)*self.speed
        self.position[1] += math.sin(self.direction)*self.speed

    def draw_on(self, screen):
        theta_r = self.direction
        theta_d = math.degrees(theta_r)
        img = pygame.transform.rotate(self.images[self.image_index], 
                                      -theta_d-45)
        draw_centered(img, screen, self.position)


class Food(GameObject):
    """This is food--- the ant goes after this stuff"""

    @classmethod
    def initialize(cls):
        cls.images = [load_image('cashew-game.png', True),
                      load_image('kiwi-game.gif', True),
                      load_image('orange-game.png', True)]

    def __init__(self, position):
        super(Food, self).__init__(position, random.choice(Food.images))

class Poison(GameObject):
    """This is poison --- ants shouldn't eat this"""
    def __init__(self, position):
        super(Poison, self).__init__(position, 
                                     load_image('poison-game.png', True))
        
class Game(object):
    """This class controls the game"""

    # different game states
    PLAYING, DYING, GAME_OVER, STARTING = range(4)

    # user-defined events
    REFRESH, START, RESTART = range(pygame.USEREVENT, pygame.USEREVENT+3)

    # some constants
    MIN_POISON = 6
    NUM_FOOD = 4

    def __init__(self):
        """Initialize a new game"""
        pygame.mixer.init()
        pygame.mixer.pre_init(44100, -16, 2, 2048)
        pygame.init()

        # set up a window
        self.width = 800
        self.height = 600
        self.screen = pygame.display.set_mode((self.width, self.height))

        # set background color
        self.bg_color = 0xef, 0xde, 0xcd  # almond
        self.txt_color = 0x6f, 0x4e, 0x37 # nice match for almond

        # initialize the Food class
        Food.initialize()

        # Game state variables
        self.lives = 3
        self.score = 0
        self.state = Game.STARTING

        # background image
        self.background_img = crop_image(load_image('pavement.jpg', False), 
                                        self.width, self.height)

        # In-game objects
        self.ant = Ant((self.width//2, self.height//2))
        self.food = []
        self.poison = []

        # Text objects
        font = load_font('barricade.ttf', 50)
        self.gameover_txt = font.render('Game Over', True, (255, 0, 0))
        self.playgame_txt = font.render('Click to Play', True, 
                                        self.txt_color)
        self.font = font

        # Sound effects
        self.die_snd = load_sound('die.wav')
        self.gameover_snd = load_sound('gameover.wav')
        self.eat_snd = load_sound('eat.wav')
        self.soundtrack = load_sound('soundtrack.wav')
        self.soundtrack.set_volume(.3)

        # Setup a timer to refresh the display FPS times per second
        self.FPS = 30
        pygame.time.set_timer(Game.REFRESH, 1000//self.FPS)

        

    def restart(self):
        """Restart a brand new game"""
        self.lives = 3
        self.score = 0
        self.ant.speed = Ant.START_SPEED
        self.start()

    def start(self):
        """Start playing (again)"""
        self.soundtrack.play(-1, 0, 1000)
        self.ant.position = [self.width//2, self.height//2]

        self.food = {self.new_food() for _ in range(Game.NUM_FOOD) }
        np = Game.MIN_POISON + self.score//5000
        self.poison = {self.new_poison() for _ in range(np) }

        self.ant.choose_food(self.food)
        self.state = Game.PLAYING

    def good_position(self):
        """Pick a good location, not too close to the ant or anything else"""
        good = False
        while not good:
            position = random.randint(50, self.width-50), \
                       random.randint(50, self.height-50)
            good = True
            if distance(self.ant.position, position) < 200:
                good = False
            for x in list(self.poison) + list(self.food):
                if distance(x.position, position) < 50:
                    good = False
        return position

    def new_food(self):
        """Generate some new food"""
        return Food(self.good_position())

    def new_poison(self):
        """Generate some new poison"""
        return Poison(self.good_position())

    def run(self):
        """Loop forever processing events"""
        running = True
        while running:
            event = pygame.event.wait()

            # time to draw a new frame
            if event.type == Game.REFRESH:
                self.draw()
                if self.state == Game.PLAYING:
                    self.ant.move()
                    self.check_ant_eating()
                    self.check_ant_poisoned()

            # player is asking to quit
            elif event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

            # user is clicking while playing
            elif event.type == pygame.MOUSEBUTTONDOWN \
                    and self.state == Game.PLAYING:
                self.clicked(event.pos)

            # user is clicking to start new game
            elif event.type == pygame.MOUSEBUTTONDOWN \
                    and self.state == Game.STARTING:
                self.restart()

            # time to resume after losing a life
            elif event.type == Game.START:
                pygame.time.set_timer(Game.START, 0) # turn this timer off
                if self.lives == 0:
                    self.game_over()
                else:
                    self.start()

            # time to switch from game over display to new game display
            elif event.type == Game.RESTART:
                pygame.time.set_timer(Game.RESTART, 0) # turn this timer off
                self.state = Game.STARTING
            
            else:
                pass # an event type we don't handle            

    def game_over(self):
        """Player is out of lives

        Play game over sound and wait for it to end before restarting.
        """
        self.state = Game.GAME_OVER
        self.gameover_snd.play()
        delay = int((self.gameover_snd.get_length()+1)*1000)
        pygame.time.set_timer(Game.RESTART, delay)

    def clicked(self, position):
        """User clicked at position --- remove poison if appropriate"""
        for p in list(self.poison):
            if distance(p.position, position) < p.size()/2:
                self.poison.remove(p)
                self.poison.add(self.new_poison())


    def check_ant_poisoned(self):
        """Check if the ant walked on the poison"""
        for p in self.poison:
            if distance(self.ant.position, p.position) \
                < (self.ant.size() + p.size())/3:
                self.die()
                return

    def die(self):
        """Lose a life"""
        self.soundtrack.stop()
        # play dying sound and wait for it to end before continuing
        self.lives -= 1
        self.state = Game.DYING
        self.die_snd.play()
        delay = int((self.die_snd.get_length()+1)*1000)
        pygame.time.set_timer(Game.START, delay)

    def check_ant_eating(self):
        """Check if the ant got to its target"""
        if distance(self.ant.position, self.ant.target.position) \
                < self.ant.speed:
            self.food.remove(self.ant.target)
            self.score += 100
            if self.score % 1000 == 0:
                self.ant.speed += 1
            if self.score % 5000 == 0 and self.score < 30000:
                self.poison.add(self.new_poison())
            self.food.add(self.new_food())
            self.ant.choose_food(self.food)
            self.eat_snd.play()

    def draw(self):
        """Update the display"""
        # everything we draw now is to a buffer that is not displayed
        
        # draw background image
        self.screen.blit(self.background_img, self.background_img.get_rect())

        # draw the food
        for f in self.food:
            f.draw_on(self.screen)

        # draw the poison
        for p in self.poison:
            p.draw_on(self.screen)

        # draw the ant
        self.ant.draw_on(self.screen)

        # draw the score and number of lives
        pad = 20
        img = self.font.render('I'*self.lives, True, self.txt_color)
        rect = img.get_rect().move(pad, pad)
        self.screen.blit(img, rect)
        img = self.font.render(str(self.score), True, self.txt_color)
        rect = img.get_rect()
        rect = rect.move(self.width-rect.width-pad, pad)
        self.screen.blit(img, rect)

        # draw game over or restart message
        if self.state == Game.GAME_OVER:
            draw_centered(self.gameover_txt, self.screen, 
                          (self.width//2, self.height//3))
        elif self.state == Game.STARTING:
            draw_centered(self.playgame_txt, self.screen, 
                         (self.width//2, self.height//3))

        # flip buffers so that everything we have drawn gets displayed
        pygame.display.flip()


Game().run()
pygame.quit()
sys.exit()

