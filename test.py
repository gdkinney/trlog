import sqlite3, time

trailerDatabase = 'test.db'
trailerTable = 'trailers'
projectTable = 'projects'
curProjID    = 'MAP-POPA'

def tag_trailer_at_dock(projID, trailer) :
    conn = sqlite3.connect(trailerDatabase)
    c = conn.cursor()

    c.execute('INSERT INTO {tt} (projectid, trailer, atdock, dockts) VALUES("{pid}","{tnum}",True,"{ts}");'\
              .format(tt=trailerTable,pid=projID,tnum=trailer,ts=time.asctime()))

    conn.commit()
    conn.close()

    
