import os, time 
import sys, getopt
import importlib

import numpy as np 

var = '??'
#bilbaodata = '/home/jcgao/BilBaoData/'
bilbaodata = '/data/home/szhang/soft_sz/topmat_src/BilBaoData/'

def check_input(inputfile):
    num_vars = 0
    f = open(inputfile,'r')
    (nsg, numk, nband) = tuple(map(int, f.readline().strip().split()))

    k_withvar = []
    for i in range(numk):
        data = f.readline().strip().split()
        for d in data:
            if d == var:
                num_vars += 1
                k_withvar.append(int(data[0]))
    return nsg, num_vars, k_withvar 


def write_input(inputfile, irr_trial):
    newfile = inputfile
    for irr in irr_trial:
        newfile = newfile + '_' + str(irr)
    with open(inputfile, 'r') as f, open(newfile, 'w') as w:
        tmp = f.readline()
        numk = int(tmp.split()[1])
        w.write(tmp)
        for ik in range(numk):
            tmp = f.readline().strip().split()
            for d in tmp:
                if d == var:
                    w.write('{:>3d}'.format(irr_trial.pop(0)))
                else:
                    w.write('{:>3s}'.format(d))
            w.write('\n')
    return newfile 


# ----------------------- BR decomposition ------------------------------

def read_SiteK(nsg):
    filename = bilbaodata + "BRlist2_A/SiteK_"+str(nsg)+".cht"
    f = open(filename, "r")
    Nsite = int(f.readline().strip().split()[-1])
    Nktp  = int(f.readline().strip().split()[-1])
    name_siteg     = ['' for i in range(Nsite)]
    name_irr_siteg = [[] for i in range(Nsite)]
    name_irr_littg = [[] for i in range(Nktp)]
    f.readline()

    BRdata = [[[] for j in range(Nktp)] for i in range(Nsite)]
    for isite in range(Nsite):
        for ikvec in range(Nktp):
            tmp = f.readline().strip().split()
            name_siteg[isite] = tmp[-2]
            nirr_site = int(tmp[-1])
            nirr_kvec = int(f.readline().strip().split()[-1])
            name_irr_siteg[isite] = ['' for i in range(nirr_site)]
            name_irr_littg[ikvec] = ['' for i in range(nirr_kvec)]

            tmp1= f.readline()
            tmp = tmp1.strip().split()
            for i in range(nirr_kvec):
                name_irr_littg[ikvec][i] = tmp1[7+5*i:12+5*i].strip()
                #name_irr_littg[ikvec][i] = tmp[2+i]
            
            for irr_site in range(nirr_site):
                tmp = f.readline().strip().split()
                name_irr_siteg[isite][irr_site] = tmp[0]
                data = list(map(int,tmp[1:]))
                BRdata[isite][ikvec].append(data)
            f.readline()
    f.close()
    return BRdata, name_siteg, name_irr_siteg, name_irr_littg


def writecode(A,b,lowbound,uppbound,isEBR):
    num_var = len(A[0])
    var_str = ['a'+str(i) for i in range(num_var)]
    with open('runZ3.py','w') as f:
        f.write("from z3 import *\n")
        f.write("\n")
        f.write("def decomBR():\n")
        f.write("    s = Solver()\n")
        for i in range(num_var):
            f.write("    a{} = Int('a{}')\n".format(i,i))
        f.write("    vars = [")
        for i in range(num_var):
            f.write("a{}".format(i))
            if i!=num_var-1:
                f.write(",")
        f.write("]\n")

        f.write("\n")
        for i in range(num_var):
            f.write("    s.add(a{} >= {})\n".format(i,lowbound[i]))
            if not isEBR:
                f.write("    s.add(a{} <= {})\n".format(i,uppbound[i]))
        for ieq, eq in enumerate(A):
            tmp_str = ''
            for icoeff, coeff in enumerate(eq):
                tmp_str = tmp_str + "{}*a{}+".format(coeff,icoeff)
            tmp_str = tmp_str + "0 == {}".format(b[ieq])
            f.write("    s.add("+tmp_str+")\n")
        #f.write(f"solve({tmp_str})")
        f.write("\n")
        f.write("    alldata = []\n")
        f.write("    #f = open('decompose','a+')\n")
        f.write("    while s.check() == sat:\n")
        f.write("        m = s.model()\n")
        f.write("        if not m:\n")
        #f.write("            print('No solutions any more')\n")
        f.write("            break\n")
        #f.write("        print(m)\n")
        #f.write("    tmp_str = '          '.join([str(m[i]) for i in vars])\n")
        #f.write("    f.write('    ')\n")
        f.write("        tmp_str = '   '.join([str(m[i]) for i in vars])\n")
        f.write("        data = list(map(int,tmp_str.strip().split()))\n")
        f.write("        alldata.append(data)\n")
        f.write("        #for i in range(len(data)):\n")
        f.write("        #    f.write('{:>7d}'.format(data[i]))\n")
        f.write("        s.add(Not(And([v() == m[v] for v in m])))\n")
        #f.write("    else:\n")
        #f.write("        print('No solutions any more')\n")
        f.write("    #f.close()\n")
        f.write("\n")
        f.write("    return alldata\n")
        f.write("\n")
        f.write("\n")
        f.write("if __name__=='__main__':\n")
        f.write("    alldata = decomBR()\n")


