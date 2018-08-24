# -*- coding: utf-8 -*-
"""
Created on Sat Aug  4 21:57:55 2018

@author: romeoorsolino
"""
import numpy as np

from context import legsthrust 

import time

from pypoman.lp import solve_lp, GLPK_IF_AVAILABLE
from pypoman.bretl import Vertex
from pypoman.bretl import Polygon

import random
import cvxopt
from cvxopt import matrix, solvers

from numpy import array, cos, cross, pi, sin
from numpy.random import random
from scipy.linalg import norm
from scipy.linalg import block_diag

from context import legsthrust 

from numpy import array, cross, dot, eye, hstack, vstack, zeros

import matplotlib.pyplot as plt
from legsthrust.plotting_tools import Plotter
from legsthrust.constraints import Constraints
from legsthrust.hyq_kinematics import HyQKinematics
from legsthrust.math_tools import Math
from legsthrust.computational_dynamics import ComputationalDynamics
from legsthrust.height_map import HeightMap

class VertexVariableConstraints():
    def __init__(self, p):
        self.x = p[0]
        self.y = p[1]
        self.next = None
        self.expanded = False

    def length(self):
        return norm([self.x-self.next.x, self.y-self.next.y])
        
    def expand(self, lp):
        #print "EXPAND VERTICES VARIABLE CONSTRAINTS"
        v1 = self
        v2 = self.next
        direction = array([v2.y - v1.y, v1.x - v2.x])  # orthogonal direction to edge
        direction = 1 / norm(direction) * direction
        #print "Current vertices V1: ", v1.x, v1.y        
        #print "Current vertices V2: ", v2.x, v2.y        
        #print "New direction ", direction
        try:
            comWorldFrame = np.array([v1.x, v1.y, 0.0])
            #print comWorldFrame
            comWorldFrame = np.array([0.0, 0.0, 0.0])
            z = optimize_direction_variable_constraint(lp, direction)
        except ValueError:
            self.expanded = True
            return False, None
        xopt, yopt = z
        delta_area = cross([xopt-v1.x, yopt-v1.y], [v1.x-v2.x, v1.y-v2.y])
        delta_area_abs = abs(cross([xopt-v1.x, yopt-v1.y], [v1.x-v2.x, v1.y-v2.y]))
        #print "Area: ",delta_area
        if delta_area_abs < 1e-2:
            self.expanded = True
            #print "the area is small enough so the vertex expansion is over"
            return False, None
        else:
            vnew = VertexVariableConstraints([xopt, yopt])
            vnew.next = self.next
            self.next = vnew
            self.expanded = False
            return True, vnew
            
class PolygonVariableConstraint():
    
    def from_vertices(self, v1, v2, v3):
        v1.next = v2
        v2.next = v3
        v3.next = v1
        self.vertices = [v1, v2, v3]

    def all_expanded(self):
        for v in self.vertices:
            if not v.expanded:
                return False
        return True
        
    def iter_expand(self, lp, max_iter):
        """
        Returns true if there's a edge that can be expanded, and expands that
        edge, otherwise returns False.
        """
        #print "START expansion"
        nb_iter = 0
        v = self.vertices[0]
        while not self.all_expanded() and nb_iter < max_iter:
            #print "iter expand"
            if v.expanded:
                v = v.next
                continue
            res, vnew = v.expand(lp)
            if not res:
                continue
            self.vertices.append(vnew)
            nb_iter += 1
        #print "STOP expansion"
        
    def sort_vertices(self):
        """
        Export vertices starting from the left-most and going clockwise.
        Assumes all vertices are on the positive halfplane.
        """
        minsd = 1e10
        ibottom = 0
        for i in range(len(self.vertices)):
            v = self.vertices[i]
            if (v.y + v.next.y) < minsd:
                ibottom = i
                minsd = v.y + v.next.y
        for v in self.vertices:
            v.checked = False
        vcur = self.vertices[ibottom]
        newvertices = []
        while not vcur.checked:
            vcur.checked = True
            newvertices.append(vcur)
            vcur = vcur.next
        newvertices.reverse()
        vfirst = newvertices.pop(-1)
        newvertices.insert(0, vfirst)
        self.vertices = newvertices

    def export_vertices(self, threshold=1e-2):
        export_list = [self.vertices[0]]
        for i in range(1, len(self.vertices)-1):
            vcur = self.vertices[i]
            vlast = export_list[-1]
            if norm([vcur.x-vlast.x, vcur.y-vlast.y]) > threshold:
                export_list.append(vcur)
        export_list.append(self.vertices[-1])  # always add last vertex
        return export_list
        
