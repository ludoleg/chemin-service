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

# [START app]
import logging

import numpy as np

import os
import phaselist

import StringIO
import csv

from flask import Flask, request, render_template, session, make_response, redirect, url_for
from flask_cors import CORS

# Application modules
import qxrd
import json

UPLOAD_FOLDER = 'uploads'

if not os.path.isdir(UPLOAD_FOLDER):
    os.mkdir(UPLOAD_FOLDER)

ALLOWED_EXTENSIONS = set(['txt', 'plv'])

# [start config]
app = Flask(__name__)
CORS(app)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = 'Ludo'

app.config['DEBUG'] = True


def rebalance(results):
    # Get the base list
    if session['dbname'] == 'difdata_cement.txt':
        db = phaselist.cementPhases
    elif session['dbname'] == 'difdata_pigment.txt':
        db = phaselist.pigmentPhases
    elif session['dbname'] == 'difdata-rockforming.txt':
        db = phaselist.rockPhases
    elif session['dbname'] == 'difdata_CheMin.txt':
        db = phaselist.cheminPhases

    available = []
    selected = [a[0] for a in results]
    inventory = [a.split('\t') for a in db]
    name = [a[0] for a in inventory]
    code = [a[1] for a in inventory]

    # for i in range(0, len(phaselist.rockPhases)):
    #     if selected[i] in phaselist.rockPhases[i]:
    #         print "yes"
    i = 0
    while i < len(name):
        if any(word in name[i] for word in selected):
            # print i, name[i]
            del name[i], code[i]
        i += 1

    for i in range(len(name)):
        available.append(name[i] + '\t' + code[i])

    selected = [a[0] + '\t' + str(a[1]) for a in results]
    selected.sort()
    available.sort()
    return selected, available


@app.route('/')
def hello():
    return render_template('index.html')


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/odr_demo')
def odr_demo():
    return render_template('odr_demo.html')


# [START ODR service]
# Duplicates /process with input from the ODR site
@app.route('/odr', methods=['GET', 'POST'])
def odr():
    if request.method == 'POST':
        # Load data from request
        json_data = request.get_json()
        data = json_data
        sample = data['sample']
        filename = sample['name']
        array = sample['data']

        # Save to file
        with open(os.path.join(app.config['UPLOAD_FOLDER'], filename), 'w') as outfile:
            json.dump(array, outfile)

        x = [li['x'] for li in array]
        y = [li['y'] for li in array]

        angle = np.asfarray(np.array(x))
        diff = np.asfarray(np.array(y))

        # Initialize the session object with chemin data
        session['autoremove'] = False
        session['dbname'] = 'difdata_CheMin.txt'
        session['selected'] = phaselist.cheminPhases
        session['available'] = phaselist.availablePhases

        # Parse phases sent by ODR
        phasearray = data['phases']
        selectedphases = [(d['name'], d['AMCSD_code']) for d in phasearray]
        # TODO 2nd pass with selected

        # Force mode
        InstrParams = {"Lambda": 0,
                       "Target": 'Co',
                       "FWHMa": 0.00,
                       "FWHMb": 0.35}

        # Force Chemin for ODR
        # Dif data captures all cristallographic data
        # Load in the DB file
        DBname = session['dbname']
        difdata = open(DBname, 'r').readlines()

        userData = (angle, diff)
        # print(userData)

        # Compute analysis QAnalyze
        results, BG, calcdiff = qxrd.Qanalyze(userData,
                                              difdata,
                                              selectedphases,
                                              InstrParams,
                                              session['autoremove'])

        # Re-create the subset of phases to select
        sel, ava = rebalance(results)
        session['selected'] = sel
        session['available'] = ava

        twoT = userData[0]
        diff = userData[1]

        Sum = calcdiff
        difference_magnification = 1
        difference = (diff - Sum) * difference_magnification
        # logging.debug(results)
        # logging.info("Done with processing")

        angle = twoT
        # diff = diff
        bgpoly = BG
        # calcdiff = calcdiff

        # csv = session_data_key.urlsafe()
        csv = 'ODR'
        session['results'] = results
        session['filename'] = filename

        template_vars = {
            'phaselist': results,
            'angle': angle.tolist(),
            'diff': diff.tolist(),
            'bgpoly': bgpoly.tolist(),
            'sum': calcdiff.tolist(),
            'difference': difference.tolist(),
            'url_text': csv,
            'key': 'ludo',
            'samplename': filename,
            'mode': 'Chemin-ODR',
            'availablephaselist': session['available'],
            'selectedphaselist': session['selected']
        }
        return render_template('chart.html', **template_vars)
    else:
        return '''<html><body><h1>Did not get a post!</h1></body></html>'''
