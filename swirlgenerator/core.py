# -------------------------------------------------------------------------------------------------------------------
#
# Main module for creating the requested swirl profile
# Also has functionality for comparing profiles
#
# -------------------------------------------------------------------------------------------------------------------

import numpy as np
from typing import Union
from configparser import ConfigParser

'''
Heavy use of numpy for fast matrix and vector operations
Matplotlib for doing visualisations
'''

# Fluid parameters
GAMMA = 1.4
kin_visc = 1.81e-5
density = 1.225         # ISA sea level condition - for incompressible

'''
For storing and convenient querying of information about the vortices which have been defined for the domain
A separate class is used since the domain could be more complex in previous versions - left as separate class rather than embedding into Input class for code clarity and future proofing
- Positive vortex strength is defined as anti-clockwise rotation
'''
class Vortices: 
    # Object constructor accepts lists also for convenience, then later converts to numpy arrays
    def __init__(self, model: int, centres: Union[list, np.ndarray], strengths: Union[list, np.ndarray],
                       radius: Union[list, np.ndarray], axialVel: float):

        self.numVortices    = len(strengths)

        self.model          = model         # Vortex type - which mathematical model to use for all the vortices in the domain

        # Make sure these are all numpy arrays not just lists
        self.centres        = (centres      if isinstance(centres,np.ndarray)   else np.array(centres))       # Vortex centre
        self.strengths      = (strengths    if isinstance(strengths,np.ndarray) else np.array(strengths))     # Vortex strength
        self.radius         = (radius       if isinstance(radius,np.ndarray)    else np.array(radius))        # Vortex core radius - where the majority of vorticity is concentrated
        self.axialVel       = axialVel                                                                        # Uniform axial velcoity - only needed for forced swirl type

    # Return data for requested vortex as tuple
    def getVortex(self,vortexIndex):
        # Check if at end of vortex list
        if (vortexIndex >= self.numVortices):
            raise IndexError(f"Index {self.vortNum} is out of bounds of vortex list with size {self.numVortices}")
        else:
            # Output tuple format 
            data = (self.centres[vortexIndex], self.strengths[vortexIndex], self.radius[vortexIndex], self.axialVel)

        return data 

