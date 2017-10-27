import simplejson as json

with open('odr.json') as data_file:
    odr = json.load(data_file)

sample = odr["sample"]
phasearray = odr["phases"]

#print (sample)

array = sample["data"]

angle = [li['x'] for li in array]
diff = [li['y'] for li in array]
#print angle
#print diff

#phaselist = [a['name','AMCSD_code'] for a in phasearray]
bob = [(d['name'], d['AMCSD_code']) for d in phasearray]

print bob

