#import libraries
import warnings 
warnings.filterwarnings("ignore",category=FutureWarning)
warnings.filterwarnings("ignore", message="numpy.dtype size changed")
import scipy.io as spio
import scipy.signal
import scipy.ndimage
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from collections import namedtuple
import math 
import re 
import pandas as pd
import os
import glob
from os.path import expanduser
import datetime
import statistics as stats
from plotly import __version__
from plotly.offline import download_plotlyjs, init_notebook_mode, plot, iplot
import plotly.graph_objs as go
init_notebook_mode(connected=True)



### Classes
class Keypoint:
    tag = ""
    parent = ['']
    child = ['']
    point = None

    def __init__(self,tag=None,parent=None,child=None,point=None):
        if tag is not None:            
            self.tag = tag
        if parent is not None:
            self.parent = parent
        if child is not None:
            self.child = child
        if point is not None:
            self.point = point


class Skeleton:
    keypoints = [Keypoint() for i in range(17)]
    tag2id = {
        "shoulderCenter" : 0,
        "head" : 1,
        "shoulderLeft" : 2,
        "elbowLeft" : 3,
        "handLeft" : 4,
        "shoulderRight" : 5,
        "elbowRight" : 6,
        "handRight" : 7,
        "hipCenter" : 8,
        "hipLeft" : 9,
        "kneeLeft" : 10,
        "ankleLeft" : 11,
        "footLeft" : 12,
        "hipRight" : 13,
        "kneeRight" : 14,
        "ankleRight" : 15,
        "footRight" : 16,
    }
    keypoints[tag2id["shoulderCenter"]] = Keypoint("shoulderCenter",[''],['head','shoulderLeft','shoulderRight','hipCenter'])
    keypoints[tag2id["head"]] = Keypoint("head",['shoulderCenter'],[''])
    keypoints[tag2id["shoulderLeft"]] = Keypoint("shoulderLeft",['shoulderCenter'],['elbowLeft'])
    keypoints[tag2id["elbowLeft"]] = Keypoint("elbowLeft",['shoulderLeft'],['handLeft'])
    keypoints[tag2id["handLeft"]] = Keypoint("handLeft",['elbowLeft'],[''])
    keypoints[tag2id["shoulderRight"]] = Keypoint("shoulderRight",['shoulderCenter'],['elbowRight'])
    keypoints[tag2id["elbowRight"]] = Keypoint("elbowRight",['shoulderRight'],['handRight'])
    keypoints[tag2id["handRight"]] = Keypoint("handRight",['elbowRight'],[''])
    keypoints[tag2id["hipCenter"]] = Keypoint("hipCenter",['shoulderCenter'],['hipLeft','hipRight'])
    keypoints[tag2id["hipLeft"]] = Keypoint("hipLeft",['shoulderCenter'],['kneeLeft'])
    keypoints[tag2id["kneeLeft"]] = Keypoint("kneeLeft",['hipLeft'],['ankleLeft'])
    keypoints[tag2id["ankleLeft"]] = Keypoint("ankleLeft",['kneeLeft'],['footLeft'])
    keypoints[tag2id["footLeft"]] = Keypoint("footLeft",['ankleLeft'],[''])
    keypoints[tag2id["hipRight"]] = Keypoint("hipRight",['shoulderCenter'],['kneeRight'])
    keypoints[tag2id["kneeRight"]] = Keypoint("kneeRight",['hipRight'],['ankleRight'])
    keypoints[tag2id["ankleRight"]] = Keypoint("ankleRight",['kneeRight'],['footRight'])
    keypoints[tag2id["footRight"]] = Keypoint("footRight",['ankleRight'],[''])

    def __init__(self,keyp_map=None):
        if keyp_map is not None:
            for tag in keyp_map.keys():
                self.keypoints[self.tag2id[tag]].point = keyp_map[tag] 

    def getKeypoint(self,keyp_tag):
        return self.keypoints[self.tag2id[keyp_tag]].point

    def getChild(self,keyp_tag):
        return self.keypoints[self.tag2id[keyp_tag]].child

    def getParent(self,keyp_tag):
        return self.keypoints[self.tag2id[keyp_tag]].parent

    def getTransformation(self):
        sagittal = None
        coronal = None
        transverse = None
        T = np.eye(4,4)
        if self.getKeypoint("shoulderLeft") is not None:
            if self.getKeypoint("shoulderRight") is not None:
                sagittal = self.getKeypoint("shoulderLeft")[0]-self.getKeypoint("shoulderRight")[0]
                sagittal = sagittal/np.linalg.norm(sagittal)
        if self.getKeypoint("shoulderCenter") is not None:
            if self.getKeypoint("hipLeft") is not None:
                if self.getKeypoint("hipRight") is not None:
                    transverse = self.getKeypoint("shoulderCenter")[0]-0.5*(self.getKeypoint("hipLeft")[0]+self.getKeypoint("hipRight")[0])
                    transverse = transverse/np.linalg.norm(transverse)
        if self.getKeypoint("shoulderCenter") is not None:
            pSC = self.getKeypoint("shoulderCenter")[0]

        if sagittal is not None:
            if coronal is not None:
                coronal = np.cross(sagittal,transverse)
                T[0,0]=coronal[0]
                T[1,0]=coronal[1]
                T[2,0]=coronal[2]
                T[0,1]=sagittal[0]
                T[1,1]=sagittal[1]
                T[2,1]=sagittal[2]
                T[0,2]=transverse[0]
                T[1,2]=transverse[1]
                T[2,2]=transverse[2]
                T[0,3]=pSC[0]
                T[1,3]=pSC[1]
                T[2,3]=pSC[2]
                T[3,3]=1
        return T

    def show(self):
        for i in range(len(self.keypoints)):
            k = self.keypoints[i]
            print("keypoint[", k.tag, "]", "=", k.point)