# [END ODR service]


# [START CVS]
@app.route('/csvDownload', methods=['GET'])
def csvDownload():
    line = StringIO.StringIO()
    cw = csv.writer(line)
    cw.writerow(['Mineral', 'AMCSD', 'Mass %'])
    cw.writerows(session['results'])
    output = make_response(line.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename={}.csv".format(
        session['filename'])
    output.headers["Content-type"] = "text/csv"
    return output
# [END CVS]


@app.errorhandler(500)
def server_error(e):
    logging.exception('An error occurred during a request.')
    return """
    An internal error occurred: <pre>{}</pre>
    See logs for full stacktrace.
    """.format(e), 500


# [START phase setting]
@app.route('/phase', methods=['GET', 'POST'])
def phase():
    if request.method == 'POST':
        selectedlist = request.form.getlist('selectedphase')
        availlist = request.form.getlist('availablephase')
        selectedlist.sort()
        availlist.sort()
        session['available'] = availlist
        session['selected'] = selectedlist
        session['autoremove'] = False
        # print '####### Inside Phase ####'
        # print session['selected']
        # print '####### Inside Phase ####'
        # print session['available']
        return redirect(url_for('process'))
        # result = request.form.get()
        # return(str(selectedlist))
        # return render_template("result.html",result = result)
    else:
        # mode = QuantModeModel()
        # print(mode, file=sys.stderr)
        # session['mode'] = mode
        # session['selected'] = phaselist.defaultPhases
        template_vars = {
            'availablephaselist': session['available'],
            'selectedphaselist': session['selected'],
            'mode': session['dbname']
        }
        return render_template('phase.html', **template_vars)


def cleanup(results):
    selected = [a[0] + '\t' + str(a[1]) for a in results]
    return selected


# [START process]
@app.route('/process', methods=['GET'])
def process():
    # Load parameters for computation
    filename = session['filename']
    DBname = session['dbname']

    # Extract angle, diff to populate userData
    with open(os.path.join(app.config['UPLOAD_FOLDER'], filename)) as infile:
        array = json.load(infile)
    x = [li['x'] for li in array]
    y = [li['y'] for li in array]
    angle = np.asfarray(np.array(x))
    diff = np.asfarray(np.array(y))
    userData = (angle, diff)

    # Phase selection
    selectedPhases = session['selected']
    # print userData

    Lambda = 0.0
    Target = 'Co'
    FWHMa = 0.0
    FWHMb = 0.35
    InstrParams = {"Lambda": Lambda,
                   "Target": Target,
                   "FWHMa": FWHMa,
                   "FWHMb": FWHMb}

    # Dif data captures all cristallographic data
    selectedphases = []
    for i in range(len(selectedPhases)):
        name, code = selectedPhases[i].split('\t')
        code = int(code)
        selectedphases.append((name, code))

    # Load in the DB file
    difdata = open(DBname, 'r').readlines()

    results, BG, calcdiff = qxrd.Qanalyze(userData,
                                          difdata,
                                          selectedphases,
                                          InstrParams,
                                          session['autoremove'])
    # print results
    # session['results'] = results
    sel, ava = rebalance(results)
    session['selected'] = sel
    session['available'] = ava
    # print(twoT.tolist(), file=sys.stderr)
    # print(userData, file=sys.stderr)

    twoT = userData[0]
    diff = userData[1]

    Sum = calcdiff
    difference_magnification = 1
    difference = (diff - Sum) * difference_magnification
    # print difference
    # logging.debug(results)
    # logging.info("Done with processing")

    angle = twoT
    # diff = diff
    bgpoly = BG
    # csv = session_data_key.urlsafe()
    csv = 'ODR'

    template_vars = {
        'phaselist': results,
        'angle': angle.tolist(),
        'diff': diff.tolist(),
        'bgpoly': bgpoly.tolist(),
        'sum': calcdiff.tolist(),
        'difference': difference.tolist(),
        'url_text': csv,
        'key': 'ludo',
        'samplename': filename,
        'mode': session['dbname'],
        'availablephaselist': session['available'],
        'selectedphaselist': session['selected']
    }
    return render_template('chart.html', **template_vars)
# [END process]


if __name__ == '__main__':
    # This is used when running locally. Gunicorn is used for Heroku
    app.run(host='127.0.0.1', port=8080, debug=True)
# [END app]
