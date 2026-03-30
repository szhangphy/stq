from turtle import position
import numpy as np
from spglib import *
from numpy.linalg import norm, inv, det
import os
from pymatgen.symmetry.analyzer import PointGroupAnalyzer
import pickle
import warnings
import sys


from collections import OrderedDict

from itertools import combinations
from tqdm import tqdm
from math import cos, sin, acos, asin, pi, sqrt, tan, exp
from rep_utils import *
from SG_utils import *

from scipy.linalg import null_space, sqrtm

from itertools import permutations, chain
from sympy import sqrt, I, Integer,MatrixSymbol
from sympy import symbols, Mul
from sympy.matrices import Matrix
from sympy.matrices import  eye,zeros
from sympy.physics.quantum import TensorProduct
import argparse
import json

class ssgGroup:  # ssg group
    def __init__(self, ssgNum, group_type):
        assert group_type == 'double' or group_type == 'single'
        self.group_type = group_type
        self.ssgNum =ssgNum  # ssg number
        self.kvec = [] # for translation factor
        # bz
        self.b1 = []
        self.b2 = []
        self.b3 = []
        self.pure_T = []
        # all operations :
        self.superCell = []
        self.Gid = ''
        self.rotC = []  # the rotation part of all operations as a list
        self.tauC = []  # the translation vector of all operations as a list
        self.spin = []
        self.su2s = []  # the SU2 matrices
        self.time_reversal = [] # 1 and -1 for time reversal
        # anti-unitary operation (can be choosen arbitrary)
        self.anti_spin = []
        self.anti_rotC = []
        self.anti_tau = []
        #
        self.mul_table = []
        self.factor_su2 = []
        self.factor_trans = []

    def load_ssg(self, ssg_dic):
        def uni_or_anti(ssg_dic):
            URot = ssg_dic['URot'][-1]
            QRot = ssg_dic['QRotC']
            QTau = ssg_dic['QTauC']
            uni = 1 # -1 if anti-unitary
            for i, spin in enumerate(URot):
                if det(spin) < 0:
                    uni = -1
                    return [uni, spin, QRot[i], QTau[i]]
            return [uni]
        self.superCell = ssg_dic['superCell']
        self.Gid = ssg_dic['Gid']
        HRot = ssg_dic['HRotC']
        HTau = ssg_dic['HTauC']
        QRot = ssg_dic['QRotC']
        QTau = ssg_dic['QTauC']
        URot = ssg_dic['URot'][-1]
        # print_matlist(URot)
        # print_matlist(QTau)
        uni = uni_or_anti(ssg_dic)
        if uni[0] == -1:
            A_spin = uni[1]
            A_rot = uni[2]
            A_tau = uni[3]
            self.anti_spin = A_spin
            self.anti_rotC = A_rot
            self.anti_tau = A_tau
        else:
            self.anti_spin = 0
            self.anti_rotC = 0
            self.anti_tau = 0
        # generate a new element list
        space_rot_uni = []
        space_tau_uni = []
        spin_uni = []
        su2_uni = []
        space_rot_tot = []
        space_tau_tot = []
        spin_tot = []
        su2_tot = []
        time_reversal = []
        for i, hrot in enumerate(HRot):
            htau = HTau[i]
            for j, spin in enumerate(URot):
                if det(spin) > 0:
                    qrot = QRot[j]
                    qtau = QTau[j]
                    # r1 t1 * r2 t2 = r1r2| r1t2 + t1
                    # qrot|qtau * hrot|htau = qrot*hrot| qrot*htau + qtau
                    rot_new = qrot @ hrot
                    tau_new = qrot @ htau + qtau
                    su2_new = SU2(spin)
                    space_rot_uni.append(rot_new)
                    space_tau_uni.append(tau_new)
                    spin_uni.append(spin)
                    su2_uni.append(su2_new)
                    time_reversal.append(1)
                    space_rot_tot.append(rot_new)
                    space_tau_tot.append(tau_new)
                    spin_tot.append(spin)
                    su2_tot.append(su2_new)

        # here the space_rot, space_tau, spin, su2 are the unitary subgroup of an antiunitary group
        # use the antiunitary element A to generate all the elements G=H+AH
        if uni[0] == -1:
            Time_R = -1j * np.array([[0, -1j], [1j, 0]])
            A_su2 = Time_R @ np.conj(SU2(-A_spin))
            for i,rot in enumerate(space_rot_uni):
                tau = space_tau_uni[i]
                spin = spin_uni[i]
                su2 =  su2_uni[i]
                space_rot_tot.append(A_rot @ rot)
                space_tau_tot.append(A_rot @ tau + A_tau)
                spin_tot.append(A_spin @ spin)
                su2_tot.append(A_su2 @ np.conj(su2))
                time_reversal.append(-1)
        self.rotC = space_rot_tot
        self.tauC = space_tau_tot
        self.spin = spin_tot
        self.su2s = su2_tot
        self.time_reversal = time_reversal

    def load_ssg_2d(self, ssg_dic):
        self.anti_spin = np.array([[1,0,0],[0,1,0],[0,0,-1]])
        self.anti_rotC = np.array([[1,0,0],[0,1,0],[0,0,1]])
        self.anti_tau = np.array([0,0,0])
        self.superCell = ssg_dic['superCell']
        self.Gid = ssg_dic['Gid']
        HRot = ssg_dic['HRotC']
        HTau = ssg_dic['HTauC']
        QRot = ssg_dic['QRotC']
        QTau = ssg_dic['QTauC']
        URot = ssg_dic['URot'][-1]
        # uni = uni_or_anti(ssg_dic)
        # assert uni[0] == -1
        # A_spin = uni[1]
        # A_rot = uni[2]
        # A_tau = uni[3]
        # generate a new element list
        space_rot_uni = []
        space_tau_uni = []
        spin_uni = []
        su2_uni = []
        space_rot_tot = []
        space_tau_tot = []
        spin_tot = []
        su2_tot = []
        time_reversal = []
        for i, hrot in enumerate(HRot):
            htau = HTau[i]
            for j, spin in enumerate(URot):
                if det(spin) > 0:
                    qrot = QRot[j]
                    qtau = QTau[j]
                    # r1 t1 * r2 t2 = r1r2| r1t2 + t1
                    # qrot|qtau * hrot|htau = qrot*hrot| qrot*htau + qtau
                    rot_new = qrot @ hrot
                    tau_new = qrot @ htau + qtau
                    su2_new = SU2(spin)
                else:
                    spin = np.array([[1,0,0],[0,1,0],[0,0,-1]]) @ spin
                    qrot = QRot[j]
                    qtau = QTau[j]
                    # r1 t1 * r2 t2 = r1r2| r1t2 + t1
                    # qrot|qtau * hrot|htau = qrot*hrot| qrot*htau + qtau
                    rot_new = qrot @ hrot
                    tau_new = qrot @ htau + qtau
                    su2_new = SU2(spin)
                space_rot_uni.append(rot_new)
                space_tau_uni.append(tau_new)
                spin_uni.append(spin)
                su2_uni.append(su2_new)
                time_reversal.append(1)
                space_rot_tot.append(rot_new)
                space_tau_tot.append(tau_new)
                spin_tot.append(spin)
                su2_tot.append(su2_new)

        # here the space_rot, space_tau, spin, su2 are the unitary subgroup of an antiunitary group
        # use the antiunitary element A to generate all the elements G=H+AH
        A_spin = np.array([[1,0,0],[0,1,0],[0,0,-1]])
        A_rot = np.eye(3)
        A_tau = np.array([0,0,0])
        Time_R = -1j * np.array([[0, -1j], [1j, 0]])
        A_su2 = Time_R @ np.conj(SU2(-A_spin))
        # A_su2 = SU2(A_spin)
        for i,rot in enumerate(space_rot_uni):
            tau = space_tau_uni[i]
            spin = spin_uni[i]
            su2 =  su2_uni[i]
            space_rot_tot.append(A_rot @ rot)
            space_tau_tot.append(A_rot @ tau + A_tau)
            spin_tot.append(A_spin @ spin)
            su2_tot.append(A_su2 @ np.conj(su2))
            time_reversal.append(-1)
        self.rotC = space_rot_tot
        self.tauC = space_tau_tot
        self.spin = spin_tot
        self.su2s = su2_tot
        self.time_reversal = time_reversal

    def load_ssg_1d(self, ssg_dic):
        self.anti_spin = np.array([[-1,0,0],[0,1,0],[0,0,1]])
        self.anti_rotC = np.array([[1,0,0],[0,1,0],[0,0,1]])
        self.anti_tau = np.array([0,0,0])
        self.superCell = ssg_dic['superCell']
        self.Gid = ssg_dic['Gid']
        HRot = ssg_dic['HRotC']
        HTau = ssg_dic['HTauC']
        QRot = ssg_dic['QRotC']
        QTau = ssg_dic['QTauC']
        URot = ssg_dic['URot'][-1]
        # uni = uni_or_anti(ssg_dic)
        # assert uni[0] == -1
        # A_spin = uni[1]
        # A_rot = uni[2]
        # A_tau = uni[3]
        # generate a new element list
        space_rot_uni = []
        space_tau_uni = []
        spin_uni = []
        su2_uni = []
        space_rot_tot = []
        space_tau_tot = []
        spin_tot = []
        su2_tot = []
        time_reversal = []
        for i, hrot in enumerate(HRot):
            htau = HTau[i]
            for j, spin in enumerate(URot):
                if det(spin) > 0:
                    qrot = QRot[j]
                    qtau = QTau[j]
                    # r1 t1 * r2 t2 = r1r2| r1t2 + t1
                    # qrot|qtau * hrot|htau = qrot*hrot| qrot*htau + qtau
                    rot_new = qrot @ hrot
                    tau_new = qrot @ htau + qtau
                    su2_new = SU2(spin)
                else:
                    spin = np.array([[-1,0,0],[0,1,0],[0,0,1]]) @ spin
                    qrot = QRot[j]
                    qtau = QTau[j]
                    # r1 t1 * r2 t2 = r1r2| r1t2 + t1
                    # qrot|qtau * hrot|htau = qrot*hrot| qrot*htau + qtau
                    rot_new = qrot @ hrot
                    tau_new = qrot @ htau + qtau
                    su2_new = SU2(spin)
                spin_c2z = np.array([[-1,0,0],[0,-1,0],[0,0,1]]) @ spin
                su2_c2z = SU2(spin_c2z)
                space_rot_uni.append(rot_new)
                space_tau_uni.append(tau_new)
                spin_uni.append(spin)
                su2_uni.append(su2_new)
                time_reversal.append(1)
                space_rot_tot.append(rot_new)
                space_tau_tot.append(tau_new)
                spin_tot.append(spin)
                su2_tot.append(su2_new)
                # double the unitary part by C2z
                space_rot_uni.append(rot_new)
                space_tau_uni.append(tau_new)
                spin_uni.append(spin_c2z)
                su2_uni.append(su2_c2z)
                time_reversal.append(1)
                space_rot_tot.append(rot_new)
                space_tau_tot.append(tau_new)
                spin_tot.append(spin_c2z)
                su2_tot.append(su2_c2z)

        # here the space_rot, space_tau, spin, su2 are the unitary subgroup of an antiunitary group
        # use the antiunitary element A to generate all the elements G=H+AH
        A_spin = np.array([[-1,0,0],[0,1,0],[0,0,1]])
        A_rot = np.eye(3)
        A_tau = np.array([0,0,0])
        Time_R = -1j * np.array([[0, -1j], [1j, 0]])
        A_su2 = Time_R @ np.conj(SU2(-A_spin))
        # A_su2 = SU2(A_spin)
        for i,rot in enumerate(space_rot_uni):
            tau = space_tau_uni[i]
            spin = spin_uni[i]
            su2 =  su2_uni[i]
            space_rot_tot.append(A_rot @ rot)
            space_tau_tot.append(A_rot @ tau + A_tau)
            spin_tot.append(A_spin @ spin)
            su2_tot.append(A_su2 @ np.conj(su2))
            time_reversal.append(-1)
        self.rotC = space_rot_tot
        self.tauC = space_tau_tot
        self.spin = spin_tot
        self.su2s = su2_tot
        self.time_reversal = time_reversal

    def ssg_bz(self):
        def calculate_reciprocal_lattice(pure_t):
            # cal the reciprocal basis from pure_t
            a1, a2, a3 = pure_t
            V = np.dot(a1, np.cross(a2, a3))
            b1 = (2 * np.pi * np.cross(a2, a3)) / V
            b2 = (2 * np.pi * np.cross(a3, a1)) / V
            b3 = (2 * np.pi * np.cross(a1, a2)) / V
            
            return b1, b2, b3
        tau_col = self.superCell
        gid = self.Gid
        prim_vec = identify_SG_lattice(gid)[1] # each col is a prim basis vector   
        t1 = np.array([tau_col[0][0], tau_col[1][0], tau_col[2][0]]) 
        t2 = np.array([tau_col[0][1], tau_col[1][1], tau_col[2][1]]) 
        t3 = np.array([tau_col[0][2], tau_col[1][2], tau_col[2][2]])
        pure_t = []
        for t_append in [t1, t2, t3]:
            pure_t.append(prim_vec @ t_append)
        self.pure_T = pure_t
        # pure t form the a_{i,j,k} in the basis of conventional basis of G
        b1, b2, b3 = calculate_reciprocal_lattice(pure_t)
        self.b1 = b1
        self.b2 = b2
        self.b3 = b3

    def get_table(self):
        def find_index(rot_new, tau_new, su2_new, t_new, space_rot, space_tau, su2_list, time_reversal, supercell, gid):
            for i,rot in enumerate(space_rot):
                tau = space_tau[i]
                su2 = su2_list[i]
                t = time_reversal[i]
                if norm(rot_new - rot) < 1e-4 and abs(t - t_new) < 1e-5:
                    id = identity_tau(tau_new, tau, supercell, gid)
                    if id[0]:
                        # print(rot_new, tau_new, su2_new)
                        # print(rot,tau,su2)
                        # print_matlist([su2, su2_new])
                        # if not (norm(su2_new - su2) < 1e-4 or norm(su2_new + su2) < 1e-4):
                        #     print_mat(su2_new)
                        #     print(su2)
                        # assert norm(su2_new - su2) < 1e-4 or norm(su2_new + su2) < 1e-4
                        # if norm(su2_new - su2) < 1e-4:
                        #     return [int(i+1), 1] 
                        # else:
                        #     return [int(i+1), -1] 
                        if norm(su2_new - su2) < 1e-4 or norm(su2_new + su2) < 1e-4:
                            # print_mat(su2_new)
                            # print(su2)
                            assert norm(su2_new - su2) < 1e-4 or norm(su2_new + su2) < 1e-4
                            if norm(su2_new - su2) < 1e-4:
                                return [int(i+1), 1] 
                            else:
                                return [int(i+1), -1] 
            print('err of index')
            ValueError('cant find index of multiple')
        #
        supercell = self.superCell
        gid = self.Gid
        space_rot = self.rotC
        space_tau = self.tauC
        spin = self.spin
        su2 = self.su2s
        time_reversal = self.time_reversal
        degree = len(space_rot)
        multiple_table = np.zeros((degree, degree))
        factor_su2 = np.zeros((degree, degree), dtype=complex)
        for i, rot1 in enumerate(space_rot):
            tau1 = space_tau[i]
            su2_1 = su2[i]
            t1 = time_reversal[i]
            for j, rot2 in enumerate(space_rot):
                tau2 = space_tau[j]
                su2_2 = su2[j]
                t2 = time_reversal[j]
                rot_new = rot1 @ rot2
                tau_new = rot1 @ tau2 + tau1
                # su2_new =  su2_1 @ su2_2
                if t1 < 0:
                    su2_new = su2_1 @ np.conj(su2_2)
                else:
                    su2_new =  su2_1 @ su2_2
                t_new = t1 * t2
                index = find_index(rot_new, tau_new, su2_new, t_new, space_rot, space_tau, su2, time_reversal, supercell, gid)
                mul_index = index[0]
                multiple_table[i][j] = mul_index
                factor_su2[i][j] = index[1]
                if self.group_type == 'single':
                    factor_su2[i][j] = 1
        # print_mat(factor_su2)
        # print_mat(multiple_table)
        self.mul_table = multiple_table
        self.factor_su2 = factor_su2
        # return multiple_table, factor_su2

    def get_trans_factor(self, kpoint):
        time_reversal = self.time_reversal
        degreee = len(time_reversal)
        space_rot = self.rotC
        space_tau = self.tauC
        factor = np.zeros((degreee, degreee),dtype=complex)
        b1, b2, b3 = self.b1, self.b2, self.b3
        k_conv = kpoint[0] * b1 + kpoint[1] * b2 + kpoint[2] * b3
        for i, rot1 in enumerate(space_rot):
            # rot1_k = inv(self.pure_T) @ rot1 @ self.pure_T
            # rot1_k = inv(rot1_k.T)
            tau1 = space_tau[i]
            t1 = time_reversal[i]
            for j, tau2 in enumerate(space_tau):
                f = np.exp( -1j * np.dot(k_conv, rot1 @ tau2 - t1 * tau2))
                # f = np.exp(- 1j * np.dot(t1 * inv(rot1)@ k_conv - k_conv, tau2))
                # factor[i][j] = f * np.exp(-1j * np.dot(k_conv, rot1 @ tau2 + tau1))
                factor[i][j] = f
        # print_mat(factor)
        self.factor_trans = factor