class Exercise:
    name = ""
    typee = ""
    metrics = []

class Tug(Exercise):
    name = "tug"
    typee = "test"
    metrics = ["ROM_0","ROM_1","ROM_2","ROM_3","ROM_4","ROM_5","step_0"]
    result = []
    month_res = {
        0: [],
        1: [],
        2: [],
        3: [],
        4: [],
        5: [],
        6: [],
        7: [],
        8: [],
        9: [],
        10: [],
        11: []
    }

    def __init__(self,month,result):
        self.result = result
        self.month_res[month] = result

    def getResult(self,month):
        return self.month_res[month]


class Metric:
    name = ''

    def __init__(self,name):
        self.name = name


class Step(Metric):
    name = "step"
    en_projection = False
    medfilt = 1
    step_thresh = 0.0
    tstanding = []
    tforward = []
    tturning1 = []
    tbackward = []
    tturning2 = []
    tsitting = []
    tend = []
    step_length = []
    step_width = []
    step_distance = []
    filtered_step_distance = []
    strikes = []
    nsteps = 0
    cadence = 0.0
    ex_time = 0.0
    walking_time = 0.0
    speed = 0.0 
    speed_z = 0.0 
    durata = 0
    
    def __init__(self,medfilt_window,en_projection, tstanding, tforward, tturning1, tbackward, tturning2, tsitting, tend, step_thresh, durata):

        # scipy median filter requires odd kernel size
        self.medfilt = int(medfilt_window)
        if not (self.medfilt & 1):
            self.medfilt = self.medfilt + 1

        self.step_thresh = step_thresh
        self.en_projection = en_projection
        self.tstanding = tstanding
        self.tforward = tforward
        self.tturning1 = tturning1
        self.tbackward = tbackward
        self.tturning2 = tturning2
        self.tsitting = tsitting
        self.tend = tend
        self.durata= durata


    def compute(self,skeleton):
        print('durata')
        print(self.durata)
        in_stand_idx, in_wf_idx, fin_wf_idx, fin_turn1_idx, fin_wb_idx, fin_turn2_idx, fin_sit_idx = compute_timing(skeleton, self.durata)
        timing_vec= [in_stand_idx, in_wf_idx, fin_wf_idx, fin_turn1_idx, fin_wb_idx, fin_turn2_idx, fin_sit_idx]
        timing_vec2= [self.tstanding, self.tforward, self.tturning1, self.tbackward, self.tturning2, self.tsitting, self.tend]
        phases_names= ['Standing', 'Walking forward', 'Turning1', 'Walking backward', 'Turning2', 'Sitting']


        win=10
        alj = skeleton.getKeypoint("ankleLeft")
        alj_filtered = scipy.signal.savgol_filter(alj, win, 2, axis=0)
        arj = skeleton.getKeypoint("ankleRight")
        arj_filtered = scipy.signal.savgol_filter(arj, win, 2, axis=0)
        hip = skeleton.getKeypoint("hipCenter")

        hip_filtered = scipy.signal.savgol_filter(hip, win, 2, axis=0)

        ankles_diff = alj[:, :2] - arj[:, :2]
        ankles_diff_filtered = alj_filtered[:, :2] - arj_filtered[:, :2]

        self.filtered_feet_distance = np.linalg.norm(ankles_diff_filtered, axis=1) #it is not the step
        self.feet_distance = np.linalg.norm(ankles_diff, axis=1)

        self.strikes,_ = scipy.signal.find_peaks(self.filtered_feet_distance, height = self.step_thresh, distance = 5) #we check peaks in the feet_distance

        if self.en_projection:
            shl = skeleton.getKeypoint("shoulderLeft")
            shl_filtered = scipy.signal.savgol_filter(shl, win, 2, axis=0)
            shr = skeleton.getKeypoint("shoulderRight")
            shr_filtered = scipy.signal.savgol_filter(shr, win, 2, axis=0)
            
            coronal = shl_filtered[:, :2] - shr_filtered[:, :2]
            coronal = coronal / np.linalg.norm(coronal)
            
            for i in range(len(shl)):
                dist = np.dot(ankles_diff_filtered[i,:],np.transpose(coronal[i,:]))
                self.step_width.append(dist)
                          
            for i in range(len(self.strikes)):
                peak_idx = self.strikes[i]
                v = ankles_diff_filtered[peak_idx,:] - self.step_width[peak_idx] * coronal[peak_idx,:]
                v = np.linalg.norm(v)
                self.step_length.append(v)

            self.step_length = stats.mean(self.step_length)
            self.step_width = stats.mean(self.step_width)
        else:
            slen = self.filtered_feet_distance[self.strikes]
            self.step_length = stats.mean(slen)
            self.step_width = np.fabs(ankles_diff) #da modificare

        with open ('report.txt', 'w') as file:   #Durata delle sottofasi: alzata, cammino andata, curva, cammino ritorno, seduta, numero di passi totali e nelle varie fasi, cadenza (passi al minuto). 
            for i in range(len(timing_vec)-1):

                file.writelines('Fase: '+ phases_names[i] + '\n')    
                tmp_idx=np.intersect1d(np.where(self.strikes>timing_vec[i]), np.where(self.strikes<timing_vec[i+1]))
                self.nsteps = len(self.strikes[tmp_idx])
                file.writelines('Passi: '+ str(self.nsteps) + '\n') 
                self.ex_time = timing_vec2[i+1] - timing_vec2[i]
                file.writelines('Tempo esecuzione: '+ str(format(self.ex_time,'.2f')) +' s\n') 
                self.cadence = self.nsteps / self.ex_time
                file.writelines('Pacing: '+ str(format(self.cadence,'.2f')) +' step/s\n') 
                
                move= np.diff(hip_filtered[timing_vec[i]:timing_vec[i+1],:2], axis=0)
                lengthmove = sum(np.linalg.norm(move, axis=1))
                self.speed =  lengthmove / self.ex_time      
                file.writelines('Velocity: '+ str(format(self.speed,'.2f')) +' m/s\n') 
                file.writelines('Acceleration: '+ str(format(self.speed/self.ex_time,'.2f')) +' m/s^2\n') 

                move_z= np.diff(hip_filtered[timing_vec[i]:timing_vec[i+1],2], axis=0)
                lengthmove_z = sum(abs(move_z))
                self.speed_z =  lengthmove_z / self.ex_time      
                file.writelines('Velocity in z: '+ str(format(self.speed_z,'.2f')) +' m/s\n') 
                file.writelines('Acceleration in z: '+ str(format(self.speed_z/self.ex_time,'.2f')) +' m/s^2\n') 
                file.writelines('\n')


            file.writelines('Full TUG\n')    
            self.nsteps = len(self.strikes)
            file.writelines('Steps: '+ str(self.nsteps) +'\n') 
            self.walking_time = timing_vec2[-2] - timing_vec2[1] #Durata totale del test: calcolata in automatico da quando il paziente si alza (gli ischi si staccano dalla sedia) a quando si risiede (gli ischi si appoggiano sulla sedia)
            file.writelines('Tempo di camminata: '+ str(format(self.walking_time,'.2f')) +' s\n')
            self.ex_time = timing_vec2[-1] - timing_vec2[0] #Durata totale del test: calcolata in automatico da quando il paziente si alza (gli ischi si staccano dalla sedia) a quando si risiede (gli ischi si appoggiano sulla sedia)
            file.writelines('Tempo TUG: '+ str(format(self.ex_time,'.2f')) +' s\n') 
            file.writelines('Mean step length: '+ str(format(self.step_length,'.2f')) +' m\n') 
            file.writelines('Mean step width: '+ str(format(self.step_width,'.2f')) +' m\n') 

            self.cadence = self.nsteps / self.walking_time
            file.writelines('Pacing: '+ str(format(self.cadence,'.2f')) +' step/s\n')  
                
            move= np.diff(hip_filtered[timing_vec[1]:timing_vec[-2],:2], axis=0)
            lengthmove = sum(np.linalg.norm(move, axis=1))
            self.speed =  lengthmove / self.ex_time      
            file.writelines('Velocity: '+ str(format(self.speed,'.2f')) +' m/s\n') 
            file.writelines('Acceleration: '+ str(format(self.speed/self.ex_time,'.2f')) +' m/s^2\n') 

            move_z= np.diff(hip_filtered[timing_vec[1]:timing_vec[-2],2], axis=0)
            lengthmove_z = sum(abs(move_z))
            self.speed_z =  lengthmove_z / self.ex_time      
            file.writelines('Velocity in z: '+ str(format(self.speed_z,'.2f')) +' m/s\n') 
            file.writelines('Acceleration in z: '+ str(format(self.speed_z/self.ex_time,'.2f')) +' m/s^2\n') 
               

