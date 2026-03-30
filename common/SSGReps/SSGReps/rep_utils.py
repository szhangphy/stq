from turtle import position
import numpy as np
from spglib import *
from numpy.linalg import norm, inv, det
import os
from pymatgen.symmetry.analyzer import PointGroupAnalyzer
import pickle
import warnings

from collections import OrderedDict

from tqdm import tqdm
from math import cos, sin, acos, asin, pi, sqrt, tan
from SG_utils import *

def round_vec(vec, tol=1e-6):
    return np.array([np.round(v) if abs(v - np.round(v)) < tol else v for v in vec]) 

def vec_is_int(vec, tol=1e-6):
    return True if norm(vec - np.round(vec)) < tol else False

def round_num(num, tol=1e-6):
    return int(round(num)) if abs(num - round(num)) < tol else num
    
def round_mat(m, tol=1e-6):
    return np.array(np.round(m), dtype=int) if norm(m - np.round(m)) < tol else m

def get_rotation(R):
    det = np.linalg.det(R)
    tmpR = det * R
    arg = (np.trace(tmpR) - 1) / 2
    if arg > 1:
        arg = 1
    elif arg < -1:
        arg = -1
    angle = acos(arg)
    axis = np.zeros((3, 1))
    if abs(abs(angle) - pi) < 1e-4:
        for i in range(3):
            axis[i] = 1
            axis = axis + np.dot(tmpR, axis)
            if max(abs(axis)) > 1e-1:
                break
        assert max(abs(axis)) > 1e-1, 'can\'t find axis'
        axis = axis / np.linalg.norm(axis)
    elif abs(angle) > 1e-3:
        # standard case, see Altmann's book
        axis[0] = tmpR[2, 1] - tmpR[1, 2]
        axis[1] = tmpR[0, 2] - tmpR[2, 0]
        axis[2] = tmpR[1, 0] - tmpR[0, 1]
        axis = axis / sin(angle) / 2
    elif abs(angle) < 1e-4:
        axis[0] = 1

    return angle, axis, det

# def get_rotation(R, return_list=False):
#     det = np.linalg.det(R)
#     assert np.allclose(abs(det), 1), det
#     det = round(det)
#     tmpR = det * R
#     arg = (np.trace(tmpR) - 1) / 2
#     if arg > 1:
#         arg = 1
#     elif arg < -1:
#         arg = -1
#     angle = acos(arg)
#     axis = np.zeros(3)
#     if abs(abs(angle) - pi) < 1e-4:
#         for i in range(3):
#             axis[i] = 1
#             axis = axis + np.dot(tmpR, axis)
#             if max(abs(axis)) > 1e-1:
#                 break
#         assert max(abs(axis)) > 1e-1, 'can\'t find axis'
#     elif abs(angle) > 1e-3:
#         # standard case, see Altmann's book
#         axis[0] = tmpR[2, 1] - tmpR[1, 2]
#         axis[1] = tmpR[0, 2] - tmpR[2, 0]
#         axis[2] = tmpR[1, 0] - tmpR[0, 1]
#         axis = axis / sin(angle) / 2
#     elif abs(angle) < 1e-4:
#         axis[0] = 1
#     # for non-orthogonal coordinates, axis may have norm>1, need to normalize
#     axis = axis / np.linalg.norm(axis)
#     axis = round_vec(axis)
#     if axis[2] != 0:
#         if axis[2] < 0:
#             angle = 2*pi-angle
#         axis = [axis[0]/axis[2], axis[1]/axis[2], 1]
#         axis = round_vec(axis)     
#     elif axis[1] != 0:
#         if axis[1] < 0:
#             angle = 2*pi-angle
#         axis = [axis[0]/axis[1], 1, 0]
#         axis = round_vec(axis)
#     else:
#         if axis[0] < 0:
#             angle = 2*pi-angle
#         axis = [1, 0, 0]     
#     angle = angle / pi * 180
#     if return_list:
#         return [det, angle, axis[0], axis[1], axis[2]]
#     else:
#         return angle, axis, det


