# whoo!

import math, random

# Gravitational constant (m^3kg^-1s^-2)
GravConstant = 6.67428e-11

# Astronomical unit (m)
AU = 149.6e9

class Body(object):
    pass

class Collection(object):
    # Clusters, associations, asteroid fields/belts, rings, etc.
    pass

class Cloud(object):
    pass

class Star(object):
    """
    A Star: a massive, luminous sphere of plasma. Currently only modeled in the
    main sequence, when luminosity is sustained by thermonuclear fusion.
    All stellar properties are determined by two parameters: the star's mass and
    age.
    """
    SolarMass = 1.99e+30 # kg
    SolarMainSeqLength = 10.0 # gigayears
    SolarRadius = 6.96e+8 # meters
    SolarLuminosity = 3.9e+26 # Watts
    SolarTemp = 5796.0 # Kelvin

    def __init__(self, mass, age):
        self.mass = mass # solar masses
        self.age = age # gigayears

        self.update()

    def update(self):
        """
        Call this after changing the mass or age of this Star to update all
        dependent quantities/properties. 
        """
        # length (gigayears) of main sequence
        self.mainSeqLength = Star.SolarMainSeqLength * \
                (1.0 / self.mass)**2.5

        if self.age > self.mainSeqLength:
            raise NotImplemented("Post main sequence stars not implemented.")
        self.sequence = "main"

        # luminosity (solar luminosities)
        self.luminosity = self.mass ** 3.9

        # absolute magnitude
        self.absoluteMag = 4.8 - 2.5*math.log(self.luminosity)

        # radius (solar radii)
        self.radius = self.luminosity ** 0.233

        # surface temp (K)
        self.surfaceTemp = Star.SolarTemp * (self.mass ** 0.505)

        # gravitational acceleration at surface (m/s/s)
        self.surfaceGravity = GravConstant * self.mass*Star.SolarMass / \
                (self.radius * Star.SolarRadius)**2

    def gravityAt(self, meters):
        """
        Returns the acceleration due to gravity in meters per second per
        second at the given distance in meters from the surface of the this
        Star.
        """
        return GravConstant * (self.mass * Star.SolarMass) / \
                (self.radius * Star.SolarRadius + meters)**2

    def angularDiameterAt(self, meters):
        """
        Returns the angular diameter in degrees of this Star when viewed at
        the given distance in meters from its surface.
        """
        rads = 2. * math.atan(0.5 * (2*self.radius*Star.SolarRadius) / meters)
        return math.degrees(rads)

    def orbitalPeriodAt(self, meters):
        """
        Returns the orbital period in Earth years of a circular orbit at the
        given distance in meters from the surface of this Star.
        """
        au = meters / AU
        return math.sqrt(au**3 / self.mass)

    def apparentMag(self, meters):
        """
        Returns the apparent magnitude of this Star when viewed from the given
        distance in meters.
        """
        au = meters / AU
        #return self.absoluteMag + 5 * math.log(meters/1000.) - 72.447
        #return self.absoluteMag - 5*math.log(((meters/1000.)/308.6)*1e15)
        return -26.73 - 2.5*math.log10(self.luminosity / au**2)

def randomStarMass():
    """
    Returns a random stellar mass drawn from a somewhat realistic distribution.
    Mass = -ln(1.0-x)/ln(1.35), where x is a number drawn uniformly at random
    from the interval [0,1).
    """
    return -math.log(1.0-random.random())/math.log(1.35)