#def read_SiteK(nsg):
#    filename = "SiteK_"+str(nsg)+".cht"
#    f = open(filename, "r")
#    Nsite = int(f.readline().strip().split()[-1])
#    NKtp  = int(f.readline().strip().split()[-1])
#    f.readline()
#
#    BRdata = [[[] for j in range(NKtp)] for i in range(Nsite)]
#    for isite in range(Nsite):
#        for ikvec in range(NKtp):
#            nirre_site = int(f.readline().strip().split()[-1])
#            nirre_kvec = int(f.readline().strip().split()[-1])
#            f.readline()
#            for irre_site in range(nirre_site):
#                data = list(map(int,f.readline().strip().split()[1:]))
#                BRdata[isite][ikvec].append(data)
#            f.readline()
#    f.close()
#    return BRdata 


def buildAb_oneshot(inputfile, BRdata, soc=0):

    isEBR = 0
    
    BR = []
    BRnum = []
    BRset = []
    BRlabel = []
    BRlabelset = []
    with open("atomwp.in", "r") as f:
        isEBR = int(f.readline().strip())
        nBR = int(f.readline().strip())
        for i in range(nBR):
            line = f.readline().strip().split()
            BR.append(tuple(map(int, line[0:2])))
            BRlabel.append(line[2])
        for idx, iBR in enumerate(BR):
            if iBR not in BRset:
                BRset.append(iBR)
                BRlabelset.append(BRlabel[idx])
        for i in BRset:
            BRnum.append(BR.count(i))

    maxk = []
    irre_onk = []
    print(inputfile)
    with open(inputfile,"r") as f:
        (nsg, nmaxk, nband) = tuple(map(int,f.readline().strip().split()))
        for i in range(nmaxk):
            data = list(map(int,f.readline().strip().split()))
            maxk.append(data[0])
            irre_onk.append(data[1:])

    nirr_eachk = [] 
    kname = []
    with open(bilbaodata + "kvec_list_A.txt","r") as f:
        while True:
            (isg, numk) = tuple(map(int,f.readline().strip().split()))
            if (isg==nsg):
                for i in range(numk):
                    tmp = f.readline().strip().split()
                    nirr_eachk.append(tuple(map(int,tmp[0:4])))
                    kname.append(tmp[5])
                break
            else:
                for i in range(numk):
                    f.readline()

    for ik in range(len(maxk)):
        if maxk[ik] < 0:
            absk = abs(maxk[ik])
            abskname = kname[absk-1]
            knameA = abskname+'A'
            kaindex = kname.index(knameA) + 1
            maxk[ik] = kaindex 
    
    nkir = []
    for ik in maxk:
        for jdata in nirr_eachk:
            if ik==jdata[0]:
                if soc==0:
                    nkir.append(jdata[2])
                else:
                    nkir.append(jdata[3])
    #print(nkir)

    #BRdata, name_siteg, name_irr_siteg, name_irr_littg  = read_SiteK(nsg)

    # construct A matrix
    A = np.zeros((sum(nkir), len(BRset)),dtype=np.int)

    #print(BRset)
    for iw in range(len(BRset)):
        isite = BRset[iw][0]
        iirre = BRset[iw][1]
        icol = iw 
        irow = 0
        for ik in range(len(maxk)):
            for ir in range(nkir[ik]):
                irk = ir if soc==0 else (ir-nkir[ik])
                A[irow, icol] = A[irow, icol] + BRdata[isite-1][maxk[ik]-1][iirre-1][irk]
                irow = irow + 1
    #print(A)

    # construct b array
    b = np.array([0 for i in range(sum(nkir))])
    for ik in range(len(maxk)):
        for rep in irre_onk[ik]:
            if soc!=0: rep = rep-nirr_eachk[maxk[ik]-1][2]
            b[sum(nkir[:ik])+rep-1] += 1
    #print(b)
           
    lowbound = np.array([0 for i in range(len(A[0]))])
    uppbound = np.array(BRnum)
    #print(lowbound)
    #print(uppbound)

    writecode(A,b,lowbound,uppbound,isEBR)
    
    #from runZ3 import decomBR
    import runZ3
    if (sys.version_info.major == 3):
        importlib.reload(runZ3)
    elif (sys.version_info.major == 2):
        reload(runZ3)
    time.sleep(1)
    alldata = runZ3.decomBR()
    del runZ3

    num_decom = len(alldata)
    print('Number of solutions:', num_decom)
    alldata = np.array(alldata).T 
    #print(alldata)
    #print(alldata!=[])

    #with open('decompose','w') as f:
    #    f.write("#")
    #    for idx, ibr in enumerate(BRset):
    #        f.write(" {:>2d}@{:<2d}({:>2d}) ".format(ibr[1],ibr[0],uppbound[idx]))
    #    f.write("\n")
    dataformat = "{:>7d}"
    with open('decompose_'+inputfile,'w') as f:
        for idx, ibr in enumerate(BRset):
            f.write("{:>4d}".format(idx+1)+
                    "  {:>2d}@{:<2d}".format(ibr[1],ibr[0])+
                    "{:>10}".format(BRlabelset[idx])+
                    "    ({:3d}) :".format(uppbound[idx]))
            if len(alldata)!=0:
                for jdx, jbr in enumerate(alldata[idx]):
                    f.write("{:>3d};".format(alldata[idx][jdx]))
            f.write("\n")
        #f.write("# ")
        #for idx in range(len(BRset)):
        #    f.write(" ({:3d}) ".format(uppbound[idx]))
        #f.write("\n")

    return num_decom 


