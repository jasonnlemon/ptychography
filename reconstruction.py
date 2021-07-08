from __future__ import division

# ptycho
from pynx2019.ptycho import*

# read save files
import os,sys,json
import csv
from PIL import Image

# math
import numpy as np

##########################################################################################
# define functions
##########################################################################################
def make_probe_gauss(probe_shape_pxlnb,probe_sigma_ratio,center=(0,0)):
    """
    return a circularly masked 2D gaussian electric field distribution without rotation, centered at (0,0)
    identical with the gauss function in simulation of didffraction pattern.
    """
    probe_sigma_pxlnb = probe_shape_pxlnb[1]//(2*probe_sigma_ratio[0]),probe_shape_pxlnb[0]//(2*probe_sigma_ratio[1])
    row, column = probe_shape_pxlnb
    v = np.array(probe_sigma_pxlnb) ** 2

    x = np.linspace(-column//2, column//2, column)
    y = np.linspace(-row//2, row//2, row)
    xx, yy = np.meshgrid(x, y)

    g = np.exp(-((xx-center[0])**2/(v[0])+(yy-center[1])**2/(v[1])))
    return g

def make_random_obj(obj_pxlnb):
    '''
    return a random object with normalised amplitude to 1 and stretched phase
    from -pi to pi.
    '''
    rand_phase = np.random.uniform(-np.pi,np.pi,obj_pxlnb)
    obj = np.random.uniform(0,1,obj_pxlnb) * np.exp(1j * rand_phase)    
    return obj

def center_scan(posx,posy):
    posx = np.array(posx)
    posy = np.array(posy)
    posx = posx - posx.mean()
    posy = posy - posy.mean()
    return (posx,posy)

def get_scan(path_scan_position):
    '''
    return scan_position.
    '''
    posx = []
    posy = []
    with open(path_scan_position,'r') as f:
        scan_reader = csv.reader(f)
        for row in scan_reader:
            posx.append(float(row[0]))
            posy.append(float(row[1]))
    scan_position = center_scan(posx,posy)
    return scan_position

def get_background(path_cam_bg):
    cam_bg = np.array(Image.open(path_cam_bg))
    return cam_bg

def get_diffraction_patterns(path_dir_diffraction):
    '''
    return 3D array of diffraction patterns in the order of scan.
    '''
    images = []
    valid_images = [".tif",".tiff",".bmp"]
    f_list = os.listdir(path_dir_diffraction)
    f_list.sort(key=lambda x:int(x[:-5]))
    for f in f_list:
        ext = os.path.splitext(f)[1]
        if ext.lower() not in valid_images:
            continue
        images.append(np.array(Image.open(os.path.join(path_dir_diffraction,f))))
    return images

def calc_obj_pxlsize(probe_wavelength,cam_obj_distance,cam_pxlnb,cam_pxlsize,nearfield):
    '''
    return a tuple of obj_pxlsize(xpxlsize,ypixelsize)
    '''
    if nearfield:
        obj_xpxlsize = cam_pxlsize
        obj_ypxlsize = cam_pxlsize
    else:
        obj_xpxlsize = probe_wavelength*cam_obj_distance/(cam_pxlnb[1]*cam_pxlsize)
        obj_ypxlsize = probe_wavelength*cam_obj_distance/(cam_pxlnb[0]*cam_pxlsize)
    obj_pxlsize = (obj_xpxlsize,obj_ypxlsize)
    return obj_pxlsize

def calc_obj_pxlnb(posx, posy, cam_pxlnb):
    """
    return the required pxl nb for the reconstructed object.
    """
    ny = int(2 * (abs(np.ceil(posy)) + 4).max() + cam_pxlnb[0])
    nx = int(2 * (abs(np.ceil(posx)) + 4).max() + cam_pxlnb[1])
    return ny, nx

##########################################################################################
# import simulationd data
##########################################################################################
# give simulation directory
path_dir_simulation = r'D:\scripts\ptychography\202107081707_ptycho_simulation' # DEFINE
# auto fill directory
path_dir_experiment = path_dir_simulation+'\\simulation_info'
path_dir_diffraction = path_dir_simulation+'\\diffraction_patterns'
# auto fill path
path_simulation_info = path_dir_experiment+'\\simulation_info.txt'
path_scan_position = path_dir_experiment+'\\scan_position.csv'
path_cam_bg = path_dir_experiment+'\\cam_bg.tiff'

# read simulation info
with open(path_simulation_info,'r') as f: 
    dict_simulationinfo = json.load(f)

# read scan position info
scan_position = get_scan(path_scan_position)
print('scan nb',len(scan_position[0]))

# read cam_bg
cam_bg = get_background(path_cam_bg)

# read diffraction pattern
intensity = get_diffraction_patterns(path_dir_diffraction)


##########################################################################################
# set parameters for known cam_obj_distance
##########################################################################################
# extract simulation for reconstruction
cam_pxlnb = dict_simulationinfo['cam_info']['cam_pxlnb']
cam_pxlsize = dict_simulationinfo['cam_info']['cam_pxlsize']
probe_wavelength = dict_simulationinfo['probe_info']['probe_wavelength']
cam_obj_distance = dict_simulationinfo['cam_info']['cam_obj_distance']
obj_nearfield = dict_simulationinfo['obj_info']['obj_nearfield']

print(f'cam_pxlnb:{cam_pxlnb} .')
print(f'cam_pxlsize:{cam_pxlsize:.3e} meter.')
print(f'probe_wavelength:{probe_wavelength:.3e} meter.')
print(f'cam_obj_distance:{cam_obj_distance:.3e} meter.')
print(f'obj_nearfield:{obj_nearfield}.')

##########################################################################################
# initial guess
##########################################################################################
# obj
obj_pxlsize = calc_obj_pxlsize(probe_wavelength,
                                cam_obj_distance,
                                cam_pxlnb,
                                cam_pxlsize,
                                obj_nearfield)

obj_pxlnb_pad = calc_obj_pxlnb(scan_position[0]/obj_pxlsize[0],
                                scan_position[1]/obj_pxlsize[1],
                                cam_pxlnb)

obj_init = make_random_obj(obj_pxlnb_pad)

# probe
probe_shape_pxlnb = cam_pxlnb
probe_sigma_ratio = (3,3)  # DEFINE

probe_shape_size = probe_shape_pxlnb[1]*obj_pxlsize[0],probe_shape_pxlnb[0]*obj_pxlsize[1]  # width height
probe_sigma_pxlnb = probe_shape_pxlnb[1]//(2*probe_sigma_ratio[0]),probe_shape_pxlnb[0]//(2*probe_sigma_ratio[1]) # width height
probe_sigma_size = probe_sigma_pxlnb[0]*obj_pxlsize[0],probe_sigma_pxlnb[1]*obj_pxlsize[1]  # width height
print(f'probe_shape_pxlnb:{probe_shape_pxlnb}.')
print(f'probe_shape_size is:{probe_shape_size[0]:.3e},{probe_shape_size[1]:.3e} meter.')
print(f'probe_sigma_pxlnb:{probe_sigma_pxlnb}.')
print(f'probe_sigma_size is:{probe_sigma_size[0]:.3e},{probe_sigma_size[1]:.3e} meter.')

probe_Efield_init = make_probe_gauss(probe_shape_pxlnb,probe_sigma_ratio)

##########################################################################################
# reconstruction
##########################################################################################
iteration_nb = 100 #DEFINE
do_ml = False #DEFINE
do_dm = True #DEFINE
do_ap = False #DEFINE

p_data = PtychoData(iobs=intensity, 
                    positions=(np.array(scan_position[0]),np.array(scan_position[1])), 
                    detector_distance=cam_obj_distance, 
                    pixel_size_detector=cam_pxlsize, 
                    wavelength=probe_wavelength)

p = Ptycho(probe=probe_Efield_init,
            obj=obj_init, 
            data=p_data, 
            background=cam_bg)

p = ScaleObjProbe(verbose=True) * p
if do_ml:
    p = ML(update_object=True, update_probe=True, calc_llk=5, show_obj_probe=5) ** iteration_nb * p
if do_dm:
    p = DM(update_object=True, update_probe=True, calc_llk=5, show_obj_probe=5) ** iteration_nb * p
if do_ap:
    p = AP(update_object=True, update_probe=True, calc_llk=5, show_obj_probe=5) ** iteration_nb * p




