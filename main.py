import kivy
kivy.require('1.11.0')

from kivy.config import Config

# make sure that the program does not exit on ESC; it is used later
Config.set('kivy', 'exit_on_escape', '0')

# do not leave 'red dots' on the screen
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelHeader, TabbedPanelItem
from kivy.uix.actionbar import ActionItem
from kivy.uix.image import Image, AsyncImage
from kivy.graphics import Rectangle
from kivy.uix.label import Label
from kivy.uix.actionbar import ActionBar
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.lang import Builder
import time, random

getTime = lambda: int(round(time.time() * 1000))
gameStartTime = getTime()

# do not show cursor
Window.show_cursor = False

# high score is stored in a file permanently
try:
  hsFile = open('hs.txt').read()
except OSError:
  hsFile = open('hs.txt', 'w')
  hsFile.write('-1')
  hsFile.close()

def updateHSFile(newHS):
  f = open('hs.txt', 'w')
  f.write(str(newHS))
  f.close()

def checkSound(sound): sound.play()

# play a sound effect with given volume
def playSound(source, volume, isLoop = False):
  sound = SoundLoader.load(source)
  if sound:
    sound.volume = volume
    sound.play()
    return sound
  if isLoop: sched_append(lambda x: checkSound(sound), 1)

def elapsedTime(t):
  currentTime = getTime()
  if (currentTime - gameStartTime) / 1000 >= t: return True
  return False

# show a 'new hight score' label on the screen
def showHS():
  imagePos = Window.width / 2 - 50, Window.height / 2
  img = Image(source='images/hs.png', pos=imagePos)
  GlobalContainer.playerShip.add_widget(img)
  Clock.schedule_once(lambda x: vanishHS(img), 2)

def vanishHS(img):
  GlobalContainer.playerShip.remove_widget(img)

# remove all handlers for cleanup purposes
def removeHandlers():
  for handler in GlobalContainer.all_handlers:
    Clock.unschedule(handler)
  Window.unbind(mouse_pos=GlobalContainer.all_binders[0])

# show about when logo is clicked; support mobile devices
def clickAbout(p, self):
  if p.pos[0] <= 65 and p.pos[1] >= Window.height - 40 and clickAbout.state:
    startAgain(GlobalContainer.anc)
    clickAbout.state = False
  elif not clickAbout.state:
    playAgain(self)
    GlobalContainer.anc.toggle = True
    clickAbout.state = True

clickAbout.state = True

def decreaseHealth(n):
  if not GlobalContainer.playerShip.hasShield:
    GlobalContainer.playerShip.health -= 20

def changeEnemyInterval(self, handler, interval):
  if not self.nowAbout:
    unsched_rem(handler)
    sched_append(handler, interval)

# laser hits enemy or player's ship
def laserHitsSprite(self, parent, isCrash = False):
  unsched_rem(self.handler)
  if isCrash: unsched_rem(self.elaser_handler)
  parent.remove_widget(self)
  decreaseHealth(20)
  EnemyInit.updateShipLook(self, GlobalContainer.playerShip.health, parent)
  playSound('sounds/gothit.mp3', 1)

  if GlobalContainer.playerShip.health <= 0:
    removeHandlers()
    playSound('sounds/game_over.mp3', 0.5)
    showGameOver(GlobalContainer.anc)

# check if any two sprites collide on the screen
# sprites are transparent, rectengular png images that act as a hitbox
# therefore it might be imprecise but not too noticable
def spritesCollided(x1, y1, width1, height1, x2, y2, width2, height2):
  return (x1 < x2 + width2 and x1 + width1 > x2 and y1 < y2 + height2 and y1 + height1 > y2)

# go back to a new game after leaving the 'about' page
def startAgain(self):
  if self.toggle:
    removeHandlers()
    removeWidgets(self)
    GlobalContainer.all_handlers = []
    self.nowAbout = True
    self.canvas.before.add(self.rect)
    self.canvas.before.add(self.about)
    self.about_handler = lambda x: self.moveAbout(self.about.pos[1])
    sched_append(self.about_handler)
    clickAbout.state = False
    self.toggle = False
  else:
    playAgain(self)
    self.toggle = True
    clickAbout.state = True

