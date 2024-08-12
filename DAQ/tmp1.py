####################################################################
### Written by Yong Ma and Jason Cardarelli                  #######
### Must Hard-Code the values for diags, rawpath, and savepath   ###
### diags: the name of the diagnostics to save - can be anyhting.###
### file_types: file extension for the diag to be saved. List    ###
###             should be same order as diags.                   ###
### savepath: the final path for data to be organized and saved. ###
### rawpath: the local path that each diag is saved to.          ###

from genericpath import isfile
from turtle import forward
# import matplotlib as mpl
import os
import sys
import glob
import time
from shutil import copy2
import matplotlib.pyplot as plt
import numpy as np
import matplotlib
from matplotlib.colors import ListedColormap, LinearSegmentedColormap
import matplotlib.colors as colors
from matplotlib import cm
from matplotlib.widgets import RangeSlider, Button
import cv2
from scipy.interpolate import interp1d
# from playsound import playsound
from PIL import Image
import datetime
import skimage.io as skio
import re
import csv
import time

add_laser_cam = True
replace_PW_with_TA2_Far = False
if replace_PW_with_TA2_Far:
	laser_cam = 'TA2-FarField'
else:
	laser_cam = 'PW_Comp_In'
counter = 0

diags =      ['EspecL', 'EspecH', 'Shadowgraphy','Ebeam', 'Betatron']
file_types = ['tif', 'tif', 'tif', 'tif', 'tif']

savepath = 'N:\\2024\\TA1-internalCommissioning'
# savepath = 'N:\\2024\\Qing_test'

rawpath = [
		   f'C:\\Users\\High Field Science\\Documents\\DAQ\\Baslers\\TA1-EspecL-tmp\\',
		   f'C:\\Users\\High Field Science\\Documents\\DAQ\\Baslers\\TA1-EspecH-tmp\\',
		   f'C:\\Users\\High Field Science\\Documents\\DAQ\\Baslers\\TA1-Shadowgraphy-tmp\\',
		   f'C:\\Users\\High Field Science\\Documents\\DAQ\\Baslers\\TA1-Ebeam-tmp\\',
		   f'W:\\',
		   ]
if add_laser_cam:
	file_types.append('tif')
	rawpath.append(f'C:\\Users\\High Field Science\\Documents\\DAQ\\Baslers\\{laser_cam}\\')
	diags.append(laser_cam)

###For especH
ek        =      np.array([400,   600,  800,  1000, 1200, 1400, 1600, 1800, 2000, 2500, 3000])
ek_pixels = (72 - np.array([11.6, 23.5, 29.3, 34.1, 37.9, 42.9, 47.6, 51.4, 54.5, 60.3, 64.4])) * 70 + 324 
ek_pixels =  np.array([int(ek_pixels[i]) for i in range(len(ek_pixels))])

#f'C:\\Users\\High Field Science\\Documents\\DAQ\\Baslers\\TA1-Autocorr-tmp\\',

currdate = datetime.date.today()


espec_calib_filename = 'INSTERT PATH TO .NPY FILE HERE'
espec_xaxis = 'Pixel' # change to either Energy, Space, or Pixel. Pixels means ploting the raw image; Energy means ploting the calibrated energy sprectrum with provided magnet dispersion curves.

from scipy.interpolate import interp1d


def xaligned_axes(ax, y_distance, width, **kwargs):
    return plt.axes([ax.get_position().x0+0.15*ax.get_position().width,
                     ax.get_position().y0-y_distance,
                     ax.get_position().width-0.3*ax.get_position().width, width],
                    **kwargs)

def yaligned_axes(ax, x_distance, width, **kwargs):
    return plt.axes([ax.get_position().x0 + ax.get_position().width + x_distance,
                     0.95*ax.get_position().y0,
                     0.1*ax.get_position().width, 0.2*ax.get_position().height],
                    **kwargs)


