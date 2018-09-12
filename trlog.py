"""trlog.py"""

from flask import Flask, render_template, request, abort, redirect, url_for, session
# these are for saving records
import sqlite3, time
# this is for keeping an activity log (who scanned what and when)
import logging

trailerDatabase = 'test.db'
trailerTable    = 'trailers'
projectTable    = 'projects'

app = Flask(__name__)
app.secret_key = '34_hRT4$es'

@app.errorhandler(404)
def page_not_found(error):
    return render_template('page_not_found.html'), 404

# Default home page
@app.route('/')
def index():
    return render_template("main_page.html")

# User/Project/Activity selection page
@app.route('/project', methods=['POST','GET'])
def select_project():
    if request.method == 'POST' :
        if request.form['userid'] != '':
            session['userid']=request.form['userid']
            session['projectid']=request.form['projectid']
            if request.form['activity'] == 'view' :
                return redirect(url_for('viewTrailerRecords'))
            elif request.form['activity'] == 'dock' :
                return redirect(url_for('scanTrailerAtDock'))
            elif request.form['activity'] == 'gate' :
                return redirect(url_for('scanTrailerAtGate'))
            else :
                pass
        else :
            return redirect(url_for('index'))

# DOCK SCAN: display prompt
@app.route('/dockconfirm')
def scanTrailerAtDock():
    """prompt for a trailer scan"""
    return render_template("scan_at_dock.html", projectid=session['projectid'], userid=session['userid'])

# DOCK SCAN: Confirm barcode, update record for last undeparted record, or add new if not found
@app.route('/dockconfirmstatus', methods=['POST','GET'])
def statusDockScan() :
    msg = 'status msg will go here'
    if request.form['submit'] == 'Submit' :
        # verify that trailer number was scanned...
        if  request.form['trailerbarcode'] != '' :
            tbarcode = request.form['trailerbarcode']
            # verify the prefix
            if tbarcode[0] == 'T' :
                # SAVE TRAILER SCAN RECORD HERE!!!
                msg = updateTrailerDockScan(tbarcode[1:])
                #msg = 'User: {un} Trailer: {tr} was scanned in dock at {ts}'.format(un=session['userid'], tr=tbarcode[1:], ts=time.asctime())
            else :
              msg = 'Wrong barcode!'
        else :
            msg = 'Please scan trailer barcode!'
    elif request.form['submit'] == 'Logout' :
        return redirect(url_for('index'))
    else :
        msg = 'shouldn\'t have got here!'
        
    return render_template("scan_status.html", statusmsg=msg, returnurl=url_for('scanTrailerAtDock'))

# GATE SCAN: Display 
@app.route('/gateconfirm')
def scanTrailerAtGate():
    """show trailer list with 'leaving' button/scan prompt"""
    tRecs = fetchTrailerRecs()
    ids   = tRecs.keys()
    ids.sort(reverse=True)
    return render_template("scan_at_gate.html", ss=session, trailerRecs=tRecs, ids=ids)

# GATE SCAN: save gate confirm to database, display confirmation message
@app.route('/gateconfirmstatus', methods=['POST','GET'])
def statusGateScan() :
    '''Handle input from gate view of trailer list'''
    msg = updateTrailerGateScan(session['userid'], request.form['submit'], False)
    return render_template("scan_status.html", statusmsg=msg, returnurl=url_for('scanTrailerAtGate'))

# GATE SCAN: undo a departure, remove gatets entry for this trailer's most recent entry
@app.route('/gateundodepart', methods=['POST','GET'])
def undoGateScan() :
    '''Handle undoing a gate scan'''
    msg = updateTrailerGateScan(session['userid'], request.form['undo'], True)
    return render_template("scan_status.html", statusmsg=msg, returnurl=url_for('scanTrailerAtGate'))

# VIEW
@app.route('/viewtrailers')
def viewTrailerRecords():
    """show last ?? trailer records and dock/gate scan status, refreshes every 30 seconds"""
    tRecs = fetchTrailerRecs()
    ids   = tRecs.keys()
    ids.sort(reverse=True)
    return render_template("view_trailer_records.html", trailerRecs=tRecs, ss=session, ids=ids)

# DATABASE Utilities