# orange -> 10p, red -> 20p, blue -> 30p
def increasePoint(enemy):
  if enemy.type == 0:
    GlobalContainer.playerShip.score += 10
  elif enemy.type == 1:
    GlobalContainer.playerShip.score += 20
  else:
    GlobalContainer.playerShip.score += 30

  # check for new high score
  if GlobalContainer.playerShip.score > GlobalContainer.playerShip.highScore:
    GlobalContainer.playerShip.highScore = GlobalContainer.playerShip.score
    updateHSFile(GlobalContainer.playerShip.highScore)
    if not GlobalContainer.hsShown:
      playSound('sounds/newhs.mp3', 1)
      GlobalContainer.hsShown = True
      showHS()

# check for game over
def showGameOver(self):
  GlobalContainer.anc.isDuringGO = True
  gameOverText = Image(source='images/game_over.png', size=(200, 200),
    pos=(Window.width / 2 - 100, Window.height / 2 - 100))
  self.add_widget(gameOverText)
  GlobalContainer.sprites.append(gameOverText)
  Clock.schedule_once(lambda x: playAgain(self, True), 3)

# manually remove the widgets (except the header) from the screen when restarting the game
def removeWidgets(self):
  for enemy in GlobalContainer.enemies:
    self.remove_widget(enemy)

  for sprite in GlobalContainer.sprites:
    self.remove_widget(sprite)

  self.remove_widget(GlobalContainer.playerShip)

# reset game state and start a new game
def playAgain(self, fromGO = False):
  # if sound works fine then uncomment the following 2 lines with code
  # if kivy gives a warning about ffmpeg or does not play sounds then it leave it as it is
  # because it breaks the program
  """
  SpaceApp.bgMusic.stop()
  SpaceApp.bgMusic.unload()
  """
  removeHandlers()
  GlobalContainer.all_handlers = []
  removeWidgets(self)
  initGame(self)
  if fromGO: GlobalContainer.anc.isDuringGO = False

# initialize global attributes
def initReset(obj):
  obj.enemies = []
  obj.anc = None
  obj.shipPos = Window.width / 2 - 50, Window.height / 2 - 100
  obj.playerShip = None
  obj.hsShown = False
  obj.all_handlers = []
  obj.all_binders = []
  obj.sprites = []

# class containing data that is needed globally
class GlobalContainer: pass

initReset(GlobalContainer)

# explosion gif image; shown when enemy died
class Blast(Image):
  def __init__(self, **kwargs):
    Image.__init__(self, **kwargs)
    self.source = 'images/boom.gif'
    self.size = 30, 30

  def performBlast(self, enemy, parent):
    playSound('sounds/explode.mp3', 0.25)
    spaceshipBoom = Blast()
    spaceshipBoom.pos = enemy.pos[0], enemy.pos[1]
    parent.add_widget(spaceshipBoom)
    Clock.schedule_once(lambda x: Blast.boomVanish(self, parent, spaceshipBoom), 0.5)

  def boomVanish(self, parent, blast):
    parent.remove_widget(blast)

# remove/append handlers globally
def sched_append(handler, interval=1.0 / 60.0):
  Clock.schedule_interval(handler, interval)
  GlobalContainer.all_handlers.append(handler)

def unsched_rem(handler):
  Clock.unschedule(handler)
  if handler in GlobalContainer.all_handlers: GlobalContainer.all_handlers.remove(handler)