def overwrite_data_checker(past_shots, counter, diags, file_type, savepath, first_loop=False):
### This should be re-written to check os.path.exists() for the data in the diags first. Check all diags file names with shot number and see if 
	shot_num = -1
	reinput = True
	if counter == 0:
		print("\nThis is your first shot since running this code. Please be mindful that you're not overwriting a shot number on your first shot.")
	while reinput is True:
		shot_num    = input('\nWhenever you are ready please input a shot number, I will save the data for you: ')
		if not shot_num.isdigit():
			print("Shot number must be numeric. Please re-enter.")
			continue
		past_exists = []
		exists_indiceis = []
		for ii, diag in enumerate(diags):
			if os.path.exists(r'%s%s\shot%s.%s'%(savepath, diag, shot_num, file_type[ii])):
				past_exists.append(True)
				exists_indiceis.append(ii)
			else:
				past_exists.append(False)
		if any(past_exists):
			overwrite_loop = True
			while overwrite_loop is True:
				overwrite_y_n = input(f"Wait! Shot {shot_num} in this date & run already exists for {sum(past_exists)} diagnostics: {[diags[ll] for ll in exists_indiceis]}.\nOverwrite shot {shot_num}? (y/n) ")
				if overwrite_y_n.lower() == 'n' or overwrite_y_n.lower() == 'no':
					reinput = True
					overwrite_loop = False
				elif overwrite_y_n.lower() == 'y' or overwrite_y_n.lower() == 'yes':
					reinput = False
					overwrite_loop = False
				else:
					print("I did not understand your response. Please answer again.")
					overwrite_loop = True
		else:
			if first_loop == True:
				for ii in range(1,int(shot_num)+1):
					past_shots.append(str(ii))
					# first_loop = False
			else:
				past_shots.append(shot_num)
			reinput = False
	return shot_num

def does_this_file_exist(filepath):
	if not os.path.exists(filepath):
		return False
	else:
		overwrite_warning = input(f"WHOA! You've already taken this shot. Overwrite? (y/n): ")
		if overwrite_warning.lower() == 'y':
			return False
		else:
			return True
def non_match_dicts(dict_a, dict_b):
    diff = dict(dict_a.items() - dict_b.items())
    #print(diff)
    if diff == {}:
        # print("Empty Set")
        return []
    else:
        # print("NOT empty set")
        return diff


