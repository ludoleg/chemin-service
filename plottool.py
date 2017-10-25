import matplotlib.pyplot as plt
import numpy as np

def overplotgraph(userdata,BGpoly,Sum, graphlist,filename):
    angle, diff = userdata
    angle = np.array(angle)
    diff = np.array(diff)
    fig = plt.figure(figsize=(15,5)) 
    plt.plot(angle, diff, linestyle="solid",  color="black")
    fig.patch.set_facecolor('white')
    plt.xlabel('2-theta (deg)')
    plt.ylabel('intensity')
    #plt.plot(BGX, BGY, linestyle="none",  marker="o", color="yellow")  #plots data og calculate linear background
    #plt.plot(angle, Diffmodel, linestyle="solid", color="green")
    plt.plot(angle, BGpoly, linestyle="solid", color="green")
    plt.plot(angle, Sum, linestyle="solid", color="blue")
    xmin = 5
    xmax = max(angle)
    plt.xlim(xmin,xmax)
    Imax = max(diff[min(np.where(np.array(angle)>xmin)[0]):max(np.where(np.array(angle)>xmin)[0])])
    plt.ylim(0,Imax*2)
    offset = Imax/2*3
    difference_magnification = 1
    difference = (diff - Sum) * difference_magnification
    offsetline = [offset]*len(angle)
    plt.plot(angle, difference+offset, linestyle="solid", color="pink")
    plt.plot(angle, offsetline, linestyle="dotted", color="red")
    textposleft = xmin+(xmax-xmin)/50
    percentpos = xmin+(xmax-xmin)/50*12
    FOMpos = xmax-(xmax-xmin)/50
    FOM = sum(abs(diff-Sum))/len(diff)
    plt.text(textposleft, offset/10*12, filename, fontsize=12, color="black")
    plt.text(FOMpos, offset/10*12, "FOM = %.2f" %(FOM), fontsize=12, color="pink", horizontalalignment='right')
    vertpos = offset/10*9 
    for i in range(0,len(graphlist)):
        minname = graphlist[i][0]
        code = graphlist[i][1]
        if len(minname)>12:
            minname = '%s.' %minname[0:12]
        plt.text(textposleft, vertpos,"%s #%s :" %(minname,code), fontsize=12, color="blue")       
        plt.text(percentpos, vertpos,"%.1f %%" %float(graphlist[i][2]), fontsize=12, color="blue",  horizontalalignment='right')
        vertpos -= offset/15
    if len(graphlist) == 10:
        plt.text(xmin+(xmax-xmin)/50, vertpos,"...", fontsize=12, color="blue")
    plt.show()

    return