class IterativeProjection:
        
    def setup_iterative_projection(self, contacts, comWF, trunk_mass, mu, normals):
        ''' parameters to be tuned'''
        g = 9.81
        isOutOfWorkspace = False;

        grav = array([0., 0., -g])
        contactsNumber = np.size(contacts,0)
        # Unprojected state is:
        #
        #     x = [f1_x, f1_y, f1_z, ... , f3_x, f3_y, f3_z]
        Ex = np.zeros((0)) 
        Ey = np.zeros((0))        
        G = np.zeros((6,0))   
        for j in range(0,contactsNumber):
            r = contacts[j,:]
            graspMatrix = compDyn.getGraspMatrix(r)[:,0:3]
            Ex = hstack([Ex, -graspMatrix[4]])
            Ey = hstack([Ey, graspMatrix[3]])
            G = hstack([G, graspMatrix])            
            
        E = vstack((Ex, Ey)) / (g)
        f = zeros(2)
        proj = (E, f)  # y = E * x + f
        
        # number of the equality constraints
        m_eq = 6
        
        # see Equation (52) in "ZMP Support Areas for Multicontact..."
        A_f_and_tauz = array([
            [1, 0, 0, 0, 0, 0],
            [0, 1, 0, 0, 0, 0],
            [0, 0, 1, 0, 0, 0],
            [0, 0, 0, 0, 0, 1]])
        A = dot(A_f_and_tauz, G)
        t = hstack([0, 0, g, 0])
        #print A,t
        eq = (A, t)  # A * x == t
        
        act_LF = np.zeros((0,1))
        act_RF = np.zeros((0,1))
        act_LH = np.zeros((0,1))
        act_RH = np.zeros((0,1))
        actuation_polygons = np.zeros((0,1))
        # Inequality matrix for a contact force in local contact frame:
        constr = Constraints()
        #C_force = constr.linearized_cone_halfspaces(ng, mu)
        # Inequality matrix for stacked contact forces in world frame:
        if constraint_mode == 'ONLY_FRICTION':
            C, d = constr.linearized_cone_halfspaces_world(contactsNumber, ng, mu, normals)
            
        elif constraint_mode == 'ONLY_ACTUATION':
            #kin = Kinematics()
            kin = HyQKinematics()
            foot_vel = np.array([[0, 0, 0],[0, 0, 0],[0, 0, 0],[0, 0, 0]])
            contactsFourLegs = np.vstack([contacts, np.zeros((4-contactsNumber,3))])
            q, q_dot, J_LF, J_RF, J_LH, J_RH, isOutOfWorkspace = kin.inverse_kin(np.transpose(contactsFourLegs[:,0] - comWF[0]),
                                                  np.transpose(foot_vel[:,0]),
                                                    np.transpose(contactsFourLegs[:,1] - comWF[1]),
                                                    np.transpose(foot_vel[:,1]),
                                                    np.transpose(contactsFourLegs[:,2] - comWF[2]),
                                                    np.transpose(foot_vel[:,2]))
            J_LF, J_RF, J_LH, J_RH = kin.update_jacobians(q)

            if isOutOfWorkspace:
                C = np.zeros((0,0))
                d = np.zeros((1,0))
            else:
                act_LF = constr.computeActuationPolygon(J_LF)
                act_RF = constr.computeActuationPolygon(J_RF)
                act_LH = constr.computeActuationPolygon(J_LH)
                act_RH = constr.computeActuationPolygon(J_RH)            
                ''' in the case of the IP alg. the contact force limits must be divided by the mass
                because the gravito inertial wrench is normalized'''
                
                C = np.zeros((0,0))
                d = np.zeros((1,0))
                actuation_polygons = np.array([act_LF,act_RF,act_LH,act_RH])
                for j in range (0,contactsNumber):
                    hexahedronHalfSpaceConstraints, knownTerm = constr.hexahedron(actuation_polygons[j]/trunk_mass)
                    C = block_diag(C, hexahedronHalfSpaceConstraints)
                    d = hstack([d, knownTerm.T])
                    
                d = d.reshape(6*contactsNumber)    
                #C = block_diag(c1, c2, c3, c4)
                #d = np.vstack([e1, e2, e3, e4]).reshape(6*4)
                #print C, d
        
        ineq = (C, d)  # C * x <= d
        
        if isOutOfWorkspace:
            lp = 0
        else:
            max_radius=1e5
            (E, f), (A, b), (C, d) = proj, ineq, eq
            assert E.shape[0] == f.shape[0] == 2
            # Inequality constraints: A_ext * [ x  u  v ] <= b_ext iff
            # (1) A * x <= b and (2) |u|, |v| <= max_radius
            A_ext = zeros((A.shape[0] + 4, A.shape[1] + 2))
            A_ext[:-4, :-2] = A
            A_ext[-4, -2] = 1
            A_ext[-3, -2] = -1
            A_ext[-2, -1] = 1
            A_ext[-1, -1] = -1
            A_ext = cvxopt.matrix(A_ext)
            
            b_ext = zeros(b.shape[0] + 4)
            b_ext[:-4] = b
            b_ext[-4:] = array([max_radius] * 4)
            b_ext = cvxopt.matrix(b_ext)
            
            # Equality constraints: C_ext * [ x  u  v ] == d_ext iff
            # (1) C * x == d and (2) [ u  v ] == E * x + f
            C_ext = zeros((C.shape[0] + 2, C.shape[1] + 2))
            C_ext[:-2, :-2] = C
            C_ext[-2:, :-2] = E[:2]
            C_ext[-2:, -2:] = array([[-1, 0], [0, -1]])
            C_ext = cvxopt.matrix(C_ext)
            
            d_ext = zeros(d.shape[0] + 2)
            d_ext[:-2] = d
            d_ext[-2:] = -f[:2]
            d_ext = cvxopt.matrix(d_ext)
            
            lp_obj = cvxopt.matrix(zeros(A.shape[1] + 2))
            lp = lp_obj, A_ext, b_ext, C_ext, d_ext
        
        return lp, actuation_polygons/trunk_mass, isOutOfWorkspace

