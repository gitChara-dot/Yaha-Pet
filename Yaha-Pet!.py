import os
import sys
from PyQt6.QtWidgets import QApplication, QWidget, QSystemTrayIcon, QMenu, QLabel
from PyQt6.QtCore import Qt, QSize, QPoint, QUrl, QPropertyAnimation, QTimer
from PyQt6.QtGui import QIcon, QGuiApplication, QPixmap, QAction
from PyQt6.QtMultimedia import QSoundEffect
from pathlib import Path
import random 

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

#Functions
def close_app():
    app.quit()


def get_size():
    primary_screen = QGuiApplication.primaryScreen()
    screen_size = primary_screen.size()
    return screen_size

def get_size_for_characters():
    size = get_size()
    width = size.width()//10
    height = size.height()//10
    size = QSize(width, height)
    return size

def resize_to_current_screen():
    screen_size = get_size()
    screen_width = screen_size.width()
    screen_height = screen_size.height()
    yahawindow.resize(screen_width, screen_height)


def say_hi_message():
    if(len(characters_names)>0):
        name = random.choice(characters_names)
        #Setting the sound
        sound_path = resource_path(f'assets/{name}/sounds/hi.wav')
        sound.setSource(QUrl.fromLocalFile(sound_path))
        sound.setVolume(0.5)
        
        yaha_tray.showMessage(f'{name} says:','Hi!', yaha_icon, 500)
        sound.setLoopCount(1)
        sound.play()
    else:
        yaha_tray.showMessage('Wait!','You have not spawned anyone yet!', QSystemTrayIcon.MessageIcon.Information, 500)