def loadSsgGroup(ssgNum, kvec, group_type, ssg_dic):
    ssg = ssgGroup(ssgNum, group_type)
    if 'P' in ssgNum:
        # print('coplanar condition')
        ssg.load_ssg_2d(ssg_dic)
    elif 'L' in ssgNum:
        ssg.load_ssg_1d(ssg_dic)
    else:
        ssg.load_ssg(ssg_dic)
    ssg.ssg_bz()
    ssg.get_table()
    ssg.get_trans_factor(kvec)
    return ssg


def convert_to_serializable(obj):
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, list):
        return [convert_to_serializable(item) for item in obj]
    return obj


class LittleGroup:  # little group at a special k point
    def __init__(self, ssgNum, kvec, group_type, ssg_dic, need_beautify):
        self.ssg = loadSsgGroup(ssgNum, kvec, group_type, ssg_dic)
        self.need_beautify = need_beautify
        self.ssgNum =ssgNum  # ssg number
        self.kvec = kvec  # k vector
        self.antiunitary = False
        self.oplist = []
        self.anti_index = 0
        self.rotC = []  # the rotation part of all operations as a list
        self.tauC = []  # the translation vector of all operations as a list
        self.spin = []
        self.su2s = []
        self.time_reversal = []
        self.pure_T = []
        self.Dv = [] # representation on k
        self.eta_0 = 0
        self.hT_index = []
        self.Fh = []
        self.mul_table = []
        self.factor = []
        self.regularRep = []
        self.rep_num = 0
        self.character = []
        self.linear_character = []
        self.correp_matrix = []
        self.Wmatrix = []
        self.classes = []
        self.subgroup = []
    
    def to_dic_json(self):
        return{
            "ssgNum": self.ssgNum,
            "kvec": convert_to_serializable(self.kvec),
            "rotC": convert_to_serializable(self.rotC),
            "spin": convert_to_serializable(self.spin),
            "su2": convert_to_serializable(self.su2s),
            "timeReversal": convert_to_serializable(self.time_reversal),
            "tauC": convert_to_serializable(self.tauC),
            "character": convert_to_serializable(self.character),
            "repMatrix": convert_to_serializable(self.correp_matrix),
            "torsion": convert_to_serializable(self.torsion),
            "repDegree": convert_to_serializable(self.rep_degree)
        }

    def to_dic_npy(self):
        return{
            "ssgNum": self.ssgNum,
            "kvec": self.kvec,
            "rotC": self.rotC,
            "spin": self.spin,
            "su2": self.su2s,
            "timeReversal": self.time_reversal,
            "tauC": self.tauC,
            "character": self.character,
            "repMatrix": self.correp_matrix,
            "torsion": self.torsion,
            "repDegree": self.rep_degree
        }
    
    def k_op1(self):
        def identity_kpoint(kpoint, r, t, pure_t):
            R_supercell = pure_t @ r @ inv(pure_t)
            # print(R_supercell)
            k_new = t * (inv(R_supercell)).T @ kpoint
            # k_new = t * R_supercell @ kpoint
            check = kpoint - k_new
            if norm(check- np.round(check)) < 1e-4:
                return True
            else:
                return False
        # a1, a2, a3 = get_pure_translation(ssg)
        # P = np.array([a1, a2, a3])
        ssg = self.ssg
        pure_t = np.array(ssg.pure_T)
        # print(pure_t)
        rot = ssg.rotC
        time_reversal = ssg.time_reversal
        self.b1, self.b2, self.b3 = ssg.b1, ssg.b2, ssg.b3
        kop_list = []
        for i, r in enumerate(rot):
            # print_mat(r)
            t= time_reversal[i]
            if identity_kpoint(self.kvec, r, t, pure_t):
                kop_list.append(i)
                if t < 0:
                    self.antiunitary = True
        self.oplist = kop_list
        # print(kop_list)
    
    def k_op(self):
        def identity_kpoint(kpoint, r, t, pure_t):
            t1, t2, t3 = pure_t
            # R_supercell = pure_t @ r @ inv(pure_t)
            # print(R_supercell)
            # print_mat(t * (inv(R_supercell.T)))
            # k_new = t * (inv(R_supercell)).T @ kpoint
            # k_new = t * R_supercell @ kpoint
            for tau in pure_t:
                factor = 1 - np.exp( 1j * np.dot(k_conv, -tau + t * r @ tau))
                if abs(factor) > 1e-3:
                    return False
            return True
            # check = kpoint - k_new
            # print(check)
            # if norm(check- np.round(check)) < 1e-4:
            #     return True
            # else:
            #     return False
        # a1, a2, a3 = get_pure_translation(ssg)
        # P = np.array([a1, a2, a3])
        ssg = self.ssg
        pure_t = np.array(ssg.pure_T)
        # print(pure_t)
        rot = ssg.rotC
        time_reversal = ssg.time_reversal
        self.b1, self.b2, self.b3 = ssg.b1, ssg.b2, ssg.b3
        b1, b2, b3 = self.b1, self.b2, self.b3
        kpoint = self.kvec
        k_conv = kpoint[0] * b1 + kpoint[1] * b2 + kpoint[2] * b3
        kop_list = []
        for i, r in enumerate(rot):
            # print_mat(r)
            t= time_reversal[i]
            if identity_kpoint(k_conv, r, t, pure_t):
                kop_list.append(i)
                if t < 0:
                    self.antiunitary = True
        # kop_list = [0, 1, 2, 3]
        self.oplist = kop_list
        # print(kop_list)
    
    def get_regular_rep_list(self):
        def get_mul_table(table, op_list):
            # print(table)
            # print(op_list)
            row = np.size(table, 0)
            col = np.size(table, 1)
            new_table = np.zeros((row, col))
            assert row == col
            for i in range(row):
                for j in range(col):
                    ele = int(table[i][j])
                    new_ele = op_list.index(ele - 1) + 1
                    new_table[i][j] = new_ele
            return new_table
        #
        def regular_rep_from_table(mul_table, factor_table, m):
            degree = np.size(mul_table, 0)
            rep = np.zeros((degree, degree), dtype=complex)
            for i in range(degree):
                mul = mul_table[m][i]
                factor = factor_table[m][i]
                # if mul > 0:
                #     double = 1
                # else:
                #     double = -1
                # mul = double * mul
                mul = mul - 1
                assert abs(mul-round(mul)) < 1e-4
                mul = round(mul)
                rep[mul][i] = factor
            return rep
        rep_list = []
        k_op_list = self.oplist
        ssg = self.ssg
        time_reversal_all = ssg.time_reversal
        time_reversal = [time_reversal_all[i] for i in k_op_list]
        # degree = len(k_op_list)
        new_mul_table = extract_submatrix(ssg.mul_table, k_op_list)
        new_mul_table = get_mul_table(new_mul_table, k_op_list)
        new_factor_table = extract_submatrix(ssg.factor_su2, k_op_list)
        new_trans_factor = extract_submatrix(ssg.factor_trans, k_op_list)
        self.mul_table = new_mul_table.astype(int)
        self.factor = np.multiply(new_factor_table, new_trans_factor)
        for num, op_num in enumerate(k_op_list):
            rep_list.append(regular_rep_from_table(new_mul_table, self.factor, num))
        # return rep_list, time_reversal
        self.regularRep = rep_list
        self.time_reversal = time_reversal
        self.pure_T = ssg.pure_T
        self.rotC = [ssg.rotC[i] for i in k_op_list]
        self.tauC = [ssg.tauC[i] for i in k_op_list]
        self.spin = [ssg.spin[i] for i in k_op_list]
        self.su2s = [ssg.su2s[i] for i in k_op_list]


    def get_irreducible_rep(self):
        check_ir = False
        loop_num = 0
        while not check_ir and loop_num < 5:
            loop_num = loop_num + 1
            replist = self.regularRep
            degree = len(replist)
            H = generate_random_matrix(degree)
            H_sum = np.zeros((degree, degree))
            # degree_half = degree / 2
            # assert abs(degree_half - round(degree_half)) < 1e-4
            # degree_half = int(round(degree_half)) 
            for i, rep in enumerate(replist):
                if self.time_reversal[i] > 0:
                    H_sum = H_sum + rep @ H @ inv(rep)
                else:
                    H_sum = H_sum + rep @ np.conj(H) @ inv(rep)
            H_hermitian = H_sum + np.conj(H_sum.T)
            eigenvalues, eigenvectors = np.linalg.eigh(H_hermitian)
            idx = eigenvalues.argsort()[::-1]   
            eigenvalues = eigenvalues[idx]
            eigenvectors = eigenvectors[:,idx]
            block_list = []
            character = []
            repetitions = cal_repetitions(eigenvalues, tolerance = 0.0001)
            # print(repetitions)
            # print(eigenvalues)
            # print('eigenvectors @ np.conj(eigenvectors.T)')
            # print_mat(eigenvectors @ np.conj(eigenvectors.T))
            assert np.sum(repetitions) == degree
            # num_rep = len(repetitions)
            for i, rep in enumerate(replist):
                if self.time_reversal[i] > 0:
                    block_rep = inv(eigenvectors) @ rep @ eigenvectors
                    block_list.append(block_rep)
                    character.append(calculate_diagonal_sums(block_rep, repetitions))
                else:
                    block_rep = inv(eigenvectors) @ rep @ np.conj(eigenvectors)
                    block_list.append(block_rep)
                    # character.append(calculate_diagonal_sums(block_rep, repetitions))
            # print_matlist(block_list)
            # character only contains unitary part
            character = np.array(character)
            character = character.T
            character_now = []
            row_num = 0
            cor_rep_list =[]
            def character_exist(character_now, ch):
                if character_now == []:
                    return True
                for i in character_now:
                    if norm(i - ch) < 1e-4:
                        return False
                return True
            for r, rep in enumerate(repetitions):
                # row_num = row_num + rep
                if character_exist(character_now, character[r]):
                    character_now.append(character[r])
                    cor_rep = []
                    for block_rep in block_list:
                        # print_mat(block_rep)
                        # print_mat(block_rep[row_num:row_num+rep,row_num:row_num+rep])
                        cor_rep.append(block_rep[row_num:row_num+rep,row_num:row_num+rep])
                    cor_rep_list.append(cor_rep)
                row_num = row_num + rep
            unitary_degree = np.size(character_now, 1)
            linear_character = []
            k_conv = self.b1 * self.kvec[0] + self.b2 * self.kvec[1] + self.b3 * self.kvec[2]
            for rep in character_now:
                ch = []
                for uni in range(unitary_degree):
                    ch.append(rep[uni]* np.exp(-1j * np.dot(k_conv, self.tauC[uni])))
                linear_character.append(ch)
            # sort the character list 
            n = np.size(character_now, 0)
            def compare_ch(ch1, ch2):
                # num_op = len(ch1)
                for i,rep1 in enumerate(ch1):
                    rep2 = np.real(ch2[i])
                    rep1 = np.real(rep1)
                    if rep1 > rep2 + 1e-2:
                        return True
                    if rep1 < rep2 - 1e-2:
                        return False
                for i,rep1 in enumerate(ch1):
                    rep2 = np.imag(ch2[i])
                    rep1 = np.imag(rep1)
                    if rep1 > rep2 + 1e-3:
                        return True
                    if rep1 < rep2 - 1e-3:
                        return False
                ValueError('cant sort the character')


            # for i in range(1, n):
            #     j = i
            #     while j > 0 and compare_ch(character_now[indices[j]], character_now[indices[j - 1]]):
            #         indices[j], indices[j - 1] = indices[j - 1], indices[j]
            #         j -= 1
            # sorted_indices = sorted(range(len(character_now)), key=lambda i: compare_ch(character_now[i], character_now[i-1]))
            # sorted_indices = sorted(range(len(character_now)), key=lambda i: character_now[i])
            # sorted_indices = indices
            sorted_indices = list(range(n))
            for i in range(n):
                sortnum = 0
                for j in range(n):
                    ch1 = character_now[i]
                    if not i == j:
                        if compare_ch(ch1, character_now[j]):
                            sortnum += 1
                sorted_indices[sortnum] = i
                

            # print(sorted_indices)
            character = [character_now[i] for i in sorted_indices]
            correp_matrix = [cor_rep_list[i] for i in sorted_indices]
            linear_character = [linear_character[i] for i in sorted_indices]
            rep_num = np.size(character, 0)
            rep_degree = []
            for ch in character:
                rep_degree.append(int(round(np.real(ch[0]))))
                if int(round(np.real(ch[0]))) > 9:
                    print(self.ssgNum)
                    print('degree:', int(round(np.real(ch[0]))))
            self.rep_num = rep_num
            self.rep_degree = rep_degree
            self.character = character
            self.correp_matrix = correp_matrix
            self.linear_character = linear_character
            torsion = []
            if self.antiunitary:
                for ch in character:
                    tor = 0
                    for i, time in enumerate(self.time_reversal):
                        if time > 0:
                            tor = tor + abs(ch[i])**2
                    tor = tor/degree * 2
                    assert abs(tor - np.round(tor)) < 1e-3
                    torsion.append(int(np.round(np.real(tor))))
            # if unitary, we define its torsion as 0
            else:
                for ch in character:
                    torsion.append(0)
            self.torsion = torsion
            # now check the irreducibility
            if_all = []
            if self.antiunitary:
                for ch in character:
                    sum_ch = 0
                    for i in range(unitary_degree):
                        kappa1 = ch[i] * np.conj(ch[i])
                        # print(unitary_degree)
                        kappa2_omega = self.factor[i+unitary_degree ,i+unitary_degree]
                        kappa2_mul = ch[self.mul_table[i+unitary_degree, i+unitary_degree] - 1]
                        sum_ch = sum_ch + (kappa1 + kappa2_mul * kappa2_omega)/(2*unitary_degree)
                    # print(sum_ch)
                    if abs(sum_ch - 1) > 1e-2:
                        if_all.append(1)
            else:
                for ch in character:
                    sum_ch = 0
                    for i in range(unitary_degree):
                        kappa1 = ch[i] * np.conj(ch[i])
                        # print(unitary_degree)
                        # kappa2_omega = self.factor[i+unitary_degree ,i+unitary_degree]
                        # kappa2_mul = ch[self.mul_table[i+unitary_degree, i+unitary_degree] - 1]
                        sum_ch = sum_ch + kappa1 /unitary_degree
                    # print(sum_ch)
                    if abs(sum_ch - 1) > 1e-2:
                        if_all.append(1)
            if 1 in if_all:
                check_ir = False
                print('retry!!')
                if loop_num == 4:
                    print('something wrong')
            else:
                check_ir = True
        # beautify the representations
        if self.need_beautify:
            correp_matrix = []
            # print('#################################################')
            # print(self.ssgNum)
            for i in range(rep_num):
                if rep_degree[i] > 1:
                    # print('dim:', rep_degree[i], 'torsion:', torsion[i])
                    cc = self.beautify_rep_subgroups(i)
                    
                    # print_matlist(cc)
                    # print('======================')
                    correp_matrix.append(cc)
                else:
                    # print('1-dim representation.')
                    # print('======================')
                    # print_matlist(self.correp_matrix[i])
                    correp_matrix.append(self.correp_matrix[i])
            self.correp_matrix = correp_matrix

        # solve factor or not
        L_solve_factor = 1
        if L_solve_factor:
            correp_matrix = []
            for i in range(rep_num):
                cc = self.solve_factor(i)
                correp_matrix.append(cc)

            self.correp_matrix = correp_matrix



    def beautify_rep_subgroups(self, repnum):
        def are_all_elements_unique(arr, tolerance=1e-4):
            n = len(arr)
            for i in range(n-1):
                if abs(arr[i] - arr[i+1]) < tolerance:
                    return False
            return True
        def is_diagonal_matrix(matrix, threshold=1e-4):
            rows, cols = matrix.shape
            for i in range(rows):
                for j in range(cols):
                    if i != j and abs(matrix[i, j]) > threshold:
                        return False
            return True
        # first let the H being the subgroup
        # if all the representations of one subgroup is diagonal
        degree = self.rep_degree[repnum]
        subgroups = self.subgroup
        # check the subgroup
        replist = self.correp_matrix[repnum]
        non_diagonal_subgroups = []
        for subg in subgroups:
            for iss, subg_element in enumerate(subg):
                if not is_diagonal_matrix(replist[subg_element]):
                    non_diagonal_subgroups.append(subg)
                    break
        subgroups = non_diagonal_subgroups
        subgroups.append([0])
        # print('subgroup', subgroups)
        torsion =self.torsion[repnum]
        # if torsion != 1 , can first do H block first
        if torsion > 1.1:
            subgroup_old = list(range(len(self.time_reversal)//2))
            H = generate_random_matrix(degree)
            H_sum = np.zeros((degree, degree))
            # degree_half = degree / 2
            # assert abs(degree_half - round(degree_half)) < 1e-4
            # degree_half = int(round(degree_half)) 
            replist = self.correp_matrix[repnum]
            for i, rep in enumerate(replist):
                if self.time_reversal[i] > 0:
                    H_sum = H_sum + rep @ H @ inv(rep)
            H_hermitian = H_sum + np.conj(H_sum.T)
            eigenvalues, eigenvectors = np.linalg.eigh(H_hermitian)
            idx = eigenvalues.argsort()[::-1]   
            eigenvalues = eigenvalues[idx]
            eigenvectors = eigenvectors[:,idx]
            # this eigenvectors block the unitary part but the antiunitary part may still has random numbers
            found  = 0      
            new = []
            for i in range(len(self.time_reversal)):
                if self.time_reversal[i] > 0:
                    new_rep = inv(eigenvectors) @ replist[i] @ eigenvectors
                    new.append(new_rep)
                else:
                    if not found: # get the u1 factor to beautify the anti-unitary part
                        anti_correp = inv(eigenvectors) @ replist[i] @ np.conj(eigenvectors)
                        anti_correp = list(np.reshape(anti_correp, (degree**2, 1)))
                        for num in anti_correp:
                            if abs(num) > 1e-3:
                                u1factor = np.sqrt(num)
                                break
                        found = 1
                        eigenvectors = eigenvectors * u1factor
                    new.append(inv(eigenvectors) @ replist[i] @ np.conj(eigenvectors))
        else:
            subgroup_old = [-1]
            new = self.correp_matrix[repnum]
            eigenvalues = np.zeros(degree, dtype=complex)
        # use sar_all_elements_unique to justify if the function can return the representations
        if are_all_elements_unique(eigenvalues):
            return new
        # use subgroups until the eigenvalus are all unique
        subgroup_index = 0
        def ainb(a, b):
            for i in a:
                if i not in b:
                    return False
            return True
        def repetitions2matrix(repetitions):
            degree = sum(repetitions)
            if len(repetitions) == 1:
                H = generate_random_matrix(degree)
                return H
            H = np.zeros((degree, degree), dtype= complex)
            left = 0
            for repe in repetitions:
                right = left + repe
                H[left:right, left:right] = generate_random_matrix(repe)
                left = right
            return H
        subgroup_use = subgroups[subgroup_index]

        # while not are_all_elements_unique(eigenvalues):
        while subgroup_use != [0]:
            # subgroup_use = subgroups[subgroup_index]
            repetitions = cal_repetitions(eigenvalues, 1e-3)
            assert abs(sum(repetitions) - degree) < 1e-3
            check2 = True
            if 1:
                check2 = False
                H = repetitions2matrix(repetitions)
                # print('random matrix', H)
                replist = new
                H_sum1 = np.zeros((degree, degree))
                H_sum2 = np.zeros((degree, degree))
                # print('subgroup choose:', [q+1 for q in subgroup_use])
                # find the quotient group degree g/2
                for i, rep in enumerate(replist):
                    if i in subgroup_use:
                        if self.time_reversal[i] > 0:
                            H_sum1 = H_sum1 + rep @ H @ inv(rep)
                        else:
                            H_sum1 = H_sum1 + rep @ np.conj(H) @ inv(rep)
                for i, rep in enumerate(replist):
                    if i in subgroup_old:
                        if self.time_reversal[i] > 0:
                            H_sum2 = H_sum2 + rep @ H @ inv(rep)
                        else:
                            H_sum2 = H_sum2 + rep @ np.conj(H) @ inv(rep)
                H_hermitian1 = H_sum1 + np.conj(H_sum1.T)
                H_hermitian2 = H_sum2 + np.conj(H_sum2.T)
                # eigenvalues1, eigenvectors1 = np.linalg.eigh(H_hermitian1)
                # eigenvalues2, eigenvectors2 = np.linalg.eigh(100 * H_hermitian2)
                # print(eigenvalues2)
                # a = eigenvalues2[0]
                # b = np.ptp(eigenvalues2)
                # if b / a < 0.05 and :
                #     check2 = True
                # sorted_list = sorted(eigenvalues2)

                # differences = [abs(sorted_list[i + 1] - sorted_list[i]) for i in range(len(sorted_list) - 1)]

                # # min_difference = min(differences)
                # max_diff = np.ptp(eigenvalues1) 
                # print('max_diff', max_diff)
                # for diff in differences:
                #     if diff > 1e-2:
                #         print
                #         if diff < max_diff:
                #             check2 = True
                # if max_diff < min_difference:
                #     check2 = False
            H_hermitian = H_hermitian1 + 100000 * H_hermitian2
            eigenvalues, eigenvectors = np.linalg.eigh(H_hermitian)
            idx = eigenvalues.argsort()[::-1]   
            eigenvalues = eigenvalues[idx]
            eigenvectors = eigenvectors[:,idx]
            repetitions_new = cal_repetitions(eigenvalues, 1e-3)
            # self.repetitions = repetitions_new
            # print('repetitions and eigenvales', repetitions_new, eigenvalues)
            # self.repetitions[repnum] = repetitions_new
            # print('old repetitions:', repetitions)
            subgroup_old = subgroup_use
            if len(repetitions) == len(repetitions_new):
                subgroup_index = subgroup_index + 1
                subgroup_use= subgroups[subgroup_index]
            # elif are_all_elements_unique(eigenvalues):
            #     return new
            else:
                new = []
                for i in range(len(self.time_reversal)):
                    if self.time_reversal[i] > 0:
                        new_rep = inv(eigenvectors) @ replist[i] @ eigenvectors
                        new.append(new_rep)
                    else:
                        new.append(inv(eigenvectors) @ replist[i] @ np.conj(eigenvectors))
                # generate the new subgroups
                if are_all_elements_unique(eigenvalues):
                    return new
                subgroups_new = []
                for s in subgroups:
                    if len(s) < len(subgroup_use) and ainb(s, subgroup_use):
                        if not all(is_diagonal_matrix(new[ss]) for ss in s):
                        # if 1:
                            subgroups_new.append(s)
                subgroups_new.append([0])
                if subgroups_new == []:
                    return new
                subgroups = subgroups_new
                subgroup_index = 0
                subgroup_use = subgroups[subgroup_index]
        return new
                

    # in this step, elements have been in the form of diagonal, only to solve factor and trun to the standard form
    def solve_factor(self, repnum):
        def find_position(uni, pos1, pos2, replist, time_reversal):
            for ir, rep in enumerate(replist):
                if abs(uni - time_reversal[ir]) < 1e-3:
                    position = rep[pos1, pos2]
                    # aa = rep[pos1,:]
                    # bb = rep[:,pos2]
                    if abs(position) > 1e-2 and abs(abs(position)-1) < 1e-3:
                        return position
            print('cant find the position')
            return 1
            # ValueError('cant find non-zero')

        def find_position_unitary(pos1, pos2, replist):# just for the function solve_factor_unitary
            for ir, rep in enumerate(replist):
                if 1:
                    position = rep[pos1, pos2]
                    # aa = rep[pos1,:]
                    # bb = rep[:,pos2]
                    if abs(position) > 1e-2 and abs(abs(position)-1) < 1e-3:
                        return position
            print('cant find the position')
            return 1
            # ValueError('cant find non-zero')

        # solve the factor of a n-degree diagonal form
        def solve_factor_unitary(replist, degree):
            factors = np.zeros(degree, dtype = complex)
            factors[0] = 1
            for ifactor in range(degree - 1):
                factors[ifactor + 1] = find_position_unitary(ifactor+1,  0, replist)
            factor_matrix = np.diag(factors)
            return do_similar_transform(replist, [1]*1000, factor_matrix)

        def solve_factor_torsion_1(replist, time_reversal, degree):
            factors = np.zeros(degree, dtype=complex)
            # print(factors)
            factors[0] = 1
            for ifactor in range(degree - 1):
                factors[ifactor + 1] = find_position(1, ifactor+1,  0, replist, time_reversal)
            factor_matrix = np.array(np.diag(factors))
            # print('factor matrix')
            # print(factor_matrix)
            replist =  do_similar_transform(replist, time_reversal, factor_matrix)
            alpha = find_position(-1, 0, 0, replist, time_reversal)
            alpha = np.sqrt(alpha)
            return do_similar_transform(replist, time_reversal, np.diag(np.array(degree * [alpha])))



        def do_similar_transform(replist, time_reversal, factor):
            new_rep_list = []
            if np.size(factor, 0) == 1:
                for ir, rep in enumerate(replist):
                    if time_reversal[ir] > 0:
                        new_rep_list.append(np.conj(factor) * rep * factor)
                    else:
                        new_rep_list.append(np.conj(factor) * rep * np.conj(factor))
                return new_rep_list

            for ir, rep in enumerate(replist):
                if time_reversal[ir] > 0:
                    new_rep_list.append(inv(factor) @ rep @ factor)
                else:
                    new_rep_list.append(inv(factor) @ rep @ inv(factor))
            return new_rep_list

        def find_index_class(a_index, h_index, mul_table):
            # find the index of a^{-1} h a
            degree = np.size(mul_table, 0)
            for i in range(degree):
                if mul_table[i, a_index] == 1:
                    inverse_a = i
                    break
            a_inverse_h = mul_table[inverse_a, h_index] - 1
            return mul_table[a_inverse_h, a_index] - 1
        
        def is_diagonal_matrix(matrix, threshold=1e-4):
            rows, cols = matrix.shape
            for i in range(rows):
                for j in range(cols):
                    if i != j and abs(matrix[i, j]) > threshold:
                        return False
            return True
        
        def find_multiplier(a, b, mul_table):
            # find a * ? = b
            # mul_a = mul_table[a,:]
            degree = np.size(mul_table, 0)
            for i in range(degree):
                if b == mul_table[a, i] - 1:
                    return i

        def Dh_to_replist_torsion_2(Dh_list, Dh_degree, time_reversal, mul_table, factor_table):
            # print(Dh_list, Dh_degree)
            find_diagonal = False
            for ia, itt in enumerate(time_reversal):
                if itt < 0 and not find_diagonal:
                    index_aa = mul_table[ia, ia] - 1
                    if is_diagonal_matrix(Dh_list[index_aa]):
                        U_a = np.block([[np.zeros((Dh_degree,Dh_degree)), factor_table[ia, ia]* Dh_list[index_aa]], [np.eye(Dh_degree), np.zeros((Dh_degree,Dh_degree))]])
                        anti_index = ia
                        find_diagonal = True
            if not find_diagonal:
                anti_index = len(time_reversal)//2
                ia = anti_index
                index_aa = mul_table[ia, ia] - 1
                U_a = np.block([[np.zeros((Dh_degree,Dh_degree)), factor_table[ia, ia]* Dh_list[index_aa]], [np.eye(Dh_degree), np.zeros((Dh_degree,Dh_degree))]])
            index_a = anti_index
            Eh_list = []
            for irr, Dh in enumerate(Dh_list):
                aha = find_index_class(index_a, irr, mul_table)
                Eh = np.conj(factor_table[irr, index_a] / factor_table[index_a, aha]) * Dh_list[aha]
                Eh_list.append(Eh)
            # get the Eh and Dh, unitary part can be constructed 
            # now find the anti_index as anti-unitary and U_a
            new_rep_list = []
            uni_rep_list = []
            for ir, rep in enumerate(time_reversal):
                if time_reversal[ir] > 0:
                    Uh = np.block([[Dh_list[ir], np.zeros((Dh_degree,Dh_degree))], [np.zeros((Dh_degree,Dh_degree)), np.conj(Eh_list[ir])]])
                    new_rep_list.append(Uh)
                    uni_rep_list.append(Uh)
            # finish the unitary part
            # mul_a = mul_table[anti_index, :]
            for i in range(len(time_reversal)// 2):
                index_need = i + len(time_reversal)//2
                h_need = find_multiplier(anti_index, index_need, mul_table)
                # print(h_need)
                U_anti = factor_table[anti_index, h_need] * U_a @ np.conj(uni_rep_list[h_need])
                new_rep_list.append(U_anti)
            return new_rep_list
        
        # get Dh from the representations and solve the factor of Dh
        def get_Dh(replist, torsion, time_reversal, degree):
            assert torsion == 2 or torsion == 4
            Dh_list = []
            for it,tt in enumerate(time_reversal):
                if tt > 0:
                    Dh_list.append(replist[it][0:degree//2, 0:degree//2])
            # print(Dh_list)
            Dh_list = solve_factor_unitary(Dh_list, degree//2)
            return Dh_list
        
        # def Dh_to_replist_torsion_4(Dh_list, Dh_degree, time_reversal, mul_table, factor_table):


        replist = self.correp_matrix[repnum]
        degree  = self.rep_degree[repnum]
        torsion = self.torsion[repnum]
        time_reversal = self.time_reversal
        factor_table = self.factor
        mul_table = self.mul_table
        # torsion = 0
        if not self.antiunitary:
            new_rep_list = solve_factor_unitary(replist, degree)
            return new_rep_list

        # torsion = 1 and degree = 1
        if degree == 1:
            new_rep_list = []
            alpha = replist[len(time_reversal)//2]
            for itt, L_time in enumerate(time_reversal):
                if L_time > 0:
                    new_rep_list.append(replist[itt])
                else:
                    new_rep_list.append(replist[itt]/alpha)
            return new_rep_list
                    
        # torsion = 1
        if torsion == 1:
            return solve_factor_torsion_1(replist, time_reversal, degree)

        # if torsion = 2 or 4, always solve D(h) first
        Dh_list = get_Dh(replist, torsion, time_reversal, degree)

        # torsion =2 , can be solved
        if torsion == 2:
            return Dh_to_replist_torsion_2(Dh_list, degree//2, time_reversal, mul_table, factor_table)

        # now the solve the torsion = 4 KK^* = -sigma D(aa)
        assert torsion == 4
        # degree = 2, KK^* can only be 1
        if degree == 2:
            new_rep_list = []
            uni_rep_list = []
            for irr, rep in enumerate(replist):
                if time_reversal[irr] > 0:
                    uni_rep_list.append(np.array([[rep[0,0],0],[0,rep[0,0]]]))
                    new_rep_list.append(np.array([[rep[0,0],0],[0,rep[0,0]]]))
            Dt0 = np.array([[0,-1],[1,0]])
            idt0 = len(time_reversal)//2
            for irrep, rep in enumerate(uni_rep_list):
                new_rep_list.append(mul_table[idt0, irrep] * Dt0 @ np.conj(rep))
            return new_rep_list
        
        # degree = 4, dim K = 2
        if degree == 4:
            new_rep_list = []
            uni_rep_list = []
            for i in range(len(time_reversal)// 2):
                Uh = np.block([[Dh_list[i], np.zeros((2,2))], [np.zeros((2,2)), Dh_list[i]]])
                new_rep_list.append(Uh)
                uni_rep_list.append(Uh)
            # finish the unitary part
            # find the K^2 being identity or diagonal
            find_K = False
            for i in range(len(time_reversal)// 2):
                ia = i + len(time_reversal)// 2
                index_aa = mul_table[ia, ia] - 1
                k_square = - factor_table[ia, ia] * Dh_list[index_aa]
                # KK^* = I
                if norm(k_square - np.eye(2)) < 1e-3:
                    index_a = ia
                    K = np.eye(2)
                    find_K = True
                    break
                #KK^*= -I
                elif norm(k_square + np.eye(2)) < 1e-3:
                    index_a = ia
                    K = np.array([[0,-1],[1,0]])
                    find_K = True
                    break
            if not find_K:
                for i in range(len(time_reversal)// 2):
                    ia = i + len(time_reversal)// 2
                    index_aa = mul_table[ia, ia] - 1
                    k_square = - factor_table[ia, ia] * Dh_list[index_aa]
                    if is_diagonal_matrix(k_square):
                        ma = k_square[0, 0]
                        mb = k_square[1,1]
                        assert abs(ma - np.conj(mb))< 1e-3
                        index_a = ia
                        K = np.array([[0,ma],[1,0]])
                        find_K = True
                        break
            if not find_K:
                print('cant find K at torsion = 4')
                return replist
            anti_index = index_a
            U_a = np.block([[np.zeros((2,2)), -K], [K, np.zeros((2,2))]])
            for i in range(len(time_reversal)// 2):
                index_need = i + len(time_reversal)//2
                h_need = find_multiplier(anti_index, index_need, mul_table)
                U_anti = factor_table[anti_index, h_need] * U_a @ np.conj(uni_rep_list[h_need])
                new_rep_list.append(U_anti)
            return new_rep_list
        
        if degree == 6:
            new_rep_list = []
            uni_rep_list = []
            for i in range(len(time_reversal)// 2):
                Uh = np.block([[Dh_list[i], np.zeros((3,3))], [np.zeros((3,3)), Dh_list[i]]])
                new_rep_list.append(Uh)
                uni_rep_list.append(Uh)
            # finish the unitary part
            # find the K^2 being identity or diagonal
            find_K = False
            for i in range(len(time_reversal)// 2):
                ia = i + len(time_reversal)// 2
                index_aa = mul_table[ia, ia] - 1
                k_square = - factor_table[ia, ia] * Dh_list[index_aa]
                if norm(k_square - np.eye(3)) < 1e-3:
                    index_a = ia
                    K = np.eye(3)
                    find_K = True
                    break
            if not find_K:
                return replist
                # ValueError('cant find K at torsion = 4')
            anti_index = index_a
            U_a = np.block([[np.zeros((3,3)), -K], [K, np.zeros((3,3))]])
            for i in range(len(time_reversal)// 2):
                index_need = i + len(time_reversal)//2
                h_need = find_multiplier(anti_index, index_need, mul_table)
                U_anti = factor_table[anti_index, h_need] * U_a @ np.conj(uni_rep_list[h_need])
                new_rep_list.append(U_anti)
            return new_rep_list

        
        # high degree with torsion = 4
        if degree > 7:
            d_half = degree//2
            new_rep_list = []
            uni_rep_list = []
            for i in range(len(time_reversal)// 2):
                Uh = np.block([[Dh_list[i], np.zeros((degree//2,degree//2))], [np.zeros((degree//2,degree//2)), Dh_list[i]]])
                new_rep_list.append(Uh)
                uni_rep_list.append(Uh)
            # finish the unitary part
            # find the K^2 being identity or diagonal
            find_K = False
            for i in range(len(time_reversal)// 2):
                ia = i + len(time_reversal)// 2
                index_aa = mul_table[ia, ia] - 1
                k_square = - factor_table[ia, ia] * Dh_list[index_aa]
                if norm(k_square - np.eye(d_half)) < 1e-3:
                    index_a = ia
                    K = np.eye(d_half)
                    find_K = True
                    break
            if not find_K:
                return replist
                ValueError('cant find K at torsion = 4')
            anti_index = index_a
            U_a = np.block([[np.zeros((3,3)), -K], [K, np.zeros((3,3))]])
            for i in range(len(time_reversal)// 2):
                index_need = i + len(time_reversal)//2
                h_need = find_multiplier(anti_index, index_need, mul_table)
                U_anti = factor_table[anti_index, h_need] * U_a @ np.conj(uni_rep_list[h_need])
                new_rep_list.append(U_anti)
            return new_rep_list




            

        

    
    def cal_classes(self):
        def find_inversion(element, multable):
            row = multable[element]
            ind = np.argwhere(row == 1)
            assert len(ind) == 1
            return ind[0][0]
        def find_one_class(element, multable, time_reversal): # element is an element number from 0
            degree = np.size(multable, 0)
            class1 = [element]
            for i in range(degree):
                element_inv = find_inversion(i, multable)
                if time_reversal[i] > 0:
                    mul1 = multable[element_inv][element] - 1
                    mul2 = multable[mul1][i] - 1
                else:
                    h_inv = find_inversion(element, multable)
                    mul1 = multable[element_inv][h_inv] - 1
                    mul2 = multable[mul1][i] - 1
                if mul2 not in class1:
                    class1.append(mul2)
            return class1
        def find_calsses(multable, time_reversal):
            def exit_class(element, class_list):
                for class1 in class_list:
                    if element in class1:
                        return True
                return False
            class_list = [[0]]
            degree = np.size(multable, 0)
            if -1 in time_reversal:
                uni_degree = degree//2
            else:
                uni_degree = degree
            for i in range(uni_degree):
                if not exit_class(i, class_list):
                    class_list.append(find_one_class(i, multable, time_reversal))
            d = 0
            for class1 in class_list:
                d = d + len(class1)
            assert abs(d  - uni_degree) < 1e-3
            return class_list
        mul_table = self.mul_table
        # unitary_degree = len(self.time_reversal)//2
        time_reversal = self.time_reversal
        # unitary_mul_table = extract_submatrix(mul_table, list(range(unitary_degree)))
        classes = find_calsses(mul_table, time_reversal)
        self.classes = classes
        return classes


    def regular_subgroup(self):
        def check_subgroup(mul_table, checkarray):
            sub_multable = extract_submatrix(mul_table, checkarray)
            len1 = len(checkarray)
            len2 = np.size(mul_table, 0)
            qlen = len2/len1
            if abs(qlen - round(qlen)) > 1e-3:
                return False
            for row in sub_multable:
                for ele in row:
                    ele = ele -1
                    if ele not in checkarray:
                        return False
            return True
        def class2subgroup(classes, mul_table):
            subgroup = []
            len1 = np.size(mul_table, 0)
            num_classes = len(classes)
            num_loop = num_classes - 2
            not_special = True
            if len(classes) == len1//2:
                not_special = False
            while num_loop > 0:
                # print(num_loop)
                if not_special or num_loop == 1: 
                    sub_classes_list = list(combinations(classes[1:], num_loop))
                    for sub_classes in sub_classes_list:
                        sub_classes = combine_array(sub_classes)
                        sub_classes.append(0)
                        if check_subgroup(mul_table, sub_classes):
                            subgroup.append(sub_classes)
                num_loop = num_loop - 1
            return subgroup
        classes = self.cal_classes()
        mul_table = self.mul_table
        subgroups = class2subgroup(classes, mul_table)
        def sort_key(arr):
            return len(arr)
        sorted_list = sorted(subgroups, key=sort_key, reverse=True)
        sorted_list.append([0])
        self.subgroup = sorted_list
        return sorted_list



    
    def get_kdotp(self):
        dv = []
        for i, r in enumerate(self.rotC):
            t = self.time_reversal[i]
            pure_t = self.pure_T
            r_k = inv(pure_t) @ r @ pure_t
            # print('det', det(r_k))
            dv.append(t * inv(r_k.T))
        self.Dv = dv
        degree = len(self.time_reversal)
        anti_index = degree // 2
        self.anti_index = anti_index
        assert self.time_reversal[degree//2] == -1
        self.eta_0 = self.factor[anti_index, anti_index]
        self.hT_index = self.mul_table[0: anti_index, anti_index]
        Fh = []
        rep_num = np.size(self.character,0)
        # print(rep_num)
        for rep in range(rep_num):
            fhh = []
            correp = self.correp_matrix[rep]
            for uni in range(anti_index):
                fffh=np.dot(np.dot(correp[anti_index], np.conj(correp[uni])), np.conj(correp[anti_index].T))
                fhh.append(fffh)
            Fh.append(fhh)
        self.Fh = Fh

    def get_W(self, rep_num):# rep_num being the number of representation
        Wmatrix = []
        degree = len(self.time_reversal)
        anti_index = degree // 2
        Dv = self.Dv
        correp = self.correp_matrix[rep_num]
        # print_matlist(correp)
        Fh = self.Fh[rep_num]
        for uni in range(anti_index):
            # degreeW = np.size(Dv[0], 0) * np.size(correp[0], 0) * np.size(Fh[0], 0)
            # part1 = np.zeros((degreeW, degreeW))
            part1 = np.kron(Dv[uni], np.kron(correp[uni], Fh[uni]))
            FdotM = np.dot(Fh[uni], correp[self.mul_table[anti_index, anti_index]-1])# -1 because the multible table index is from 1 
            MFM = TwistOperator(correp[uni], FdotM)
            part2 = np.kron(Dv[self.hT_index[uni]-1], MFM) # -1 because the multible table index is from 1 
            Wmatrix.append(0.5*(part1 + self.eta_0 * part2))
        # print_matlist(Wmatrix)
        self.Wmatrix = Wmatrix
            # print_mat(part1）
        
    # def get_multiplicity(self, rep_num):
        degree = len(self.time_reversal)
        anti_index = degree // 2
        Dv = self.Dv
        correp = self.correp_matrix[rep_num]
        ai = 0
        for uni in range(anti_index):
            character_uni = np.trace(correp[uni])
            part1 = abs(character_uni)* abs(character_uni) *np.trace(Dv[uni])
            index_hT = self.hT_index[uni] - 1
            omega = self.factor[index_hT, index_hT]
            kappa = correp[self.mul_table[index_hT, index_hT] -1]
            part2 = np.trace(Dv[index_hT])* omega * np.trace(kappa)
            # print(part1)
            # print(part2)
            ai = ai + (part1 + part2)/(degree)
        aii = round(abs(ai))
        assert norm(aii - ai)< 1e-5
        # print('the number of independent matrices from formula:')
        # print(aii)
        # return aii
    
    # def common_null_space(self):
        # eigenvalues_B, eigenvectors_B = np.linalg.eig(Wmatrix[0])
        # print(eigenvalues_B)
        # Wmatrix = self.Wmatrix
        Sn = []
        for mat in Wmatrix:
            ssn = mat - np.eye(np.size(mat,0))
            Sn.append(ssn)
        # print_matlist(Sn)
        Ssn = np.vstack(Sn)  
        nullspace = null_space(Ssn)
        # print('the number of independent matrices from solving nullspace:')
        # print(np.size(nullspace, 1))
        # change the bases WT:
        anti_index = self.anti_index
        mt0 = correp[anti_index]
        WT = np.kron(self.Dv[anti_index], np.kron(mt0, mt0))
        TInSub = np.conj(nullspace.T) @ WT @ np.conj(nullspace)
        rpt = sqrtm(TInSub)
        # print(np.conj(rpt.T) @ TInSub @ np.conj(rpt))
        BasisW = nullspace @ rpt
        dim_dv = np.size(Dv[0], 0)
        dim_rep = np.size(mt0, 0)
        assert aii == np.size(nullspace, 1)
        for i in range(aii):
            print(i+1, 'th independent kdotp Hamiltonian:')
            for kd in range(dim_dv):
                ll = BasisW[kd * dim_rep* dim_rep : kd * dim_rep* dim_rep + dim_rep* dim_rep, i]
                gamma = np.reshape(ll, (dim_rep, dim_rep))
                # numpy reshape 1: 4 to 2,2: [[1,2],[3.4]]
                # matlab reshape " [[1,3],[2,4]]"
                Gamma_final = gamma @ np.conj(mt0)
                kkp = ['kx', 'ky', 'kz']
                print(kkp[kd], ':')
                print_mat(Gamma_final)
        
        # check = Ssn @ solve1
        # print(norm(check))




def load_little_group(ssgNum, kvec, need_beautify , group_type, ssg_dic):
    lg = LittleGroup(ssgNum, kvec, group_type, ssg_dic, need_beautify)
    lg.k_op()
    lg.get_regular_rep_list()
    if need_beautify:
        lg.cal_classes()
        lg.regular_subgroup()
    lg.get_irreducible_rep()
    # lg.get_kdotp()
    # lg.get_W(1)
    return lg

# def common_null_space(Wmatrix):
#     # eigenvalues_B, eigenvectors_B = np.linalg.eig(Wmatrix[0])
#     # print(eigenvalues_B)
#     Sn = []
#     for mat in Wmatrix:
#         ssn = mat - np.eye(np.size(mat,0))
#         Sn.append(ssn)
#     # print_matlist(Sn)
#     Ssn = np.vstack(Sn)  
#     nullspace = null_space(Ssn, 1e-2)
#     print('the number of independent matrices from solving nullspace:')
#     print(np.size(nullspace, 1))
#     solve1 = nullspace[:,0]
#     check = Ssn @ solve1
#     print(norm(check))

class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, complex):
            return {"real": obj.real, "imag": obj.imag}
        return super().default(obj)

def load_one_ssg_kvec(ssgnum, kvec, single, out ,fileType , optimize): # rep_degree character
    if single == 1:
        sd = 'single'
    else:
        sd = 'double'
    script_dir = os.path.dirname(os.path.abspath(__file__))
    pkl_file_path = os.path.join(script_dir, '../ssg_data/identify.pkl')
    file = pkl_file_path
    with open(file, 'rb') as f:
        ssg_list = pickle.load(f)
    ssgdic_list = []
    find_ssg = 0
    for ssg in ssg_list:
        num = ssg['ssgNum']
        if ssg['ssgNum'] == ssgnum:
            a = ssg
            find_ssg = 1
            break
    if not find_ssg:
        raise ValueError('not a valid SSG number in the database, please check the input SSG number.')
    Gid = int(ssgnum.split('.')[0])
    # need_beautify = 0
    # if out == out == 'rep_matrix':
    #     need_beautify = 1
    # kvec_dict = ssgkvec[Gid-1]
    if 1:
        print('k vector:', kvec)
        ssglg = load_little_group(ssgnum, kvec, optimize, sd, a)
        # output json file
        if fileType == 'json':
            with open("output.json", "w", encoding="utf-8") as file:
                json.dump(ssglg.to_dic_json(), file, cls=CustomEncoder, ensure_ascii=False, indent=4)
        if fileType == 'npy':
            np.save("output.npy", ssglg.to_dic_npy())
            # to read npy: 
            # loaded_data = np.load("output.npy", allow_pickle=True).item()
            
        for irotlg, rotlg in enumerate(ssglg.rotC):
            print(irotlg+1, ' th operation:  space rotation  spin rotation translation')
            print_mat(rotlg)
            print_mat(ssglg.spin[irotlg])
            print(ssglg.tauC[irotlg])
            
        # print('Space rotations:')
        # print_matlist(ssglg.rotC)
        # print('Spin rotations:')
        # print_matlist(ssglg.spin)
        # print('Translations:')
        # print
        rep_degree = ssglg.rep_degree
        rep_num = len(rep_degree)
        # print('the su2 factor part')
        # print_mat(ssglg.ssg.factor_su2)
        # print('the trans factor part')
        # print_mat(ssglg.ssg.factor_trans)
        # print('sum being:')
        # print_mat(ssglg.factor)
        if out == 'rep_degree':
            print('repdgree is:')
            print(rep_degree)
        # print_matlist(ssglg.spin)
        if out == 'character':
            print('representation characters:')
            for I in range(rep_num):
                print(f'{I+1}th:')
                print('torsion:', ssglg.torsion[I])
                ch = ssglg.linear_character[I]
                for ic, chh in enumerate(ch):
                    real_part = f'{chh.real:+.5f}'
                    imag_part = f'{chh.imag:+.5f}' #if chh.imag != 0 else '0.00000'
                    if ic + 1 < 10:
                        print(f'{ic+1}  {real_part}{imag_part}*i')
                    else:
                        print(f'{ic+1} {real_part}{imag_part}*i')
        if out == 'rep_matrix':
            print('representations:')
            for i in range(rep_num):
                print(i+1,'th:')
                print_matlist(ssglg.correp_matrix[i])
    return ssglg


import argparse
import numpy as np

def main():
    parser = argparse.ArgumentParser(description='SSG Representation Program')
    parser.add_argument('--ssgNum', type=str, required=True, help='SSG number')
    parser.add_argument('--kp', nargs=3, type=float, required=True, help='k-point coordinates as three floats', metavar=('kx', 'ky', 'kz'))
    parser.add_argument('--groupType', type=int, default=2, help='Group type: 1 for single group, 2 for double group (default: 2)')
    parser.add_argument('--out', type=str, default='character', help='Output type: character, rep_matrix, rep_degree (default: character)')
    parser.add_argument('--fileType', type=str, default=None, help="Output file type: 'json', 'npy', or None (default: None)")
    parser.add_argument('--optimize', type=bool, default=False, help="Optimize SSG representation matrices (default: False)")

    try:
        args = parser.parse_args()
        
        # Validate inputs
        ssgNum = args.ssgNum
        kx, ky, kz = args.kp
        groupType = args.groupType
        out = args.out
        fileType = args.fileType
        optimize = args.optimize

        if groupType not in [1, 2]:
            raise ValueError('Group type must be 1 (single group) or 2 (double group).')

        if out not in ['character', 'rep_degree', 'rep_matrix']:
            raise ValueError("Output type must be one of 'character', 'rep_matrix', or 'rep_degree'.")

        if fileType not in [None, 'json', 'npy']:
            raise ValueError("File type must be one of 'json', 'npy', or None.")

        if not isinstance(optimize, bool):
            raise ValueError("Optimize must be a boolean value (True or False).")

        # Call the main function with parsed arguments
        load_one_ssg_kvec(
            ssgNum,
            np.array([kx, ky, kz]),
            single=groupType,
            out=out,
            fileType=fileType,  # Pass fileType to load_one_ssg_kvec
            optimize=optimize   # Pass optimize to load_one_ssg_kvec
        )
    
    except ValueError as e:
        print(f"Input error: {e}")
        print("Use python SSGReps.py --help to see usage details.")
    except Exception as e:
        print(f"Unexpected error: {e}")
        print("Check your input and try again. Use python SSGReps.py --help for more information.")


if __name__ == '__main__':
    main()