'''
Class for reading and storing the information in the config file
'''
class Input:
    def __init__(self):
        # Intiailise all possible variables first
        self.filename = None
        self.format = None
        self.xSide = None
        self.ySide = None
        self.radius = None
        self.zSide = None
        self.shape = None
        self.xNumCells = None
        self.yNumCells = None
        self.zNumCells = None
        self.vortModel = None
        self.vortCoords = []
        self.vortStrengths = []
        self.vortRadius = []
        self.axialVel = None

    def read(self, configFile):
        # Initialise config parser and read config file
        config = ConfigParser()
        config.read(configFile)

        # Check which sections are present

        if ('METADATA' in config):
            # Get section
            metadata = config['METADATA']

            # Supported formats 
            formats = ['su2']

            try:
                self.filename = metadata.get('filename')
                
                format = metadata.get('format')
                if (format in formats):
                    self.format = format
                else:
                    raise NotImplementedError(f"{format} not supported")
            except KeyError:
                raise KeyError(f"Non-optional matadata missing in file {configFile}")

        if ('MESH DEFINITION' in config):
            # Get section
            meshDefinitions = config['MESH DEFINITION']

            # Get specified inlet shape
            try:
                self.shape = meshDefinitions.get('shape')
            except:
                raise KeyError("Shape of inlet face must be specified")

            # Get necessary inputs for inlet shape
            if self.shape == 'circle':
                try:
                    self.radius = float(meshDefinitions.get('radius'))
                except KeyError:
                    raise KeyError("Radius of circular inlet needs to be defined")
                except ValueError:
                    raise ValueError("Invalid value defined for inlet radius")
            elif self.shape == 'rect':
                try:
                    self.xSide = float(meshDefinitions.get('x_side'))
                    self.ySide = float(meshDefinitions.get('y_side'))
                except KeyError:
                    raise KeyError("Side lengths of rectangular inlet need to be defined")
                except ValueError:
                    raise ValueError("Invalid values defined for side lengths")
            else:
                raise NotImplementedError("Specified inlet shape not valid")

            # Get mesh density
            try:
                self.xNumCells = int(meshDefinitions.get('x_num_cells'))
                self.yNumCells = int(meshDefinitions.get('y_num_cells'))
            except KeyError:
                raise KeyError(f"Non-optional mesh parameters are missing in file {configFile}")
            except ValueError:
                raise ValueError(f"Invalid values defined for mesh parameters")

            # Optional parameters
            if ('z_side' in meshDefinitions):
                self.zSide = float(meshDefinitions.get('z_side'))

            if ('z_num_cells' in meshDefinitions):
                self.zNumCells = int(meshDefinitions.get('z_num_cells'))

        else:
            raise ValueError(f"Non-optional mesh definitions section not present in file {configFile}")

        if ('VORTEX DEFINITIONS' in config):
            # Get section
            vortexDefs = config['VORTEX DEFINITIONS']

            # Get number of vortices defined
            numVortices = sum(1 for key in vortexDefs) - 1

            # Check present inputs
            try:
                self.vortModel = vortexDefs.get('vortex_model').lower()
            except KeyError:
                raise KeyError(f"Non-optional vortex parameters are missing in file {configFile}")

            if (numVortices > 0):
                try:
                    # Extract the numeric data from the string for each vortex into an array
                    for i in range(1,numVortices+1):
                        data = list(float(numString) for numString in vortexDefs.get(f"vortex{i}")[1:-1].split(','))

                        if (len(data) < 4):
                            raise SyntaxError(f"Invalid number of parameters when defining vortex {i}")

                        self.vortCoords.append(data[0:2])
                        self.vortStrengths.append(data[2])
                        self.vortRadius.append(data[3])

                except ValueError:
                    raise ValueError(f"Invalid values defined for vortex parameters")
            else:
                raise KeyError(f"At least one vortex needs to be defined in {configFile}")
        else:
            raise ValueError(f"Non-optional vortex definitions section not present in file {configFile}")

        # Optional section
        if ('EXTRA' in config):
            # Get section
            extraParams = config['EXTRA']

            # May need better solution than this in future since will need a try/except pair for each optional config
            try:
                self.axialVel = float(extraParams.get('axial_vel'))
            except:
                pass

        # Set defaults if values weren't set
        self.axialVel   = (1.0 if self.axialVel is None else self.axialVel)

