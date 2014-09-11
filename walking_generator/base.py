import numpy
from math import cos, sin
from copy import deepcopy

class BaseGenerator(object):
    """
    Base class of walking pattern generator for humanoids, cf.
    LAAS-UHEI walking report.

    BaseClass provides all matrices and timestepping methods that are
    defined for the pattern generator family. In derived classes different
    problems and their solvers can be realized.
    """
    # define some constants
    g = 9.81

    def __init__(self, N=16, T=0.1, T_step=0.8, h_com=0.814):
        """
        Initialize pattern generator, i.e.
        * allocate memory for matrices
        * populate them according to walking reference document

        Parameters
        ----------

        N : int
            Number of time steps of prediction horizon

        T : float
            Time increment between two time steps (default: 0.1 [s])

        nf : int
            Number of foot steps planned in advance (default: 2 [footsteps])

        h_com: float
            Height of center of mass for the LIPM (default: 0.81 [m])

        T_step : float
            Time for the robot to make 1 step

        T_window : float
            Duration of the preview window of the controller
        """
        self.N = N
        self.T = T
        self.T_window = N*T
        self.T_step = T_step
        self.nf = (int)(self.T_window/T_step)
        self.h_com = h_com
        self.currentTime = 0.0

        # objective weights

        self.a = 1.0   # weight for CoM velocity tracking
        self.b = 0.0   # weight for CoM average velocity tracking
        self.c = 1e-06 # weight for ZMP reference tracking
        self.d = 1e-05 # weight for jerk minimization

        # matrix to get average velocity

        self.E = numpy.zeros((self.N/self.nf, self.N))
        self.E[:, :self.N/self.nf] = -numpy.eye(self.N/self.nf)
        self.E[:,-self.N/self.nf:] =  numpy.eye(self.N/self.nf)
        self.E /= 2*self.T_step

        # center of mass initial values

        self.c_k_x = numpy.zeros((3,), dtype=float)
        self.c_k_y = numpy.zeros((3,), dtype=float)
        self.c_k_q = numpy.zeros((3,), dtype=float)

        # center of mass matrices

        self.  C_kp1_x = numpy.zeros((N,), dtype=float)
        self. dC_kp1_x = numpy.zeros((N,), dtype=float)
        self.ddC_kp1_x = numpy.zeros((N,), dtype=float)

        self.  C_kp1_y = numpy.zeros((N,), dtype=float)
        self. dC_kp1_y = numpy.zeros((N,), dtype=float)
        self.ddC_kp1_y = numpy.zeros((N,), dtype=float)

        self.  C_kp1_q = numpy.zeros((N,), dtype=float)
        self. dC_kp1_q = numpy.zeros((N,), dtype=float)
        self.ddC_kp1_q = numpy.zeros((N,), dtype=float)

        # jerk controls for center of mass

        self.dddC_k_x = numpy.zeros((N,), dtype=float)
        self.dddC_k_y = numpy.zeros((N,), dtype=float)
        self.dddC_k_q = numpy.zeros((N,), dtype=float)

        # reference matrices

        self. dC_kp1_x_ref = numpy.zeros((N,), dtype=float)
        self. dC_kp1_y_ref = numpy.zeros((N,), dtype=float)
        self. dC_kp1_q_ref = numpy.zeros((N,), dtype=float)

        # feet matrices

        self.F_kp1_x = numpy.zeros((N,), dtype=float)
        self.F_kp1_y = numpy.zeros((N,), dtype=float)
        self.F_kp1_q = numpy.zeros((N,), dtype=float)

        self.f_k_x = 0.0
        self.f_k_y = 0.0
        self.f_k_q = 0.0

        self.F_k_x = numpy.zeros((self.nf,), dtype=float)
        self.F_k_y = numpy.zeros((self.nf,), dtype=float)
        self.F_k_q = numpy.zeros((self.nf,), dtype=float)

        # zero moment point matrices

        self.Z_kp1_x = numpy.zeros((N,), dtype=float)
        self.Z_kp1_y = numpy.zeros((N,), dtype=float)

        # transformation matrices

        self.Pps = numpy.zeros((N,3), dtype=float)
        self.Ppu = numpy.zeros((N,N), dtype=float)

        self.Pvs = numpy.zeros((N,3), dtype=float)
        self.Pvu = numpy.zeros((N,N), dtype=float)

        self.Pas = numpy.zeros((N,3), dtype=float)
        self.Pau = numpy.zeros((N,N), dtype=float)

        self.Pzs = numpy.zeros((N,3), dtype=float)
        self.Pzu = numpy.zeros((N,N), dtype=float)

        # convex hulls used to bound the free placement of the foot
            # support foot : right
        self.rfhull = numpy.array((
                (-0.28, -0.2),
                (-0.20, -0.3),
                ( 0.00, -0.4),
                ( 0.20, -0.3),
                ( 0.28, -0.2),
        ), dtype=float)

            # support foot : left
        self.lfhull = numpy.array((
                (-0.28, 0.2),
                (-0.20, 0.3),
                ( 0.00, 0.4),
                ( 0.20, 0.3),
                ( 0.28, 0.2),
        ), dtype=float)

            # set of Cartesian equalities
        self.A0r = numpy.zeros((5,2), dtype=float)
        self.ubB0r = numpy.zeros((5,), dtype=float)
        self.A0l = numpy.zeros((5,2), dtype=float)
        self.ubB0l = numpy.zeros((5,), dtype=float)

        # Linear constraints matrix
        self.Acop = numpy.zeros((), dtype=float)
        self.Afoot = numpy.zeros((), dtype=float)
        self.eqAfoot = numpy.zeros( (2,2*(self.N+self.nf)), dtype=float)

        # Linear constraints vector
        self.ubBfoot = numpy.zeros((), dtype=float)
        self.ubBcop = numpy.zeros((), dtype=float)
        self.eqBfoot = numpy.zeros((2,), dtype=float)

        # security margins for CoP constraints
        self.SecurityMarginX = SMx = 0.04
        self.SecurityMarginY = SMy = 0.04

        # Position of the foot in the local foot frame
        self.nFootEdge = 4
        self.footWidth  = fW = 0.2172
        self.footHeigth = fH = 0.138
        # position of the vertices of the feet in the foot coordinates.
        #  #<---footWidht---># --- ---
        #  #<>=SMx     SMx=<>#  |   |=SMy
        #  #  *-----------*  #  |  ---
        #  #  |           |  #  |=footHeight
        #  #  *-----------*  #  |  ---
        #  #                 #  |   |=SMy
        #  #-----------------# --- ---

        # left foot
        self.lfoot = numpy.array((
            ( (0.5*fW - SMx),  (0.5*fH - SMy)),
            ( (0.5*fW - SMx), -(0.5*fH - SMy)),
            (-(0.5*fW - SMx), -(0.5*fH - SMy)),
            (-(0.5*fW - SMx),  (0.5*fH - SMy)),
        ), dtype=float)

        # right foot
        self.rfoot = numpy.array((
            ( (0.5*fW - SMx), -(0.5*fH - SMy)),
            ( (0.5*fW - SMx),  (0.5*fH - SMy)),
            (-(0.5*fW - SMx),  (0.5*fH - SMy)),
            (-(0.5*fW - SMx), -(0.5*fH - SMy)),
        ), dtype=float)

        # Corresponding linear system
        self.A0rf = numpy.zeros((self.nFootEdge,2), dtype=float)
        self.ubB0rf = numpy.zeros((self.nFootEdge,), dtype=float)
        self.A0lf = numpy.zeros((self.nFootEdge,2), dtype=float)
        self.ubB0lf = numpy.zeros((self.nFootEdge,), dtype=float)

        # D_kp1 = (D_kp1x, Dkp1_y)
        self.D_kp1  = numpy.zeros( (self.nFootEdge*self.N, 2*N), dtype=float )
        self.D_kp1x = self.D_kp1[:, :N] # view on big matrix
        self.D_kp1y = self.D_kp1[:,-N:] # view on big matrix
        self.b_kp1 = numpy.zeros( (self.nFootEdge*self.N,), dtype=float )

        # Current support state
        self.currentSupport = BaseTypeSupportFoot(x=self.f_k_x, y=self.f_k_y, theta=self.f_k_q, foot="left")
        self.supportDeque = numpy.empty( (N,) , dtype=object )
        for i in range(N):
            self.supportDeque[i] = BaseTypeSupportFoot()

        """
        NOTE number of foot steps in prediction horizon changes between
        nf and nf+1, because when robot takes first step nf steps are
        planned on the prediction horizon, which makes a total of nf+1 steps.
        """
        self.v_kp1 = numpy.zeros((N,),   dtype=int)
        self.V_kp1 = numpy.zeros((N,self.nf), dtype=int)

        # initialize all elementary problem matrices, e.g.
        # state transformation matrices, constraints, etc.
        self._initialize_matrices()

    def _initialize_matrices(self):
        """
        initializes the transformation matrices according to the walking report
        """
        T_step = self.T_step
        T = self.T
        N = self.N
        nf = self.nf
        h_com = self.h_com
        g = self.g

        for i in range(N):
            j = i+1
            self.Pzs[i, :] = (1.,   j*T, (j**2*T**2)/2. - h_com/g)
            self.Pps[i, :] = (1.,   j*T,           (j**2*T**2)/2.)
            self.Pvs[i, :] = (0.,    1.,                      j*T)
            self.Pas[i, :] = (0.,    0.,                       1.)

            for j in range(N):
                if j <= i:
                    self.Pzu[i, j] = (3.*(i-j)**2 + 3.*(i-j) + 1.)*T**3/6. - T*h_com/g
                    self.Ppu[i, j] = (3.*(i-j)**2 + 3.*(i-j) + 1.)*T**3/6.
                    self.Pvu[i, j] = (2.*(i-j) + 1.)*T**2/2.
                    self.Pau[i, j] = T

        # initialize foot decision vector and matrix
        nstep = int(self.T_step/T) # time span of single support phase
        self.v_kp1[:nstep] = 1 # definitions of initial support leg

        for j in range (nf):
            a = min((j+1)*nstep, N)
            b = min((j+2)*nstep, N)
            self.V_kp1[a:b,j] = 1

        self._calculate_support_order()

        # linear system corresponding to the convex hulls
        self.ComputeLinearSystem( self.rfhull, "right", self.A0r, self.ubB0r)
        self.ComputeLinearSystem( self.lfhull, "left", self.A0l, self.ubB0l)

        # linear system corresponding to the convex hulls
        self.ComputeLinearSystem( self.rfoot, "right", self.A0rf, self.ubB0rf)
        self.ComputeLinearSystem( self.lfoot, "left", self.A0lf, self.ubB0lf)

        self._updateD()

        # define initial support feet order
        self._calculate_support_order()

        # build the constraints linked to
        # the foot step placement and to the cop
        self.buildConstraints()

    def _initState(self, comx, comy , comz, supportfootx, supportfooty, supportfootq, secmarginx, secmarginy):
        self.f_k_x = supportfootx
        self.f_k_y = supportfooty
        self.f_k_q = supportfootq
        self.c_k_x[...] = comx
        self.c_k_y[...] = comy
        self.h_com = comz
        self.SecurityMarginX = secmarginx
        self.SecurityMarginY = secmarginy
        self._initialize_matrices()

    def _calculate_support_order(self):
        # find correct initial support foot
        if (self.currentSupport.foot == "left" ) :
            pair = "left"
            impair = "right"
        else :
            pair = "right"
            impair = "left"
        timeLimit = self.supportDeque[0].timeLimit
        # define support feet for whole horizon
        for i in range(self.N):
            for j in range(self.nf):
                if self.V_kp1[i][j] == 1 :
                    self.supportDeque[i].stepNumber = j+1
                    if (j % 2) == 1:
                        self.supportDeque[i].foot = pair
                    else :
                        self.supportDeque[i].foot = impair

            if i > 0 :
                self.supportDeque[i].ds = self.supportDeque[i].stepNumber -\
                                          self.supportDeque[i-1].stepNumber
            if self.supportDeque[i].ds == 1 :
                timeLimit = self.currentTime + self.T_step

            self.supportDeque[i].timeLimit = timeLimit

    def update(self):
        """
        Update all interior matrices, vectors.
        Has to be used to prepare the QP after each iteration
        """
        self._updatev() # update selection matrix and determine support order
        # NOTE call updatev before updateD! The latter depends on support order
        self._updateD() # update constraint transformation matrix

    def _updatev(self):
        """
        Update selection vector v_kp1 and selection matrix V_kp1.

        Therefore shift foot decision vector and matrix by one row up,
        i.e. the first entry in the selection vector and the first row in the
        selection matrix drops out and selection vector's dropped first value
        becomes the last entry in the decision matrix
        """
        nf = self.nf
        nstep = int(self.T_step/self.T)
        N = self.N

        # save first value for concatenation
        first_entry_v_kp1 = self.v_kp1[0].copy()

        self.v_kp1[:-1]   = self.v_kp1[1:]
        self.V_kp1[:-1,:] = self.V_kp1[1:,:]

        # clear last row
        self.V_kp1[-1,:] = 0

        # concatenate last entry
        self.V_kp1[-1, -1] = first_entry_v_kp1

        # when first column of selection matrix becomes zero,
        # then shift columns by one to the front
        if (self.v_kp1 == 0).all():
            self.v_kp1[:] = self.V_kp1[:,0]
            self.V_kp1[:,:-1] = self.V_kp1[:,1:]
            self.V_kp1[:,-1] = 0

            # this way also the current support foot changes
            self.currentSupport.foot       = deepcopy(self.supportDeque[0].foot)
            self.currentSupport.ds         = deepcopy(self.supportDeque[0].ds)

            # supportDeque is then calculated from
            # from current support in the following

        self._calculate_support_order()

    def _updateD(self):
        """
        update foot constraint transformation matrices

        NOTE: call updatev beforehand for actual support order!
        """
        for i in range(self.N):
            if self.supportDeque[i].foot == "left" :
                A0 = self.A0lf
                B0 = self.ubB0lf
            else :
                A0 = self.A0rf
                B0 = self.ubB0rf
            for j in range(self.nFootEdge):
                self.D_kp1x[i*self.nFootEdge+j][i] = A0[j][0]
                self.D_kp1y[i*self.nFootEdge+j][i] = A0[j][1]
                self.b_kp1 [i*self.nFootEdge+j]    = B0[j]

    def simulate(self):
        """
        integrates model for given initial CoM states, jerks and feet positions
        and orientations by applying the linear time stepping scheme
        """
        self.  C_kp1_x = self.Pps.dot(self.c_k_x) + self.Ppu.dot(self.dddC_k_x)
        self. dC_kp1_x = self.Pvs.dot(self.c_k_x) + self.Pvu.dot(self.dddC_k_x)
        self.ddC_kp1_x = self.Pas.dot(self.c_k_x) + self.Pau.dot(self.dddC_k_x)

        self.  C_kp1_y = self.Pps.dot(self.c_k_y) + self.Ppu.dot(self.dddC_k_y)
        self. dC_kp1_y = self.Pvs.dot(self.c_k_y) + self.Pvu.dot(self.dddC_k_y)
        self.ddC_kp1_y = self.Pas.dot(self.c_k_y) + self.Pau.dot(self.dddC_k_y)

        self.  C_kp1_q = self.Pps.dot(self.c_k_q) + self.Ppu.dot(self.dddC_k_q)
        self. dC_kp1_q = self.Pvs.dot(self.c_k_q) + self.Pvu.dot(self.dddC_k_q)
        self.ddC_kp1_q = self.Pas.dot(self.c_k_q) + self.Pau.dot(self.dddC_k_q)

        self.Z_kp1_x = self.Pzs.dot(self.c_k_x) + self.Pzu.dot(self.dddC_k_x)
        self.Z_kp1_y = self.Pzs.dot(self.c_k_y) + self.Pzu.dot(self.dddC_k_y)

    def ComputeLinearSystem(self, hull, foot, A0, B0 ):
        """
        automatically calculate linear constraints from polygon description
        """
        # get number of edged from the hull specification, e.g.
        # single and double support polygon, foot position hull
        nEdges = hull.shape[0]

        # get sign for hull from given foot
        if foot == "left" :
            sign = 1
        else :
            sign = -1

        # calculate linear constraints from hull
        for i in range(nEdges):
            if i == nEdges-1 :
                k = 0
            else :
                k = i + 1

            x1 = hull[i,0]
            y1 = hull[i,1]
            x2 = hull[k,0]
            y2 = hull[k,1]

            dx = y1 - y2
            dy = x2 - x1
            dc = dx*x1 + dy*y1

            # symmetrical constraints
            A0[i,0] = sign * dx
            A0[i,1] = sign * dy
            B0[i] =   sign * dc

    def buildConstraints(self):
        self.nc = 0
        self.buildCoPconstraint()
        self.buildFootEqConstraint()
        self.buildFootIneqConstraint()

    def buildCoPconstraint(self):
        #rename for convenience
        D_kp1 = self.D_kp1

        # define shape
        zeroDim = (self.N, self.N+self.nf)

        # ???
        PZUVx = numpy.concatenate( (self.Pzu,-self.V_kp1,numpy.zeros(zeroDim,dtype=float)) , 1 )
        PZUVy = numpy.concatenate( (numpy.zeros(zeroDim,dtype=float),self.Pzu,-self.V_kp1) , 1 )
        PZUV = numpy.concatenate( (PZUVx,PZUVy) , 0 )

        PZSC = numpy.concatenate( (self.Pzs.dot(self.c_k_x),self.Pzs.dot(self.c_k_y)) , 0 )
        v_kp1fc = numpy.concatenate( (self.v_kp1.dot(self.f_k_x), self.v_kp1.dot(self.f_k_y) ) , 0 )

        # build CoP linear constraints
        self.Acop = D_kp1.dot(PZUV)
        self.ubBcop = self.b_kp1 - D_kp1.dot(PZSC) + D_kp1.dot(v_kp1fc)

    def buildFootEqConstraint(self):
        # B <= A x <= B
        # Support_Foot(k+1) = Support_Foot(k)
        itBeforeLanding = numpy.sum(self.v_kp1)
        itBeforeLandingThreshold = 2
        if ( itBeforeLanding < itBeforeLandingThreshold ) :
            self.eqAfoot[0][self.N] = 1
            self.eqAfoot[1][2*self.N+self.nf] = 1

            self.eqBfoot[0][self.N] = self.F_k_x[0]
            self.eqBfoot[1][self.N] = self.F_k_y[0]


    def buildFootIneqConstraint(self):
        """
        build linear inequality constraints for the placement of the feet

        NOTE: needs actual self.supportFoot to work properly
        """

        # inequality constraint on both feet A u + B <= 0
        # A0 R(theta) [Fx_k+1 - Fx_k] <= ubB0
        #             [Fy_k+1 - Fy_k]

        matSelec = numpy.array([ [1, 0],[-1, 1] ])
        footSelec = numpy.array([ [self.f_k_x, 0],[self.f_k_y, 0] ])
        theta = self.currentSupport.theta

        # rotation matrice from F_k+1 to F_k
        rotMat = numpy.array([[cos(theta), sin(theta)],[-sin(theta), cos(theta)]])
        nf = self.nf
        nEdges = self.A0l.shape[0]
        N = self.N
        ncfoot = nf * nEdges

        A0lrot = self.A0l.dot(rotMat)
        A0rrot = self.A0r.dot(rotMat)

        if self.currentSupport.foot == "left":
            A_f1 = A0rrot
            A_f2 = A0lrot
            B_f1 = self.ubB0r
            B_f2 = self.ubB0l
        else :
            A_f1 = A0lrot
            A_f2 = A0rrot
            B_f1 = self.ubB0l
            B_f2 = self.ubB0r

        tmp1 = numpy.array( [A_f1[:,0],numpy.zeros((nEdges,),dtype=float)] )
        tmp2 = numpy.array( [numpy.zeros((nEdges,),dtype=float),A_f2[:,0]] )
        tmp3 = numpy.array( [A_f1[:,1],numpy.zeros((nEdges,),dtype=float)] )
        tmp4 = numpy.array( [numpy.zeros(nEdges,),A_f2[:,1]] )

        X_mat = numpy.concatenate( (tmp1.T,tmp2.T) , 0)
        A0x = X_mat.dot(matSelec)
        Y_mat = numpy.concatenate( (tmp3.T,tmp4.T) , 0)
        A0y = Y_mat.dot(matSelec)

        B0full = numpy.concatenate( (B_f1, B_f2) , 0 )
        B0 = B0full + X_mat.dot(footSelec[0,:]) + Y_mat.dot(footSelec[1,:])

        self.Afoot = numpy.concatenate ( (numpy.zeros((ncfoot,N),dtype=float),\
                                          A0x,\
                                          numpy.zeros((ncfoot,N),dtype=float),\
                                          A0y) , 1 )
        self.ubBfoot = B0
        self.nc = self.nc + ncfoot

    def buildOriConstraints():
        raise NotImplementedError

    def solve(self):
        """
        Solve problem on given prediction horizon with implemented solver.
        """
        err_str = 'Please derive from this class to implement your problem and solver'
        raise NotImplementedError(err_str)

