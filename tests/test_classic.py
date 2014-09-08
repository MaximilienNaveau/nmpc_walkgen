import os
import numpy
numpy.set_printoptions(threshold=numpy.nan, linewidth =numpy.nan)
from numpy.testing import *

from walking_generator.classic import ClassicGenerator
try:
    from qpoases import PyOptions as Options
    from qpoases import PyPrintLevel as PrintLevel
    from qpoases import PySQProblem as SQProblem
    from qpoases import PySolutionAnalysis as SolutionAnalysis
except ImportError:
    err_str = 'Please install qpOASES python interface, else you will not be able to use this pattern generator.'
    raise ImportError(err_str)

BASEDIR = os.path.dirname(os.path.abspath(__file__))

class TestClassicGenerator(TestCase):
    """
    Test classic pattern generator, also against results from LAAS
    """
    #define tolerance for unittests
    ATOL = 1e-07
    RTOL = 1e-07

    def test_qp_setup_with_toy_example(self):
        gen = ClassicGenerator()

        # define input matrices
        gen.pos_H[...] = numpy.eye(gen.pos_nv)
        gen.pos_g[...] = numpy.ones((gen.pos_nv,))

        gen.pos_lb[...] = -numpy.ones((gen.pos_nv,))*0.5
        gen.pos_ub[...] =  numpy.ones((gen.pos_nv,))*0.5

        gen.pos_A[...]   = numpy.eye(gen.pos_nc, gen.pos_nv) + numpy.eye(gen.pos_nc, gen.pos_nv, k=1)
        gen.pos_lbA[...] = -numpy.ones((gen.pos_nc,))
        gen.pos_ubA[...] =  numpy.ones((gen.pos_nc,))

        # define input matrices
        gen.ori_H[...] = numpy.eye(gen.ori_nv)
        gen.ori_g[...] = numpy.ones((gen.ori_nv,))

        gen.ori_lb[...] = -numpy.ones((gen.ori_nv,))*0.5
        gen.ori_ub[...] =  numpy.ones((gen.ori_nv,))*0.5

        gen.ori_A[...]   = numpy.eye(gen.ori_nc, gen.ori_nc) + numpy.eye(gen.ori_nc, gen.ori_nv, k=1)
        gen.ori_lbA[...] = -numpy.ones((gen.ori_nc,))
        gen.ori_ubA[...] =  numpy.ones((gen.ori_nc,))

        # define solution
        ori_x = -numpy.ones((gen.ori_nv,))*0.11764706
        ori_x[gen.ori_nc] = 0.5
        pos_x = -numpy.ones((gen.pos_nv,))*0.5
        pos_f = -13.5
        ori_f = -1.2573529411764695

        # test first qp solution
        gen._solve_qp()
        gen._postprocess_solution()

        # get solution
        assert_allclose(gen.ori_dofs, ori_x, rtol=self.RTOL, atol=self.ATOL)
        assert_allclose(gen.ori_qp.getObjVal(), ori_f, rtol=self.RTOL, atol=self.ATOL)
        assert_allclose(gen.pos_dofs, pos_x, rtol=self.RTOL, atol=self.ATOL)
        assert_allclose(gen.pos_qp.getObjVal(), pos_f, rtol=self.RTOL, atol=self.ATOL)

    def test_qp_setup_with_toy_example_hack_from_qpoases_manual(self):
        gen = ClassicGenerator()

        options = Options()
        options.printLevel = PrintLevel.LOW


        # define matrices from qpoases manual
        H   = numpy.array([ 1.0, 0.0, 0.0, 0.5 ]).reshape((2,2))
        A   = numpy.array([ 1.0, 1.0 ]).reshape((1,2))
        g   = numpy.array([ 1.5, 1.0 ])
        lb  = numpy.array([ 0.5, -2.0 ])
        ub  = numpy.array([ 5.0, 2.0 ])
        lbA = numpy.array([ -1.0 ])
        ubA = numpy.array([ 2.0 ])

        x = numpy.array([0.5, -1.5])
        f = -6.25e-02

        # hack pattern generator
        gen.ori_nv = 2
        gen.ori_nc = 1
        gen.ori_dofs = numpy.zeros((2,))
        gen.ori_qp = SQProblem(gen.ori_nv, gen.ori_nc)
        gen.ori_qp.setOptions(options)

        gen.ori_H   = H
        gen.ori_A   = A
        gen.ori_g   = g
        gen.ori_lb  = lb
        gen.ori_ub  = ub
        gen.ori_lbA = lbA
        gen.ori_ubA = ubA

        gen.pos_nv = 2
        gen.pos_nc = 1
        gen.pos_dofs = numpy.zeros((2,))
        gen.pos_qp = SQProblem(gen.pos_nv, gen.pos_nc)
        gen.pos_qp.setOptions(options)

        gen.pos_H   = H
        gen.pos_A   = A
        gen.pos_g   = g
        gen.pos_lb  = lb
        gen.pos_ub  = ub
        gen.pos_lbA = lbA
        gen.pos_ubA = ubA

        # test first qp solution
        gen._solve_qp()

        # get solution
        # NOTE post_process put entries into array that dont match anymore
        gen.pos_qp.getPrimalSolution(gen.pos_dofs)
        gen.ori_qp.getPrimalSolution(gen.ori_dofs)

        assert_allclose(gen.pos_dofs, x, rtol=self.RTOL, atol=self.ATOL)
        assert_allclose(gen.pos_qp.getObjVal(), f, rtol=self.RTOL, atol=self.ATOL)
        assert_allclose(gen.ori_dofs, x, rtol=self.RTOL, atol=self.ATOL)
        assert_allclose(gen.ori_qp.getObjVal(), f, rtol=self.RTOL, atol=self.ATOL)

        # define matrices for warmstart
        H_new   = numpy.array([ 1.0, 0.5, 0.5, 0.5 ]).reshape((2,2))
        A_new   = numpy.array([ 1.0, 5.0 ]).reshape((1,2))
        g_new   = numpy.array([ 1.0, 1.5 ])
        lb_new  = numpy.array([ 0.0, -1.0 ])
        ub_new  = numpy.array([ 5.0, -0.5 ])
        lbA_new = numpy.array([ -2.0 ])
        ubA_new = numpy.array([ 1.0 ])

        x = numpy.array([0.5, -0.5])
        f = -1.875e-01

        # hack pattern generator
        gen.ori_H   = H_new
        gen.ori_A   = A_new
        gen.ori_g   = g_new
        gen.ori_lb  = lb_new
        gen.ori_ub  = ub_new
        gen.ori_lbA = lbA_new

        gen.pos_H   = H_new
        gen.pos_A   = A_new
        gen.pos_g   = g_new
        gen.pos_lb  = lb_new
        gen.pos_ub  = ub_new
        gen.pos_lbA = lbA_new

        # test qp warmstart
        gen._solve_qp()

        # get solution
        # NOTE post_process put entries into array that dont match anymore
        gen.pos_qp.getPrimalSolution(gen.pos_dofs)
        gen.ori_qp.getPrimalSolution(gen.ori_dofs)

        assert_allclose(gen.pos_dofs, x, rtol=self.RTOL, atol=self.ATOL)
        assert_allclose(gen.pos_qp.getObjVal(), f, rtol=self.RTOL, atol=self.ATOL)
        assert_allclose(gen.ori_dofs, x, rtol=self.RTOL, atol=self.ATOL)
        assert_allclose(gen.ori_qp.getObjVal(), f, rtol=self.RTOL, atol=self.ATOL)

    def test_qp_objective_setup_against_real_pattern_generator(self):
        # instantiate pattern generator
        gen = ClassicGenerator()

        # data follows other convention, i.e.
        # U_k = (dddC_x, dddC_y, F_x, F_y)

        # assemble pos_H and pos_g for our convention
        data_H = numpy.loadtxt(os.path.join(BASEDIR, "data", "Q.dat"), skiprows=1)
        pos_H  = numpy.zeros((gen.pos_H.shape))

        data_g = numpy.loadtxt(os.path.join(BASEDIR, "data", "P.dat"), skiprows=1)
        pos_g  = numpy.zeros((gen.pos_g.shape))

        # compare values for dddC_kp1_x
        a = 0; b = gen.N; e = 0; f = gen.N
        c = 0; d = gen.N; g = 0; h = gen.N
        pos_H[a:b,c:d] = data_H[e:f,g:h]
        pos_g[a:b]     = data_g[e:f]

        # compare values for F_k_x
        a = gen.N; b = gen.N + gen.nf-1; e = 2*gen.N + 0; f = 2*gen.N + 1
        c = gen.N; d = gen.N + gen.nf-1; g = 2*gen.N + 0; h = 2*gen.N + 1
        pos_H[a:b,c:d] = data_H[e:f,g:h]
        pos_g[a:b]     = data_g[e:f]

        # compare values for dddC_kp1_y
        a = gen.N + gen.nf; b = 2*gen.N+gen.nf; e = gen.N; f = 2*gen.N
        c = gen.N + gen.nf; d = 2*gen.N+gen.nf; g = gen.N; h = 2*gen.N
        pos_H[a:b,c:d] = data_H[e:f,g:h]
        pos_g[a:b]     = data_g[e:f]

        # compare values for F_k_x
        a = 2*gen.N +gen.nf; b = 2*gen.N + 2*gen.nf - 1; e = 2*gen.N + 1; f = 2*gen.N + 2
        c = 2*gen.N +gen.nf; d = 2*gen.N + 2*gen.nf - 1; g = 2*gen.N + 1; h = 2*gen.N + 2
        pos_H[a:b,c:d] = data_H[e:f,g:h]
        pos_g[a:b]     = data_g[e:f]

        # get box constraints from data
        pos_lb = numpy.loadtxt(os.path.join(BASEDIR, "data", "LB.dat"), skiprows=1)
        pos_ub = numpy.loadtxt(os.path.join(BASEDIR, "data", "UB.dat"), skiprows=1)

        # setup QP matrices
        gen._preprocess_solution()

        # test Hessian and gradient
        assert_allclose(gen.pos_H, pos_H, rtol=self.RTOL, atol=self.ATOL)
        assert_allclose(gen.pos_g, pos_g, rtol=self.RTOL, atol=self.ATOL)

    def test_qpO_constraint_setup_against_real_pattern_generator(self):
        # instantiate pattern generator
        gen = ClassicGenerator()

        # data follows other convention, i.e.
        # U_k = (dddC_x, dddC_y, F_x, F_y)

        # get linear constraints from data
        pos_lbA = numpy.loadtxt(
            os.path.join(BASEDIR, "data", "lbA.dat"), skiprows=1)

        # get box constraints from data
        pos_lb = numpy.loadtxt(os.path.join(BASEDIR, "data", "LB.dat"), skiprows=1)
        pos_ub = numpy.loadtxt(os.path.join(BASEDIR, "data", "UB.dat"), skiprows=1)

        # setup QP matrices
        gen._preprocess_solution()

        # test linear constraints
        assert_allclose(gen.pos_lbA[:-gen.pos_nc_eqfoot], pos_lbA, rtol=self.RTOL, atol=self.ATOL)

        # test box constraints
        assert_allclose(gen.pos_lb[:34], pos_lb, rtol=self.RTOL, atol=self.ATOL)
        assert_allclose(gen.pos_ub[:34], pos_ub, rtol=self.RTOL, atol=self.ATOL)

    def test_generator_with_zero_reference_velocity(self):
        gen = ClassicGenerator()

        # set reference velocities to zero
        gen.dC_kp1_x_ref[...] = 0.0
        gen.dC_kp1_y_ref[...] = 0.0
        gen.dC_kp1_q_ref[...] = 0.0

        gen.solve()

        for i in range(100):
            gen.c_k_x[0] = gen.  C_kp1_x[0]
            gen.c_k_x[1] = gen. dC_kp1_x[0]
            gen.c_k_x[2] = gen.ddC_kp1_x[0]

            gen.c_k_y[0] = gen.  C_kp1_y[0]
            gen.c_k_y[1] = gen. dC_kp1_y[0]
            gen.c_k_y[2] = gen.ddC_kp1_y[0]

            gen.c_k_q[0] = gen.  C_kp1_q[0]
            gen.c_k_q[1] = gen. dC_kp1_q[0]
            gen.c_k_q[2] = gen.ddC_kp1_q[0]

            gen.update()
            gen.solve()

            assert_allclose(gen.dddC_k_x, 0.0, rtol=self.RTOL, atol=self.ATOL)
            assert_allclose(gen.dddC_k_y, 0.0, rtol=self.RTOL, atol=self.ATOL)
            assert_allclose(gen.dddC_k_q, 0.0, rtol=self.RTOL, atol=self.ATOL)

            assert_allclose(gen.F_k_x, 0.0, rtol=self.RTOL, atol=self.ATOL)
            assert_allclose(gen.F_k_y, 0.0, rtol=self.RTOL, atol=self.ATOL)
            assert_allclose(gen.F_k_q, 0.0, rtol=self.RTOL, atol=self.ATOL)

    def test_against_real_pattern_genererator_walkForward2m_s(self):
        # get test data
        data = numpy.loadtxt(os.path.join(BASEDIR, "data",
            "walkForward2m_s.dat")
        )

        #
        gen = ClassicGenerator()

        # define reference velocity
        dC_kp1_x_ref = numpy.zeros((data.shape[0], gen.N), dtype=float)
        dC_kp1_y_ref = numpy.zeros((data.shape[0], gen.N), dtype=float)
        dC_kp1_q_ref = numpy.zeros((data.shape[0], gen.N), dtype=float)

        dC_kp1_x_ref[50:,:] = 0.2 #m/s
        dC_kp1_y_ref[50:,:] = 0.2 #m/s

        gen.dC_kp1_x_ref[:] = dC_kp1_x_ref[0,:]
        gen.dC_kp1_y_ref[:] = dC_kp1_y_ref[0,:]

        gen.solve()

        for i in range(100):
            print 'iteration: i = ', i
            gen.dC_kp1_x_ref[:] = dC_kp1_x_ref[i,:]
            gen.dC_kp1_y_ref[:] = dC_kp1_y_ref[i,:]

            gen.c_k_x[0] = gen.  C_kp1_x[0]
            gen.c_k_x[1] = gen. dC_kp1_x[0]
            gen.c_k_x[2] = gen.ddC_kp1_x[0]

            gen.c_k_y[0] = gen.  C_kp1_y[0]
            gen.c_k_y[1] = gen. dC_kp1_y[0]
            gen.c_k_y[2] = gen.ddC_kp1_y[0]

            gen.c_k_q[0] = gen.  C_kp1_q[0]
            gen.c_k_q[1] = gen. dC_kp1_q[0]
            gen.c_k_q[2] = gen.ddC_kp1_q[0]

            gen.update()
            gen.solve()

            # get reference from data
            dddC_k_x = data[i,  0:16]
            dddC_k_y = data[i, 18:34]
            F_k_x    = data[i, 16:18]
            F_k_y    = data[i, 34:36]

            assert_allclose(gen.dddC_k_x, dddC_k_x, rtol=self.RTOL, atol=self.ATOL)
            assert_allclose(gen.dddC_k_y, dddC_k_y, rtol=self.RTOL, atol=self.ATOL)
            assert_allclose(gen.dddC_k_y, 0.0, rtol=self.RTOL, atol=self.ATOL)

            assert_allclose(gen.F_k_x, F_k_x, rtol=self.RTOL, atol=self.ATOL)
            assert_allclose(gen.F_k_y, F_k_y, rtol=self.RTOL, atol=self.ATOL)
            assert_allclose(gen.F_k_q, 0.0, rtol=self.RTOL, atol=self.ATOL)

    def test_against_real_pattern_genererator_walk_forward_interpolation(self):
         # get test data
         data = numpy.loadtxt(os.path.join(BASEDIR, "data",
             "walkForward2m_sInterpolation.dat")
         )

         time   = data[:, 0]
         C_x    = data[:, 1]
         C_y    = data[:, 2]
         C_z    = data[:, 3]
         C_q    = data[:, 4]
         dC_x   = data[:, 5]
         dC_y   = data[:, 6]
         dC_z   = data[:, 7]
         Z_x    = data[:, 8]
         Z_y    = data[:, 9]
         Fl_x   = data[:,10]
         Fl_y   = data[:,11]
         Fl_z   = data[:,12]
         dFl_x  = data[:,13]
         dFl_y  = data[:,14]
         dFl_z  = data[:,15]
         ddFl_x = data[:,16]
         ddFl_y = data[:,17]
         ddFl_z = data[:,18]
         Fl_q   = data[:,19]
         dFl_q  = data[:,20]
         ddFl_q = data[:,21]
         Fr_x   = data[:,10]
         Fr_y   = data[:,11]
         Fr_z   = data[:,12]
         dFr_x  = data[:,13]
         dFr_y  = data[:,14]
         dFr_z  = data[:,15]
         ddFr_x = data[:,16]
         ddFr_y = data[:,17]
         ddFr_z = data[:,18]
         Fr_q   = data[:,19]
         dFr_q  = data[:,20]
         ddFr_q = data[:,21]

         gen = ClassicGenerator()

    def test_against_real_pattern_genererator_walkSideward2m_s(self):
        # get test data
        data = numpy.loadtxt(os.path.join(BASEDIR, "data",
            "walkSideward2m_s.dat")
        )

    def test_against_real_pattern_genererator_walk_sideward_interpolation(self):
        # get test data
        data = numpy.loadtxt(os.path.join(BASEDIR, "data",
            "walkSideward2m_sInterpolation.dat")
        )

        time   = data[:, 0]
        C_x    = data[:, 1]
        C_y    = data[:, 2]
        C_z    = data[:, 3]
        C_q    = data[:, 4]
        dC_x   = data[:, 5]
        dC_y   = data[:, 6]
        dC_z   = data[:, 7]
        Z_x    = data[:, 8]
        Z_y    = data[:, 9]
        Fl_x   = data[:,10]
        Fl_y   = data[:,11]
        Fl_z   = data[:,12]
        dFl_x  = data[:,13]
        dFl_y  = data[:,14]
        dFl_z  = data[:,15]
        ddFl_x = data[:,16]
        ddFl_y = data[:,17]
        ddFl_z = data[:,18]
        Fl_q   = data[:,19]
        dFl_q  = data[:,20]
        ddFl_q = data[:,21]
        Fr_x   = data[:,10]
        Fr_y   = data[:,11]
        Fr_z   = data[:,12]
        dFr_x  = data[:,13]
        dFr_y  = data[:,14]
        dFr_z  = data[:,15]
        ddFr_x = data[:,16]
        ddFr_y = data[:,17]
        ddFr_z = data[:,18]
        Fr_q   = data[:,19]
        dFr_q  = data[:,20]
        ddFr_q = data[:,21]


if __name__ == '__main__':
    try:
        import nose
        nose.runmodule()
    except ImportError:
        err_str = 'nose needed for unittests.\nPlease install using:\n   sudo pip install nose'
        raise ImportError(err_str)