def run_buildAb(inputfile, soc):

    nsg, num_vars, k_withvar = check_input(inputfile)
    BRdata, name_siteg, name_irr_siteg, name_irr_littg = read_SiteK(nsg)
    nirr_eachk = [] 
    with open(bilbaodata + "kvec_list_A.txt","r") as f:
        while True:
            (isg, numk) = tuple(map(int,f.readline().strip().split()))
            if (isg==nsg):
                for i in range(numk):
                    nirr_eachk.append(tuple(map(int,f.readline().strip().split()[0:4])))
                break
            else:
                for i in range(numk):
                    f.readline()

    irr_trial = []
    for ik in range(len(k_withvar)):
        if (soc == 0):
            irr_trial.append([i+1 for i in range(nirr_eachk[k_withvar[ik]-1][2])])
        else:
            irr_trial.append([nirr_eachk[k_withvar[ik]-1][2]+i+1 for i in range(nirr_eachk[k_withvar[ik]-1][3])])

    if (num_vars == 0):
        num_decom = buildAb_oneshot(inputfile, BRdata, soc)
    elif (num_vars == 1):
        summary = open('solutions','w')
        summary.write('# trial_irr  num_solutions\n')
        for irr1 in irr_trial[0]:
            new_inputfile = write_input(inputfile,[irr1])
            num_decom = buildAb_oneshot(new_inputfile, BRdata, soc)
            if (num_decom > 0):
                summary.write('{:>5d}:{:>5d}\n'.format(irr1, num_decom))
            else:
                summary.write('{:>5d}:\n'.format(irr1))
        summary.close()
    elif (num_vars == 2):
        summary = open('solutions','w')
        summary.write('# trial_irr1  trial_irr2  num_solutions\n')
        for irr1 in irr_trial[0]:
            for irr2 in irr_trial[1]:
                new_inputfile = write_input(inputfile,[irr1, irr2])
                num_decom = buildAb_oneshot(new_inputfile, BRdata, soc)
                if (num_decom > 0):
                    summary.write('{:>5d}{:>5d}:{:>5d}\n'.format(irr1,irr2, num_decom))
                else:
                    summary.write('{:>5d}{:>5d}:\n'.format(irr1,irr2))
        summary.close()
    elif (num_vars == 3):
        summary = open('solutions','w')
        summary.write('# trial_irr1  trial_irr2  trial_irr3  num_solutions\n')
        for irr1 in irr_trial[0]:
            for irr2 in irr_trial[1]:
                for irr3 in irr_trial[2]:
                    new_inputfile = write_input(inputfile,[irr1, irr2, irr3])
                    num_decom = buildAb_oneshot(new_inputfile, BRdata, soc)
                    if (num_decom > 0):
                        summary.write('{:>5d}{:>5d}{:>5d}:{:>5d}\n'.format(irr1,irr2,irr3, num_decom))
                    else:
                        summary.write('{:>5d}{:>5d}{:>5d}:\n'.format(irr1,irr2,irr3))
        summary.close()
    else:
        sys.exit('{}(>3) variables in input file'.format(num_vars))
    return


