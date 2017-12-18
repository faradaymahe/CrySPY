#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import os
import xml.etree.ElementTree as ET

import numpy as np
from pymatgen import Structure

from ...IO import pkl_data


def collect_vasp(current_id, work_path):
    # ---------- check optimization in previous stage
    try:
        with open(work_path+'prev_OUTCAR', 'r') as fpout:
            lines = fpout.readlines()
        check_opt = 'not_yet'
        for line in lines:
            if 'reached required accuracy' in line:
                check_opt = 'done'
    except:
        check_opt = 'no_file'

    # ---------- obtain energy and magmom
    try:
        with open(work_path+'OSZICAR',  'r') as foszi:
            oszi = foszi.readlines()
        if 'F=' in oszi[-1]:
            energy = float(oszi[-1].split()[2])    # free energy (eV)
            if 'mag=' in oszi[-1]:
                magmom = float(oszi[-1].split()[-1])    # total magnetic moment
            else:
                magmom = np.nan
        else:
            energy = np.nan    # error
            magmom = np.nan    # error
            print('    Structure ID {0}, could not obtain energy from OSZICAR'.format(current_id))
    except:
        energy = np.nan    # error
        magmom = np.nan    # error
        print('    Structure ID {0}, could not obtain energy from OSZICAR'.format(current_id))

    # ---------- collect CONTCAR
    try:
        opt_struc = Structure.from_file(work_path+'CONTCAR')
    except:
        opt_struc = None

    # ---------- mv xxxxx fin_xxxxx
    vasp_files = ['POSCAR', 'CONTCAR', 'OUTCAR', 'OSZICAR', 'WAVECAR', 'CHGCAR', 'vasprun.xml']
    for f in vasp_files:
        if os.path.isfile(work_path+f):
            os.rename(work_path+f, work_path+'fin_'+f)

    # ---------- remove STOPCAR
    if os.path.isfile(work_path+'STOPCAR'):
        os.remove(work_path+'STOPCAR')

    # ---------- clean stat file
    os.remove(work_path+'stat_job')

    # ---------- return
    return opt_struc, energy, magmom, check_opt


def get_energy_step_vasp(energy_step_data, current_id, filename):
    # ---------- get energy step from vasprun
    try:
        # ------ read file
        tree = ET.parse(filename)
        root = tree.getroot()
        # ------ children nodes: calculation
        cals = root.findall('calculation')
        # ------ init.
        energy_step = []
        # ------ loop for relaxation step
        for cal in cals:
            eng = cal.find('energy')    # first 'energy' child node
            fr_eng = eng.find('i')    # first 'i' tag is free energy

            if fr_eng.attrib['name'] == 'e_fr_energy':
                energy_step.append(fr_eng.text)
            else:
                raise ValueError('bug')
        # ------ list, str --> array
        energy_step = np.array(energy_step, dtype='float')
    except:
        energy_step = None
        print('\n#### ID: {0}: failed to parse vasprun.xml\n\n'.format(current_id))

    # ---------- append energy_step
    if energy_step_data.get(current_id) is None:
        energy_step_data[current_id] = []    # initialize
    energy_step_data[current_id].append(energy_step)

    # ---------- save energy_step_data
    pkl_data.save_energy_step(energy_step_data)

    # ---------- return
    return energy_step_data


def get_struc_step_vasp(struc_step_data, current_id, filename):
    # ---------- get struc step from vasprun
    try:
        # ------ read file
        tree = ET.parse(filename)
        root = tree.getroot()
        # ------ get atom list
        atoms = root.findall("atominfo/array[@name='atoms']/set/rc")
        atomlist = []
        for atom in atoms:
            atomlist.append(atom.find('c').text)
        # ------ children nodes: calculation
        cals = root.findall('calculation')
        # ------ init.
        struc_step = []
        # ------ loop for relaxation step
        for cal in cals:
            # -- lattice
            basis = cal.findall("structure/crystal/varray[@name='basis']/v")
            lattice = []
            for a in basis:
                lattice.append([float(x) for x in a.text.split()])    # char --> float
            # -- positions
            positions = cal.findall("structure/varray/[@name='positions']/v")
            incoord = []
            for a in positions:
                incoord.append([float(x) for x in a.text.split()])    # char --> float
            # -- structure in pymatgen format
            struc = Structure(lattice, atomlist, incoord)
            # -- append
            struc_step.append(struc)
    except:
        struc_step = None
        print('\n#### ID: {0}: failed to parse vasprun.xml\n\n'.format(current_id))

    # ---------- append struc_step
    if struc_step_data.get(current_id) is None:
        struc_step_data[current_id] = []    # initialize
    struc_step_data[current_id].append(struc_step)

    # ---------- save energy_step_data
    pkl_data.save_struc_step(struc_step_data)

    # ---------- return
    return struc_step_data


def get_fs_step_vasp(fs_step_data, current_id, filename):
    force_step_data, stress_step_data = fs_step_data

    # ---------- get force and stress step from vasprun
    try:
        # ------ read file
        tree = ET.parse(filename)
        root = tree.getroot()
        # ------ children nodes: calculation
        cals = root.findall('calculation')
        # ------ init.
        force_step = []
        stress_step = []
        # ------ loop for ralaxation step
        for cal in cals:
            varrays = cal.findall('varray')
            # -- init
            force = []
            stress = []
            # -- varrays[0]: force, varrays[1]: stress
            for varray in varrays:
                vs = varray.findall('v')
                # loop for v
                for v in vs:
                    if varray.attrib['name'] == 'forces':
                        force.append(v.text.split())
                    if varray.attrib['name'] == 'stress':
                        stress.append(v.text.split())
            # -- list, str --> array
            force = np.array(force, dtype='float')
            stress = np.array(stress, dtype='float')
            # -- appned force_step and stress_step
            force_step.append(force)
            stress_step.append(stress)
    except:
        force_step = None
        stress_step = None
        print('\n#### ID: {0}: failed to parse vasprun.xml\n\n'.format(current_id))

    # ---------- append force_step
    if force_step_data.get(current_id) is None:
        force_step_data[current_id] = []    # initialize
    force_step_data[current_id].append(force_step)

    # ---------- append stress_step
    if stress_step_data.get(current_id) is None:
        stress_step_data[current_id] = []    # initialize
    stress_step_data[current_id].append(stress_step)

    # ---------- save energy_step_data
    fs_step_data = (force_step_data, stress_step_data)
    pkl_data.save_fs_step(fs_step_data)

    # ---------- return
    return fs_step_data