class Character(QWidget):
    def __init__(self, name: str, size: QSize):
        super().__init__(parent = None)
        #Basic attributes
        self.name = name
        self.drag = False
        self.char_size = size
        self.first = True # Its the first time it spawns, useful when calling the function set_sprite.

        #self.start_time : float
        #self.end_time : float # - BENCHMARKING PURPOSES

        #Sound player
        self.soundplayer = QSoundEffect()
        self.soundplayer.setVolume(0.5)
        self.soundplayer.setLoopCount(1)
        self.mutesounds : bool = False

        #Sound Effects
        self.grabbed_soundeffects = [] # List of all sound effects available when the character gets grabbed with mouse
        sound_effect_path = Path(resource_path(f'assets/{self.name}/sounds'))
        for file in sound_effect_path.iterdir():
            file_name = file.name
            if(file_name[0:7] == "grabbed" and file_name[-4:] == ".wav"):
                file_name = file_name[0:8] # leave only the name, remove extension
                self.grabbed_soundeffects.append(file_name)
                print(file_name)
        print(self.grabbed_soundeffects)


        #Animation variables
        self.onanimation = False  # Its not on animation, useful to avoid clicks when falling
        self.animation = None
        self.before_anim_pos : QPoint # Save position 
        self.walktocoord = QPoint(0,self.pos().y()) # Coordinate that the character will walk to during their animation.
        self.animationnames = [] # Animation names for preloading purposes 
        self.randomtimer = QTimer() # Timer for random animations

        #pre-loading animation frames
        self.frames : dict[str, list[QPixmap]] = {} # Example: "Dance", "frame1,frame2,frame3"
        self.current_frame_idx = 0 
        self.anim_idx : dict[str,int] = {} # Example: Dance, 1
        self.current_anim_name = ''

        #Setting the timer for random animations
        self.frame_timer = QTimer()
        self.frame_timer.timeout.connect(self.next_frame)


        #Valid random animations
        self.modified_animationlist = totalanimations.copy()
        try:
            self.modified_animationlist[self.name].remove("walkright")
            self.modified_animationlist[self.name].remove("walkleft") # Remove unwanted random animations
            self.modified_animationlist[self.name].remove("falling")
        except ValueError:
            pass

        #Direction walk-animation variables
        self.direction : int = 0
        
        #Idle Timer 
        self.idle_timer = QTimer()
        self.idle_timer.timeout.connect(self.try_animation)

        #Creating label for containing the sprite
        self.label = QLabel(parent = self) 
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter) # Align with parent
        self.label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True) # Doesnt consume click entries

        #Character window flags: Always on top, no text and no taskbar icon, and receive click inputs
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint) 
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowFlag(Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False) 

        #Widget Attributes
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True) # no backg
        self.resize(self.char_size) # same size as parent

        #Start the random animation timer
        self.start_random_timer()

    def start_random_timer(self):
        random_time = random.randrange(3000,10000)
        self.randomtimer.start(random_time)
        self.randomtimer.timeout.connect(self.try_animation)
            
    def start_anim(self, animname: str, fps: int = 40):
        if(not self.onanimation and not self.drag):
            self.before_anim_pos = self.pos()
            if animname not in self.frames: # If animation hasnt loaded yet
                self.preload_animations(animname)
            if self.frames.get(animname): # If frames are loaded
                self.current_anim_name = animname # Set animation to current animation
                self.current_frame_idx = 0
                self.onanimation = True # avoid clicking
                self.frame_timer.start(int(1000 / fps))
                if(self.mutesounds == False):
                    self.play_animsound(animname)
    def play_animsound(self, animname:str ):
        self.soundplayer.setMuted(False)
        self.soundplayer.setLoopCount(1)
        

        soundpath = resource_path(f'assets/{self.name}/sounds/{animname}.wav')
        print(f"sound: {soundpath}")
        if(Path.exists(Path(soundpath))):
            self.soundplayer.setSource(QUrl.fromLocalFile(soundpath))
            self.soundplayer.play()
    def stop_current_sound(self):
        self.soundplayer.stop()

    def try_animation(self):
        if(not self.onanimation and not self.drag):
            roll = random.randrange(0,100)
            if(roll<=50): #If roll<=X, do walking animation
                min_walk_distance = 100
                screen_width = get_size().width()
                
                self.roll_direction = random.randrange(0, 2) #If 0 go left, if 1 go right
                
                if(self.roll_direction == 0):
                    start_range = 0
                    end_range = self.pos().x() - min_walk_distance
                   
                else:
                    start_range = self.pos().x() + min_walk_distance
                    end_range = screen_width-self.width()
                    
                if(start_range<end_range):
                    if(self.roll_direction == 0):
                        self.start_anim("walkleft")
                    else:
                        self.start_anim("walkright")
                    possible_direction = random.randrange(start_range,end_range) # Leave some pixels as margin
                    self.walktocoord = QPoint(possible_direction, self.pos().y())
                
                else: # If invalid range, dont start any animation and try again later.
                    return
            
                time = int(abs(self.walktocoord.x()-self.pos().x()))
                time = int(5*time) # Convert to int to avoid bugs
                self.animation = QPropertyAnimation(self, b"pos")
                self.animation.setDuration(time) # Time it takes the animation to be completed
                self.animation.setTargetObject(self) # Widget as the target for the animation
                self.animation.setStartValue(QPoint(self.pos())) # Current pos as start
                self.animation.setEndValue(QPoint(self.walktocoord.x(), self.pos().y())) # Same y coord.
                self.animation.finished.connect(self.stop_current_animation)
                self.animation.finished.connect(self.stop_current_sound) 
                self.animation.start()
            else:
                
                chosen_animation = random.choice(self.modified_animationlist[self.name])
                self.start_anim(chosen_animation)

    def next_frame(self):
        
        frames = self.frames.get(self.current_anim_name, [])   # Get the frames from the current animation
        if self.current_frame_idx<len(frames) and self.current_frame_idx>=0 : # While the current frame is still valid
            
           
            if(self.current_anim_name != "walkleft" and self.current_anim_name != "walkright"):
                #Compensating for size change between images
                prevpos = self.pos()
                prevsize = self.size()

                current_frame = frames[self.current_frame_idx]
                newsize = current_frame.size()

                deltawidth = newsize.width() - prevsize.width()
                deltaheight = newsize.height() - prevsize.height()
                new_pos = QPoint(
                    prevpos.x() - deltawidth // 2,
                    prevpos.y() - deltaheight // 2
                )
                self.move(new_pos)
            
            self.label.resize(frames[self.current_frame_idx].size()) # Resize the label and widget to the img size
            self.resize(frames[self.current_frame_idx].size())
             
            self.label.setPixmap(frames[self.current_frame_idx]) # Set the image of the character to corresponding frame
            #print(self.walktocoord.x())
            self.current_frame_idx += 1
            
        else: # If the current frame doesnt exist 
            
            if(self.animation != None and self.animation.state() == QPropertyAnimation.State.Running): # If animation is still running, repeat the frames
                self.current_frame_idx = 1
                print("reseted frame")
            else:
                print("reached")
                self.stop_current_animation()
            
            
            if(self.current_anim_name != "walkleft" and self.current_anim_name != "walkright"):  # Avoid changing the position for the walk ainmation
                self.move(self.before_anim_pos) # Changes the position in order to adjust for different image sizes
    def stop_current_animation(self):
        self.frame_timer.stop()  # Stop the timer
        self.setDefaultLabel() # Set default animation
        self.onanimation = False # Animation ended


    def preload_animations(self, animname):
        base_path = resource_path(f'assets/{self.name}/animations/{animname}')
        base = Path(base_path)
        files = sorted(base.glob("*.png"), key=lambda f: int(f.stem)) # Sort files by number
        target: QSize = self.char_size # Set target size for images 
        width = target.width()
        height = target.height()
        match animname:
            case "dance":
                width = int(width*1.5)
                height = int(height*1.5)
        target = QSize(width,height)
            
        loaded: list[QPixmap] = []
        for f in files:
            reader = QPixmap(str(f)).scaled(target, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)  # QPixmap ready
            loaded.append(reader) # Append each image to  frames
        self.frames[animname] = loaded # Set the image list to the corresponding animation
        self.anim_idx[animname] = 0
    def preload_allanimations(self):
        for animation in totalanimations[self.name]:
            self.preload_animations(animation)
    def set_sprite(self, filename: str):
        # Initial widget position at center, above task bar
        posinicialx = get_size().width()//2
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        #Creating pixmap that contains the image and scales it to char_size
        pix = QPixmap(filename)
        scaled = pix.scaled(self.char_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation )

        #Setting the image to the label
        self.label.setPixmap(scaled)
        self.label.resize(scaled.size()) # Make the label same size as image
        self.resize(scaled.size()) # Make the widget same size as image
        
        #Showing the label
        self.label.show() 

        #self.setStyleSheet("border: 2px solid red;")  # DEBUG

        #Position and animation if its the first time spawning the instance
        if(self.first == True):
            print("reached")
            self.first = False
            self.move(posinicialx, 0)
            self.show()
            self.fall_animation() #Start with the fall animation
        
        #print("label:", self.label.size(), "pixmap:", scaled.size()) // DEBUG

    def mousePressEvent(self, e):
        if(not self.onanimation):
            if(e.button() == Qt.MouseButton.LeftButton):
                self.drag = True
                self.offset = e.globalPosition().toPoint() - self.frameGeometry().topLeft() # Put the cursor at the center of the widget

                if(self.grabbed_soundeffects):
                    sound_effect = QSoundEffect()
                    sound_effect.setVolume(1)
                    sound_chosen = random.choice(self.grabbed_soundeffects) # Choose a random "grabbed" sfx
                    print(sound_chosen)
                    sound_source = resource_path(f'assets/{self.name}/sounds/{sound_chosen}.wav')
                    sound_effect.setSource(QUrl.fromLocalFile(sound_source))
                    sound_effect.play()
                    sound_effect.playingChanged.connect(lambda: sound_effect.deleteLater()) # Destroy itself to avoid being picked up by garbage col.
                    
            
    def mouseMoveEvent(self, e):
        if(self.onanimation == False):
            if(self.drag and e.buttons() & Qt.MouseButton.LeftButton):
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
                new_top_left = e.globalPosition().toPoint()-self.offset
                new_top_left = self.clamp_to_screen(new_top_left) # Ensures the character falls onto the taskbar
                self.move(new_top_left)

                #Set special image when grabbing
                grabbed_image_dir = resource_path(f'assets/{self.name}/sprites/grabbed.png')
                self.setLabelImage(grabbed_image_dir)

                
                

    def mouseReleaseEvent(self, e):
        if(e.button() == Qt.MouseButton.LeftButton and not self.onanimation):

            self.setCursor(Qt.CursorShape.ArrowCursor) # Set cursor to default
            self.drag = False
            
            self.fall_animation() 

            #Stop the sound effects to avoid audio glitches
            
    def clamp_to_screen(self, pt: QPoint) -> QPoint:
        # Gets actual screen or the one under the cursor
        scr = QGuiApplication.screenAt(pt) or self.windowHandle().screen()
        rect = scr.availableGeometry()  # Ignores the task bar space

        x = max(rect.left(),  min(pt.x(), rect.right()  - self.width()  + 5))
        y = max(rect.top(),   min(pt.y(), rect.bottom() - self.height() + 1))
        return QPoint(x, y)       

    
    def getName(self):
        return self.name
    
    def getLabel(self):
        return self.label
    
    def setLabelImage(self, dir):
        pix = QPixmap(dir)
        scaled = pix.scaled(self.char_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation )
        self.label.setPixmap(scaled)
        self.label.repaint()

    def setDefaultLabel(self):
        pix = QPixmap(resource_path(f'assets/{self.name}/sprites/spawn.png'))
        scaled = pix.scaled(self.char_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation )
        self.label.setPixmap(scaled)
        self.resize(scaled.size())
        self.label.resize(scaled.size())

    def getTimer(self):
        return self.frame_timer
    def mute(self, flag: bool):
        self.mutesounds = flag
    def setOnAnimation(self):
        self.onanimation = not self.onanimation
    def fall_animation(self):
        self.onanimation = True # Warns click events that this widget is on an animation and it cant be clicked.

        #Get current position
        current_pos = self.pos()
        
        #Get the target height destination 
        y = self.clamp_to_screen(QPoint(0, get_size().height()-self.label.pixmap().size().height())).y() # Ensures that it falls onto the taskbar

        #Length of animation
        time = (get_size().height()-current_pos.y()) # Formula for time to fall is (size of screen - current y pos)
        time = int(1.5*time) # Convert to int to avoid bugs

        #Set the falling sprite
        self.set_sprite(resource_path(f'assets/{self.name}/animations/falling/falling.ico'))

        
        #Animation 
        self.animation = QPropertyAnimation(self, b"pos")
        self.animation.setDuration(time) # Time it takes the animation to ble completed
        self.animation.setTargetObject(self) # Widget as the target for the animation
        self.animation.setStartValue(current_pos) # Current pos as start
        self.animation.setEndValue(QPoint(current_pos.x(), y)) # Same x coord, right above the taskbar as final frame
        self.animation.start() 
        
        #Setting a timer to go back to normal sprite
        self.timer = QTimer()
        self.timer.setSingleShot(True) #Only once
        self.timer.start(time) # Same time as animation length
        self.timer.timeout.connect(lambda: self.set_sprite(resource_path(f'assets/{self.name}/sprites/spawn.png'))) # When it ends, go back to normal sprite
        self.timer.timeout.connect(self.setOnAnimation)
        