def flushOldRecords():
    """ delete trailer records more than 30 days old """
    pass

def updateTrailerDockScan(trailerid):
    """ update the record for this project/trailer with userid/timestamp of dock scan """
    conn = sqlite3.connect(trailerDatabase)
    c=conn.cursor()
    try:
        c.execute('select max(id) from trailers where projectid=\"{pid}\" and trailer=\"{tnum}\" and gatets is null'\
                  .format(pid=session['projectid'], tnum=trailerid))
        rec = c.fetchall()[0][0]
        if rec == None : # record does not exist
            query = 'insert into trailers (projectid,trailer,atdock,dockts,dockby) VALUES("{pid}","{tnum}",1,"{ts}","{un}")'\
                    .format(pid=session['projectid'],tnum=trailerid,ts=time.asctime(),un=session['userid'])
            #print(query)
            c.execute(query)
        else : # update existing record
            query = 'update trailers set atdock=1,dockts=\"{ts}\",dockby=\"{un}\" where id={recid}'\
                    .format(ts=time.asctime(),un=session['userid'],recid=rec)
            #print(query)
            c.execute(query)

        conn.commit()
        msg = 'Trailer: {tnum} scanned at dock at {ts}'.format(tnum=trailerid,ts=time.asctime())
    except sqlite3.Error as e:
        msg = 'Dock scan error: {err}'.format(err=e)
    finally:
        conn.close()
        
    return msg

def updateTrailerGateScan(userid, trailerid, undoFlag) :
    """ update the record for this project/trailer with userid/timestamp, undo if flag true """
    conn = sqlite3.connect(trailerDatabase)
    c = conn.cursor()
    if not undoFlag:
        try:
            # see if trailer# is on file without a gate scan, return highest id
            c.execute('SELECT MAX(id) from trailers where trailer=\"{tr}\" and projectid=\"{pid}\" and atgate is Null'.format(tr=trailerid,pid=session['projectid']))
            rec = c.fetchall()[0][0]
            if rec == None :
                # it's not on file, so we'll add it
                query='insert into trailers (projectid,trailer,atgate,gatets,gateby) VALUES("{pid}","{tnum}",1,"{ts}","{un}")'\
                          .format(pid=session['projectid'],tnum=trailerid,ts=time.asctime(),un=session['userid'])
                #print(query)
                c.execute(query)
            else:
                # It's on file, so we'll update it with new timestamp
                query='update trailers set atgate=1,gatets=\"{ts}\",gateby=\"{un}\" where id={recid}'\
                          .format(ts=time.asctime(), un=session['userid'], recid=rec)
                #print(query)
                c.execute(query)
                
            conn.commit()
            msg = 'Trailer: {tnum} departed at {ts}'.format(tnum=trailerid,ts=time.asctime()) 
        except sqlite3.Error as e:
            conn.close()
            msg = "Update record failed! {err}".format(err=e)
        finally:
            conn.close()
    else :          
        # should it be???
        msg = 'Undo gate scan not implemented yet!'
        
    return msg

def fetchTrailerRecs() :
    """ return a dict with trailer records for projectid, last 100 seen """
    # get trailer recs from database,
    # order descending by 'id'
    trailerRecs={}
    
    conn = sqlite3.connect(trailerDatabase)
    c = conn.cursor()
    try:
        c.execute('SELECT * FROM trailers where projectid=\"{pid}\" order by id desc, gatets desc, trailer desc limit 50'\
                  .format(pid=session['projectid']))
        recs = c.fetchall()
        if len(recs) > 0 :
            for rec in recs :
                trailerRecs[rec[0]] = {}
                trailerRecs[rec[0]]['number'] = rec[1]
                trailerRecs[rec[0]]['dockts'] = rec[4]
                trailerRecs[rec[0]]['dockby'] = rec[7]
                trailerRecs[rec[0]]['gatets'] = rec[5]
                trailerRecs[rec[0]]['gateby'] = rec[8]
                trailerRecs[rec[0]]['id'] = rec[0]
                
                print(rec)
                
        #print(recs)
    except sqlite3.Error as e :
        print(e)
    finally:
        conn.close()
    
    return trailerRecs



if __name__ == "__main__" :
    app.run(host='0.0.0.0',port='8080')
    


