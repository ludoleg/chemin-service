import qxrdtools

# datafilename = "cma.csv"
datafilename = "Mix3C-film.txt"

XRDdata = file(datafilename, 'r')

userData = qxrdtools.openXRD(XRDdata, datafilename)
print userData
