import os, sys, inspect
HERE_PATH = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
sys.path.append(HERE_PATH)

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
from geopy.geocoders import Nominatim
from sunrise import sun
from tzwhere import tzwhere
import pytz

# LOCATION ARGUMENT
tz = tzwhere.tzwhere()

if len(sys.argv) > 1:
    LOC_ARG = sys.argv[1]
else:
    LOC_ARG = "Rio de Janeiro Brazil"

# FUNCTIONS
def find_closest(x,a):
    """ Finds the closest index in x to a given value a."""
    return np.argmin(abs(x-a))

def add_clouds_to(axis,dates,highcloud,midcloud,lowcloud, interp=True):
    """ Adds the different types of clouds to a given axis."""
    # add sun (and moon?)
    for t in np.arange(len(dates)):
        idate = datetime.datetime(2018,6,7,12,0)
        while idate < dates[-1]:
            #sun = Circle((dates[t], 0.5), 0.2, color='yellow', zorder=0)
            sun = Ellipse((idate, 0.5), 0.4/2., 0.4, angle=0.0, color='yellow', zorder=0)
            axis.add_artist(sun)
            idate = idate + datetime.timedelta(1)

    # interpolate dates (if set)
    if interp:
        dates = spline_dates(dates)

    # add mean cloud covers and scale to [0...1]
    highcloudm = np.median(highcloud,axis=1)
    midcloudm = np.median(midcloud,axis=1)
    lowcloudm = np.median(lowcloud,axis=1)

    totalcloud=(highcloudm+midcloudm+lowcloudm)/3.
    totalcloudhalf=totalcloud/2.
    lowerbound=-totalcloudhalf+0.5
    upperbound=totalcloudhalf+0.5

    # don't plot clouds where totalcloud <= e.g. 0.05
    threshold=0.05

    # highcloud light grey, lowcloud dark grey
    axis.fill_between(dates, y1=lowerbound, y2=upperbound, color='0.95',zorder=1, alpha=0.8, edgecolor='none',where=totalcloud>=threshold)
    axis.fill_between(dates, y1=lowerbound, y2=upperbound-highcloudm/3., color='0.7',zorder=2, alpha=0.6, edgecolor='none',where=totalcloud>=threshold)
    axis.fill_between(dates, y1=lowerbound, y2=lowerbound+lowcloudm/3.,  color='0.4',zorder=3, alpha=0.3, edgecolor='none',where=totalcloud>=threshold)
    axis.set_facecolor('lightskyblue')
    axis.set_xlim([dates[0],dates[-1]])
    axis.set_ylim([0., 1])

def convert_longitude(lon):
    if lon < 0:
        return 360.+lon
    else:
        return lon

def lon_string(lon):
    if lon >= 0:
        return "{:.1f}".format(lon)+u'\N{DEGREE SIGN}'+"E"
    else:
        return "{:.1f}".format(abs(lon))+u'\N{DEGREE SIGN}'+"W"

def lat_string(lat):
    if lat > 0:
        return "{:.1f}".format(lat)+u'\N{DEGREE SIGN}'+"N"
    else:
        return "{:.1f}".format(abs(lat))+u'\N{DEGREE SIGN}'+"S"

def timezone_offset(loc,date):
    timezone_str = tz.tzNameAt(loc.latitude,loc.longitude)
    timezone = pytz.timezone(timezone_str)
    utcoffset = timezone.utcoffset(date)
    return utcoffset

def sunrise_sunset(loc,date):
    # find timezone first
    utcoffset = timezone_offset(loc,date)
    sunsun = sun(lat=loc.latitude,long=loc.longitude)
    t_sunrise = sunsun.sunrise(when=date)
    t_sunset = sunsun.sunset(when=date)

    # convert from time to datetime object
    t_sunrise = datetime.datetime(2000,1,1,t_sunrise.hour,t_sunrise.minute)
    t_sunset = datetime.datetime(2000,1,1,t_sunset.hour,t_sunset.minute)

    # add utcoffset
    t_sunrise = (t_sunrise+utcoffset).time()
    t_sunset = (t_sunset+utcoffset).time()		

    return t_sunrise,t_sunset

def sunrise_string(loc,date):

    sunsymb = u"\u263C"
    arrowup = u"\u2191"
    arrowdn = u"\u2193"

    sunrise,sunset = sunrise_sunset(loc,date)
    sunrise_str = "{:0=2d}:{:0=2d}".format(sunrise.hour,sunrise.minute)
    sunset_str = "{:0=2d}:{:0=2d}".format(sunset.hour,sunset.minute)
    
    return sunsymb+arrowup+sunrise_str+arrowdn+sunset_str

# READ DATA
DAT = Dataset(HERE_PATH+"/data/forecast.nc")
DATrain = Dataset(HERE_PATH+"/data/precip.nc")

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
   
# PICK LOCATION based on geopy
loc_search = LOC_ARG

geolocator = Nominatim()
loc = geolocator.geocode(loc_search)

lati = find_closest(lat,loc.latitude)   # index for given location
loni = find_closest(lon,convert_longitude(loc.longitude))

# shift dates according to timezone
utcoffset = timezone_offset(loc,dates[0])
dates = [d-utcoffset for d in dates]

# shifted datevector for rain
rain_left_space = 6
rdates = [d+three_hours for d in dates[:-rain_left_space]]

