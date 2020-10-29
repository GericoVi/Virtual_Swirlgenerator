import numpy as np
from matplotlib import pyplot as plt
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
For storing information about the vortices which have been defined for the domain
Each vortex can be defined as a different type
- Vortex models: 1 - Isentropic; 2 - Lamb-Oseen; 3 - Forced/Solid
- Positive vortex strength is defined as anti-clockwise rotation
'''
class Vortices: 
    # Object constructor accepts lists also for convenience, then later converts to numpy arrays
    def __init__(self, model: int, centres: Union[list, np.ndarray], strengths: Union[list, np.ndarray],
                       radius: Union[list, np.ndarray] = [], axialVel: Union[list, np.ndarray] = []):

        self.numVortices    = len(strengths)

        self.model          = model         # Vortex type - which mathematical model to use for all the vortices in the domain

        # Make sure these are all numpy arrays not just lists
        self.centres        = (centres      if isinstance(centres,np.ndarray)   else np.array(centres))       # Vortex centre
        self.strengths      = (strengths    if isinstance(strengths,np.ndarray) else np.array(strengths))     # Vortex strength
        self.radius         = (radius       if isinstance(radius,np.ndarray)    else np.array(radius))        # Vortex radius - can define a strong edge to the vortex, it has no effect on the flow outside this
        self.axialVel       = (axialVel     if isinstance(axialVel,np.ndarray)  else np.array(axialVel))      # Uniform axial velcoity - only needed for forced swirl type

        self.vortNum        = 0             # For keeping track during iteration

        # If there are forced vortices defined, make sure necessary arguements are defined
        if (self.model == 3 and (self.radius.size == 0 or self.axialVel.size == 0)):
            raise RuntimeError("Forced vortex type defined but radius, direction or axial velocity arguement is missing")

    # Return data for next vortex as tuple, for iteration
    def getNextVortex(self):
        # Check if at end of vortex list
        if (self.vortNum == self.numVortices):
            raise IndexError(f"Index {self.vortNum} is out of bounds of vortex list with size {self.numVortices}")
        else:
            # Output correct tuple format depending on vortex type
            if (self.model == 3):
                data = (self.centres[self.vortNum], self.strengths[self.vortNum], self.radius[self.vortNum], self.axialVel[self.vortNum])
            else:
                data = (self.centres[self.vortNum], self.strengths[self.vortNum])

            self.vortNum += 1

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
        self.zSide = None
        self.xNumCells = None
        self.yNumCells = None
        self.zNumCells = None
        self.vortModel = None
        self.vortCoords = []
        self.vortStrengths = []
        self.vortRadius = []
        self.axialVel = None

    # For creating an example configuration file that's compatible with this module
    def writeExample(self):
        # Intialise config parser object
        config = ConfigParser(allow_no_value=True)

        # Fill object with sections and keys
        config.add_section('METADATA')
        config.set('METADATA', '# Name of inlet boundary condition output file')
        config.set('METADATA', 'filename', 'example.dat')
        config.set('METADATA', '# Which cfd framework to format the file for (su2, )')
        config.set('METADATA', 'format', 'su2')

        config.add_section('MESH DEFINITION')
        config.set('MESH DEFINITION', '# Side lengths of inlet face (width, height)')
        config.set('MESH DEFINITION', 'x_side', '1.0')
        config.set('MESH DEFINITION', 'y_side', '1.0')
        config.set('MESH DEFINITION', '# (Optional) Define z length of domain if also generating the test meshed domain')
        config.set('MESH DEFINITION', 'z_side', '5.0')
        config.set('MESH DEFINITION', '# Number of mesh cells along each side')
        config.set('MESH DEFINITION', 'x_num_cells', '20')
        config.set('MESH DEFINITION', 'y_num_cells', '20')
        config.set('MESH DEFINITION', '# (Optional) Define z mesh if also generating the test meshed domain')
        config.set('MESH DEFINITION', 'z_num_cells', '100')

        config.add_section('VORTEX DEFINITIONS')
        config.set('VORTEX DEFINITIONS', '# Vortex model')
        config.set('VORTEX DEFINITIONS', 'vortex_model', '2')
        config.set('VORTEX DEFINITIONS', '# List of vortex data - for each vortex: (x-coord, y-coord, strength, radius[only for required for solid vortex])')
        config.set('VORTEX DEFINITIONS', 'vortex1', '(0.0, 0.0, 2.0)')

        config.add_section('EXTRA')
        config.set('EXTRA', '# Uniform axial (streamwise) velocity of inlet (default is 1)')
        config.set('EXTRA', 'axial_vel', '1.0')

        # Write to file
        with open('example.config', 'w') as file:
            config.write(file)


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

            # Check present inputs
            try:
                self.xSide = float(meshDefinitions.get('x_side'))
                self.ySide = float(meshDefinitions.get('y_side'))
                self.xNumCells = int(meshDefinitions.get('x_num_cells'))
                self.yNumCells = int(meshDefinitions.get('y_num_cells'))
            except KeyError:
                raise KeyError(f"Non-optional mesh parameters are missing in file {configFile}")
            except ValueError:
                raise ValueError(f"Invalid values defined for mesh parameters")

            if ('Z_SIDE' in meshDefinitions):
                self.zSide = float(meshDefinitions.get('z_side'))

            if ('Z_NUM_CELLS' in meshDefinitions):
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
                self.vortModel = int(vortexDefs.get('vortex_model'))
            except KeyError:
                raise KeyError(f"Non-optional vortex parameters are missing in file {configFile}")

            if (numVortices > 0):
                try:
                    # Extract the numeric data from the string for each vortex into an array
                    for i in range(1,numVortices+1):
                        data = list(float(numString) for numString in vortexDefs.get(f"vortex{i}")[1:-1].split(','))

                        if (len(data) < 3):
                            raise SyntaxError(f"Invalid number of parameters when defining vortex {i}")

                        self.vortCoords.append(data[0:2])
                        self.vortStrengths.append(data[2])

                        if (len(data) > 3):
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

            # May need better solution than this since will need a try/except pair for each optional config
            try:
                self.axialVel = float(extraParams.get('axial_vel'))
            except:
                pass


'''
Class containing data and functions relevant to the flow field
'''
class FlowField:
    def __init__(self, sideLengths=[10,10], numCells=[100,100]):
        # Flow field descretisation descriptions
        self.sideLengths = sideLengths
        self.numCells = numCells
        self.cellSides = np.divide(self.sideLengths,self.numCells)

        # Create coordinate grids of flow field mesh cells
        self.coordGrids = self.makeGrid()

        # Initialise the actual flow field variables
        self.velGrids   = None
        self.rho        = None
        self.pressure   = None

        # Some comparison and metrics
        self.swirlAngle = None

    # Make meshgrids to store coordinate system; as a result, all variable fields will be meshgrids also, good performance since using numpy matrix operations
    # Stores coords of mesh nodes rather than cell centres
    def makeGrid(self):
        # Create coordinate system from mesh info - domain is centered at 0, I think makes for more intuitive definition of vortex positions
        x = np.linspace(-self.sideLengths[0]/2, self.sideLengths[0]/2, self.numCells[0]+1)
        y = np.linspace(-self.sideLengths[1]/2, self.sideLengths[1]/2, self.numCells[1]+1)

        # Protection for division by zero later - better solution than this?
        x[x == 0] = 1e-32
        y[y == 0] = 1e-32

        # Create meshgrid to store coordinate grid - useful in this form for plotting later and reduces the amount of for loops since we can use numpy matrix operations instead
        X, Y = np.meshgrid(x,y, indexing='xy')        # Use familiar ij matrix indexing

        # Stack grids into a 3D array, for convenience when passing between functions - not sure about performance effect, better or worse or negligible?
        coordGrids = np.dstack([X,Y])

        return coordGrids

    '''
    Generic multiple vortices function
    Calculates the velocity and thermodynamic fields
    vortDefs - Vortices object; axialVel - uniform axial velocity to be applied; density - if defined, assume that flow is incompressible
    '''
    def defineVortices(self, vortDefs: Vortices, axialVel=1, density = None):
        # Intialise 3D arrays to store multiple meshgrids - one for the component effect of each vortex
        uComps = np.zeros(np.append(self.coordGrids[:,:,0].shape, vortDefs.strengths.shape[0]))
        vComps = uComps.copy()

        # Dictionary mapping for functions - will be faster then multiple if/else statements - also more readable code
        vortexType = {1:self.__isoVortex__, 2:self.__loVortex__, 3:self.__solidVortex__}

        # Loop through given vortices and calculate their effect on each cell of the grid
        for i in range(vortDefs.strengths.shape[0]):
            # Get function for this vortex type
            func = vortexType.get(vortDefs.model)
            # Call vortex function to fill component arrays - with data for a single vortex
            uComps[:,:,i], vComps[:,:,i] = func(vortDefs.getNextVortex())

        # Collate effects of each vortex
        U = np.sum(uComps,axis=2)
        V = np.sum(vComps,axis=2)

        # Add uniform axial velocity field? Or have some other equation for it
        W = np.ones(U.shape)*axialVel

        # Stack velocity grids into multidimensional array
        self.velGrids = np.dstack([U,V,W])

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
    - using adapted equations from StreamVane paper, generalised for an arbitrary number of vortices at arbitrary positions
    ------- Equations from StreamVane paper has slight error for v velocity component, correct here
    - Generic twin swirl profile can be created with by placing two vortices with parameters from paper

    vortData - tuple produced by getNextVortex() function of Vortices class
    '''
    def __loVortex__(self, vortData):
        # Some parameter - a0=0.1 apparently creates maximum swirl angle of 16deg when other parameters same as paper
        a0 = 0.1

        # Get radius of each cell from centre of this vortex
        r = np.sqrt((self.coordGrids[:,:,0]-vortData[0][0])**2 + (self.coordGrids[:,:,1] - vortData[0][1])**2)
        rsquare = r**2

        # Get omega (actual vortex strength?)
        omega = vortData[1]/(np.pi * a0**2)

        # Velocity components due to this vortex
        uComp = 0.5 * (a0**2 * omega * (self.coordGrids[:,:,1] - vortData[0][1]) / r**2) * (1 - np.exp(-r**2/a0**2))
        vComp = 0.5 * (a0**2 * omega * (vortData[0][0] - self.coordGrids[:,:,0]) / r**2) * (1 - np.exp(-r**2/a0**2))

        return uComp, vComp

    '''
    Function for outputting the effect of a forced vortex
    - linear increase in swirl angle from center to outer edge
    - swirl angle defined as angle between resultant vector and axial velocity component (cause by tangential component velocity)
    - solid/forced vortex - not realistic; ie instantaneously created vortex, no effect on cells outside it's radius
    - also assumes no radial velocity

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
        rNorm[(rNorm > 1)] = 0

        # Get swirl angle distribution
        swirlAngles = maxSwirlAngle*rNorm

        # Transform so swirl is coherent (either clockwise or anticlockwise) - without this, the swirl profile produced is mirrored about the y axis
        swirlAngles[(self.coordGrids[:,:,0] * anitclockwise < 0)] = swirlAngles[(self.coordGrids[:,:,0] * anitclockwise < 0)] * -1

        # Get tangential velocity at each cell
        tangentVel = vortData[3]*np.tan(swirlAngles)

        # Get theta_dot at each cell
        theta_dot = tangentVel/r

        # Get velocity vector components, in-plane cartesian (assume no radial velocity)
        uComp = -r*theta_dot*np.sin(theta)
        vComp =  r*theta_dot*np.cos(theta)

        return uComp, vComp

    '''
    Utility for showing and saving all plots
    '''
    def plotAll(self, pdfName=None):
        self.plotVelocity()

        #plotThermos()

        self.plotSwirl()

        # If saving, don't show plots
        if (pdfName != None):
            self.__saveFigsToPdf__(pdfName)
        else:
            plt.show()

        # Clear figures when done
        plt.close('all')

    '''
    Create plots for the swirling velocity profile as a quiver plot and a streamlines plot
    '''
    def plotVelocity(self):
        # Get individual grids, more convenient for pruning etc. for plots
        X = self.coordGrids[:,:,0]
        Y = self.coordGrids[:,:,1]

        # For making quiver plot sparser, but independent of grid density
        quiverEvery = int(X.size**(1/2) / 20)
        quiverEvery = (1 if (quiverEvery == 0) else quiverEvery)

        # Make quiver plot
        plt.figure()
        plt.gca().set_aspect('equal', adjustable='box')
        plt.title("Quiver")
        skip = (slice(None,None,quiverEvery), slice(None,None,quiverEvery))       # Prune output so quiver plot is not so dense
        plt.quiver(self.coordGrids[:,:,0][skip], self.coordGrids[:,:,1][skip], self.velGrids[:,:,0][skip], self.velGrids[:,:,1][skip])

        # Make streamlines plot
        plt.figure()
        plt.gca().set_aspect('equal', adjustable='box')
        plt.title("Streamlines")
        plt.streamplot(self.coordGrids[1,:,0], self.coordGrids[:,1,1], self.velGrids[:,:,0], self.velGrids[:,:,1], density=2)            # streamplot uses vector axis for xy instead of meshgrid for some reason?

    '''
    Create contour plots for density and pressure field
    '''
    def plotThermos(self):
        plt.figure()
        plt.title('Density')
        plt.contourf(self.coordGrids[:,:,0],self.coordGrids[:,:,1],self.rho,100)
        plt.colorbar()

        plt.figure()
        plt.title('Pressure')
        plt.contourf(self.coordGrids[:,:,0],self.coordGrids[:,:,1],self.pressure,100)
        plt.colorbar()

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
        # Make sure swirl angle profile has been computed for this FlowField
        if self.swirlAngle is None:
            self.getSwirl()

        RMSE = np.sqrt((1/np.size(self.swirlAngle))*np.sum((self.swirlAngle-desiredSwirl)**2))

        return RMSE

    '''
    Create contour plot for swirl angle
    '''
    def plotSwirl(self):
        # Make sure swirl angle profile has been computed for this FlowField
        if self.swirlAngle is None:
            self.getSwirl()

        # Make contour plot
        plt.figure()
        plt.title('Swirl angle')
        plt.contourf(self.coordGrids[:,:,0],self.coordGrids[:,:,1],self.swirlAngle,100)
        plt.colorbar()

    '''
    Save all current figures into a multi-page pdf
    '''
    def __saveFigsToPdf__(self, outputFile):
        from matplotlib.backends.backend_pdf import PdfPages

        with PdfPages(outputFile) as pdf:
            # Go through all active figures and save to a separate pdf page
            for fig in range(1, plt.gcf().number+1):
                pdf.savefig(fig)

    '''
    Wrapper function for saving the flow field - so that calling script does not need to import numpy just for this
    '''
    def save(self, outputFile):
        np.savez(outputFile, velGrids=self.velGrids, rho=self.rho, pressure=self.pressure)

    '''
    Unpacks zipped archive file created by saveFlowField() and returns the numpy arrays in the familiar format
    '''
    def load(self, file):
        # Extract file into an npz file
        npzfile = np.load(file)

        # Check if correct format
        if ('velGrids' in npzfile and 'rho' in npzfile and 'pressure' in npzfile):
            self.velGrids    = npzfile['velGrids']
            self.rho         = npzfile['rho']
            self.pressure    = npzfile['pressure']

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

    print("Generating generic bulk twin swirl profile (isentropic vortices)...")

    # Initialise flow field object with domain side lengths and number of cells
    flowField = FlowField([10,10],[100,100])

    # Initialise object to store data about multiple vortices
    VortexDefs = Vortices(1, [[-2,0],[2,0]], [-5,5])

    # Place vortices in domain
    flowField.defineVortices(VortexDefs, 5)

    # Plot and save fields
    flowField.plotAll()



if __name__ == '__main__':
    main()