'''
Class containing data and functions relevant to the flow field
Initialised with an Input object
'''
class FlowField:
    def __init__(self, InputData: Input):
        # Get flow field descretisation descriptions from input object
        self.shape = InputData.shape
        self.radius = InputData.radius

        if InputData.xSide is not None:
            self.sideLengths = np.array([InputData.xSide, InputData.ySide])
        else:
            # If circular domain, still need side lengths for defining the grid
            self.sideLengths = np.array([InputData.radius*2, InputData.radius*2])
        
        self.numCells = np.array([InputData.xNumCells, InputData.yNumCells])

        # Initialise the actual flow field variables
        self.velGrids   = None
        self.rho        = None
        self.pressure   = None

        # Some comparison and metrics
        self.swirlAngle = None

        # Side lengths of each cell - using np.divide here also serves to automatically convert python lists into numpy arrays
        if self.shape == 'rect':
            # For rectangular domain, simple calculation
            self.cellSides = np.divide(self.sideLengths,self.numCells)
        elif self.shape == 'circle':
            # For circular domain, diameter (equal to grid side length) is used
            self.cellSides = np.divide(self.radius*2,self.numCells)
        else:
            raise NotImplementedError('Invalid domain shape \'{self.shape}\'')

        # Create coordinate grid which will contain the domain, also store axis ticks (may not be recoverable from coordinate grids depending on domain shape)
        self.coordGrids, self.axis = self.makeGrid()

        # Set domain boundary and mask to get all cells within domain
        self.mask, self.boundaryCells = self.setDomain()

        # Set cells outside domain to nan so that the flow field there is not unnecessarily calculated
        self.coordGrids[np.invert(np.dstack([self.mask,self.mask]))] = np.nan

    '''
    Make meshgrids to store coordinate system; as a result, all variable fields will be meshgrids also, good performance since using numpy matrix operations
    Stores coords of mesh nodes rather than cell centres
    '''
    def makeGrid(self):
        # Create coordinate system from mesh info - domain is centered at 0, I think makes for more intuitive definition of vortex positions
        x = np.linspace(-self.sideLengths[0]/2, self.sideLengths[0]/2, self.numCells[0]+1)      # x-axis is positive to the right
        y = np.linspace(self.sideLengths[1]/2, -self.sideLengths[1]/2, self.numCells[1]+1)      # y-axis is positive upwards

        # Protection for division by zero later - better solution than this?
        x[x == 0] = 1e-32
        y[y == 0] = 1e-32

        # Create meshgrid to store coordinate grid - useful in this form for plotting later and reduces the amount of for loops since we can use numpy matrix operations instead
        X, Y = np.meshgrid(x,y, indexing='xy')        # Use familiar ij matrix indexing

        # Stack grids into a 3D array, for convenience when passing between functions - not sure about performance effect, better or worse or negligible?
        coordGrids = np.dstack([X,Y])

        # Stack axis ticks
        axis = np.vstack([x,y])

        return coordGrids, axis

    ''' 
    Create a mask to specify the domain shape and borders within the meshgrid
    Outputs two boolean arrays, mask and boundary - mask is true when cell is within the boundary, boundary is true when cell is at the boundary
    '''
    def setDomain(self):
        if self.shape == 'circle':
            # Radius of each cell from origin
            radius = np.sqrt(self.coordGrids[:,:,0]**2 + self.coordGrids[:,:,1]**2)

            # Get mask using inequality - add buffer so that circular domain edges touch grid edges, since working with nodes rather than cell centres
            mask = radius < self.radius + self.cellSides[0]/2
            # Get boundary using equality with a tolerance since discrete space
            boundary = abs(radius - self.radius) < self.cellSides[0]/2

        elif self.shape == 'rect':
            # All cells are within boundary when rectangular domain shape
            mask = np.ones(self.coordGrids.shape[0:2], dtype=bool)

            # Boundary cells are simply those at the edges
            boundary = np.zeros(mask.shape, dtype=bool)
            boundary[1:-1,1:-1] = True

        else:
            raise NotImplementedError(f'Domain shape \'{self.shape}\' not valid')

        # Show boundary for debugging
        # import matplotlib.pyplot as plt
        # plt.figure()
        # plt.imshow(mask)
        # plt.figure()
        # plt.imshow(boundary)
        # plt.show()

        return mask, boundary

    '''
    Generic multiple vortices function
    Calculates the velocity field by superimposing the effect of the individual vortices
    Solid boundaries are modelled using the method of images
    vortDefs - Vortices object; axialVel - uniform axial velocity to be applied; density - if defined, assume that flow is incompressible
    '''
    def computeDomain(self, vortDefs: Vortices, axialVel, density = None):
        # Intialise 3D arrays to store multiple meshgrids - one for the component effect of each vortex
        uComps = np.zeros(np.append(self.coordGrids[:,:,0].shape, vortDefs.strengths.shape[0]))
        vComps = uComps.copy()

        # Dictionary mapping for functions - will be faster than multiple if/else statements - also more readable code
        vortexType = {'iso':self.__isoVortex__, 'lo':self.__loVortex__, 'solid':self.__solidVortex__}

        # Loop through given vortices and calculate their effect on each cell of the grid
        for i in range(vortDefs.strengths.shape[0]):
            # Get function for this vortex type
            func = vortexType.get(vortDefs.model)
            # Call vortex function to fill component arrays - with data for a single vortex
            uComps[:,:,i], vComps[:,:,i] = func(vortDefs.getVortex(i))

            # Calculate the effect of solid walls on this vortex using mirror image vortices
            uComps[:,:,i], vComps[:,:,i] = self.__boundary__(vortDefs.getVortex(i), uComps[:,:,i], vComps[:,:,i], func)


        # Collate effects of each vortex
        U = np.sum(uComps,axis=2)
        V = np.sum(vComps,axis=2)

        # Add uniform axial velocity field? Or have some other equation for it
        W = np.ones(U.shape)*axialVel

        # Stack velocity grids into multidimensional array
        self.velGrids = np.dstack([U,V,W])

        # Get swirl angle
        self.getSwirl()

    '''
    Models the effect of a solid wall on a vortex by placing a symmetric vortex
    Effect of these symmetric vortices are superimposed onto the input arrays
    WIP ---- DOES NOT CUURENTLY WORK CORRECTLY
    '''
    def __boundary__(self, vortData, uComp, vComp, vortexFunc):
        if self.shape == 'rect':
            # Get distance of vortex from walls - defined starting with bottom wall, going clockwise
            vortXc, vortYc = vortData[0]
            boundaryDist = [-self.sideLengths[1]/2-vortYc, -self.sideLengths[0]/2-vortXc, self.sideLengths[1]/2-vortYc, self.sideLengths[0]/2-vortXc]
            boundaryDist = list(map(abs,boundaryDist))  # Magnitudes
       
            # Place image vortices outside the domain - such that the bounday conditions are met while keeping the total circulation of the unbounded domain equalt to 0
            imageVortO = [[vortXc, vortYc-(2*boundaryDist[0])], 
                          [vortXc-(2*boundaryDist[1]), vortYc], 
                          [vortXc-(2*boundaryDist[1]), vortYc-(2*boundaryDist[0])],
                          [vortXc, vortYc+(2*boundaryDist[1])],
                          [vortXc, vortYc+(3*boundaryDist[1])],
                          [vortXc+(2*boundaryDist[3]), vortYc],
                          [vortXc+(3*boundaryDist[3]), vortYc]]
            imageVortS = [-vortData[1],-vortData[1],vortData[1],-vortData[1],vortData[1],-vortData[1],vortData[1]]

            for i in range(len(imageVortS)):
                # Create new array for this image vortex to be passed on to the appropriate vortex model function
                imageVortData = list(vortData)
                imageVortData[0] = imageVortO[i]
                imageVortData[1] = imageVortS[i]

                #print(f'image vortex @ {imageVortData[0]}, with strength {imageVortData[1]}')

                # Get effect of image vortex on grid
                uBoundary, vBoundary = vortexFunc(tuple(imageVortData))

                # Superimpose effect
                uComp += uBoundary
                vComp += vBoundary


        elif self.shape == 'circle':
            # Protection for division by zero
            vortData[0][vortData[0] == 0] = 1e-32   

            # Vortex of opposite strength
            imageVortS = -vortData[1]
            # At the inverse point - according to circle theorem
            imageVortO = (self.radius**2/(np.linalg.norm(vortData[0]))**2)*vortData[0]

            # Creating new vortex data list
            imageVortData = list(vortData)
            imageVortData[0] = imageVortO
            imageVortData[1] = imageVortS

            #print(f'image vortex @ {imageVortData[0]}, with strength {imageVortData[1]}')

            # Get effect of image vortex on grid
            uBoundary, vBoundary = vortexFunc(tuple(imageVortData))

            # Superimpose effect
            uComp += uBoundary
            vComp += vBoundary
            
        else:
            raise NotImplementedError('Duct shape not valid')

        return uComp, vComp

    '''
    Function for outputting the effect of a simple isentropic vortex on the domain
    - edge of grid currently not a bounding wall, ie vortex is acting like it's in an infinite domain and grid is just a smple of this
    vortData - tuple produced by getNextVortex() function of Vortices class
    '''
    def __isoVortex__(self, vortData):
        # Get radius of each cell from centre of this vortex
        r = np.sqrt((self.coordGrids[:,:,0]-vortData[0][0])**2 + (self.coordGrids[:,:,1] - vortData[0][1])**2)

        # Velocity components due to this vortex
        uComp = (vortData[1]/(2*np.pi)) * np.exp(0.5*(1-r**2)) * (self.coordGrids[:,:,1] - vortData[0][1])
        vComp = (vortData[1]/(2*np.pi)) * np.exp(0.5*(1-r**2)) * (vortData[0][0] - self.coordGrids[:,:,0])

        return uComp, vComp

    '''
    Function for outputting the effect of a Lamb-Oseen vortex
    - using equations given by Brandt (2009)

    vortData - tuple produced by getNextVortex() function of Vortices class
    '''
    def __loVortex__(self, vortData):
        # Extract individual variables from stacked tuples and arrays for convenience
        xc, yc = vortData[0]
        strength = vortData[1]
        a0 = vortData[2]
        x, y = self.coordGrids[:,:,0], self.coordGrids[:,:,1]

        # Get radius of each cell from centre of this vortex
        rr = (x-xc)**2 + (y-yc)**2

        # Get omega, the peak magnitude of vorticity (positive counterclockwise)
        omega = -strength/(np.pi * a0**2)

        # Velocity components due to this vortex
        uComp = 0.5  * (a0**2 * omega * (y - yc) / rr) * (1 - np.exp(-rr/a0**2))
        vComp = -0.5 * (a0**2 * omega * (x - xc) / rr) * (1 - np.exp(-rr/a0**2))

        return uComp, vComp

    '''
    Function for outputting the effect of a forced vortex
    - linear increase in swirl angle from center to outer edge
    - solid/forced vortex - not realistic; ie instantaneously created vortex, no effect on cells outside it's radius

    vortData - tuple produced by getNextVortex() function of Vortices class
    '''
    def __solidVortex__(self, vortData):
        # Get swirl angle and convert it to radians
        maxSwirlAngle = np.deg2rad(np.abs(vortData[1]))

        # Get vortex rotation information from sign of maximum angle specified
        anitclockwise = (True if vortData[1] > 0 else False)

        # Get axial coordinates
        r = np.sqrt((self.coordGrids[:,:,0]-vortData[0][0])**2 + (self.coordGrids[:,:,1] - vortData[0][1])**2)
        theta = np.arctan(self.coordGrids[:,:,1]/self.coordGrids[:,:,0])

        # Normalise radius for straightforward angle calculation and set cells outside vortex size to 0
        rNorm = r/vortData[2]
        # Add some tolerance to the equality to smooth out circle because discretised as nodes
        rNorm[np.nan_to_num(rNorm) > 1] = 0

        # Get swirl angle distribution
        swirlAngles = maxSwirlAngle*rNorm

        # Transform so swirl is coherent (either clockwise or anticlockwise) - without this, the swirl profile produced is mirrored about the y axis
        swirlAngles[(np.nan_to_num(self.coordGrids[:,:,0] * anitclockwise) < 0)] = swirlAngles[(np.nan_to_num(self.coordGrids[:,:,0] * anitclockwise) < 0)] * -1

        # Get tangential velocity at each cell
        tangentVel = vortData[3]*np.tan(swirlAngles)

        # Get theta_dot at each cell
        theta_dot = tangentVel/r

        # Get velocity vector components, in-plane cartesian (assume no radial velocity)
        uComp = -r*theta_dot*np.sin(theta)
        vComp =  r*theta_dot*np.cos(theta)

        return uComp, vComp

    '''
    For verifying physically correct boundary conditions after applying the method of images to model the solid boundaries
    ie checking if there is any flow across the solid boundaries and no slip condition:
    V_normal = 0, V_tangential = V_wall = 0
    '''
    def checkBoundaries(self):
        boundary_ok = True

        if self.shape == 'rect':
            # Check top wall
            if (any(self.velGrids[0,:,1] != 0)):
                boundary_ok = False
                print('Boundary broken, flow through top wall:')
                print(self.velGrids[0,:,1])
            # Check bottom wall
            if (any(self.velGrids[-1,:,1] != 0)):
                boundary_ok = False
                print('Boundary broken, flow through bottom wall:')
                print(self.velGrids[-1,:,1])
            # Check right wall
            if (any(self.velGrids[:,-1,0] != 0)):
                boundary_ok = False
                print('Boundary broken, flow through right wall:')
                print(self.velGrids[:,-1,0])
            # Check left wall
            if (any(self.velGrids[:,0,0] != 0)):
                boundary_ok = False
                print('Boundary broken, flow through left wall:')
                print(self.velGrids[:,0,0])

        elif self.shape == 'circle':
            raise NotImplementedError('Circle boundary check has not yet been implemented')
        else:
            raise NotImplementedError(f'\'{self.shape}\' boundary not valid')

        return boundary_ok

    '''
    Get swirl angles
    '''
    def getSwirl(self):
        # Get theta_dot - rate of chane of theta angle (rad/s)
        theta_dot = (self.coordGrids[:,:,0]*self.velGrids[:,:,1] - self.velGrids[:,:,0]*self.coordGrids[:,:,1]) / (self.coordGrids[:,:,0]**2 + self.coordGrids[:,:,1]**2)
        # Get radius
        r = np.sqrt(self.coordGrids[:,:,0]**2 + self.coordGrids[:,:,1]**2)

        # Get tangential velocity
        velTheta = r*theta_dot

        # Get swirl angle - as defined in literature
        swirlAngle = np.arctan(velTheta/self.velGrids[:,:,2])
        # Convert to degrees
        self.swirlAngle = np.rad2deg(swirlAngle)

    '''
    Calculate Root Mean Square error between this flow field's swirl angle profile and a given one
    '''
    def getError(self, desiredSwirl):
        RMSE = np.sqrt((1/np.size(self.swirlAngle))*np.sum((self.swirlAngle-desiredSwirl)**2))

        return RMSE

    '''
    Wrapper function for saving the flow field - so that calling script does not need to import numpy just for this
    '''
    def save(self, outputFile):
        np.savez(outputFile, velGrids=self.velGrids, rho=self.rho, pressure=self.pressure, swirl=self.swirlAngle)

    '''
    Unpacks zipped archive file created by saveFlowField() and returns the numpy arrays in the familiar format
    '''
    def load(self, file):
        # Extract file into an npz file
        npzfile = np.load(file)

        # Check if correct format
        if ('velGrids' in npzfile and 'rho' in npzfile and 'pressure' in npzfile and 'swirl' in npzfile):
            self.velGrids    = npzfile['velGrids']
            self.rho         = npzfile['rho']
            self.pressure    = npzfile['pressure']
            self.swirlAngle  = npzfile['swirl']

        else:
            raise RuntimeError('File format/contents invalid - make sure this file was created by swirlGenerator.saveFigsToPdf')

    '''
    Utility function for copying this flow field into another separate object
    '''
    def copy(self):
        # Create new object
        newField = FlowField(self.sideLengths,self.numCells)

        # Copy all data so far
        newField.velGrids   = self.velGrids
        newField.rho        = self.rho
        newField.pressure   = self.pressure
        newField.swirlAngle = self.swirlAngle

        return newField

def main():
    '''
    Default behaviour to showcase tool - ideally the swirlGenerator functions should be called from external scripts
    '''

    print("Generating generic bulk twin swirl profile (Lamb-Oseen vortices)...")

    # Initialise flow field object with domain side lengths and number of cells
    flowField = FlowField([10,10],[100,100])

    # Initialise object to store data about multiple vortices
    VortexDefs = Vortices('LO', [[-2,0],[2,0]], [-5,5])

    # Place vortices in domain
    flowField.defineVortices(VortexDefs, 5)

    # Plot and save fields
    flowField.plotAll()



if __name__ == '__main__':
    main()