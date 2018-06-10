import numpy as np
import matplotlib.pyplot as plt
from matplotlib.dates import DayLocator, HourLocator, DateFormatter, drange, date2num, num2date
from netCDF4 import Dataset
from matplotlib.ticker import FormatStrFormatter
import datetime
from matplotlib import gridspec
from scipy.interpolate import interp1d
from matplotlib.patches import Circle, Ellipse
from matplotlib.collections import PatchCollection

# READ DATA
path = "git/prob_meteogram/data/"
DAT = Dataset(path+"forecast.nc")
DATrain = Dataset(path+"precip.nc")

# grid
lat = DAT.variables["latitude"][:]
lon = DAT.variables["longitude"][:]
time = DAT.variables["time"][:]
n_members = len(DAT.variables["number"][:])

# convert time to datetime objects
datetime0 = datetime.datetime(1900,1,1)
dt = datetime.timedelta(hours=0.7)
dates = [datetime0 + datetime.timedelta(hours=int(t)) for t in time]
three_hours = datetime.timedelta(hours=3.)
rain_left_space = 6
rdates = [d+three_hours for d in dates[:-rain_left_space]]

# FUNCTIONS
def find_closest(x,a):
    """ Finds the closest index in x to a given value a."""
    return np.argmin(abs(x-a))

def add_clouds_to(axis,dates,highcloud,midcloud,lowcloud):
    """ Adds the different types of clouds to a given axis."""
    # add sun (and moon?)
    for t in np.arange(time.shape[0]):
        if dates[t].hour==12:
            #sun = Circle((dates[t], 0.5), 0.2, color='yellow', zorder=0)
            sun = Ellipse((dates[t], 0.5), 0.4/1.5, 0.4, angle=0.0, color='yellow', zorder=0)
            axis.add_artist(sun)
    # add mean cloud covers and scale to [0...1]
    highcloudm = np.median(highcloud,axis=1)
    midcloudm = np.median(midcloud,axis=1)
    lowcloudm = np.median(lowcloud,axis=1)
    
    totalcloud=(highcloudm+midcloudm+lowcloudm)/3.
    totalcloudhalf=totalcloud/2.
    lowerbound=-totalcloudhalf+0.5
    upperbound=totalcloudhalf+0.5
    # highcloud light grey, lowcloud dark grey
    axis.fill_between(dates, y1=lowerbound, y2=upperbound, color='0.95',zorder=1, alpha=0.8, edgecolor='none')
    axis.fill_between(dates, y1=lowerbound, y2=upperbound-highcloudm/3., color='0.7',zorder=2, alpha=0.6, edgecolor='none')
    axis.fill_between(dates, y1=lowerbound, y2=lowerbound+lowcloudm/3.,  color='0.4',zorder=3, alpha=0.3, edgecolor='none')
    axis.set_facecolor('lightskyblue')
    axis.set_xlim([dates[0],dates[-1]])
    axis.set_ylim([0., 1])

# PICK LOCATION
lat0 = 21.5      # in degrees
lon0 = 0

lati = find_closest(lat,lat0)   # index for given location
loni = find_closest(lon,lon0)
loc = (lat[lati],lon[loni])

# extract data for given location
t = DAT.variables["t2m"][:,:,lati,loni]-273.15      # Kelvin to degC
u = DAT.variables["u10"][:,:,lati,loni]
v = DAT.variables["v10"][:,:,lati,loni]
lcc = DAT.variables["lcc"][:,:,lati,loni]
mcc = DAT.variables["mcc"][:,:,lati,loni]
hcc = DAT.variables["hcc"][:,:,lati,loni]
#TODO this is only large-scale preicipitation, add convective precip?
lsp = DATrain.variables["lsp"][:,:,lati,loni]*1e4


## smooth and mean temperature
SPLINE_RES = 360

t_mean = np.mean(t, axis=1)
tminmax = (t.min(),t.max()) 

numdates = date2num(dates)
t_mean_spline = interp1d(numdates, t_mean, kind='cubic')
dates_fine = np.linspace(numdates[0], numdates[-1], num=SPLINE_RES)

t_data_spline = np.empty((SPLINE_RES, t.shape[1]))
for e in range(0, t.shape[1]):
    t_spline = interp1d(numdates, t[:,e], kind='cubic')
    t_data_spline[:,e] = t_spline(dates_fine)

## calculate precipitation probability
bins = np.array([min(0,lsp.min()),0.05,0.5,1,max(2,lsp.max())])        # in mm

P = np.empty((len(bins)-1,len(rdates)))                  # probablity per rainfall category
for i in range(len(rdates)):
    P[:,i],_ = np.histogram(lsp[i,:],bins)

P = P/n_members

# turn into alpha values
C0_blue = np.zeros((P.shape[1],4))
C0_blue[:,0] = 0.12         # RGB values of "C0" matplotlib standard
C0_blue[:,1] = 0.47
C0_blue[:,2] = 0.71

