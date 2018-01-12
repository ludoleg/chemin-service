from flask import Flask, request, render_template, url_for, session, \
    make_response, redirect
from werkzeug.utils import secure_filename

import numpy as np
import StringIO
import csv
import sys
import logging
import json

from flask_cors import CORS

# Application modules
import qxrd
import qxrdtools
import phaselist

ALLOWED_EXTENSIONS = set(['txt', 'plv', 'csv', 'mdi', 'dif'])
UPLOAD_DIR = 'uploads'

# create the application object
app = Flask(__name__)
CORS(app)
app.logger.addHandler(logging.StreamHandler(sys.stdout))
app.logger.setLevel(logging.INFO)
app.logger.info('Welcome to Qanalyze')

# config
import os
app.config['UPLOAD_FOLDER'] = UPLOAD_DIR
app.secret_key = 'Ludo'

if not os.path.isdir(UPLOAD_DIR):
    os.mkdir(UPLOAD_DIR)


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
        else:
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


@app.route('/odr_demo')
def odr_demo():
    return render_template('odr_demo.html')


@app.route('/odr_post')
def odr_post():
    return render_template('odr_post.html')


# [START odr second pass process, this is run when the user changes the phases and relaunch after the chemin call]
@app.route('/process', methods=['GET'])
def process():
    # Load parameters for computation
    filename = session['filename']

    # Extract angle, diff to populate userData
    with open(os.path.join(app.config['UPLOAD_FOLDER'], filename)) as infile:
        array = json.load(infile)
    x = [li['x'] for li in array]
    y = [li['y'] for li in array]
    angle = np.asfarray(np.array(x))
    diff = np.asfarray(np.array(y))

    # Force mode
    Lambda = 0.0
    Target = 'Co'
    FWHMa = 0.0
    FWHMb = 0.35
    InstrParams = {"Lambda": Lambda,
                   "Target": Target,
                   "FWHMa": FWHMa,
                   "FWHMb": FWHMb}

    # Phase selection
    selectedPhases = session['selected']
    # Dif data captures all cristallographic data
    selectedphases = []
    for i in range(len(selectedPhases)):
        name, code = selectedPhases[i].split('\t')
        code = int(code)
        selectedphases.append((name, code))

    # Load in the DB file
    DBname = session['dbname']
    difdata = open(DBname, 'r').readlines()
    userData = (angle, diff)
    results, BG, calcdiff = qxrd.Qanalyze(userData,
                                          difdata,
                                          selectedphases,
                                          InstrParams,
                                          session['autoremove'],
                                          True)

    # Re-create the subset of phases to select
    sel, ava = rebalance(results)
    session['selected'] = sel
    session['available'] = ava
    # print(twoT.tolist(), file=sys.stderr)
    # print(userData, file=sys.stderr)

    twoT = userData[0]
    diff = userData[1]
    angle = twoT
    bgpoly = BG
    xmin = 5
    # xmax = max(angle)
    Imax = max(diff[min(np.where(np.array(angle) > xmin)[0])                    :max(np.where(np.array(angle) > xmin)[0])])
    offset = Imax / 2 * 3

    Sum = calcdiff
    difference_magnification = 1
    difference = (diff - Sum) * difference_magnification
    # logging.debug(results)
    # logging.info("Done with processing")
    difference = difference + offset

    csv = 'ODR'
    app.logger.warning('Length of angle array: %d', len(angle))
    print len(angle)

    session['results'] = results

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


# [START ODR service]
# Duplicates /process with input from the ODR site
@app.route('/chemin', methods=['GET', 'POST'])
def chemin():
    if request.method == 'POST':
        # print request.__dict__
        # Load data from request
        # Ajax case
        if request.is_json:
            json_data = request.get_json()
            data = json_data
        # Regular post, text/plain encoded in body
        else:
            # Regular post x-www-form-urlencoded
            dsample = request.form['data']
            data = json.loads(dsample)
            # Other type of encoding via text/plain
            # a, b = request.data.split('=')
            # data = json.loads(b)

        sample = data['sample']
        filename = sample['name']
        array = sample['data']

        # Save to file
        with open(os.path.join(app.config['UPLOAD_FOLDER'], filename), 'w') as outfile:
            json.dump(array, outfile)

        # Initialize the session object with chemin data
        session['autoremove'] = False
        session['dbname'] = 'difdata_CheMin.txt'
        session['selected'] = phaselist.cheminPhases
        session['available'] = phaselist.availablePhases
        session['filename'] = filename

        x = [li['x'] for li in array]
        y = [li['y'] for li in array]

        angle = np.asfarray(np.array(x))
        diff = np.asfarray(np.array(y))

        # Force mode
        Lambda = 0.0
        Target = 'Co'
        FWHMa = 0.0
        FWHMb = 0.35
        InstrParams = {"Lambda": Lambda,
                       "Target": Target,
                       "FWHMa": FWHMa,
                       "FWHMb": FWHMb}

        # Parse phases sent by ODR
        phasearray = data['phases']
        selectedphases = [(d['name'], d['AMCSD_code']) for d in phasearray]
        # TODO 2nd pass with selected

        # Force Chemin for ODR
        # Dif data captures all cristallographic data
        # Load in the DB file
        DBname = session['dbname']
        difdata = open(DBname, 'r').readlines()
        userData = (angle, diff)
        results, BG, calcdiff = qxrd.Qanalyze(userData,
                                              difdata,
                                              selectedphases,
                                              InstrParams,
                                              session['autoremove'],
                                              True)

        # Re-create the subset of phases to select
        sel, ava = rebalance(results)
        session['selected'] = sel
        session['available'] = ava
        # print(twoT.tolist(), file=sys.stderr)
        # print(userData, file=sys.stderr)

        twoT = userData[0]
        diff = userData[1]
        angle = twoT
        bgpoly = BG
        xmin = 5
        # xmax = max(angle)
        Imax = max(diff[min(np.where(np.array(angle) > xmin)[0])                        :max(np.where(np.array(angle) > xmin)[0])])
        offset = Imax / 2 * 3

        Sum = calcdiff
        difference_magnification = 1
        difference = (diff - Sum) * difference_magnification
        # logging.debug(results)
        # logging.info("Done with processing")
        difference = difference + offset

        csv = 'ODR'
        app.logger.warning('Length of angle array: %d', len(angle))

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


# [START PHASE MANIP]
@app.route('/phaseAnalysis', methods=['GET', 'POST'])
def phaseAnalysis():
    # select = request.form.get('key')
    # return select
    results = session['results']
    sel, ava = reformat
    session['selected'] = sel
    session['available'] = ava
    template_vars = {
        'availablephaselist': session['available'],
        'selectedphaselist': session['selected'],
        'mode': session['dbname']
    }
    return render_template('selector.html', **template_vars)

    # return render_template('selector.html')


def reformat(results):
    selected = [a[0] for a in results]
    available = []
    db = session['selected']

    # print selected
    # inventory = phaselist.rockPhasesj
    # print inventory
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
        else:
            i += 1

    for i in range(len(name)):
        available.append(name[i] + '\t' + code[i])

    # selected = [name+code for a in name]

    # selected = [name[0]+'\t'+str(a[1]) for a in results]
    # selected = [(name, code) for a in name]
    # print available
    # print selected
    selected = [a[0] + '\t' + str(a[1]) for a in results]
    # print selected, available
    return selected, available


def cleanup(results):
    selected = [a[0] + '\t' + str(a[1]) for a in results]
    return selected


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


if __name__ == '__main__':
    # This is used when running locally. Gunicorn is used for Heroku
    app.run(host='127.0.0.1', port=8080, debug=True)
# [END app]