def optimize_direction_variable_constraint(lp, vdir, solver=GLPK_IF_AVAILABLE):
    #print 'I am hereeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee'
    """
    Optimize in one direction.

    Parameters
    ----------
    vdir : (3,) array
        Direction in which the optimization is performed.
    lp : array tuple
        Tuple `(q, G, h, A, b)` defining the LP. See
        :func:`pypoman.lp..solve_lp` for details.
    solver : string, optional
        Backend LP solver to call.

    Returns
    -------
    succ : bool
        Success boolean.
    z : (3,) array, or 0
        Maximum vertex of the polygon in the direction `vdir`, or 0 in case of
        solver failure.
    """
    """ contact points """
            
    lp_q, lp_Gextended, lp_hextended, lp_A, lp_b = lp
    lp_q[-2] = -vdir[0]
    lp_q[-1] = -vdir[1]
    x = solve_lp(lp_q, lp_Gextended, lp_hextended, lp_A, lp_b, solver=solver)
    tempSolution = x[-2:]

    return tempSolution
    #return comWorld[0:2], errorNorm


def optimize_angle_variable_constraint(lp, theta, solver=GLPK_IF_AVAILABLE):

    """
    Optimize in one direction.

    Parameters
    ----------
    theta : scalar
        Angle of the direction in which the optimization is performed.
    lp : array tuple
        Tuple `(q, G, h, A, b)` defining the LP. See
        :func:`pypoman.lp..solve_lp` for details.
    solver : string, optional
        Backend LP solver to call.

    Returns
    -------
    succ : bool
        Success boolean.
    z : (3,) array, or 0
        Maximum vertex of the polygon in the direction `vdir`, or 0 in case of
        solver failure.
    """
    #print "Optimize angle!!!!!!!!!!!!!!!!!!!!!!"
    d = array([cos(theta), sin(theta)])
    z = optimize_direction_variable_constraint(lp, d, solver=solver)
    return z


