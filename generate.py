import qxrdtools

# datafilename = "cma.csv"
datafilename = "reference_odr_Cumberland.csv"

XRDdata = file(datafilename, 'r')

userData = qxrdtools.openXRD(XRDdata, datafilename)
print userData

