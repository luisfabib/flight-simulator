import contextlib
with contextlib.redirect_stdout(None):
    import pygame
import os
from pygame.locals import *
from math import cos, sin , exp, radians, sqrt, asin, degrees, ceil
from random import randint

# Initialize PyGame
pygame.init()

# Default screen size
info = pygame.display.Info()
W = info.current_w/2
H = info.current_h*2/3

# Set frames-by-second and simulation resolution 
FPS = 60

# Configure the ground and runway
GROUND_HEIGHT = 2 # m
AIRPORTS = [0,8000,40000,60000,80000,100000,120000] # m
RUNWAY_HEIGHT = 5 # m
RUNWAY_LENGTH = 2200 # m
MARKINGS_LENGTH = 50 # m
CITY_EXTENSION = 25 # m
screen = pygame.display.set_mode((W,H), pygame.RESIZABLE)

pygame.display.set_caption('2D Flight simulator')

# Load and prepare background mountain sprites for parallax effect
bgs = []
bgsX = []
parallax_speed = [0.1,0.14,0.25,0.27,0.30,0.35,0.4,0.45,0.5,0.55,0.6,0.65,0.7,0.75,0.80,0.85]
bgYs = [1840, 1350, 1200, 780, 720, 400, 400, 240, 240, 240, 40,  190, 37, 0, 0,-20]
bgYs = [x/8 for x in bgYs]
vertical_scroll_factor = 0.15
for n in range(len(bgYs)-1,-1,-1):
    bg = pygame.image.load(os.path.join('assets', f'pixel_parallax_{n}.png')).convert_alpha()
    scale = 0.3
    bg = pygame.transform.scale(bg, (scale*bg.get_width(), scale*bg.get_height()))
    bg_copies = ceil(W/bg.get_width())
    bgs.append(bg)
    bgsX.append( [x*bg.get_width() for x in range(bg_copies+3)] )


# Load and prepare background city sprites for parallax effect
city_bgs = []
city_bgsX = []
city_parallax_speed = [0.9,0.95,1]
city_bgYs = [1,0,-1]
for n in range(3,0,-1):
    bg = pygame.image.load(os.path.join('assets', f'city_parallax_{n}.png')).convert_alpha()
    scale = 1
    bg = pygame.transform.scale(bg, (scale*bg.get_width(), scale*bg.get_height()))
    bg_copies = ceil(W/bg.get_width())
    city_bgs.append(bg)
    city_bgsX.append( [x*bg.get_width() for x in range(bg_copies+3)] )

# Load environmental sprites
cloud_image = pygame.image.load(os.path.join('assets', f'cloud1.png')).convert_alpha()
airport_image_og = pygame.image.load(os.path.join('assets', f'airport.png')).convert_alpha()
crash_image_og = pygame.image.load(os.path.join('assets', f'crash.png')).convert_alpha()

# Load the plane sprites
plane_sprite_og = pygame.image.load(os.path.join('assets', 'plane_gear_down.png'))
plane_sprite_og = pygame.transform.flip(plane_sprite_og,True,False)
plane2_sprite_og = pygame.image.load(os.path.join('assets', 'plane_gear_up.png'))
plane2_sprite_og = pygame.transform.flip(plane2_sprite_og,True,False)

# Color definitions
background_sky_color = (87, 184, 250)
white =  (255,255,255)
grey = (92,94,93)
yellow = (239,166,35)
green = (0,154,23)
brown = (128, 96, 67)

#=========================================================================================================
# Natural constants 
speed_sound = 340.3 # m/s
gravitation = 9.81 # m/s^2
air_density_sea_level = 1.225 # kg/m^3