###### General functions
def compute_kinematics(skeleton, tag):
    sc = skeleton.getKeypoint(tag)

    win=10
    poly_ord=2
    dev_ord=1

    acc_x = scipy.signal.savgol_filter(sc[:,0], win, poly_ord, 2, delta = 0.1, axis=0)
    acc_y = scipy.signal.savgol_filter(sc[:,1], win, poly_ord, 2, delta = 0.1, axis=0)
    acc_z = scipy.signal.savgol_filter(sc[:,2], win, poly_ord, 2, delta = 0.1, axis=0)
    vel_x = scipy.signal.savgol_filter(sc[:,0], win, poly_ord, dev_ord, delta = 0.1, axis=0)
    vel_y = scipy.signal.savgol_filter(sc[:,1], win, poly_ord, dev_ord, delta = 0.1, axis=0)
    vel_z = scipy.signal.savgol_filter(sc[:,2], win, poly_ord, dev_ord, delta = 0.1, axis=0)        

    return vel_x, vel_y, vel_z, acc_x, acc_y, acc_z


def compute_timing(skeleton, durata):
    dur= durata #49
    nsigma=3

    vel_shoulCenter_x, vel_shoulCenter_y, vel_shoulCenter_z, acc_shoulCenter_x, acc_shoulCenter_y, acc_shoulCenter_z= compute_kinematics(skeleton, "shoulderCenter")
    vel_hipCenter_x, vel_hipCenter_y, vel_hipCenter_z, acc_hipCenter_x, acc_hipCenter_y, acc_hipCenter_z = compute_kinematics(skeleton, "hipCenter")
    vel_ankleLeft_x, vel_ankleLeft_y, vel_ankleLeft_z, acc_ankleLeft_x, acc_ankleLeft_y, acc_ankleLeft_z = compute_kinematics(skeleton, "ankleLeft")
    vel_ankleRight_x, vel_ankleRight_y, vel_ankleRight_z, acc_ankleRight_x, acc_ankleRight_y, acc_ankleRight_z = compute_kinematics(skeleton, "ankleRight")
    vel_shoulRight_x, vel_shoulRight_y, vel_shoulRight_z, acc_shoulRight_x, acc_shoulRight_y, acc_shoulRight_z = compute_kinematics(skeleton, "shoulderRight")
    vel_shoulLeft_x, vel_shoulLeft_y, vel_shoulLeft_z, acc_shoulLeft_x, acc_shoulLeft_y, acc_shoulLeft_z = compute_kinematics(skeleton, "shoulderLeft")

    # L'alzata inizia quando noto un'accelerazione in z del centro delle spalle e, contemporaneamente, una crescita della distanza in y tra il centro delle spalle e il centro delle anche.
    init_mean= np.mean(acc_hipCenter_z[0:dur])
    init_std= np.std(acc_hipCenter_z[0:dur])
    cond1 = np.where(np.abs((acc_hipCenter_z-init_mean)/init_std) > nsigma)[0]
    cond2=np.where(np.diff(np.sign(acc_hipCenter_y-acc_shoulCenter_y)))[0]

    in_stand_idx= np.intersect1d(cond1,cond2)[0]

    # La camminata inizia appena uno dei due piedi accelera in y e finisce con l'inizio della rotazione. Quest'ultima inizia quando la distanza in x delle due spalle inizia a descrescere e ho superato la linea dei 3m.
    init_mean= np.mean(acc_ankleRight_y[0:dur])
    init_std= np.std(acc_ankleRight_y[0:dur])
    in_wf_Right_y_idx = np.where(np.abs((acc_ankleRight_y-init_mean)/init_std) > nsigma)[0]
    in_wf_Right_y_idx = np.where(vel_ankleRight_y[in_stand_idx:] < -1)[0]+in_stand_idx-2
    init_mean= np.mean(acc_ankleLeft_y[0:dur])
    init_std= np.std(acc_ankleLeft_y[0:dur])
    in_wf_Left_y_idx = np.where(np.abs((acc_ankleLeft_y-init_mean)/init_std) > nsigma)[0]
    in_wf_Left_y_idx = np.where(vel_ankleLeft_y[in_stand_idx:] < -1)[0]+in_stand_idx-2
    if in_wf_Right_y_idx[0]<in_wf_Left_y_idx[0]:
        cond1 = in_wf_Right_y_idx
    else:
        cond1 = in_wf_Left_y_idx
    cond2 = np.array(np.where(vel_hipCenter_y[in_stand_idx:]<0.))[0]+in_stand_idx-2#
    in_wf_idx=np.intersect1d(cond1,cond2)[0]

    diff_vel_x=vel_shoulRight_x-vel_shoulLeft_x
    diff_acc_x=acc_shoulRight_x-acc_shoulLeft_x
    cond1= np.array(np.where(diff_acc_x>0))[0]

    rfoot_cross3m = np.array(np.where(skeleton.getKeypoint("ankleRight")[:,1]<-3.))[0]#
    lfoot_cross3m = np.array(np.where(skeleton.getKeypoint("ankleLeft")[:,1]<-3.))[0]#
    if rfoot_cross3m[0]<lfoot_cross3m[0]:
        foot_cross3m = rfoot_cross3m
    else:
        foot_cross3m = lfoot_cross3m

    fin_wf_idx=np.intersect1d(cond1,foot_cross3m)[0]

    # La fase di rotazione quando la distanza in x delle due spalle ritorna ai valori iniziali e la velocita' in y del centro spalle e' positiva.
    diff_shoul = skeleton.getKeypoint("shoulderRight")[:,0]-skeleton.getKeypoint("shoulderLeft")[:,0]
    cond1= np.array(np.where(abs(diff_shoul[fin_wf_idx:]-abs(diff_shoul[0]))<0.01))[0]
    cond2 = np.array(np.where(vel_shoulCenter_y[fin_wf_idx:]>0.))[0]#
    fin_turn1_idx=np.intersect1d(cond1,cond2)[0]+fin_wf_idx

    # La fase di camminata di ritorno termina quando inizia la seconda rotazione.
    diff_acc_x=acc_shoulRight_x-acc_shoulLeft_x
    cond1= np.array(np.where(diff_acc_x[fin_turn1_idx:]<0))[0]

    rfoot_cross0m = np.array(np.where(skeleton.getKeypoint("ankleRight")[fin_turn1_idx:,1]>0.))[0]#
    lfoot_cross0m = np.array(np.where(skeleton.getKeypoint("ankleLeft")[fin_turn1_idx:,1]>0.))[0]#
    if rfoot_cross0m[0]<lfoot_cross3m[0]:
        foot_cross0m = rfoot_cross0m
    else:
        foot_cross0m = lfoot_cross0m
    fin_wb_idx=np.intersect1d(cond1,foot_cross0m)[0]+fin_turn1_idx

    # La seconda rotazione termina quando noto una decelerazione in z del centro delle spalle e, contemporaneamente, una diminuzione della distanza in y tra il centro delle spalle e il centro delle anche.
    cond1 = np.where(vel_shoulCenter_z[fin_wb_idx:] < 0.)[0]
    cond2=np.where(np.diff(np.sign(acc_hipCenter_y[fin_wb_idx:]-acc_shoulCenter_y[fin_wb_idx:])))[0]
    fin_turn2_idx= np.intersect1d(cond1,cond2)[0]+fin_wb_idx

    ###
    zero_vel = np.where(np.diff(np.sign(vel_shoulCenter_z[fin_turn2_idx:])))[0]
    in_sit_idx= fin_turn2_idx + zero_vel[0]
    init_mean= np.mean(acc_shoulCenter_z[:dur])
    init_std= np.std(acc_shoulCenter_z[:dur])
    outliers_indices1 = np.where(np.abs((acc_shoulCenter_z[fin_turn2_idx:]-init_mean)/init_std) < nsigma)[0]
    init_mean= np.mean(skeleton.getKeypoint("shoulderCenter")[:dur,2])
    init_std= np.std(skeleton.getKeypoint("shoulderCenter")[:dur,2])
    outliers_indices2 = np.where(np.abs((skeleton.getKeypoint("shoulderCenter")[fin_turn2_idx:,2]-init_mean)/init_std) < nsigma)[0]
    elem=np.intersect1d(outliers_indices1,outliers_indices2)[0]
    fin_sit_idx = fin_turn2_idx + elem

    return in_stand_idx, in_wf_idx, fin_wf_idx, fin_turn1_idx, fin_wb_idx, fin_turn2_idx, fin_sit_idx



## Additional functions to load data
def loadmat(filename):
    '''
    this function should be called instead of direct spio.loadmat
    as it cures the problem of not properly recovering python dictionaries
    from mat files. It calls the function check keys to cure all entries
    which are still mat-objects
    '''
    data = spio.loadmat(filename, struct_as_record=False, squeeze_me=True)
    return _check_keys(data)

def _check_keys(dict):
    '''
    checks if entries in dictionary are mat-objects. If yes
    todict is called to change them to nested dictionaries
    '''
    for key in dict:
        if isinstance(dict[key],  spio.matlab.mat_struct):
            dict[key] = _todict(dict[key])
    return dict        

def _todict(matobj):
    '''
    A recursive function which constructs from matobjects nested dictionaries
    '''
    dict = {}
    for strg in matobj._fieldnames:
        elem = matobj.__dict__[strg]
        if isinstance(elem, spio.matlab.mat_struct):
            dict[strg] = _todict(elem)
        else:
            dict[strg] = elem
    return dict