# extract data for given location
t = DAT.variables["t2m"][:,:,lati,loni]-273.15      # Kelvin to degC
u = DAT.variables["u10"][:,:,lati,loni]
v = DAT.variables["v10"][:,:,lati,loni]
lcc = DAT.variables["lcc"][:,:,lati,loni]
mcc = DAT.variables["mcc"][:,:,lati,loni]
hcc = DAT.variables["hcc"][:,:,lati,loni]
lsp = DATrain.variables["lsp"][:,:,lati,loni]*1e4       # only large-scale precip

# smooth and mean data
SPLINE_RES = 360

def spline_dates(dates, resolution=SPLINE_RES):

    numdates = date2num(dates)
    numdates_spline = np.linspace(numdates[0], numdates[-1], num=resolution)
    return num2date(numdates_spline)
    
numdates = date2num(dates)

# temperature
t_mean = np.mean(t, axis=1)
tminmax = (t.min(),t.max())
t_mean_spline = interp1d(numdates, t_mean, kind='cubic')

# interpolation of data
def spline_data_by_date(data, numdates=numdates, resolution=SPLINE_RES):
    numdates_spline = np.linspace(numdates[0], numdates[-1], num=resolution)
    data_spline = np.empty((resolution, data.shape[1]))
    for e in range(0, data.shape[1]):
        spline = interp1d(numdates, data[:,e], kind='cubic')
        data_spline[:,e] = spline(numdates_spline)
    return data_spline

t_data_spline = spline_data_by_date(t)
lcc_data_spline = spline_data_by_date(lcc)
mcc_data_spline = spline_data_by_date(mcc)
hcc_data_spline = spline_data_by_date(hcc)

# calculate precipitation probability
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
C0_example[:,-1] = [0.2,1.]

dsize = 78
dstring = (2, 0, 45) #"|" #(1, 0, 45) #"o"


#  axes formatting
def cloud_ax_format(ax,dates,loc):
    loc_name = loc.address.split(",")[0]
    ax.set_title("Meteogram "+loc_name+" ("+lat_string(loc.latitude)+", "+lon_string(loc.longitude)+")",loc="left",fontweight="bold")
    ax.set_xticks([])
    ax.set_yticks([])

def rain_ax_format(ax,dates):
    ax.set_xlim(dates[0],dates[-1])
    ax.set_ylim(-0.5,2.5)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.plot([0.88,0.88],[-1,3],transform=ax.transAxes,alpha=.5,lw=0.5)
    ax.scatter([0.9,0.9],[0.3,0.55],dsize,linewidths=2,color=C0_example,transform=ax.transAxes,marker=dstring)
    ax.text(0.92,0.75,"rainfall",fontsize=8,fontweight="bold",transform=ax.transAxes,ha="left")
    ax.text(0.92,0.5,"very likely",fontsize=8,transform=ax.transAxes,ha="left")
    ax.text(0.92,0.25,"less likely",fontsize=8,transform=ax.transAxes,ha="left")

def temp_ax_format(ax,tminmax,dates):
    ax.text(0.01,0.92,sunrise_string(loc,dates[0]),fontsize=10,transform=ax.transAxes)
    ax.set_yticks(np.arange(np.round(tminmax[0])-3,np.round(tminmax[1])+3,3))
    ax.set_ylim(np.round(tminmax[0])-3,np.round(tminmax[1])+3)
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

    # add vertical line after each sunday
    mondays = [datetime.datetime(2018,6,11,0,0)]
    for m in mondays:
        ax.plot([m,m],[-50,50],"k",lw=0.1)

def temp_plotter(ax, times, mean_spline, data_spline, mean_c='C1', data_c='orange', alpha=0.05):
    numtime = date2num(spline_dates(times))
    mean = mean_spline(numtime)
    data = data_spline

    #ax.plot(times, mean, mean_c)

    for i in range(data.shape[1]):
        ax.fill_between(numtime,mean,data[:,i],facecolor=data_c,alpha=alpha)  


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

temp_plotter(temp_ax, dates, t_mean_spline, t_data_spline)
add_clouds_to(cloud_ax,dates,hcc_data_spline,mcc_data_spline,lcc_data_spline)


# light rain
rain_ax.scatter(rdates,np.zeros_like(rdates),dsize,linewidths=2,color=C0_lightrain,marker=dstring)

# medium rain
rain_ax.scatter([d+dt for d in rdates],1.08+np.zeros_like(rdates),dsize,linewidths=2,color=C0_medrain,marker=dstring)
rain_ax.scatter([d-dt for d in rdates],0.92+np.zeros_like(rdates),dsize,linewidths=2,color=C0_medrain,marker=dstring)

# heavy rain
rain_ax.scatter([d+dt+dt for d in rdates],2.15+np.zeros_like(rdates),dsize,linewidths=2,color=C0_heavyrain,marker=dstring)
rain_ax.scatter([d+dt for d in rdates],2.03+np.zeros_like(rdates),dsize,linewidths=2,color=C0_heavyrain,marker=dstring)
rain_ax.scatter([d-dt for d in rdates],1.97+np.zeros_like(rdates),dsize,linewidths=2,color=C0_heavyrain,marker=dstring)

rain_ax.yaxis.set_ticks(np.arange(3))
rain_ax.set_yticklabels(('light','medium','heavy'), fontsize=8)

plt.show()