class Plane(object):
    """
    Represents an aircraft in a flight simulator.

    Attributes:
        x : int
            x-coordinate in pixels of the top-left corner of the bounding box of the Plane.
        y : int
            y-coordinate in pixels of the top-left corner of the bounding box of the Plane.
        width : int
            Width in pixels of the bounding box of the Plane.
        height : int
            Height in pixels of the bounding box of the Plane.
        vertical_speed : float
            Vertical speed of the Plane in m/s.
        horizontal_speed : float
            Horizontal speed of the Plane in m/s.ddd
        altitude : float
            Altitude of the Plane in m.
        position : float
            Position of the Plane in m.
        slope : float
            Slope of the Plane in deg.
        angle_of_attack : float 
            Angle of attack of the Plane in deg.
        pitch : float 
            Pitch of the Plane in deg.
        thrust_level : float  
            Thrust level of the Plane.
        gear_down : bool 
            Indicates whether the gear of the Plane is down.
        flap_deflection : float 
            Flap deflection angle of the Plane in deg.
        mass_aircraft : float 
            Mass of the Plane in kg.
        mass_fuel : float 
            Mass of the Plane's fuel in kg.
        thrust_specific_fuel_consumption : float
            Thrust-specific fuel consumption coefficient in kg/(N*s).
        length : float
            Length of the Plane in m.
        front_surface : float
            Front surface of the Plane in m^2.
        wings_surface : float
            Wings surface of the Plane in m^2.
        engines :int
            Number of engines of the Plane.
        engine_thrust : float 
            Thrust of the Plane's engines in N.
        max_speed : float
            Maximum speed of the Plane in m/s.
        critic_match : float
            Critical mach number of the Plane.
        friction_coefficient : float
            Friction coefficient of the Plane.
        critical_crash_energy :float
            Critical crash energy of the Plane in J.
        tail_strike_pitch : float
            Tail strike pitch of the Plane in deg.
        gear_down_sprite :str
            Gear-down plane sprite.
        gear_up_sprite : str
            Gear-up plane sprite.
        crash_sprite : str
            Crashed plane sprite.
        crashed :bool
            Indicates whether the Plane has crashed.
    """
    def __init__(self, width, height):
        self.x = W/4
        self.y = 0
        self.width = width
        self.height = height

        # Aircraft positioning parameters
        self.vertical_speed = 0 # m/s
        self.horizontal_speed = 0 # m/s
        self.altitude = 0 # m
        self.position = 0 # m
        self.slope = 0 # deg
        self.angle_of_attack = 0 # deg

        # Aircraft control properties
        self.pitch = 0 # deg
        self.thrust_level = 0
        self.gear_down = True
        self.flap_deflection = 0  # deg
        self.spoilers = False 
        self.brakes = False 

        # Aircraft technical specifications
        # (default values from Airbus A320-232 technical data sheets)
        self.height = 11.76 # m
        self.length = 37.57 # m
        self.front_surface = 12.6 # m^2
        self.wings_surface = 122.6 # m^2
        self.engines = 2 
        self.engine_thrust = 140000 # N
        self.max_speed = 0.92*speed_sound # m/s
        self.critic_match = 0.78 # match
        self.friction_coefficient = 0.02 
        self.critical_crash_energy = 1323000 # J
        self.tail_strike_pitch = 11.5 # deg
        self.mass_aircraft = 57230 # kg
        self.mass_fuel = 11608 #kg
        self.thrust_specific_fuel_consumption = 0.000018 # kg/(N*s)
        self.braking_deceleration = 1.70 # m/s^2 

        # Visual properties
        self.gear_down_sprite = plane_sprite_og
        self.gear_up_sprite = plane2_sprite_og
        self.crash_sprite = crash_image_og
        self.crashed = False 

    #------------------------------------------------------------
        """Total mass of the aircraft
        Returns:
            float: Mass in kg
        """
    def mass(self):
        return self.mass_aircraft+self.mass_fuel
    #------------------------------------------------------------
    def air_rarefaction_factor(self):
        """Approximate air density reduction factor due to altitude

        Returns:
            float: Air rarefaction factor
        """
        return exp(-9.33*10**(-5)*self.altitude)
    #------------------------------------------------------------
    def air_density(self):
        """Air density around the aircraft's altitude

        Returns:
            float: Air density in kg/m^3
        """
        return air_density_sea_level*self.air_rarefaction_factor()
    #------------------------------------------------------------
    def match(self,speed):
        """Convert speed in m/s to Match level.

        Args:
            speed (float): Speed in m/s

        Returns:
            float: Speed in Match
        """
        return speed/speed_sound 
    #------------------------------------------------------------
    def collinear_speed(self):
        """Speed collinear with the aircraft's direction

        Returns:
            float: Collinear speed in m/s
        """
        return sqrt(self.horizontal_speed**2 + self.vertical_speed**2) 
    #------------------------------------------------------------
    def drag_coefficient(self):
        """
        Drag coefficient of the aircraft.

        The function accounts for the effects of approaching the speed of sound on the drag coefficient. 
        The minimal drag coefficient is approximated approximated as a third order polynomial function 
        of the flap deflection angle based on Fig.12 of Ref.1.

        Returns:
            float: Drag coefficient

        References:
            [1] Hussein et al., "Aerodynamic study of slotted flap for NACA 24012 airfoil by dynamic mesh techniques and visualization flow"
             Journal of Thermal Engineering 2021, 7(2), 230-239
        """
        # Use angle of attack in degrees
        angle_of_attack = self.angle_of_attack
        # Minimal drag coefficient 
        # (approximated as third order polynomial function of the flap deflection angle based on Fig.12 of DOI:10.18186/thermal.871989)
        Cdrag_min = 0.012*(7.867 - 0.377*self.flap_deflection + 0.046*self.flap_deflection**2 - 6.88e-04*self.flap_deflection**3)
        # Compute drag coefficient at different angles of attack
        Cdrag = Cdrag_min + (0.02*angle_of_attack)**2 # N
        # Account for turbulence when approaching Match speeds
        match_speed = self.match(self.collinear_speed()) 
        if match_speed < self.critic_match:
            return Cdrag/sqrt(1 - (match_speed**2))
        else:
            return Cdrag*15*(match_speed - self.critic_match) + Cdrag/sqrt(1 - (self.critic_match ** 2))
    #------------------------------------------------------------
    def lift_coefficient(self):
        """
        Lift coefficient of the aircraft.

        The function accounts for the effects of approaching the speed of sound on the lift coefficient. 
        The maximal lift coefficient is approximated approximated as a third order polynomial function 
        of the flap deflection angle based on Fig.20 of Ref.1.

        Returns:
            float: Lift coefficient

        References:
            [1] Obeid et al., "RANS Simulations of Aerodynamic Performance of NACA 0015 Flapped Airfoil"
                Fluids 2017, 2(1), 2
        """        
        # Use angle of attack in degrees
        angle_of_attack = self.angle_of_attack
        # Maximal lift coefficient
        # (approximated as third order polynomial function of the flap deflection angle based on Fig.20 of DOI:10.3390/fluids2010002)
        Clift_max = 0.317*(3.702 + 0.159*self.flap_deflection - 3.17e-3*self.flap_deflection**2 + (2.15e-05)*self.flap_deflection**3) - 0.2
        if abs(angle_of_attack) < 15:
            Clift =  abs(angle_of_attack)/15*Clift_max
        elif abs(angle_of_attack) < 20:
            Clift =  (1 - abs(angle_of_attack - 15)/15)*Clift_max
        else:
            Clift =  0
        # Account for turbulences when approaching Match speeds
        match_speed = self.match(self.horizontal_speed) 
        M_d = self.critic_match + (1 - self.critic_match)/4
        if match_speed <= self.critic_match:
            return Clift
        elif match_speed <= M_d:
            return Clift + 0.1*(match_speed - self.critic_match)
        else:
            return Clift + 0.1*(M_d - self.critic_match) - 0.8*(match_speed - M_d)
    #------------------------------------------------------------
    def wheels_drag(self):
        """Drag factor due to the aircraft's gear.

        Assumes that while gear is down, 25% of the drag originates from the gear [1]. 

        Returns:
            float: Gear drag factor
        
        References: 
            [1] Brandt et al., "The Effects of Wheel Design on the Aerodynamic Drag of Passenger Vehicles," 
                SAE Int. J. Adv. & Curr. Prac. in Mobility 1(3):1279-1299, 2019,
        """
        return 1.333 if self.gear_down else 1
    #------------------------------------------------------------
    def drag(self):
        """Drag force acting on the airplane due to the air flowing around the wings.

        Returns:
            float: Drag force in N
        """
        # Use angle of attack in radians
        angle_of_attack = radians(self.angle_of_attack)

        # Compute surface area experiencing drag
        drag_surface = self.front_surface*cos(angle_of_attack) +  self.wings_surface*sin(angle_of_attack)
        
        # Account for decrease of lift if spoilers are deployed
        spoilers_drag_factor = 1
        if self.spoilers:
            spoilers_drag_factor = 2.5

        # Compute drag
        return self.wheels_drag()*1/2*self.air_density()*self.drag_coefficient()*drag_surface*self.collinear_speed()**2*spoilers_drag_factor
    #------------------------------------------------------------
    def lift(self):
        """Lift force acting on the airplane due to the air flowing around the wings.

        Returns:
            float: Lift force in N
        """
        # Use angle of attack in radians
        angle_of_attack = radians(self.angle_of_attack)

        # Compute surface area experiencing drag
        lift_surface = self.front_surface*sin(angle_of_attack) +  self.wings_surface*cos(angle_of_attack)
        
        # Account for decrease of lift if spoilers are deployed
        spoilers_lift_factor = 1
        if self.spoilers:
            spoilers_lift_factor = 0.5

        # Compute lift
        return 1/2*self.air_density()*self.lift_coefficient()*lift_surface*self.horizontal_speed**2*spoilers_lift_factor
    #------------------------------------------------------------
    def thrust(self):
        """Thrust force acting on the airplane due to the engines.

        Returns:
            float: Thrust force in N
        """
        return self.thrust_level*self.engines*self.engine_thrust*self.air_rarefaction_factor()
    #------------------------------------------------------------
    def weight(self):
        """Weight force acting on the airplane due to gravity.

        Returns:
            float: Weight force in N
        """
        return self.mass()*gravitation # kg*m/s^2
    #------------------------------------------------------------
    def friction_wheels(self):
        """Friction force acting on the airplane while the gear touches the ground.

        Only accounts for dynamic friction (not static).

        Returns:
            float: Weight force in N
        """
        if self.gear_down and self.altitude==0 and self.horizontal_speed>0: 
            return self.friction_coefficient*self.weight()
        else: 
            return 0
    #------------------------------------------------------------
    def horizontal_force(self):
        """Total horizontal force being subjected onto the airplane based on Newton's second law.

        Returns:
            float: Net horizontal force in N 
        """
        # Use angles in radians 
        pitch = radians(self.pitch)
        slope = radians(self.slope)
        # Apply Newton's second law to the horizontal force components
        return cos(pitch)*self.thrust() - cos(slope)*self.drag() - sin(pitch)*self.lift() - self.friction_wheels()
    #------------------------------------------------------------
    def vertical_force(self):
        """Total vertical force being subjected onto the airplane based on Newton's second law.

        Returns:
            float: Net vertical force in N 
        """
        # Use angles in radians 
        pitch = radians(self.pitch)
        slope = radians(self.slope)
        # Apply Newton's second law to the vertical force components
        return sin(pitch)*self.thrust() - sin(slope)*self.drag() + cos(pitch)*self.lift() - self.weight()
    #------------------------------------------------------------
    def update(self, screen):
        """
        Update the state of the aircraft. 
        """        
        # Burn fuel
        fuel_consumption = self.thrust_specific_fuel_consumption*self.thrust()*Δt
        self.mass_fuel -= fuel_consumption
        # If there is not fuel left, there is not thrust
        if self.mass_fuel<=0:
            self.mass_fuel = 0
            self.thrust_level = 0

        # If the plane is moving, update the slope angle
        if self.collinear_speed()>0:
            self.slope = degrees(asin(self.vertical_speed/self.collinear_speed()))
        else:
            self.slope = 0
        # Update the angle of attack
        self.angle_of_attack = self.pitch - self.slope

        # Compute the current forces acting on the plane
        horizontal_acceleration = self.horizontal_force()/self.mass()
        vertical_acceleration = self.vertical_force()/self.mass()

        if self.brakes and self.altitude==0 and self.horizontal_speed>0:
            horizontal_acceleration = horizontal_acceleration - self.braking_deceleration

        if self.brakes and self.altitude==0 and self.horizontal_speed<0:
            horizontal_acceleration = horizontal_acceleration + self.braking_deceleration

        # Compute the acceleration vectors
        self.horizontal_speed += horizontal_acceleration*Δt
        self.vertical_speed += vertical_acceleration*Δt

        # Update the position of plane
        self.position += self.horizontal_speed*Δt # m
        self.altitude += self.vertical_speed*Δt # m

        # If the plane is on the ground, it cannot descend or accelerate further down 
        if self.altitude<0 and self.vertical_speed<0:
            kinetic_energy = 1/2*self.mass()*self.vertical_speed**2
            if kinetic_energy>self.critical_crash_energy:
                self.crashed = True
            self.altitude = 0
            self.vertical_speed = 0 
        
        # If the plane exceeds the maximal speed it breaks due to air forces
        if self.altitude==0 and self.pitch>self.tail_strike_pitch:
            self.crashed = True

        # If the plane exceeds the maximal speed it breaks due to air forces
        if self.collinear_speed()>self.max_speed:
            self.crashed = True

        # If the plane if on the ground, it cannot physically pitch nose down
        if self.altitude==0 and self.pitch<0:
            self.pitch=0

       # If the plane if on the ground, it cannot physically pitch more than 15deg without the tail touching the ground
        if self.altitude==0 and self.pitch>self.tail_strike_pitch:
            self.pitch=self.tail_strike_pitch        

        self.y = altitude_to_pixel(self.altitude*vertical_scroll_factor)
        if self.y<static_altitude_point:
            self.y = static_altitude_point

        # Prepare the plane's sprite 
        if self.gear_down:         
            original_sprite = self.gear_down_sprite # Plane with wheels
        else: 
            original_sprite = self.gear_up_sprite # Plane without wheels

        if self.crashed:
            draw_sprite(self.crash_sprite,self.position,0)
            return 

        # Compute the pivot point (i.e. back wheels of the plane)
        pivot_wheels_pos = (self.x+plane_size[0]-plane_size[0]*2.8/5,  self.y+plane_size[1]-plane_size[1]/5)

        # Perform rotation of the plane about the back wheels
        image_rect = original_sprite.get_rect(topleft = (self.x, self.y))

        # Compute a vector from the pivot to the center of the sprite
        self.rect = original_sprite.get_rect(center=(self.x + plane_size[0]/2, self.y + plane_size[1]/2))

        vector_center_to_pivot = pygame.math.Vector2(pivot_wheels_pos) - image_rect.center
        rotated_offset = vector_center_to_pivot.rotate(-self.pitch)
        rotated_image_center = (pivot_wheels_pos[0] - rotated_offset.x, pivot_wheels_pos[1] - rotated_offset.y)
        rotated_sprite = pygame.transform.rotozoom(original_sprite, self.pitch, 1)
        rotated_image_rect = rotated_sprite.get_rect(center = rotated_image_center)
        self.rect = rotated_sprite.get_rect(center=self.rect.center)

        screen.blit(rotated_sprite, rotated_image_rect)
