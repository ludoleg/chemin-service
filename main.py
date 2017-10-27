# Copyright 2015 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from __future__ import print_function # In python 2.7
import sys

# [START app]
import logging


import os
import phaselist

import StringIO
import csv

from logics import QuantModeModel

from flask import Flask, flash, request, render_template, redirect, session, make_response, url_for, send_from_directory

#Application modules
import qxrd
import qxrdtools

import samples
import json

from werkzeug.utils import secure_filename


UPLOAD_DIR = 'uploads'
UPLOAD_FOLDER = UPLOAD_DIR

if not os.path.isdir(UPLOAD_DIR):
    os.mkdir(UPLOAD_DIR)

ALLOWED_EXTENSIONS = set(['txt', 'plv'])

    # [start config]
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = 'Ludo'

app.config['DEBUG'] = True

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# This will upload a file and print content
@app.route('/boo', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also
        # submit a empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return redirect(url_for('uploaded_file',
                                    filename=filename))
    return '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form method=post enctype=multipart/form-data>
      <p><input type=file name=file>
         <input type=submit value=Upload>
    </form>
    '''

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],
                               filename)


@app.route('/printdata', methods=['GET', 'POST'])
def printdata():
    resp = make_response(render_template('index.html'))
    return resp    

@app.route('/odr')
def odr():
    return render_template('odr.html')

@app.route('/')
def hello():
    session['inventory'] = 'rockforming';
    session['lambda'] = 0
    session['target'] = "Co"
    session['fwhma'] = -0.001348
    session['fwhmb'] = 0.352021
    session['title'] = 'default'
    session['selected'] = phaselist.defaultPhases
    session['available'] = phaselist.availablePhases

    print(session, file=sys.stderr)
    return render_template('index.html')


@app.route('/cheminfile')
def get_data():
#    return("upload your file")
    return '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form method=post enctype=multipart/form-data>
      <p><input type=file name=file>
         <input type=submit value=Upload>
    </form>
    '''
    
# [START form]
# This will upload a file and process as quant
@app.route('/form')
def form():
    return """
<form method="POST" action="/process" enctype="multipart/form-data">
    <input type="file" name="file">
    <input type="submit">
</form>
"""
# [END form]

# [START phase setting]
@app.route('/phase', methods=['GET', 'POST'])
def phase():
    if request.method == 'POST':
        selectedlist = request.form['selectedphase']
        availlist = request.form['availablephase']
        # selectedlist.sort()
        # availlist.sort()

        return redirect('/')
    else:
        mode = QuantModeModel()
        print(mode, file=sys.stderr)
        # session['mode'] = mode

        template_vars = {
            'availablephaselist': mode.available,
            'selectedphaselist': mode.selected,
            'mode': ''
        }
        return render_template('phase.html', **template_vars)

# [START process]
@app.route('/process', methods=['POST'])
def process():
    uploaded_file = request.files.get('file')
    if not uploaded_file:
        return 'No file uploaded.', 400

    # Load the sample data file in userData
    # parse sample data file wrt format

    filename = uploaded_file.filename
    XRDdata = uploaded_file
    userData = qxrdtools.openXRD(XRDdata, filename)

    # Unpack the selected inventory
    if session['inventory'] == "cement":
        # phaselistname = 'difdata_cement_inventory.csv'
        DBname ='difdata_cement.txt'
    elif session['inventory'] == "pigment":
        # phaselistname = 'difdata_pigment_inventory.csv'
        DBname ='difdata_pigment.txt'
    elif session['inventory'] == "rockforming":
        # phaselistname = 'difdata-rockforming_inventory.csv'
        DBname ='difdata-rockforming.txt'
    elif session['inventory'] == "chemin":
        # phaselistname = 'difdata_CheMin_inventory.csv'
        DBname ='difdata_CheMin.txt'
    else:
        logging.critical("Can't find inventory")
    # datafilename = "Mix3C-film.txt"
    
    # Calibration parameters
    Lambda = session['lambda']
    Target = session['target']
    FWHMa = session['fwhma']
    FWHMb = session['fwhmb']

    # Boundaries check
    if(Lambda > 2.2 or Lambda == 0):
        Lambda = ''
    if(FWHMa > 0.01):
        FWHMa = 0.01
    if(FWHMa < -0.01):
        FWHMa = -0.01
    if(FWHMb > 1.0):
        FWHMb = 1.0
    if(FWHMb < 0.01):
        FWHMb = 0.01    

    InstrParams = {"Lambda": Lambda, "Target": Target, "FWHMa": FWHMa, "FWHMb": FWHMb}

    # Phase selection
    selectedPhases = session['selected']
    print(selectedPhases, file=sys.stderr)

    # Dif data captures all cristallographic data
    selectedphases = []
    for i in range (len(selectedPhases)):
        name, code = selectedPhases[i].split('\t')
        code = int(code)
        selectedphases.append((name,code))

    # Load in the DB file
    difdata = open(DBname, 'r').readlines()

    results, BG, calcdiff = qxrd.Qanalyze(userData, difdata, selectedphases, InstrParams)

    # print(twoT.tolist(), file=sys.stderr)
    print(userData, file=sys.stderr)

    # session.results = results
    # session.put()
    twoT = userData[0]
    diff = userData[1]

    # logging.debug(results)
    # logging.info("Done with processing")

    angle = twoT
    # diff = diff
    bgpoly = BG
    #calcdiff = calcdiff


    # csv = session_data_key.urlsafe()
    csv = 'LUDO'
    
    template_vars = {
        'phaselist': results,
        'angle': angle.tolist(),
        'diff': diff.tolist(),
        'bgpoly': bgpoly.tolist(),
        'sum': calcdiff.tolist(),
        'url_text': csv,
        'key': 'ludo',
        'samplename': filename,
        'mode': ''
    }
    return render_template('chart.html', **template_vars)

    
    #    return "Total computation  time = %.2fs" %(time.time()-t0)
    #return_str = ''
    #return_str += 'results: {}<br />'.format(str(results))
    #return return_str