# laser that the player shoots
class Laser(Image, GlobalContainer):
  def __init__(self, p, parent, **kwargs):
    Image.__init__(self, **kwargs)
    self.source = 'images/laser.png'
    self.size = 60, 30
    self.pos = p.pos[0] - 25, p.pos[1] + 52
    self.handler = lambda x: self.updateLaserPos(p, parent)
    sched_append(self.handler)
    GlobalContainer.sprites.append(self)
    
  # when enemy ship is killed show blast gif & do a cleanup
  def killEnemy(self, enemy, parent):
    if enemy in self.enemies: self.enemies.remove(enemy)
    self.anc.remove_widget(enemy)
    unsched_rem(enemy.handler)
    Blast.performBlast(self, enemy, parent)
    increasePoint(enemy)
          
  # check if laser hit an enemy
  def laserHitsEnemy(self, p, parent):
    for enemy in self.enemies:
      if spritesCollided(self.pos[0], self.pos[1], self.width, self.height, enemy.pos[0],
        enemy.pos[1], enemy.width, enemy.height):
        unsched_rem(self.handler) 
        unsched_rem(enemy.elaser_handler)
        parent.remove_widget(self)
        enemy.life -= 1
        if enemy.life <= 0:
          self.killEnemy(enemy, parent) 
        elif enemy.type == 1:
          enemy.source = 'images/enemy2_d1.png'
        elif enemy.type == 2 and enemy.life == 2:
          enemy.source = 'images/enemy3_d1.png'
        else:
          enemy.source = 'images/enemy3_d2.png' 
        return

  # is laser reaches end of map remove it
  def laserHitsEdge(self, p, parent):
    if p.pos[1] >= Window.height - 130:
      playSound('sounds/woosh.mp3', 1)
      unsched_rem(self.handler)
      parent.remove_widget(self) 
      return

  # parent is needed for remove_widget; only removes a direct ancestor
  def updateLaserPos(self, p, parent):
    self.laserHitsEnemy(p, parent)  
    self.laserHitsEdge(p, parent)

    # update laser pos
    p.pos = list(p.pos)
    p.pos[1] += 5
    self.pos = p.pos[0] - 25, p.pos[1] + 52 

  def shootLaser(self, p):
    playSound('sounds/laser.mp3', 0.1)
    self.add_widget(Laser(p, self))

# handle spaceship; store instance in GlobalContainer
class SpaceshipInit(Image, GlobalContainer):
  def __init__(self, parent, **kwargs):
    Image.__init__(self, **kwargs)
    self.source = 'images/spaceship.png'
    self.health = 100
    self.score = 0
    self.width = min(Window.width / 7, 70);
    self.height = self.width;
    self.hasShield = False
    self.hasSpeedo = False
    self.highScore = int(open('hs.txt').read())
    self.pos = Window.width / 2 - 50, Window.height / 2 - 100
    self.binder1 = lambda w, p: self.updateSpaceshipPos(p, parent)
    Window.bind(mouse_pos=self.binder1)
    GlobalContainer.all_binders.append(self.binder1)
    sched_append(self.laserHandler, 0.75)
    GlobalContainer.playerShip = self

  # create new Laser instance
  def laserHandler(self, w):
    class obj: pass
    obj.pos = self.pos[0] + 30, self.pos[1] + 30
    Laser.shootLaser(self, obj)
 
  # update spaceship pos as the cursor is moving
  # also make sure that the spaceship cannot go out of the map (screen)
  def updateSpaceshipPos(self, p, parent):
    x_pos = p[0] - 45
    y_pos = p[1] - 45
    if p[0] + 27 >= Window.width:
      x_pos = Window.width - 73
    elif p[0] <= 48:
      x_pos = 3
    if p[1] <= 43:
      y_pos = 0
    if p[1] >= Window.height - 90:
      y_pos = Window.height - 135

    self.pos = x_pos, y_pos
    GlobalContainer.shipPos = self.pos

# manage laser that enemy shoots
class EnemyLaser(Image, GlobalContainer):
  def __init__(self, parent, pos, etype, **kwargs):
    Image.__init__(self, **kwargs)

    # 3 types of lasers: straight, diagonally left, diagonally right
    self.source = ['images/enemy_laser.png', 'images/el_pdeg45.png', 
                    'images/el_ndeg45.png'][etype]
    if etype == 0: self.width = 8
    else: self.width = 16
    self.pos = pos[0], pos[1]
    self.handler = lambda x: self.updatePos(parent, etype)
    sched_append(self.handler)
    GlobalContainer.sprites.append(self)

  # update laser pos in regard of their types
  def updatePos(self, parent, etype):
    if etype == 0:
      self.pos = self.pos[0], self.pos[1] - 3
    elif etype == 1:
      self.pos = self.pos[0] - 3, self.pos[1] - 3
    else:
      self.pos = self.pos[0] + 3, self.pos[1] - 3
      
    if self.pos[1] <= 0:
      parent.remove_widget(self)
      unsched_rem(self.handler)

    # check if collides with player's ship
    ship = self.playerShip
    if (spritesCollided(self.pos[0], self.pos[1], self.width, self.height, ship.pos[0],
      ship.pos[1], ship.width, ship.height)):
      laserHitsSprite(self, parent)