def create_character(name: str):
    
    name = name.lower() # lowercase to avoid compiling issues      
    if(name not in characters_names):
         
        characters_names.append(name) # Add to character list
        #print(name)
        play_animation_menu.setDisabled(False) # Activate the animation menu
        kick_menu.setDisabled(False) # Enable kicking the character
        match name:
            case 'usagi':
                play_animation_usagi_menu.setDisabled(False)
                
            case 'chiikawa':
                play_animation_chiikawa_menu.setDisabled(False)
            case 'hachiware':
                play_animation_hachiware_menu.setDisabled(False)
        kick_menu.addAction(name)
        muteall_button.setDisabled(False)
        #Instance the character
        character = Character(name, get_size_for_characters()) 
        #Preload all animations
        yaha_tray.showMessage(f'Loading {name}', 'This may take a while the first time', QSystemTrayIcon.MessageIcon.Information, 500)
        character.preload_allanimations()
        character.set_sprite(resource_path(f'assets/{name}/sprites/spawn.png'))

        #Play the spawn animation sound for the corresponding character
        character.play_animsound("spawn")
        #Add character to alive widgets list
        characters.append(character)
    else:
        yaha_tray.showMessage('Fail', 'Character already spawned!', QSystemTrayIcon.MessageIcon.Information, 500)