# [END process]

# [START chemin micro service]
# WE are not using np.loadtxt to split angle, diff so no need to massage for display
# util for chemin service
# util for chemin service
# util for chemin service
@app.route('/chemin', methods=['POST'])
def chemin_process_data():
    json_dict = request.get_json()
    # samplename = json_dict['samplename']
    # list = json_dict['phaselist']
    #    selectedphases = json_dict.items()
    list = json_dict['phaselist']
    samplename = json_dict['samplename']
    angle = json_dict['angle']
    diff = json_dict['diff']
    selectedphases = list.items()
    print(selectedphases, file=sys.stderr)

    # Chemin: Parameters are fixed, as well as the mineral database
    InstrParams = {"Lambda": 0, "Target": 'Co', "FWHMa": 0.00, "FWHMb": 0.35}
    DBname ='difdata_CheMin.txt'
    # Dif data captures all cristallographic data
    # Load in the DB file
    difdata = open(DBname, 'r').readlines()
    
    #Data coming from ODR
    #samplename = "Mix3C-film.txt"
    # userData = (samples.angle, samples.diff)
    userData = (angle, diff)
#    selectedphases = samples.phaselist.items()
    print(selectedphases, file=sys.stderr)
        
    results, BG, calcdiff = qxrd.Qanalyze(userData, difdata, selectedphases, InstrParams)
    print(userData, file=sys.stderr)

    twoT = userData[0]
    diff = userData[1]

    # logging.debug(results)
    # logging.info("Done with processing")

    angle = twoT
    # diff = diff
    bgpoly = BG
    #calcdiff = calcdiff

    # csv = session_data_key.urlsafe()
    csv = 'LUDO'
    
    template_vars = {
        'phaselist': results,
        'angle': angle,
        'diff': diff,
        'bgpoly': bgpoly.tolist(),
        'sum': calcdiff.tolist(),
        'url_text': csv,
        'key': 'ludo',
        'samplename': samplename,
        'mode': ''
    }
    return render_template('chart.html', **template_vars)
# [END chemin]

# [START CVS]
@app.route('/csvDownload', methods=['GET'])
def csvDownload():
#    response.headers['Content-Type'] = 'text/csv'
#    response.headers['Content-Disposition'] = 'attachment; filename={}.csv'.format(session.sampleFilename)
#    writer = csv.writer(self.response.out)
#    writer.writerow(['Mineral', 'AMCSD', 'Mass %'])
#    writer.writerows(session.results)

    line = StringIO.StringIO()
    cw = csv.writer(line)
    cw.writerow(['Mineral', 'AMCSD', 'Mass %'])
    output = make_response(line.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=export.csv"
    output.headers["Content-type"] = "text/csv"
    return output
# [END CVS]


# Start ludo
@app.route('/ludo')
def ludo():
    return render_template('odr.html')

@app.route('/ludo', methods=['POST'])
def ludo_process_data():
    json_dict = request.get_json()

    sample = json_dict["sample"]
    samplename = sample["name"]

    array = sample["data"]
    angle = [li['x'] for li in array]
    diff = [li['y'] for li in array]

    phasearray = json_dict["phases"]
    selectedphases = [(d['name'], d['AMCSD_code']) for d in phasearray]

    print(selectedphases, file=sys.stderr)

    # Chemin: Parameters are fixed, as well as the mineral database
    InstrParams = {"Lambda": 0, "Target": 'Co', "FWHMa": 0.00, "FWHMb": 0.35}
    DBname ='difdata_CheMin.txt'
    # Dif data captures all cristallographic data
    # Load in the DB file
    difdata = open(DBname, 'r').readlines()
    
    #Data coming from ODR
    #samplename = "Mix3C-film.txt"
    # userData = (samples.angle, samples.diff)
    userData = (angle, diff)
#    selectedphases = samples.phaselist.items()
    print(selectedphases, file=sys.stderr)
        
    results, BG, calcdiff = qxrd.Qanalyze(userData, difdata, selectedphases, InstrParams)
    print(userData, file=sys.stderr)

    twoT = userData[0]
    diff = userData[1]

    # logging.debug(results)
    # logging.info("Done with processing")

    angle = twoT
    # diff = diff
    bgpoly = BG
    #calcdiff = calcdiff

    # csv = session_data_key.urlsafe()
    csv = 'LUDO'
    
    template_vars = {
        'phaselist': results,
        'angle': angle,
        'diff': diff,
        'bgpoly': bgpoly.tolist(),
        'sum': calcdiff.tolist(),
        'url_text': csv,
        'key': 'ludo',
        'samplename': samplename,
        'mode': ''
    }
    return render_template('chart.html', **template_vars)
# [END ludo]




@app.errorhandler(500)
def server_error(e):
    logging.exception('An error occurred during a request.')
    return """
    An internal error occurred: <pre>{}</pre>
    See logs for full stacktrace.
    """.format(e), 500

if __name__ == '__main__':
    # This is used when running locally. Gunicorn is used to run the
    # application on Google App Engine. See entrypoint in app.yaml.
    app.run(host='127.0.0.1', port=8080, debug=True)
# [END app]