#=========================================================================================================


#=========================================================================================================
def endScreen(message, gameover):
    """
    Displays either a 'Game Over' or 'Success' message on the screen depending on the outcome of the game.
    The screen displays the message until the user closes the window or clicks on the screen.

    Arguments:
    message : string
        The reason for the game ending
    gameover :  boolean
        Determines if the game has ended with success or failure
    """
    global run

    while run:
        pygame.time.delay(2)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
                pygame.quit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                run = False
            
        largeFont = pygame.font.SysFont('consolas', 80)
        mediumFont = pygame.font.SysFont('consolas', 30)
        if gameover:
            GameOver = largeFont.render('Game Over',1,white)
            Reason = mediumFont.render(message,1,white)
        else:
            GameOver = largeFont.render('Success',1,white)
            Reason = mediumFont.render(message,1,white)

        screen.blit(GameOver, (W/2 - GameOver.get_width()/2, H/2))
        screen.blit(Reason, (W/2 - Reason.get_width()/2, H/2-50))

        pygame.display.update()
#=========================================================================================================

#=========================================================================================================
def draw_surface(x, y, length, height, color, transparent=False):
    """Draws a surface of given color on the screen

    Arguments:
    x : float
        Position of the surface in meters
    y : float
        Altitude of the surface in meters
    length : float
        Length of the surface in meters
    height : float 
        Height of the surface in meters
    color : tuple or list 
        Color of the surface in RGB format
    """
    # If surface is out of screen bounds, do not render
    if x>position_range_screen[1] or (x+length)<position_range_screen[0] or y>altitude_range_screen[1] or (y+height)<altitude_range_screen[0]:
        return 
        
    # Compute positions and sizes of surface
    posX = (x - position_range_screen[0])/pixel_to_length # pixels
    posY = H - (y - altitude_range_screen[0])/pixel_to_height # pixels
    length = length/pixel_to_length
    height = height/pixel_to_height
    
    # Draw the surface at ground level
    if transparent:
        surface = pygame.Surface((length,height))  
        surface.set_alpha(150)               
        surface.fill(color)           
        screen.blit(surface, (posX,posY))
    else:
        pygame.draw.rect(screen, color, (posX, posY, length, height))