def compute_polygon_variable_constraint(comWorldFrame, contactsWorldFrame, max_iter=50, solver=GLPK_IF_AVAILABLE):
    """
    Expand a polygon iteratively.

    Parameters
    ----------
    lp : array tuple
        Tuple `(q, G, h, A, b)` defining the linear program. See
        :func:`pypoman.lp.solve_lp` for details.
    max_iter : integer, optional
        Maximum number of calls to the LP solver.
    solver : string, optional
        Name of backend LP solver.

    Returns
    -------
    poly : Polygon
        Output polygon.
    """

    trunk_mass = 100
    mu = 0.8

    axisZ= array([[0.0], [0.0], [1.0]])
    
    n1 = np.transpose(np.transpose(math.rpyToRot(0.0,0.0,0.0)).dot(axisZ))
    n2 = np.transpose(np.transpose(math.rpyToRot(0.0,0.0,0.0)).dot(axisZ))
    n3 = np.transpose(np.transpose(math.rpyToRot(0.0,0.0,0.0)).dot(axisZ))
    n4 = np.transpose(np.transpose(math.rpyToRot(0.0,0.0,0.0)).dot(axisZ))
    # %% Cell 2
    normals = np.vstack([n1, n2, n3, n4])
        
    iterProj = IterativeProjection()
    
    lp, actuation_polygons, isOutOfWorkspace = iterProj.setup_iterative_projection(contactsWorldFrame, comWorldFrame, trunk_mass, mu, normals)
    
    if isOutOfWorkspace:
        return False
    else:
        two_pi = 2 * pi
        theta = pi * random()
        init_vertices = [optimize_angle_variable_constraint(lp, theta, solver)]
        step = two_pi / 3
        while len(init_vertices) < 3 and max_iter >= 0:
            theta += step
            if theta >= two_pi:
                step *= 0.25 + 0.5 * random()
                theta += step - two_pi
            #comWorldFrame = np.array([0.0, 0.0, 0.0])
            z = optimize_angle_variable_constraint(lp, theta, solver)
            if all([norm(z - z0) > 1e-5 for z0 in init_vertices]):
                init_vertices.append(z)
            max_iter -= 1
        if len(init_vertices) < 3:
            raise Exception("problem is not linearly feasible")
        v0 = Vertex(init_vertices[0])
        v1 = Vertex(init_vertices[1])
        v2 = Vertex(init_vertices[2])
        polygon = Polygon()
        polygon.from_vertices(v0, v1, v2)
        polygon.iter_expand(lp, max_iter)
        return polygon

def line(p1, p2):
    A = (p1[1] - p2[1])
    B = (p2[0] - p1[0])
    C = (p1[0]*p2[1] - p2[0]*p1[1])
    return A, B, -C

def two_lines_intersection(L1, L2):
    D  = L1[0] * L2[1] - L1[1] * L2[0]
    Dx = L1[2] * L2[1] - L1[1] * L2[2]
    Dy = L1[0] * L2[2] - L1[2] * L2[0]
    if D != 0:
        x = Dx / D
        y = Dy / D
        return x,y
    else:
        return False


def find_intersection(vertices_input, desired_direction, comWF):
    desired_direction = desired_direction/np.linalg.norm(desired_direction)
    #print "desired dir: ", desired_direction
    
    desired_com_line = line(comWF, comWF+desired_direction)
    #print "des line : ", desired_com_line
    tmp_vertices = np.vstack([vertices_input, vertices_input[0]])
    intersection_points = np.zeros((0,2))
    points = np.zeros((0,2))
    for i in range(0,len(vertices_input)):
        v1 = tmp_vertices[i]
        v2 = tmp_vertices[i+1]        
        actuation_region_edge = line(v1, v2)
        #print desired_com_line, actuation_region_edge
        new_point = two_lines_intersection(desired_com_line, actuation_region_edge)
        #print "new point ", new_point
        if new_point:
            intersection_points = np.vstack([intersection_points, new_point])
        else:
            print "lines are parallel!"
            while new_point is False:
                desired_com_line = line(comWF, comWF+desired_direction+np.array([random()*0.01,random()*0.01,0.0]))
                new_point = two_lines_intersection(desired_com_line, actuation_region_edge)
                intersection_points = np.vstack([intersection_points, new_point])
                print new_point
                
        #print intersection_points
        epsilon = 0.0001;
        if np.abs(desired_direction[0]- comWF[0]) > epsilon:
            alpha_com_x_line = (new_point[0] - comWF[0])/(desired_direction[0]- comWF[0])
        else:
            alpha_com_x_line = 1000000000.0;
            
        if np.abs(desired_direction[1]- comWF[1]) > epsilon:
            alpha_com_y_line = (new_point[1] - comWF[1])/(desired_direction[1]- comWF[1])
        else:
            alpha_com_y_line = 1000000000.0
            
        #print alpha_com_x_line, alpha_com_y_line
        
        if alpha_com_x_line > 0.0 and alpha_com_y_line >= 0.0:
            if np.abs(v2[0] - v1[0]) > epsilon:
                alpha_vertices_x = (new_point[0] - v1[0])/(v2[0] - v1[0])
            else:
                alpha_vertices_x = 0.5
            
            #print "alpha_vertices_x ", alpha_vertices_x
            if alpha_vertices_x >= 0.0 and alpha_vertices_x <= 1.0:
                if np.abs(v2[1] - v1[1]) > epsilon:
                    alpha_vertices_y = (new_point[1] - v1[1])/(v2[1] - v1[1]) 
                else:
                    alpha_vertices_y = 0.5
                
                #print "alpha vertx y ", alpha_vertices_y
                if alpha_vertices_y >= 0.0 and alpha_vertices_y <= 1.0:                   
                    points = np.vstack([points, new_point])
                            
            elif np.abs(v2[1] - v1[1]):
                alpha_vertices_y = (new_point[1] - v1[1])/(v2[1] - v1[1])            
                if alpha_vertices_y >= 0.0 and alpha_vertices_y <= 1.0:                   
                    points = np.vstack([points, new_point])
                    
    print points
    return points, intersection_points
    
    