# ------------------------------- end BR decomposition ---------------------------------------



# ------------------------------- CR ----------------------------------
def check_pair(inputfile, pairfile):

    f = open(pairfile,'r')
    num_hspk = int(f.readline())
    pair = dict()
    for ik in range(num_hspk):
        tmp = f.readline().split()
        kind = int(tmp[2]) + 1
        kname = tmp[3]
        num_irr = int(tmp[4])
        if not pair.__contains__((kind, kname)):
            # Here we ignore 'UA' in the pair file.
            pair[(kind, kname)] = dict()
        for ir in range(num_irr):
            tmp = list(map(int, f.readline().strip().split()))
            pair[(kind, kname)][tmp[0]+1] = (tmp[1], tmp[2]+1, tmp[3]+1)
    f.close()

    def check_pair_func(irrlist, irrpair):
        match = True 
        for ir in irrpair.keys():
            if irrpair[ir][0] == -1:
                num_ir = irrlist.count(ir)
                if num_ir%2 > 0:
                    match = False
                    return match 
            elif irrpair[ir][0] == 0:
                ir1 = irrpair[ir][1]
                ir2 = irrpair[ir][2]
                num_ir1 = irrlist.count(ir1)
                num_ir2 = irrlist.count(ir2)
                if num_ir1 != num_ir2:
                    match = False 
                    return match 
        return match 

    f = open(inputfile, 'r')
    sg, numk, _ = list(map(int, f.readline().strip().split()))
    k_notmatch = []
    for ik in range(numk):
        tmp = list(map(int, f.readline().strip().split()))
        indk = tmp[0]
        if indk > 0:
            for kinfo in pair.keys():
                if kinfo[0] == indk:
                    match = check_pair_func(tmp[1:], pair[kinfo])
        else:
            for kinfo in pair.keys():
                if kinfo[0] == -indk:
                    break 
            for kinfo2 in pair.keys():
                if kinfo2[1] == kinfo[1] + 'A':
                    match = check_pair_func(tmp[1:], pair[kinfo2])
        if not match:
            k_notmatch.append(ik)
    f.close()
    return k_notmatch 