# judge 2 tau are the same by supercell
# for example,  010 and 120 are the same if 110 is the linear combination of supercell
# there exit integer a,b and c ,  a* s1 + b* s2 + c*s3 = tau1 - tau2
def identity_tau(tau1, tau2, supercell, gid):
    prim_vec = identify_SG_lattice(gid)[1] # each col is a prim basis vector   
    t1 = np.array([supercell[0][0], supercell[1][0], supercell[2][0]]) 
    t2 = np.array([supercell[0][1], supercell[1][1], supercell[2][1]]) 
    t3 = np.array([supercell[0][2], supercell[1][2], supercell[2][2]])
    s1 = prim_vec @ t1
    s2 = prim_vec @ t2
    s3 = prim_vec @ t3
    A = np.array([[s1[0], s2[0], s3[0]], [s1[1], s2[1], s3[1]], [s1[2], s2[2], s3[2]]])
    B = tau1 - tau2
    solve = np.linalg.solve(A, B)
    l1 = solve[0]
    l2 = solve[1]
    l3 = solve[2]
    for l in [l1, l2, l3]:
        if np.abs(l - np.round(l)) > 1e-4:
            return [False, 0, 0, 0]
    return [True, int(round(l1)), int(round(l2)), int(round(l3))]


def SU2(so3):  
    # SU2 matrix calculated from SO3 matrix, may be different from su2s read from Bilbao
    sigma0 = np.array([[1, 0], [0, 1]], dtype=complex)
    sigma1 = np.array([[0, 1], [1, 0]], dtype=complex)
    sigma2 = np.array([[0, -1j], [1j, 0]], dtype=complex)
    sigma3 = np.array([[1, 0], [0, -1]], dtype=complex)
    # A = np.array([self.basisP[0], self.basisP[1], self.basisP[2]], dtype=float).T
    # B = np.linalg.inv(A)
    # for iop in range(len(self.rotP)):
    if 1:
        # rotCart = np.dot(np.dot(A, self.rotP[iop]), B)  # SO3 matrix in Cartesian coordinates
        angle, axis, det = get_rotation(so3)
        # print(angle, axis)
        # print(so3)
        su2 = cos(angle / 2) * sigma0 - 1j * sin(angle / 2) * (axis[0] * sigma1 + axis[1] * sigma2 + axis[2] * sigma3)
        # selsu2c.append(su2)
        return su2

def round_complex_matrix(matrix, decimals=4):
    # Round each element of the complex matrix to the specified number of decimals
    rounded_matrix = np.around(matrix, decimals=decimals)
    return rounded_matrix


def print_mat(mat, wfile=None, print1=True):
    dim = np.shape(mat)[0]
    len_dim = len(np.shape(mat))
    strg = ''
    if len_dim > 1:
        for row in range(dim):
            strg += '[ '
            for col in range(dim):
                num = mat[row, col]
                if abs(num) < 1e-8:
                    strg += '     0      '
                elif abs(num.real) < 1e-8:
                    strg += ' %4.3f *I ' % (num.imag)
                elif abs(num.imag) < 1e-8:
                    strg += ' %4.3f ' % (num.real)
                else:
                    strg += ' (%4.3f + %4.3f *I) ' % (num.real, num.imag)
            strg += ' ]\n'
        if print1:
            print(strg, file=wfile)
        else:
            return strg
    else:
        strg += '[ '
        for row in range(dim):
            num = mat[row]
            if abs(num) < 1e-8:
                strg += '     0      '
            elif abs(num.real) < 1e-8:
                strg += ' %4.3f *I ' % (num.imag)
            elif abs(num.imag) < 1e-8:
                strg += ' %4.3f ' % (num.real)
            else:
                strg += ' (%4.3f + %4.3f *I) ' % (num.real, num.imag)
        strg += ' ]'
        if print1:
            print(strg, file=wfile)
        else:
            return strg

def print_matlist(matlist):
    for cnt,mat in enumerate(matlist):
        print(cnt+1,':')
        print_mat(mat)