# 3 bonuses to help the player
class RandomDrop(Image, GlobalContainer):
  def __init__(self, parent, **kwargs):
    Image.__init__(self, **kwargs)

    # choose a random bonus and its speed
    chooseRand = random.randint(0, 2)
    self.source = ['images/hppack.png', 'images/shield.png', 'images/speedup.png'][chooseRand]
    self.type = chooseRand
    self.pos = (random.randint(30, Window.width - 30),
      random.randint(self.playerShip.top + 50, Window.height + 51))
    self.handler = lambda x: self.moveDrop(parent)
    sched_append(self.handler)
    self.width = 20
    self.y_vel = random.randint(15, 20) / 10
    GlobalContainer.sprites.append(self)

  # if player's ship picks the bonus up take action
  def moveDrop(self, parent):
    self.pos = self.pos[0], self.pos[1] - self.y_vel
    ship = self.playerShip
    if self.pos[1] < 0: parent.remove_widget(self)
    if (spritesCollided(self.pos[0], self.pos[1], self.width, self.height, ship.pos[0],
      ship.pos[1], ship.width, ship.height)):
      parent.remove_widget(self)
      if self.type == 0: self.handleHealth(parent)
      elif self.type == 1: self.handleShield(parent)
      else: self.handleSpeed(parent)

  # player's ship will shoot lasers in every 0.3 secs for 5 secs
  def handleSpeed(self, parent):
    playSound('sounds/speedo.mp3', 0.8)
    GlobalContainer.playerShip.hasSpeedo = True
    self.sImage = Image(source='images/speedo.gif',
      pos=(self.playerShip.pos[0], self.playerShip.pos[1]),
      height=(self.playerShip.height), width=(self.playerShip.width))
    parent.add_widget(self.sImage)
    self.speedHandler = lambda x: self.cleanupDrop(parent, 'sImage')
    Clock.schedule_once(self.speedHandler, 1)
    sched_append(lambda x: self.followShip(parent, 0, 0, 'sImage'))
    unsched_rem(self.handler)

    # change the pace of laser shots
    unsched_rem(self.playerShip.laserHandler)
    sched_append(self.playerShip.laserHandler, 0.3)
    Clock.schedule_once(lambda x: self.laserCleanup(), 5)

  def laserCleanup(self):
    unsched_rem(self.playerShip.laserHandler)
    sched_append(self.playerShip.laserHandler, 0.75)
  
  # for 5 secs player becomes immortal
  def handleShield(self, parent):
    playSound('sounds/pickshield.mp3', 0.3)
    GlobalContainer.playerShip.hasShield = True
    self.shImage = Image(source='images/around.png',
      pos=(self.playerShip.pos[0] - 20, self.playerShip.pos[1] - 20),
      height=(self.playerShip.height + 40), width=(self.playerShip.width + 40))
    parent.add_widget(self.shImage)
    self.shieldHandler = lambda x: self.cleanupDrop(parent, 'shImage')
    Clock.schedule_once(self.shieldHandler, 5)
    sched_append(lambda x: self.followShip(parent, -20, -20, 'shImage'))
    unsched_rem(self.handler)

  # 1 hp pack adds +20 hp if hp < 100; also update ship look on the way
  def handleHealth(self, parent):
    playSound('sounds/pickhp.mp3', 0.5)
    if self.playerShip.health < 100:
      if self.playerShip.health <= 80: self.playerShip.health += 20 
      else: self.playerShip.health += 100 - self.playerShip.health
      EnemyInit.updateShipLook(self, self.playerShip.health, parent, True)

    self.hImage = Image(source='images/healing.gif', height=170, 
      pos=(self.playerShip.pos[0] - 10, self.playerShip.pos[1] - 50))
    parent.add_widget(self.hImage)
    Clock.schedule_once(lambda x: self.cleanupDrop(parent, 'hImage'), 1)
    sched_append(lambda x: self.followShip(parent, -10, -30, 'hImage'))
    unsched_rem(self.handler)

  # the gif animation of the drop should 'stick with' player's ship until it lasts
  def followShip(self, parent, n1, n2, img):
    self.__dict__[img].pos = self.playerShip.pos[0] + n1, self.playerShip.pos[1] + n2
  
  def cleanupDrop(self, parent, img):
    parent.remove_widget(self.__dict__[img])
    unsched_rem(self.followShip)
    # if shield is over reset its state
    if img == 'shImage': self.playerShip.hasShield = False