def run_CR(inputfile, soc, nmsg=None): 

    nsg, num_vars, k_withvar = check_input(inputfile)
    if num_vars > 0:
        print('There are undefined representations in the inputfile.')
        return -1 

    if soc:
        crfile = bilbaodata + 'CompRel/' + str(nsg) + '_soc.txt'
    else:
        crfile = bilbaodata + 'CompRel/' + str(nsg) + '_nsoc.txt'
    
    if nmsg is not None: 
        msginfo = dict()
        f = open(bilbaodata+'msginfo','r')
        fdata = f.readlines()
        f.close()
        for i in range(1651):
            tmp = fdata[i].strip().split()
            msginfo[int(tmp[0])] = tmp[2]
        if soc:
            pairfile = bilbaodata + 'pairfiles_msghspk/' + msginfo[nmsg] + '.txt'
        else:
            pairfile = bilbaodata + 'pairfiles_msghspk_nsoc/' + msginfo[nmsg] + '.txt'
        k_notmatch = check_pair(inputfile, pairfile)
        if len(k_notmatch) > 0:
            print('The following k-points do not match the CR relations under MSGs')
            print(k_notmatch)
            return None 

    symlines = []
    kirrep = []  
    with open(crfile,'r') as f:
        num_row, num_col = list(map(int, f.readline().strip().split()))
        crmat = np.zeros((num_row, num_col), dtype=int)
        for ir in range(num_row):
            symlines.append(f.readline().strip())
        for ir in range(num_row):
            tmp = list(map(int, f.readline().strip().split()))
            for ic in range(num_col):
                crmat[ir,ic] = tmp[ic]
        tmp = f.readline()
        for ic in range(num_col):
            kirrep.append(tmp[5*ic:5*(ic+1)+1].strip())
    for ic in range(num_col):
        if soc:
            kirrep[ic] = kirrep[ic][:-1]
        kirrep[ic] = kirrep[ic].replace('m','')
    # scratch kvec from the name of irreps
    tmp = []
    kvecname = []
    for ic in range(num_col):
        for istr in range(len(kirrep[ic])):
            if kirrep[ic][istr].isdigit():
                tmp.append(kirrep[ic][:istr])
                break 
    for ic in range(num_col):
        if tmp[ic] not in kvecname:
            kvecname.append(tmp[ic])

    kdict = dict()
    with open(bilbaodata + 'CompRel/kvec_list_230msg.txt','r') as f:
        iline = 0
        num_lines = len(f.readlines())
        f.seek(0)
        while iline < num_lines:
            sg_in_k, numk = list(map(int, f.readline().strip().split()))
            if sg_in_k == nsg:
                for i in range(numk):
                    tmp = f.readline().split()
                    kind = int(tmp[0])
                    if not kdict.__contains__(kind):
                        kdict[kind] = dict()
                        kdict[kind]['num_irr'] = int(tmp[1])
                        kdict[kind]['num_irr_single'] = int(tmp[2])
                        kdict[kind]['num_irr_double'] = int(tmp[3])
                        kdict[kind]['name'] = tmp[5]
                break 
            else:
                iline += (numk + 1)
                for i in range(numk):
                    f.readline()

    maxk = []
    irre_onk = []
    with open(inputfile, "r") as f:
        (nsg, nmaxk, nband) = tuple(map(int,f.readline().strip().split()))
        for i in range(nmaxk):
            data = list(map(int,f.readline().strip().split()))
            maxk.append(data[0])
            irre_onk.append(data[1:])

    bandvec = np.zeros((num_col,1), dtype=int)
    icol = 0
    for kname in kvecname:
        for kind in kdict.keys():
            if kdict[kind]['name'] == kname:
                break 
        for ik in range(nmaxk):
            if maxk[ik] == kind:
                break 
        if soc:
            possible_irr = [ir+1 for ir in range(kdict[kind]['num_irr_single'], kdict[kind]['num_irr'])]
        else:
            possible_irr = [ir+1 for ir in range(kdict[kind]['num_irr_single'])]
        for ir in possible_irr:
            for ir_on_k in irre_onk[ik]:
                if ir_on_k == ir:
                    bandvec[icol] += 1
            icol += 1

    crossline = []
    checkvec = np.dot(crmat, bandvec)
    for ic in range(len(checkvec)):
        if checkvec[ic] != 0:
            crossline.append(symlines[ic])
    if len(crossline) == 0:
        print('Satisfy CR')
    else:
        print('CR is not satisfied on the following line(s):')
        for cross in crossline:
            print(cross)
    
    return crossline

# ------------------------------- end CR ----------------------------------