''' MAIN '''
start_t_IPVC = time.time()
math = Math()
compDyn = ComputationalDynamics()
# number of contacts
nc = 3
# number of generators, i.e. rays used to linearize the friction cone
ng = 4

# ONLY_ACTUATION or ONLY_FRICTION
constraint_mode = 'ONLY_ACTUATION'
useVariableJacobian = True
trunk_mass = 100
mu = 0.8
# number of decision variables of the problem
n = nc*6
i = 0
comTrajectoriesToStack = np.zeros((0,3))
terrain = HeightMap()

comWF = np.array([0.1, 0.1, 0.0])
optimizedVariablesToStack = np.zeros((0,3))
iterProj = IterativeProjection()        
for_iter = 0
for LH_x in np.arange(-0.8,-0.3, 0.1):
    for LH_y in np.arange(0.1,0.4, 0.1):
        for dir_y in np.arange(-0.2,0.0,0.2):
            desired_direction = np.array([-1.0, dir_y, 0.0])
            #print "direction: ", desired_direction
            """ contact points """
            LF_foot = np.array([0.4, 0.3, -0.5])
            RF_foot = np.array([0.4, -0.3, -0.5])
            terrainHeight = terrain.get_height(LH_x, LH_y)
            LH_foot = np.array([LH_x, LH_y, terrainHeight-0.5])
            #print "Terrain height: ", LH_foot        
            RH_foot = np.array([-0.3, -0.2, -0.5])
    
            contactsToStack = np.vstack((LF_foot,RF_foot,LH_foot,RH_foot))
            contacts = contactsToStack[0:nc, :]
            #print "i am here"
            final_points = np.zeros((0,2))
            newCoM = comWF
            comToStack = np.zeros((0,3))
            increment = np.array([100.0, 100.0, 0.0])
            while_iter = 0
            #print "enter while loop"
            while (np.amax(np.abs(increment))>0.05) and (while_iter<10):
                comToStack = np.vstack([comToStack, newCoM])
                polygon = compute_polygon_variable_constraint(newCoM, contacts)
                if polygon:
                    polygon.sort_vertices()
                    vertices_list = polygon.export_vertices()
                    vertices1 = [array([v.x, v.y]) for v in vertices_list]
                    new_p, all_points = find_intersection(vertices1, desired_direction, comWF)
                    final_points = np.vstack([final_points, new_p])
                    increment = np.hstack([new_p[0], 0.0]) - newCoM
                    
                    newCoM = 0.5*increment + newCoM
                    while_iter += 1
                else:
                    print "foot position is out of workspace!"
                    while_iter += 10
                    #print "while: ",while_iter
            for_iter += 1
            #print "for ",for_iter
            comTrajectoriesToStack = np.vstack([comTrajectoriesToStack, comToStack[-1]])
            optimizedVariablesToStack = np.vstack([optimizedVariablesToStack, np.array([LH_x, LH_y, dir_y])])

print "Final CoM points ", comTrajectoriesToStack
print "Tested combinations: ", optimizedVariablesToStack