class EnemyInit(Image, GlobalContainer):
  def __init__(self, parent, **kwargs):
    Image.__init__(self, **kwargs)

    # choose randomly from 3 types of enemies with 1, 2 and 3 hp, respectively
    enemyImages = ['enemy1', 'enemy2', 'enemy3']
    randEnemyType = random.randint(0, 2)
    self.source = 'images/' + enemyImages[randEnemyType] + '.png'
    self.type = randEnemyType
    self.life = self.type + 1

    # start enemy ship from top, at a random position
    x_coord = random.randint(50, Window.width - 50)
    y_coord = Window.height - 90
    self.pos = x_coord, y_coord
    self.width = min(Window.width / 10, 40);
    self.height = self.width;
    self.x_vel = 1.5
    self.y_vel = 1.5

    # as the time goes increase enemy ship speed and pace
    interval = [1, 1.3, 1.5][self.type]
    if elapsedTime(15):
      self.x_vel = 1.75
      self.y_vel = 1.75
      interval = [1, 1.2, 1.5][self.type]
    elif elapsedTime(30):
      self.x_vel = 2
      self.y_vel = 2
      interval = [1, 1, 1.2][self.type]
    elif elapsedTime(60):
      self.x_vel = 3
      self.y_vel = 3
      interval = [1, 1, 1][self.type]

    # spaceship moves straight or diagonally (2 cases)
    d = random.randint(1, 3)
    if d == 2: self.x_vel *= -1
    elif d == 3: self.x_vel = 0

    # generate random moving on the map
    self.handler = lambda x: self.randomEnemyMove(self.pos[0], self.pos[1], parent)
    sched_append(self.handler)

    # enemy laser shoot
    self.elaser_handler = lambda x: self.shootEnemyLaser(parent)
    sched_append(self.elaser_handler, interval)

  def shootEnemyLaser(self, parent):
    # create different laser shooting implementations for different enemy ships
    current_pos = self.pos[0] + 13, self.pos[1] - 60
    if self.type == 0:
      parent.add_widget(EnemyLaser(parent, current_pos, 0))
    elif self.type == 1:
      parent.add_widget(EnemyLaser(parent, current_pos, 1))
      parent.add_widget(EnemyLaser(parent, current_pos, 2))
    else:
      for i in range(3):
        parent.add_widget(EnemyLaser(parent, current_pos, i))

  # enemy moving; when an edge is reached bounce off; when bottom is reached remove
  def randomEnemyMove(self, x, y, parent):
    new_x_coord = x + (1 * self.x_vel)
    new_y_coord = y - (1 * self.y_vel)
    if new_x_coord >= Window.width - 60 or new_x_coord <= 20:
      self.x_vel *= -1
    elif new_y_coord <= 0:
      if self in self.enemies:
        self.enemies.remove(self)
      parent.remove_widget(self)
      unsched_rem(self.handler)
      unsched_rem(self.elaser_handler)
      return
    self.pos = new_x_coord, new_y_coord 
    if self.collidesWithShip((x, y), parent):
      if self in self.enemies: self.enemies.remove(self)
      Blast.performBlast(self, self, parent)
      increasePoint(self)
      laserHitsSprite(self, parent, True)
      return

  # gradual damage on the ship over time
  def updateShipLook(self, health, parent, isHpPack = False):
    if health >= 80:
      if not isHpPack: return
      GlobalContainer.playerShip.source = 'images/spaceship.png'
    elif 60 <= health < 80: GlobalContainer.playerShip.source = 'images/spaceship_d1.png'
    elif 40 <= health < 60: GlobalContainer.playerShip.source = 'images/spaceship_d2.png'
    elif 20 <= health < 40: GlobalContainer.playerShip.source = 'images/spaceship_d3.png'
    elif 0 < health < 20: GlobalContainer.playerShip.source = 'images/spaceship_d4.png'
    else:
      Blast.performBlast(self, GlobalContainer.playerShip, GlobalContainer.anc)
      GlobalContainer.anc.remove_widget(GlobalContainer.playerShip)

  def collidesWithShip(self, enemy_pos, parent):
    if (enemy_pos[0] - 90 < self.shipPos[0] < enemy_pos[0] + 50
        and enemy_pos[1] - 90 < self.shipPos[1] < enemy_pos[1] + 40):
      return True
    return False