#Setting up variables

app = QApplication([])

#Setting the window and flags
yahawindow = QWidget()
yahawindow.setWindowFlag(Qt.WindowType.FramelessWindowHint) #  No title bar
yahawindow.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint) # Always on top
yahawindow.setWindowFlag(Qt.WindowType.Tool) # No taskbar icon
app.setQuitOnLastWindowClosed(False)

#Setting the window size
resize_to_current_screen()

#Attributes
yahawindow.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True) # Transparency: True

#Tray and icon
icon_path = resource_path('assets/usagi/icons/usagi.ico')
yaha_icon = QIcon(icon_path)
yaha_tray = QSystemTrayIcon(yaha_icon,parent=app)
yaha_tray.show()
tray_menu = QMenu()

##Context Menu actions
#Create character
character_list_menu = QMenu("Spawn Character")
character_list_menu.addAction("Usagi")
character_list_menu.addAction("Hachiware")
character_list_menu.addAction("Chiikawa")
character_list_menu.triggered.connect(lambda action: create_character(action.text()))
tray_menu.addMenu(character_list_menu)

#Play animation
play_animation_menu = QMenu("Play Animation")
play_animation_menu.setDisabled(True)

#Creating each menu for each character containing their animations
play_animation_usagi_menu = QMenu("Usagi")
play_animation_hachiware_menu = QMenu("Hachiware")
play_animation_chiikawa_menu = QMenu("Chiikawa")
play_animation_usagi_menu.setDisabled(True)
play_animation_hachiware_menu.setDisabled(True)
play_animation_chiikawa_menu.setDisabled(True)
#Adding the character's animation submenu to the play animation menu
play_animation_menu.addMenu(play_animation_usagi_menu)
play_animation_menu.addMenu(play_animation_chiikawa_menu)
play_animation_menu.addMenu(play_animation_hachiware_menu)