# ------------------------------- MTQC ------------------------------------
def calc_ind(inputfile, soc, nmsg):
    
    nsg, num_vars, k_withvar = check_input(inputfile)
    if num_vars > 0:
        print('There are undefined representations in the inputfile.')
        return None

    msginfo = dict()
    f = open(bilbaodata+'msginfo','r')
    fdata = f.readlines()
    f.close()
    for i in range(1651):
        tmp = fdata[i].strip().split()
        msginfo[int(tmp[0])] = tmp[2]
    
    if soc:
        indfile = bilbaodata + 'output/Lindex_'+msginfo[nmsg]+'.txt'
    else:
        indfile = bilbaodata + 'output_nsoc/Lindex_'+msginfo[nmsg]+'.txt'
    f = open(indfile, 'r')
    num_ind, num_kirr = list(map(int, f.readline().strip().split()))

    if num_ind == 0:
        f.close()
        print('No symmetry indicator.')
        return
        

    ind_group = list(map(int, f.readline().strip().split()))
    f.readline()
    ind_formula = []
    for i in range(num_ind):
        ind_formula.append(list(map(int, f.readline().strip().split())))

    irr_onk = [{'kind':0, 'irrname':'', 'irrind':[],'A':False} for ik in range(num_kirr)]
    for ik in range(num_kirr):
        tmp = f.readline().strip().split()
        irrname_tmp = tmp[-1]
        irrname_tmp = irrname_tmp.replace('KA','K')
        irrname_tmp = irrname_tmp.replace('HA','H')
        irrname_tmp = irrname_tmp.replace('WA','W')
        irrname_tmp = irrname_tmp.replace('PA','P')
        origk_ind = int(tmp[2])
        for jk in range(num_kirr):
            if irrname_tmp == irr_onk[jk]['irrname']:
                irr_onk[ik]['A'] = True 
                origk_ind = irr_onk[jk]['kind']
                break 
        irr_onk[ik]['kind'] = origk_ind 
        irr_onk[ik]['irrname'] = irrname_tmp
        if int(tmp[1]) == 1:
            irr_onk[ik]['irrind'].append(int(tmp[3]))
        else:
            irr_onk[ik]['irrind'].append(int(tmp[3]))
            irr_onk[ik]['irrind'].append(int(tmp[5]))
    f.close()

    # The label of KA is a confusion in the whole project.
    #   KA induced by high symmetry k-points and time-reversal symmetry (used in type II MSGs)
    # are written explicitly in kvec_list files, and in the Lindex files,
    # their index are positive and bigger than other K index.
    # In irvsp, KA are given as minus index.
    #   KA induded by high symmetry line k-points and antiunitary symmetry (used in type III MSGs)
    # are written explicitly in kvec_list_msginsub.txt, with the same index as K.
    # In the Lindex files, KA and K share the same index and names. The order of k-points in Lindex files
    # are same as the order in kvec_list_msginsub.txt.
    # In irvsp, such KA have the same index as K. 

    irrdata = dict()
    f = open(inputfile, 'r')
    sg, numk, _ = list(map(int, f.readline().strip().split()))
    for ik in range(numk):
        tmp = list(map(int, f.readline().strip().split()))
        if not irrdata.__contains__(tmp[0]):
            irrdata[tmp[0]] = tmp[1:]
        else:
            irrdata[-tmp[0]] = tmp[1:]
    f.close()

    #print(irr_onk)
    #print(irrdata)
    
    count = [0 for irk in range(len(irr_onk))]
    for irk in range(len(irr_onk)):
        kind = irr_onk[irk]['kind']
        if irr_onk[irk]['A']:
            kind = -kind 
        irrind = irr_onk[irk]['irrind']
        if len(irrind) == 1:
            count[irk] = irrdata[kind].count(irrind[0])
        else:
            irrind1 = irrind[0]
            irrind2 = irrind[1]
            if irrind1 == irrind2:
                num_tmp = irrdata[kind].count(irrind1)
                assert num_tmp%2 == 0
                count[irk] = int(num_tmp/2)
            else:
                num_tmp1= irrdata[kind].count(irrind1)
                num_tmp2= irrdata[kind].count(irrind2)
                assert num_tmp1 == num_tmp2 
                count[irk] = num_tmp1 
        
    valZ = []
    for ind, n in enumerate(ind_group):
        formula = ind_formula[ind]
        Z = 0
        for irk in range(len(formula)):
            Z += count[irk]*formula[irk]
        valZ.append(Z%n)

    Zstr = ''
    for ind, n in enumerate(ind_group):
        Zstr += ('Z'+str(n)+'='+str(valZ[ind])+',')
    print(Zstr)

    return Zstr

# ------------------------------ end MTQC ---------------------------------
def helpfunction():
    print("""
    python dealfort.py -n $nmsg --cr/--ind [-i inputfile] [--soc=1]
    """)
    return


if __name__ == '__main__':

    soc = 0
    inputfile = 'tqc.data'

    nmsg = None
    work = None

    argv = sys.argv[1:]
    try:
        opts, args = getopt.getopt(argv, "hi:n:", ["help", "cr", "ind", "soc="])
    except getopt.GetoptError:
        helpfunction()
        sys.exit()
    for opt, arg in opts:
        if opt in ("-h","--help"):
            helpfunction()
            sys.exit()
        elif opt == "--cr":
            work = "cr"
        elif opt == "--ind":
            work = "ind"
        elif opt == "-n":
            nmsg = int(arg)
        elif opt == "-i":
            inputfile = arg
        elif opt == "--soc":
            soc = int(arg)
        
    if work is None:
        print("cr or ind must be specified in the args")
        helpfunction()
    if nmsg is None and work == 'ind':
        print("nmsg must be specified in the args")
        helpfunction()

    if work == "cr" and nmsg is None:
        run_CR(inputfile, soc)
    elif work == "cr" and nmsg is not None:
        run_CR(inputfile, soc, nmsg) 
    elif work == "ind":
        calc_ind(inputfile, soc, nmsg)

    #buildAb_oneshot(inputfile, soc)
    #run_buildAb(inputfile, soc)