def print_tau(mat):
    dim = np.shape(mat)[0]

    for row in range(dim):
        strg += '[ '
        if 1:
            num = mat[row]
            if abs(num) < 1e-8:
                strg += '     0      '
            elif abs(num.real) < 1e-8:
                strg += ' %4.3f *I ' % (num.imag)
            elif abs(num.imag) < 1e-8:
                strg += ' %4.3f ' % (num.real)
            else:
                strg += ' (%4.3f + %4.3f *I) ' % (num.real, num.imag)
        strg += ' ]\n'

def print_taulist(matlist):
    for cnt,mat in enumerate(matlist):
        print(cnt+1,':')
        print_tau(mat)


def generate_random_matrix(g):
    # Generate a g x g matrix with random numbers in the range [1, 6]
    if g == 2:
        random_matrix = np.array([
            [1.23456 + 1j* 2.14793, 1.57993 + 1j* 4.22339],
            [3.4563277 + 1j* 1.778431, 2.3399532 + 1j* 5.114779]
        ])
        return random_matrix
    random_matrix = 10 * np.random.rand(g, g) + 10*1j * np.random.rand(g, g)
    # random_matrix = np.random.randint(1, 100, size=(g, g)) + 1j * np.random.randint(1, 100, size=(g, g))
    # print_mat(random_matrix)
    return random_matrix

def calculate_diagonal_sums(arr, repetitions):
    diagonal_sums = []
    current_index = 0
    diag = np.diagonal(arr)
    
    for rep in repetitions:
        diagonal_sum = np.sum(diag[current_index : current_index + rep])
        diagonal_sums.append(diagonal_sum)
        current_index += rep
        
    return diagonal_sums
def cal_repetitions(arr, tolerance):
    repetitions = []
    current_count = 1
    
    for i in range(1, len(arr)):
        if abs(arr[i] - arr[i - 1]) <= tolerance:
            current_count += 1
        else:
            repetitions.append(current_count)
            current_count = 1
    
    repetitions.append(current_count)
    return repetitions

def extract_submatrix(matrix, indices):
    # 将行和列索引列表进行排序，以确保按顺序提取子矩阵
    indices.sort()
    submatrix = matrix[np.ix_(indices, indices)]
    return submatrix

import numpy as np

def TwistOperator(A, B):
    na1 = np.size(A, 0)
    nb1 = np.size(B, 0)

    z0a = np.zeros((na1, na1), dtype=complex)
    z0b = np.zeros((nb1, nb1), dtype=complex)

    Twist = np.kron(z0a, z0b)

    for k in range(na1):
        for j in range(na1):
            for l in range(nb1):
                for i in range(nb1):
                    Twist[k * nb1 + l, i * nb1 + j] = A[k, j] * B[l, i]

    return Twist



def SchmidtOrthogonalization(in_matrix):
    # Get the size of the input matrix
    _, n = in_matrix.shape
    
    # Initialize the orthogonal matrix
    OrthMatrix = np.zeros_like(in_matrix)

    if n > 1:
        OrthMatrix[:, 0] = in_matrix[:, 0]

    # Orthogonalization
    for k in range(1, n):
        for t in range(k):
            OrthMatrix[:, k] = OrthMatrix[:, k] - np.dot(OrthMatrix[:, t], in_matrix[:, k]) / np.dot(OrthMatrix[:, t], OrthMatrix[:, t]) * OrthMatrix[:, t]
        OrthMatrix[:, k] = OrthMatrix[:, k] + in_matrix[:, k]

    # Normalization
    for k in range(n):
        OrthMatrix[:, k] = OrthMatrix[:, k] / np.linalg.norm(OrthMatrix[:, k], ord='fro')

    return OrthMatrix



def combine_array(nested_list):
    flat_list = [item for sublist in nested_list for item in sublist]
    return flat_list


if __name__ == '__main__':
    C2x = np.array([[1,0,0],[0,-1,0],[0,0,-1]])
    C2z = np.array([[-1,0,0],[0,-1,0],[0,0,1]])
    print(SU2(C2z))