class BaseTypeSupportFoot(object):

    def __init__(self, x=0, y=0, theta=0, foot="left"):
        self.x = x
        self.y = y
        self.theta = theta
        self.foot = foot
        self.ds = 0
        self.stepNumber = 0
        self.timeLimit = 0

    def __eq__(self, other):
        """ equality operator to check if A == B """
        return (isinstance(other, self.__class__)
            or self.__dict__ == other.__dict__)

    def __ne__(self, other):
        return not self.__eq__(other)

class BaseTypeFoot(object):

    def __init__(self, x=0, y=0, theta=0, foot="left", supportFoot=0):
        self.x = x
        self.y = y
        self.theta = theta

        self.dx = 0
        self.dy = 0
        self.dtheta = 0

        self.ddx = 0
        self.ddy = 0
        self.ddtheta = 0

        self.supportFoot = supportFoot

    def __eq__(self, other):
        """ equality operator to check if A == B """
        return (isinstance(other, self.__class__)
            or self.__dict__ == other.__dict__)

    def __ne__(self, other):
        return not self.__eq__(other)

class CoMState(object):

    def __init__(self, x=0, y=0, theta=0, h_com=0.81):
        self.x = numpy.zeros( (3,) , dtype=float )
        self.y = numpy.zeros( (3,) , dtype=float )
        self.z = h_com
        self.theta = numpy.zeros( (3,) , dtype=float )

class ZMPState(object):

    def __init__(self, x=0, y=0, z=0):
        self.x = x
        self.y = y
        self.z = z

    def __eq__(self, other):
        """ equality operator to check if A == B """
        return (isinstance(other, self.__class__)
            or self.__dict__ == other.__dict__)

    def __ne__(self, other):
        return not self.__eq__(other)