#################################################
skip_terminal_call = False
breaknow = False
shotnum = 0
repeating_shot = False
def main():
	global counter
	global skip_terminal_call
	global shotnum
	global repeating_shot
	global breaknow
	global savepath
	global espec_xaxis
	global ek
	global ek_pixels
	use_vlim_sliders = True
	use_figure_buttons = True
	vmin_range = []
	vmax_range = [] 
	vlims   = [[0*jj,0] for jj in range(len(diags))]
	
	while True:
		#if shotnum > 10:
		#	break
		# print(savepath)
		date    = input('\nPlease input a date, so I can make a new folder for you: ')
		run_num = input('\nPlease input a run number: ')
		run_date_string = f'\\{date}_run{run_num}\\'
		savepath = savepath + run_date_string

		saveplot = savepath + '/rawplot/'
		if not os.path.exists(savepath):
			os.makedirs(savepath)
			os.makedirs(saveplot)
			print('I have made a new folder for you which is %s'%savepath)
			break
		elif os.path.exists(savepath):
			save_exist_path = input('\nPath exists, do you want to save to %s, (y/n)?'%savepath)
			if save_exist_path.lower() == 'y':
				break
			else:
				print('\nPath exists! Try again!')
				continue	
	
	past_shots = ['-1']
	first_loop = True
	prev_file  = []
	prev_mtime = [] 
	updated_data = []
	currentDate = datetime.date.today()
	#l_ene_sheet = open(f'{savepath}laserEnergy_{date}_run{run_num}.csv', 'a', newline = '')
	#l_ene_sheet_writer = csv.writer(l_ene_sheet, delimiter=',')
	#if os.stat(f'{savepath}laserEnergy_{date}_run{run_num}.csv').st_size == 0:
	#	l_ene_sheet_writer.writerow(['DAQ_Shotnum', 'Timestamp [(hh)(mm)(ss)(centisecond)]', 'Labview_ShotsTodayNum', 'Energy_Measurement [J]'])
	while True:
		
		#First we'll run a check if we've taken the shot being input by the user already; and if so, ask if they want to overwrite their data or not.
		if skip_terminal_call == False:
			shotnum = overwrite_data_checker(past_shots, counter, diags, file_types, savepath, first_loop)
		else:
			skip_terminal_call = False
		mid_code_overwrite = 'y'
		start = time.process_time()
		#^^ending geting shot number from user
		time.sleep(0.5)
		less_to_plot = 0
		for diag_item in diags:
			if '_noplot' in diag_item:
				less_to_plot = less_to_plot+1
		if  (len(diags)-less_to_plot) == 1:
			figuresize_0 = [18,9]
			nrows, ncols = 1, 1
			fig, axs = plt.subplots(nrows, ncols, figsize = (figuresize_0[0],figuresize_0[1]), num = counter+1, subplot_kw=dict(aspect = 'auto'))
		elif  (len(diags)-less_to_plot) == 2:
			figuresize_0 = [18,9]
			nrows, ncols = 1, 2
			fig, axs = plt.subplots(nrows, ncols, figsize = (figuresize_0[0],figuresize_0[1]), num = counter+1, subplot_kw=dict(aspect = 'auto'))
		elif (len(diags)-less_to_plot) == 3:
			figuresize_0 = [18,9]
			nrows, ncols = 1, 3
			fig, axs = plt.subplots(nrows, ncols, figsize = (figuresize_0[0],figuresize_0[1]), num = counter+1, subplot_kw=dict(aspect = 'auto'))
		elif (len(diags)-less_to_plot) == 4:
			figuresize_0 = [18,9]
			nrows, ncols = 2, 2
			fig, axs = plt.subplots(nrows, ncols, figsize = (figuresize_0[0],figuresize_0[1]), num = counter+1, subplot_kw=dict(aspect = 'auto'))
		elif (len(diags)-less_to_plot) == 5 or (len(diags)-less_to_plot) == 6:
			figuresize_0 = [18,9]
			nrows, ncols = 2, 3
			fig, axs = plt.subplots(nrows, ncols, figsize = (figuresize_0[0],figuresize_0[1]), num = counter+1, subplot_kw=dict(aspect = 'auto'))
			if len(diags)-less_to_plot == 5:
				axs[1][2].set_axis_off()
		elif (len(diags)-less_to_plot) == 7 or (len(diags)-less_to_plot) == 8:
			figuresize_0 = [20,9]
			nrows, ncols = 2, 4
			fig, axs = plt.subplots(nrows, ncols, figsize = (figuresize_0[0],figuresize_0[1]), num = counter+1, subplot_kw=dict(aspect = 'auto'))
			if (len(diags)-less_to_plot) == 7:
				axs[1][3].set_axis_off()
		
		plt.subplots_adjust(hspace = 0.45, wspace = 0.40)
		fig.subplots_adjust(bottom=0.15)
		fig.suptitle(f"Date: {date} - Run: {run_num} - Shot: {shotnum}")
		if len(diags) > 1:
			axs = axs.ravel()
		else:
			axs = [axs]
		plt.ion()
		plt.show()
		imgs = [] 
		
		for i in range(len(diags)):
			savepath_diags = savepath +  str(diags[i]).replace('_noplot', '').replace('_savemulti', '') 
			if not os.path.exists(savepath_diags):
				os.makedirs(savepath_diags)	

			os.chdir(rawpath[i])
			list_of_files = glob.glob(r'*.%s*'%file_types[i] )

			latest_file = max(list_of_files, key=os.path.getmtime)
			if first_loop == True:
				prev_file.append(latest_file)# = os.path.getmtime(latest_file)
				prev_mtime.append(os.path.getmtime(latest_file))
				updated_data.append(True)
			else:
				if (latest_file != prev_file[i]) or (os.path.getmtime(latest_file) != prev_mtime[i]): 
					#Checks to see if the filename or the file modified time is changed from previous latest file
					updated_data[i] = True
					prev_file[i] =latest_file
					prev_mtime[i] = os.path.getmtime(latest_file)
				else:
					#This indicates that the new file has both the same file name and the same modified time (data did not update!)
					updated_data[i] = False
					prev_file[i] = latest_file
					prev_mtime[i] = os.path.getmtime(latest_file)
			plat = sys.platform
			if plat == "win32":#LaserEnergy_noplot
				if diags[i] == 'LaserEnergy_noplot':
					# print('In Diag IF')
					if os.path.exists(f'G:\\Dropbox\\Kettle2022\\Laser Diagnostics\\{currentDate.strftime("%Y%m%d")}\\{currentDate.strftime("%Y%m%d")}_Energy.csv'):
						# print("In File Exists IF")
						with open(f'G:\\Dropbox\\Kettle2022\\Laser Diagnostics\\{currentDate.strftime("%Y%m%d")}\\{currentDate.strftime("%Y%m%d")}_Energy.csv', 'r') as raw_lene_file:
							# print("In open file.")
							last_line = raw_lene_file.readlines()[-1].replace('\n','').split(',')
							# print([str(shotnum)] + last_line)
							l_ene_sheet_writer.writerow([str(shotnum)] + last_line)
				elif not "_savemulti" in diags[i]:
					if add_laser_cam and 'J.tif' in latest_file:
						copy2(latest_file, savepath_diags + '/shot%d_%s'%(int(shotnum), latest_file.split('_')[-1]))
					else:
						copy2(latest_file, savepath_diags + './shot%d.%s'%(int(shotnum), file_types[i]))
				else:
					ordered_mod_time_file_list = []
					for path, subdirs, files in os.walk('.'):
						for name in sorted(files, key=lambda name: os.path.getmtime(os.path.join(path, name))):
							ordered_mod_time_file_list.append(name)
					N = 4
					latest_N_files = ordered_mod_time_file_list[-N:]
					for channel, file in enumerate(latest_N_files):
						copy2(file, savepath_diags + './scopechannel%d_shot%d.%s'%(int(channel+1),int(shotnum), file_types[i]))
			else:
				copy2(latest_file, savepath_diags + '/shot%d.%s'%(int(shotnum), file_types[i]))
			if '_noplot' in diags[i]:
				continue
			if file_types[i] == 'npy':
				im = np.load(latest_file)
			else:
				im = skio.imread(latest_file)

			#Color image, manually change to gray. Should be very rare, skio should handle this.
			if im.any() != None:
				if len(im.shape)==3:
					im = np.dot(im[...,:3], [0.2989, 0.5870, 0.1140])

			# im = cv2.medianBlur(im, 3)

			# if type(im != object):
			# 	if updated_data[i] == False and repeating_shot == False:
			# 		im_ax = axs[i].imshow(np.array(im), cmap = cm.magma, aspect='auto', vmin = np.min(im), vmax = np.max(im), alpha = 0.5)
			# 		axs[i].text(0.5,0.5,"NOT UPDATED", fontsize = 20, horizontalalignment='center', verticalalignment='center', transform=axs[i].transAxes, c= 'r', bbox=dict(facecolor='w', alpha=0.5))
			# 		axs[i].text(0.1, 0.05, 'mean = %.1f'%(np.mean(im)), transform = axs[i].transAxes, c = 'w')
			# 	else:
			# 		im_ax = axs[i].imshow(np.array(im), cmap = cm.magma, aspect='auto', vmin = np.min(im), vmax = np.max(im))
			# 		axs[i].text(0.1, 0.05, 'mean = %.1f'%(np.mean(im)), transform = axs[i].transAxes, c = 'w')
											
			# else:
			if updated_data[i] == False and repeating_shot == False:
				im_ax = axs[i].imshow(im, cmap = cm.magma, aspect='auto', vmin = np.min(im), vmax = np.max(im), alpha = 0.5)
				axs[i].text(0.5,0.5,"NOT UPDATED", fontsize = 20, horizontalalignment='center', verticalalignment='center', transform=axs[i].transAxes, c = 'r', bbox=dict(facecolor='w', alpha=0.5))
				axs[i].text(0.1, 0.85, 'mean = %.1f'%(np.mean(im)), transform = axs[i].transAxes, c = 'w')

			else:
				if diags[i] == 'EspecH':
					im_ax = axs[i].imshow(im, cmap = cm.magma, aspect='auto', vmin = np.min(im), vmax = np.max(im))
					axs[i].text(0.1, 0.85, 'mean = %.1f'%(np.mean(im)), transform = axs[i].transAxes, c = 'w')
					for j in range(len(ek)):
						axs[i].axvline(ek_pixels[j], ls = '--', color = 'gray', lw = 0.5)
						axs[i].text(ek_pixels[j]-70, 3000-j*100, str(ek[j])+'MeV', color = 'w', fontsize = 8 ) 
				else:
					im_ax = axs[i].imshow(im, cmap = cm.magma, aspect='auto', vmin = np.min(im), vmax = np.max(im))
					axs[i].text(0.1, 0.85, 'mean = %.1f'%(np.mean(im)), transform = axs[i].transAxes, c = 'w')

			
			axs[i].set_title(f'{diags[i]} shot {int(shotnum):03}')
			imgs.append(im_ax)
		fig.canvas.blit(fig.bbox)

		print(f"Finished shot {shotnum}. Going to shot {int(shotnum) + 1}.")


		if use_vlim_sliders == True:
			###ADDING SLIDERS
			sliders  = []
			sliders_ax = []
			sliders_range = []
			repeating_shot = False
			for ii in range(len(diags)):
				if '_noplot' in diags[ii]:
					continue
				axslider_i = xaligned_axes(ax=axs[ii], y_distance=0.06, width=0.03, facecolor='black')
				sliders_ax.append(axslider_i)
				axsliderrange_i = xaligned_axes(ax=axs[ii], y_distance=0.085, width=0.03, facecolor='black')
				imgz = axs[ii].get_images()
				if first_loop == True:
					if len(imgz) > 0:
						vmin_range.append(imgz[0].get_clim()[0])
						vmax_range.append(imgz[0].get_clim()[1])
						vmin_int  , vmax_int   = imgz[0].get_clim()
						if vmin_int == vmax_int:
							vmax_range[ii] = (vmax_range[ii] + 10)
							vmax_int   = vmax_range[ii]
					else:
						vmin_range.append(imgz.get_clim()[0])
						vmax_range.append(imgz.get_clim()[1])
						vmin_int  , vmax_int   = imgz.get_clim()
						if vmin_int == vmax_int:
							vmax_range[ii] = (vmax_range + 10)
							vmax_int   = vmax_range
					vlims[ii] = [vmin_int, vmax_int]
				else:
						if len(imgz) > 0:
							if imgz[0].get_clim()[0] < vmin_range[ii]:
								vmin_range[ii] = imgz[0].get_clim()[0]
							elif imgz[0].get_clim()[1] > vmax_range[ii]:
								vmax_range[ii] = imgz[0].get_clim()[1]
						else:
							if imgz.get_clim()[0] < vmin_range[ii]:
								vmin_range[ii] = imgz.get_clim()[0]
							elif imgz.get_clim()[1] > vmax_range[ii]:
								vmax_range[ii] = imgz.get_clim()[1]
						vmin_int = vlims[ii][0]
						vmax_int = vlims[ii][1]

				# slider = RangeSlider(axslider_i, "(cmin, cmax)", vmin_range[ii], vmax_range[ii], (vmin_int, vmax_int), )
				# slider.label.set_size(10)
				# sliders.append(slider)
				# imgs[ii].set_clim(sliders[ii].val[0], sliders[ii].val[1])

				slider_range = RangeSlider(axsliderrange_i, "Cbar Range", vmin_range[ii], vmax_range[ii], (vmin_int, vmax_int),)
				slider_range.label.set_size(10)
				sliders_range.append(slider_range)
				slider = RangeSlider(axslider_i, "(cmin, cmax)", slider_range.val[0], slider_range.val[1], (vmin_int, vmax_int), )
				slider.label.set_size(10)
				sliders.append(slider)
				imgs[ii].set_clim(sliders[ii].val[0], sliders[ii].val[1])


			# for ii in range(len(diags)):
			# 	sliders[ii].valmin = int(sliders_range[ii].val[0])
			# 	sliders[ii].valmax = int(sliders_range[ii].val[1])
			# 	if sliders[ii].val[0] < slidesr_range[ii].val[0]:
			# 		sliders[ii].set_min(sliders_range[ii].val[0])
			# 	if sliders[ii].val[1] > sliders_range[ii].val[1]:
			# 		sliders[ii].set_max(sliders_range[ii].val[1])
			# 	sliders[ii].ax.set_xlim(sliders[ii].valmin,sliders[ii].valmax)
			# 	imgs[ii].set_clim(sliders[ii].val[0], sliders[ii].val[1])
			# 	vlims[ii] = [sliders[ii].val[0], sliders[ii].val[1]]

			def update_vlims_slider(val):
				for ii in range(len(diags)):
					if '_noplot' in diags[ii]:
						continue
					imgs[ii].set_clim(sliders[ii].val[0], sliders[ii].val[1])
					vlims[ii] = [sliders[ii].val[0], sliders[ii].val[1]]
					fig.canvas.draw_idle()

			def update_vlims_slider_range(val):
				for ii in range(len(diags)):
					if '_noplot' in diags[ii]:
						continue
					sliders[ii].valmin = int(sliders_range[ii].val[0])
					sliders[ii].valmax = int(sliders_range[ii].val[1])
					if sliders[ii].val[0] < sliders_range[ii].val[0]:
						sliders[ii].set_min(sliders_range[ii].val[0])
					if sliders[ii].val[1] > sliders_range[ii].val[1]:
						sliders[ii].set_max(sliders_range[ii].val[1])
					sliders[ii].ax.set_xlim(sliders[ii].valmin,sliders[ii].valmax)
					imgs[ii].set_clim(sliders[ii].val[0], sliders[ii].val[1])
					vlims[ii] = [sliders[ii].val[0], sliders[ii].val[1]]
					fig.canvas.draw_idle()

			for ii in range(len(diags)):
				if '_noplot' in diags[ii]:
					continue
				sliders_range[ii].on_changed(update_vlims_slider_range)
				sliders[ii].on_changed(update_vlims_slider)

			if mid_code_overwrite.lower() == 'n':
				mid_code_overwrite = 'y'
				continue

		if use_figure_buttons == True:
			###ADDING BUTTONS:
			
			def next_shot(val):
				global skip_terminal_call
				global shotnum
				skip_terminal_call = True
				shotnum = int(shotnum) + 1
				# print(f"Finished shot {shotnum}. Going to shot {int(shotnum) + 1}.")
				plt.close()

			def redo_shot(val):
				global skip_terminal_call
				global shotnum
				global counter
				global repeating_shot
				skip_terminal_call = True
				repeating_shot = True
				os.remove(saveplot + 'plot_%s_run%s_shot%03d.png'%(date, run_num,int(shotnum)))
				print(f"Redoing shot {shotnum}")
				counter = counter - 1
				plt.close()

			def end_run(val):
				global breaknow
				breaknow = True
				plt.close()
			
			boverwrite_axes = plt.axes([0.1, 0.01, 0.2, 0.05])
			bredo_axes = plt.axes([0.4, 0.01, 0.2, 0.05])
			bnextshot_axes = plt.axes([0.7, 0.01, 0.2, 0.05])
			bendrun_axes = plt.axes([0.1, 0.95, 0.04, 0.02])
			boverwrite_axes.set_visible(False)
			bredo_axes.set_visible(False)
			bendrun_axes.set_visible(False)
			bnextshot_axes.set_visible(False)
			plt.savefig(saveplot + 'plot_%s_run%s_shot%03d.png'%(date, run_num,int(shotnum)), dpi = 100, )
			boverwrite_axes.set_visible(True)
			bredo_axes.set_visible(True)
			bendrun_axes.set_visible(True)
			bnextshot_axes.set_visible(True)

			
			bredo = Button(bredo_axes, 'Repeat Shot',color="royalblue", hovercolor = "yellow")
			bredo.label.set_fontsize(14)
			bredo.label.set_fontweight('bold')
			bredo.on_clicked(redo_shot)
			
			bnextshot = Button(bnextshot_axes, 'Next Shot',color="royalblue", hovercolor = "yellow")
			bnextshot.label.set_fontsize(14)
			bnextshot.label.set_fontweight('bold')
			bnextshot.on_clicked(next_shot)
			
			bendrun = Button(bendrun_axes, 'END RUN',color="tomato", hovercolor = "red")
			bendrun.label.set_fontsize(6)
			bendrun.on_clicked(end_run)

			boverwrite = Button(boverwrite_axes, 'Overwrite Rawplot',color="royalblue", hovercolor = "yellow")
			boverwrite.label.set_fontsize(14)
			boverwrite.label.set_fontweight('bold')
			def overwrite_raw(val):
				boverwrite_axes.set_visible(False)
				bredo_axes.set_visible(False)
				bendrun_axes.set_visible(False)
				bnextshot_axes.set_visible(False)
				print(f"Overwriting rawplot for shot {shotnum}")
				figu = matplotlib.pyplot.gcf()
				figusize = figu.get_size_inches()
				figu.set_size_inches(figuresize_0[0],figuresize_0[1], forward = True)
				os.remove(saveplot + 'plot_%s_run%s_shot%03d.png'%(date, run_num,int(shotnum)))
				plt.savefig(saveplot + 'plot_%s_run%s_shot%03d.png'%(date, run_num,int(shotnum)), dpi = 100, )
				boverwrite_axes.set_visible(True)
				bredo_axes.set_visible(True)
				bendrun_axes.set_visible(True)
				bnextshot_axes.set_visible(True)
				figu.set_size_inches(figusize, forward = True)
			boverwrite.on_clicked(overwrite_raw)
		
		plt.figtext(0.75, 0.96, s="DAQ Code Written By Yong Ma & Jason Cardarelli, 2023")
		# print(time.process_time() - start)
		plt.show(block = True)
		if use_figure_buttons == False:
			plt.savefig(saveplot + 'plot_%s_run%s_shot%03d.png'%(date, run_num,int(shotnum)), dpi = 100, )

		if breaknow == True:
			break
		counter = counter + 1
		first_loop = False
if __name__ == '__main__':
		main()