def initGame(self):
  # two images for the effect of a 'moving background'
  self.spacebg = Rectangle(pos=(0, 0),
    size=(Window.width, Window.height), source='images/spacebg.png')
  self.spacebg2 = Rectangle(pos=(0, Window.height),
    size=(Window.width, Window.height), source='images/spacebg.png')
  self.canvas.before.add(self.spacebg)
  self.canvas.before.add(self.spacebg2)
  self.twoBgs = [self.spacebg, self.spacebg2]
  sched_append(lambda x: self.updateBg())

  # initialize player's ship and enemies
  self.add_widget(SpaceshipInit(self))
  startEnemy = EnemyInit(self)
  self.add_widget(startEnemy)
  self.enemies.append(startEnemy)
  self.handler = lambda x: self.addEnemy()
  sched_append(self.handler, 2)
  self.changeInt = lambda x: changeEnemyInterval(self, self.handler, 1)
  Clock.schedule_once(self.changeInt, 3)

  # when ESC is pressed show 'about' page
  self.keyboard = Window.request_keyboard(self.close_keyboard, self)
  self.keyboard.bind(on_key_down=self.fire_keyboard)
  self.nowAbout = False
  
  self.rect = Rectangle(pos=(0, 0), size=(Window.width, Window.height),
    source='images/spacebg.png')  
  self.about = Rectangle(source='images/about.png',
    size=(Window.width / 3, Window.height / 3),
    pos=(self.x + Window.width / 2, Window.height))
  self.toggle = True
  self.next = 0

  sched_append(lambda x: print(GlobalContainer.anc.children), 1)

  # do not allow ESC press during Game Over screen
  self.isDuringGO = False
  GlobalContainer.anc = self
  sched_append(lambda x: self.add_widget(RandomDrop(self)), 7)
  Window.bind(on_touch_down=lambda x, p: clickAbout(p, self))

# initialize spaceship, enemies etc.
class MainLayout(Widget, GlobalContainer):
  def __init__(self, **kwargs):
    Widget.__init__(self, **kwargs)
    
    initGame(self)

  # implement a moving background with two images getting constantly above of each other
  def updateBg(self):
    b1 = self.spacebg
    b2 = self.spacebg2
    b1.pos = 0, b1.pos[1] - 2
    b2.pos = 0, b2.pos[1] - 2
    if self.twoBgs[self.next].pos[1] + Window.height < 2:
      self.twoBgs[self.next].pos = 0, Window.height
      self.next = (self.next + 1) % 2
  
  def close_keyboard(self):
    self.keyboard.unbind(on_key_down=self.fire_keyboard)
    self.keyboard = None
    
  # when ESC is pressed freeze everything and display 'about' page
  def fire_keyboard(self, keyboard, keycode, text, modifiers):
    if keycode[0] == 27 and not self.isDuringGO: startAgain(self)
              
  def moveAbout(self, y):
    self.about.pos = Window.width / 2 - 120, y - 1
    if self.about.pos[1] <= -210:
      Clock.unschedule(self.about_handler)
      self.showNewGame()

  # show 'Press to play' msg after 'about'
  def showNewGame(self):
    self.pressImg = Image(source='images/pressplay.png',
      pos=(Window.width / 2 - 120, Window.height / 2 - 120),
      size=(Window.width / 3, Window.height / 3))
    self.add_widget(self.pressImg)
    GlobalContainer.sprites.append(self.pressImg)
    self.pressHandler = lambda x: self.showHide(self.pressImg)
    sched_append(self.pressHandler, 1)

  def showHide(self, img):
    if img.width == 0:
      img.width = Window.width / 3
    else:
      img.width = 0

  def addEnemy(self):
    enemy = EnemyInit(self)
    self.add_widget(enemy)
    self.enemies.append(enemy)
          
class SpaceApp(App):
  def build(self):
    self.title = 'Space Blasters'
    self.icon = 'logo.png'
    SpaceApp.bgMusic = playSound('sounds/bg_music.mp3', 0.35, True)
    return MainLayout()

if __name__ == '__main__':
  app = SpaceApp()
  app.run()