#Adding the play animation menu to the main menu
tray_menu.addMenu(play_animation_menu)


#Say hi
hi_action = tray_menu.addAction("Say hi!")
hi_action.triggered.connect(say_hi_message)

#Kick out a character
kick_menu = QMenu("Kick")
kick_menu.triggered.connect(lambda action: kick_character(action))
kick_menu.setDisabled(True)
tray_menu.addMenu(kick_menu)

#Mute and mute all sounds
muteall_button = QAction("Mute All")
muteall_flag : bool = False
muteall_button.setDisabled(True)
tray_menu.addAction(muteall_button)
muteall_button.triggered.connect(lambda: mute_character('all'))




#Quit - Must always be last 
exit_action = tray_menu.addAction("Exit")
exit_action.triggered.connect(close_app)


#Set the menu to the tray
yaha_tray.setContextMenu(tray_menu)
yahawindow.show()

#Defining each animation and each character
totalanimations : dict[str, list[str]] = {}
allcharacters = ["usagi", "hachiware", "chiikawa"]
#Declaring variables for future use and keeping them alive from garbage collection
sound = QSoundEffect()
characters = [] # List to hold character instances
characters_names = [] # List to hold current alive characters

#MENU FUNCTIONS
def mute_character(name: str):
    global muteall_flag
    muteall_flag = not muteall_flag
    if(name =='all'):
        for character in characters:
            if(character != None):
                character.mute(muteall_flag)
    
def kick_character(action: QAction):
    charactername = action.text()
    characters_names.remove(charactername)
    index = 0
    match charactername:
            case 'usagi':
                play_animation_usagi_menu.setDisabled(True)
            case 'chiikawa':
                play_animation_chiikawa_menu.setDisabled(True)
            case 'hachiware':
                play_animation_hachiware_menu.setDisabled(True)
    for target in characters: # For every character in alive characters list
        if(target != None):
            if(target.getName() == charactername): 
                characters.remove(target)
                target.deleteLater()
                del target
                break
        index+=1
    kick_menu.removeAction(action)
    if(not kick_menu.actions()): #iF THERE ARENT ANY ACTIONS, THERE ARENT ANY CHARACTERS ALIVE
        kick_menu.setDisabled(True) 
        play_animation_menu.setDisabled(True)
        muteall_button.setDisabled(True)
def setup_all_menus():
    global muteall_flag
    muteall_flag = False
    if(not totalanimations):
        
        for character in allcharacters:
            character_animations = []
            dir = Path(resource_path(f'assets/{character}/animations'))
            if(Path.exists(dir)):
                for folder_name in dir.iterdir():
                    print(folder_name)
                    folder_name = folder_name.name
                    print(folder_name)
                    if(character == "usagi"):
                        play_animation_usagi_menu.addAction(folder_name)
                        if(character not in characters):
                            play_animation_usagi_menu.setDisabled(True)
                    if(character == "chiikawa"):
                        play_animation_chiikawa_menu.addAction(folder_name)
                        if(character not in characters):
                            play_animation_chiikawa_menu.setDisabled(True)
                    if(character == "hachiware"):
                        play_animation_hachiware_menu.addAction(folder_name)
                        if(character not in characters):
                            play_animation_hachiware_menu.setDisabled(True)
                    character_animations.append(folder_name)
            totalanimations[character] = character_animations
                    
        play_animation_menu.triggered.connect(lambda action: start_anim_frommenu(action))
    print(totalanimations["usagi"])
def start_anim_frommenu(action: QAction):
    animname = action.text() # Get the animation name from the action
    charactername = action.parent().title().lower() # Get the character name from the menu
    for target in characters: # For every character in alive characters list
        if(target != None):
            if(target.getName() == charactername): 
                targetcharacter = target
                break
    targetcharacter.start_anim(animname)             
 
#Start event loop
setup_all_menus()


#Let the user know that the app has been initialized
yaha_tray.showMessage('Una!','App started, check your Windows Tray and right click it to start!', yaha_icon, 500)
app.exec()