max_motion_indices = np.unravel_index(np.argsort(comTrajectoriesToStack[:,0], axis=None), comTrajectoriesToStack[:,0].shape)
max_motin_index = max_motion_indices[0][0]
print("Directed Iterative Projection: --- %s seconds ---" % (time.time() - start_t_IPVC))


''' plotting Iterative Projection points '''

axisZ= array([[0.0], [0.0], [1.0]])
n1 = np.transpose(np.transpose(math.rpyToRot(0.0,0.0,0.0)).dot(axisZ))
n2 = np.transpose(np.transpose(math.rpyToRot(0.0,0.0,0.0)).dot(axisZ))
n3 = np.transpose(np.transpose(math.rpyToRot(0.0,0.0,0.0)).dot(axisZ))
n4 = np.transpose(np.transpose(math.rpyToRot(0.0,0.0,0.0)).dot(axisZ))
        # %% Cell 2
        
normals = np.vstack([n1, n2, n3, n4])
IP_points, actuation_polygons = compDyn.iterative_projection_bretl(constraint_mode, contacts, normals, trunk_mass, ng, mu)

feasible, unfeasible, contact_forces = compDyn.LP_projection(constraint_mode, contacts, normals, trunk_mass, mu, ng, nc, mu, useVariableJacobian, 0.05, 0.05)

#IP_points_saturated_friction, actuation_polygons = compDyn.iterative_projection_bretl('ONLY_FRICTION', contacts, normals, trunk_mass, ng, mu, saturate_normal_force = True)

'''Plotting'''
plt.close('all')
plotter = Plotter()

plt.figure()
plt.grid()
plt.xlabel("X [m]")
plt.ylabel("Y [m]")
#plt.plot(intersection[:,0], intersection[:,1], 'ro', markersize=15)
#plt.plot(final_points[:,0], final_points[:,1], 'r^', markersize=20)
#plt.plot(comToStack[:,0], comToStack[:,1], 'g^', markersize=20)
#plt.plot(comToStack[-1,0], comToStack[-1,1], 'bo', markersize=20)

plt.plot(comTrajectoriesToStack[:,0], comTrajectoriesToStack[:,1], 'g^', markersize=20)
plt.plot(comTrajectoriesToStack[max_motin_index,0], comTrajectoriesToStack[max_motin_index,1], 'y^', markersize=25)
h1 = plt.plot(contacts[0:nc,0],contacts[0:nc,1],'ko',markersize=15, label='feet')

#plotter.plot_polygon(np.asanyarray(vertices1), color = 'y')

#plotter.plot_polygon(np.asanyarray(vertices2), color = 'r')

#plotter.plot_polygon(np.asanyarray(vertices3), color = 'b')

#plotter.plot_polygon(np.asanyarray(vertices4), color = 'g')

#plotter.plot_polygon(np.asanyarray(vertices5), color = 'k')

#plotter.plot_polygon(np.transpose(IP_points))

#plotter.plot_polygon(np.transpose(IP_points_saturated_friction), color = '--r')

feasiblePointsSize = np.size(feasible,0)
for j in range(0, feasiblePointsSize):
    if (feasible[j,2]<0.01)&(feasible[j,2]>-0.01):
        plt.scatter(feasible[j,0], feasible[j,1],c='g',s=50)
        lastFeasibleIndex = j
unfeasiblePointsSize = np.size(unfeasible,0)

for j in range(0, unfeasiblePointsSize):
    if (unfeasible[j,2]<0.01)&(unfeasible[j,2]>-0.01):
        plt.scatter(unfeasible[j,0], unfeasible[j,1],c='r',s=50)
        lastUnfeasibleIndex = j
h2 = plt.scatter(feasible[lastFeasibleIndex,0], feasible[lastFeasibleIndex,1],c='g',s=50, label='LP feasible')
h3 = plt.scatter(unfeasible[lastUnfeasibleIndex,0], unfeasible[lastUnfeasibleIndex,1],c='r',s=50, label='LP unfeasible')

plt.plot(optimizedVariablesToStack[:,0], optimizedVariablesToStack[:,1], 'ko', markersize = 15)
plt.plot(optimizedVariablesToStack[max_motin_index,0], optimizedVariablesToStack[max_motin_index,1], 'yo', markersize=25)
plt.xlim(-0.9, 0.5)
plt.ylim(-0.7, 0.7)
plt.legend()
plt.show()

