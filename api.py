__author__ = 'Reem'

import flask
from src import diff_finder
from src.diff_finder import Table, DiffFinder
import caleydo_server.dataset as dataset
import timeit

#create an Flask app for hosting my namespace
app = flask.Flask(__name__)

#request my configuration
#import caleydo_server.config
#config = caleydo_server.config.view('taco_server')

@app.route('/hello/<whom>')
def hello_world(whom):
  return 'hello world' +  whom+ ' ' + flask.request.args.get('to')

@app.route('/jsontest')
def jsontest():
  return flask.jsonify({'x': 'where are you', 'y': "too"})


#@direction: 0 rows, 1 cols, 2 both rows and cols
@app.route('/diff_log/<id1>/<id2>/<lod>/<direction>/<ops>')
def diff_log(id1, id2, lod, direction, ops):
    #print(lod)
    ds1 = dataset.get(id1)
    ds2 = dataset.get(id2)

    #todo find a way cash this
    #create the table object
    table1 = Table(ds1.rows(), ds1.cols(), ds1.asnumpy())
    table2 = Table(ds2.rows(), ds2.cols(), ds2.asnumpy())
    t1 = timeit.default_timer()
    dfinder = DiffFinder(table1, table2, ds1.rowtype, ds2.coltype, lod, direction)
    t2 = timeit.default_timer()
    d = dfinder.generate_diff(ops)
    t3 = timeit.default_timer()
    print("times", t2 - t1 , t3 - t2)
    d.add_union(dfinder.union)
    t4 = timeit.default_timer()
    json_result = flask.jsonify(d.serialize())
    t5 = timeit.default_timer()
    print("time for jsonify", t5 - t4, "time for everything ", t5 - t1)
    return json_result
    #todo make sure that both dataset have same rowtype and coltype before calling this api function
    #return flask.jsonify(diff_finder.generate_diff(table1, table2, ds1.rowtype, ds1.coltype, direction))
    #else:
        #print("one of the files is missing!!")
    #return flask.jsonify(ds1.asjson())
    #todo return a value that could be handled to show an error in the client side
    #return "{}"

def create():
  """
  by convention contain a factory called create returning the extension implementation
  :return:
  """
  return app

if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0', port=9000)