#=========================================================================================================

#=========================================================================================================
def draw_sprite(sprite, x, y):
    """Draws a sprite on the screen

    Arguments:
    sprite : PyGame.Image
        The sprite to draw
    x : float 
        Position of the sprite in meters
    y : Altitude of the sprite in meters
    """
    # If sprite is out of screen bounds, do not render
    if x>position_range_screen[1] or (x+sprite.get_width())<position_range_screen[0] or y>altitude_range_screen[1] or (y+sprite.get_height())<altitude_range_screen[0]:
        return 

    # Compute positions and sizes of surface
    posX = (x - position_range_screen[0])/pixel_to_length # pixels
    posY = H - (y - altitude_range_screen[0])/pixel_to_height -sprite.get_height() # pixels

    # Draw the surface at ground level
    screen.blit(sprite, (posX, posY))
#=========================================================================================================


#=========================================================================================================
def landed_on_airport(plane):
    """Determines if a plane has landed on an airport

    Arguments:
    plane -- The plane object to check
    """
    for n,airport_start in enumerate(AIRPORTS):
        if abs(plane.position)>=airport_start and abs(plane.position)<=(airport_start+RUNWAY_LENGTH):
            return n+1
    return False
#=========================================================================================================


#=========================================================================================================
def draw_background(sprite, parallax_X, altitude):
    """Draws a background sprite on the screen

    Arguments:
    sprite : PyGame.Image
        The background sprite to draw
    parallax_X : float
        X coordinate of the background sprite in pixels
    altitude : float
        Altitude of the background sprite in meters
    """
    # Compute position
    posY = H - (altitude - vertical_scroll_factor*altitude_range_screen[0])/pixel_to_height -sprite.get_height() # pixels

    # Draw the surface at ground level
    screen.blit(sprite, (parallax_X, posY))