C0_lightrain = C0_blue.copy()
C0_medrain = C0_blue.copy()
C0_heavyrain = C0_blue.copy()

C0_lightrain[:,3] = P[1,:]
C0_medrain[:,3] = P[2,:]
C0_heavyrain[:,3] = P[3,:]

C0_example = C0_blue[:2,:]
C0_example[:,-1] = [0.3,1.]

dsize = 28
dstring = "o"


##  axes formatting
def cloud_ax_format(ax,dates,loc):
    #TODO make city automatic?
    ax.set_title("Meteogram London ({:.1f}N, {:.1f}E)".format(loc[0],loc[1]),loc="left",fontweight="bold")
    ax.set_xticks([])
    ax.set_yticks([])
 
def rain_ax_format(ax,dates):
    ax.set_xlim(dates[0],dates[-1])
    ax.set_ylim(-0.5,2.5)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.plot([0.88,0.88],[-1,3],transform=ax.transAxes,alpha=.5,lw=0.5)
    ax.scatter([0.9,0.9],[0.35,0.65],dsize,color=C0_example,transform=ax.transAxes,marker=dstring)
    ax.text(0.92,0.6,"very likely",fontsize=8,transform=ax.transAxes,ha="left")
    ax.text(0.92,0.3,"less likely",fontsize=8,transform=ax.transAxes,ha="left")

def temp_ax_format(ax,tminmax,dates):
    ax.text(0.02,0.94,"sun up/down",fontsize=8,transform=ax.transAxes)
    ax.set_yticks(np.arange(np.round(tminmax[0])-3,np.round(tminmax[1])+3,3))    #TODO make automatic
    ax.set_ylim(np.round(tminmax[0])-3,np.round(tminmax[1])+3)                   #TODO make automatic
    ax.yaxis.set_major_formatter(FormatStrFormatter('%d'+u'\N{DEGREE SIGN}'+'C'))
    
    # x axis lims, ticks, labels
    ax.set_xlim(dates[0],dates[-1])
    ax.xaxis.set_minor_locator(HourLocator(np.arange(0, 25, 6)))    # minor
    ax.xaxis.set_minor_formatter(DateFormatter("%Hh"))
    ax.get_xaxis().set_tick_params(which='minor', direction='in',pad=-10,labelsize=6)
    ax.grid(alpha=0.15)
    
    ax.xaxis.set_major_locator(DayLocator())                        # major
    ax.xaxis.set_major_formatter(DateFormatter(" %a\n %d %b"))
    for tick in ax.xaxis.get_majorticklabels():
        tick.set_horizontalalignment("left")

    # remove labels at edges
    ax.get_xticklabels()[-1].set_visible(False)
    ax.get_xticklabels(which="minor")[-1].set_visible(False)
    ax.get_xticklabels(which="minor")[0].set_visible(False)

# plotting routines

def temp_plotter(ax, times, mean_spline, data_spline, mean_c='r', data_c='orange', alpha=0.05):
    mean = mean_spline(times)
    data = data_spline

    ax.plot(times, mean, mean_c)

    for i in range(data.shape[1]):
        ax.fill_between(times,mean,data[:,i],facecolor=data_c,alpha=alpha)


# PLOTTING
fig = plt.figure(figsize=(10,4))

# subplots adjust
all_ax = gridspec.GridSpec(3, 1, height_ratios=[1,2,6],hspace=0)
cloud_ax = plt.subplot(all_ax[0])
rain_ax = plt.subplot(all_ax[1])
temp_ax = plt.subplot(all_ax[2])

plt.tight_layout(rect=[0.02,.03,1,0.97])

# do axes formatting
cloud_ax_format(cloud_ax,dates,loc)
rain_ax_format(rain_ax,dates)
temp_ax_format(temp_ax,tminmax,dates)

temp_plotter(temp_ax, dates_fine, t_mean_spline, t_data_spline)
add_clouds_to(cloud_ax,dates,hcc,mcc,lcc)


# light rain
rain_ax.scatter(rdates,np.zeros_like(rdates),dsize,color=C0_lightrain,marker=dstring)

# medium rain
rain_ax.scatter([d+dt for d in rdates],1.08+np.zeros_like(rdates),dsize,color=C0_medrain,marker=dstring)
rain_ax.scatter([d-dt for d in rdates],0.92+np.zeros_like(rdates),dsize,color=C0_medrain,marker=dstring)

# heavy rain
rain_ax.scatter(rdates,2.15+np.zeros_like(rdates),dsize,color=C0_heavyrain,marker=dstring)
rain_ax.scatter([d+dt for d in rdates],2.03+np.zeros_like(rdates),dsize,color=C0_heavyrain,marker=dstring)
rain_ax.scatter([d-dt for d in rdates],1.97+np.zeros_like(rdates),dsize,color=C0_heavyrain,marker=dstring)

plt.show()