#=========================================================================================================


#=========================================================================================================
def updateScreen():
    """
    Updates the screen at every frame
    """
    # Draw solid colored background (required)
    screen.fill(background_sky_color)

    # Draw parallax background
    for bg,bgX,bgY in zip(bgs,bgsX,bgYs):
        for x in bgX:
            draw_background(bg, x, bgY)
    
    # Draw parallax city background
    for bg,bgX,bgY in zip(city_bgs,city_bgsX,city_bgYs):
        for x in bgX:
            draw_background(bg, x, bgY)

    # Draw airports
    for n,airport_position in enumerate(AIRPORTS):
        # Draw the airport terminal 
        if n>0:
            draw_sprite(airport_image, x=airport_position+RUNWAY_LENGTH-300, y=RUNWAY_HEIGHT*3/4)
        else:
            draw_sprite(airport_image, x=airport_position+100, y=RUNWAY_HEIGHT*3/4)
        # Draw the runway
        draw_surface(x=airport_position-CITY_EXTENSION, y=RUNWAY_HEIGHT*3/4, length=RUNWAY_LENGTH+20+2*CITY_EXTENSION, height=2*RUNWAY_HEIGHT, color=(210,210,210))
        draw_surface(x=airport_position, y=RUNWAY_HEIGHT*3/4, length=RUNWAY_LENGTH+20, height=2*RUNWAY_HEIGHT, color=(194,194,194))
        draw_surface(x=airport_position, y=RUNWAY_HEIGHT/2, length=RUNWAY_LENGTH, height=2*RUNWAY_HEIGHT, color=grey)
        for n in range(round(RUNWAY_LENGTH/15/2)):
            draw_surface(x=airport_position + 2*n*15 + 2, y=0.25, length=15, height=0.5, color=yellow)
        for n in range(5):
            draw_surface(x=airport_position+2, y=RUNWAY_HEIGHT/2 - 2*n - 0.25, length=MARKINGS_LENGTH/2, height=0.5, color=yellow)
            draw_surface(x=airport_position+RUNWAY_LENGTH-MARKINGS_LENGTH, y=RUNWAY_HEIGHT/2 - 2*n - 0.25, length=MARKINGS_LENGTH/2 - 2, height=0.5, color=yellow)

    # Draw the plane's shadow
    if not plane.crashed:
        shadow_start = 0.05*plane.length + position_range_screen[0] + (plane.x/W)*(position_range_screen[1] - position_range_screen[0])
        shadow_length = 0.9*plane.length*cos(radians(plane.pitch))
        draw_surface(x=shadow_start, y=0.15, length=shadow_length, height=0.3, color=(20,20,20), transparent=True)

        
    # Draw clouds
    for cloud in clouds:
        draw_sprite(cloud['image'], x=cloud['position'], y=cloud['altitude'])
        
    # Update flight status and update the sprite
    plane.update(screen)

    # Display game over if the plane has crashed
    if plane.crashed:
        endScreen('The aircraft crashed', gameover=True)
    elif plane.altitude==0 and not landed_on_airport(plane):
         endScreen('The aircraft landed outside of a runway', gameover=True)

    # Font renderers
    largeFont = pygame.font.SysFont('consolas', 17)

    if plane.slope<0:
        touchdown_prediction  = cos(plane.slope)*plane.collinear_speed()*(-plane.altitude/sin(plane.slope)/plane.collinear_speed())
        touchdown_prediction = f'{touchdown_prediction:.0f}'
    else: 
        touchdown_prediction = '-'
    nearest_runway_distance = min([airport-plane.position for airport in AIRPORTS if (airport-plane.position)>0])
    gear  = 'Down' if plane.gear_down else 'Up'
    spoilers  = 'Deployed' if plane.spoilers else 'Retracted'

    # Add plane flight control indicators
    flight_indicators = []
    flight_indicators.append(largeFont.render(f'Thrust: {plane.thrust_level*100:.0f} %', 1, white))
    flight_indicators.append(largeFont.render(f'Flaps: {plane.flap_deflection:.0f}°', 1, white))
    flight_indicators.append(largeFont.render(f'Pitch: {plane.pitch:.1f}°', 1, white))
    flight_indicators.append(largeFont.render(f'H.Speed: {plane.horizontal_speed:.1f} m/s', 1, white))
    flight_indicators.append(largeFont.render(f'V.Speed: {plane.vertical_speed:.1f} m/s', 1, white))
    flight_indicators.append(largeFont.render(f'AOA: {plane.angle_of_attack:.1f}°', 1, white))
    flight_indicators.append(largeFont.render(f'Altitude: {plane.altitude:.1f} m', 1, white))
    flight_indicators.append(largeFont.render(f'Position: {plane.position:.1f} m', 1, white))
    flight_indicators.append(largeFont.render(f'Fuel: {plane.mass_fuel:.0f} kg', 1, white))
    flight_indicators.append(largeFont.render(f'Spoilers: {spoilers}', 1, white))
    flight_indicators.append(largeFont.render(f'Gear: {gear}', 1, white))
    flight_indicators.append(largeFont.render(f'Next runway: {nearest_runway_distance:.0f} m', 1, white))
    #flight_indicators.append(largeFont.render(f'Touchdown: {touchdown_prediction} m', 1, white))

    # Grey transparent background for indicators
    panel_width = max([indicator.get_width() for indicator in flight_indicators])
    s = pygame.Surface((0.02*W+panel_width,30+len(flight_indicators)*25))  
    s.set_alpha(150)               
    s.fill(grey)           
    screen.blit(s, (0,0))
    for n,indicator in enumerate(flight_indicators):
        screen.blit(indicator, (0.01*W, 15+n*25))

    # Add objectives
    panel_width = max([largeFont.size(objective)[0] for objective in objectives])
    screen.blit(largeFont.render('Objectives:', 1, white), (W - panel_width - 100, 15))
    for n,(objective,condition) in enumerate(zip(objectives,conditions)):
        objective_display = largeFont.render(objective, 1, white)
        width = 2
        if condition(plane):
            width = 0
            conditions[n] = lambda _: True
        pygame.draw.rect(screen, white, (W-panel_width-80, 45+n*20, 15, 15), width=width)
        screen.blit(objective_display, (W-panel_width-50, 45+n*20))

    # Check if all objectives have been fulfilled, if so end the game
    if all([condition(plane) for condition in conditions]):
        endScreen('The aircraft has successfully landed', gameover=False)

    # Update the screen with new frame
    pygame.display.update()
#=========================================================================================================

#=========================================================================================================
def altitude_to_pixel(altitude):
    """Convert coordinates into pygame coordinates (lower-left => top left)."""
    scale = (altitude)/(H*pixel_to_height)
    return takeoff_height- scale*H 
#=========================================================================================================

#=========================================================================================================
def screen_configuration(W,H):
    """
    This function sets up the screen configuration for the simulation at a given resolution.

    Parameters:
    W : int
        Width of the screen in pixels
    H : int 
        Height of the screen in pixels
    """
    global plane, plane_size, airport_image
    global static_altitude_point, takeoff_height 
    global position_range_screen, altitude_range_screen, pixel_to_length, pixel_to_height, takeoff_height
    # Define screen height at which to make sprite static
    static_altitude_point = H/3 

    # Determine the plane's sprite size
    ZOOM_OUT = 2.8
    plane_default_size = plane_sprite_og.get_size() 
    plane_size = [x/ZOOM_OUT for x in plane_default_size]

    if plane is None:
        # Construct the aircraft
        plane = Plane(*plane_default_size)

    # Rescale the sprites
    plane.gear_down_sprite = pygame.transform.scale(plane_sprite_og, plane_size)
    plane.gear_up_sprite = pygame.transform.scale(plane2_sprite_og, plane_size)
    plane.crash_sprite = pygame.transform.scale(crash_image_og, (2*plane_size[0],plane_size[0]))
    airport_image = pygame.transform.scale(airport_image_og, [x/9 for x in airport_image_og.get_size()])

    # Map the physically-realistic distances in pixels
    pixel_to_length = plane.length/plane_size[0]
    pixel_to_height = plane.height/plane_size[1]

    # Map the range of distances/altitudes on the current screen
    position_range_screen = (0, W*pixel_to_length)
    altitude_range_screen = (-GROUND_HEIGHT, H*pixel_to_height)

    # Determine the start position of the plane's sprite
    takeoff_height = H - GROUND_HEIGHT/pixel_to_height - 4/5*plane_size[1]
    if plane is None:
        plane.x = W
        plane.y = takeoff_height
#=========================================================================================================


# Start running the game
#------------------------------------------
run = True
plane = None
clock = pygame.time.Clock()

# Configure screen to current resolution
screen_configuration(W,H)

# Define the game's objectives
objectives,conditions = [],[]
objectives.append('Takeoff from the airport')
conditions.append(lambda plane: plane.altitude>40)
target_altitude = round(randint(1000,3000),-2)
objectives.append(f'Reach an altitude of {target_altitude} m')
conditions.append(lambda plane: plane.altitude>=target_altitude)
objectives.append('Land on an airport')
conditions.append(lambda plane: landed_on_airport(plane)>1 and abs(plane.horizontal_speed)<5)

pause = 0
clouds = []
bgY = 0
frame = 0
last_frame = 0
flap_delay = 0


# Main game loop
#------------------------------------------
while run:

    # Get simulation time step
    Δt = clock.tick(FPS)/1000
    frame += 1

    if (round(frame/FPS,1) % 1) == 0:
        N_new_clouds = randint(1,4)
        for n in range(N_new_clouds):
            cloud = {
                'position': randint(round(position_range_screen[1]), round(1.5*position_range_screen[1])),
                'altitude': randint(round(0.5*altitude_range_screen[1]), round(altitude_range_screen[1])),
                'image': pygame.transform.scale(cloud_image,[x*randint(1,4) for x in cloud_image.get_size()]),
                'speed': 1/randint(1,8)
            } 
            if cloud['altitude']>250:
                clouds.append(cloud)

    positional_change = plane.horizontal_speed*Δt
    position_range_screen = [x+positional_change for x in position_range_screen]

    clouds = [cloud for cloud in clouds if (cloud['position']+cloud['image'].get_width())>position_range_screen[0]]

    if plane.y<=static_altitude_point:
        altitude_change = plane.vertical_speed*Δt
        altitude_range_screen = [y+altitude_change for y in altitude_range_screen]
        bgY -= altitude_change/100

    for n,(bg,bgXs,speed) in enumerate(zip(bgs,bgsX,parallax_speed)):
        for m,bgX in enumerate(bgXs):
            bgX  -= speed*positional_change/pixel_to_length
            if bgX <= bg.get_width()*(m-2):
                bgX = (m)*bg.get_width() + 0*abs(m*bg.get_width() - abs(bgX))
            bgsX[n][m] = bgX


    close_to_airports = [plane.position>(airport-CITY_EXTENSION/2) and plane.position<(airport+RUNWAY_LENGTH+CITY_EXTENSION/2-city_bgs[0].get_width()) for airport in AIRPORTS]
    arriving_to_airports = [position_range_screen[1]>(airport-CITY_EXTENSION-100) and position_range_screen[1]<(airport-CITY_EXTENSION)  for airport in AIRPORTS]
    for n,(bg,bgXs,speed) in enumerate(zip(city_bgs,city_bgsX,city_parallax_speed)):
        for m,bgX in enumerate(bgXs):
            bgX -= speed*positional_change/pixel_to_length
            if any(close_to_airports):
                if bgX <= bg.get_width()*(m-2):
                    bgX = (m)*bg.get_width() + 0*abs(m*bg.get_width() - abs(bgX))
            if any(arriving_to_airports):
                bgX = W + m*bg.get_width()
            city_bgsX[n][m] = bgX


    # Event handler
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            # Exit the game and stop the execution
            pygame.quit()
            run = False

        elif event.type == pygame.VIDEORESIZE:
            # Get new screen size
            W, H = event.dict["size"]
            # Recreate screen object required for pygame version
            screen = pygame.display.set_mode((W, H), pygame.RESIZABLE)
            # Reconfigure screen to current resolution
            screen_configuration(W,H)

    # Check user input(s)
    keys = pygame.key.get_pressed()

    # Thrust control
    #------------------------------------------
    if keys[pygame.K_UP]:
        if plane.thrust_level<1:
            plane.thrust_level += 0.006

    if keys[pygame.K_DOWN]:
        # Usually, do not allow reverse thrust
        if plane.thrust_level>0:
            plane.thrust_level -= 0.006
        # If on the ground, allow thrust-reversal
        if plane.thrust_level<=0 and plane.altitude==0 and plane.thrust_level>-1:
            plane.thrust_level -= 0.006

    # Pitch control
    #------------------------------------------
    if keys[pygame.K_LEFT]:
        plane.pitch += 0.04

    if keys[pygame.K_RIGHT]:
        plane.pitch -= 0.04

    # Gear control
    #------------------------------------------
    if keys[pygame.K_w]:
        if abs(frame-last_frame)>15:
            if plane.gear_down and plane.altitude>0:
                plane.gear_down = False
            else: 
                plane.gear_down = True
            last_frame = frame

    # Spoilers control
    #------------------------------------------
    if keys[pygame.K_s]:
        plane.spoilers = True
    else: 
        plane.spoilers = False

    # Brakes control
    #------------------------------------------
    if keys[pygame.K_d]:
        plane.brakes = True
    else: 
        plane.brakes = False

    # Flaps control
    #------------------------------------------
    if keys[pygame.K_q]:
        if plane.flap_deflection<50:
            plane.flap_deflection += 0.08
    if keys[pygame.K_a]:
        if plane.flap_deflection>0:
            plane.flap_deflection -= 0.08
    
    # Refresh the display
    updateScreen()

pygame.quit()
