import flask
import webbrowser
import simulator
from models import model

mdl = model.Model()
app = flask.Flask(__name__)

@app.route('/')
def index():
    return flask.render_template('index.html')

@app.route("/parameters", methods=('GET', 'POST'))
def parameters():
    context = {
        "params": mdl.params
    }
    if flask.request.method == 'POST':
        for k,v in flask.request.form.items():
            if mdl.params[k]['type'] == "bool":
                if v == 'True': mdl.params[k]['val'] = True
                else: mdl.params[k]['val'] = False
            else:
                mdl.params[k]['val'] = v
            mdl.save_params({param:obj['val'] for (param,obj) in mdl.params.items()})
        return flask.redirect(flask.url_for('parameters'))
    return flask.render_template("parameters.html", **context)

@app.route('/simulation', methods=('GET', 'POST'))
def simulation():
    if flask.request.method == 'POST':
        test_simulator = simulator.test_unit(units=simulator.MONTE_CARLO_RUNS)
        s_rate, arr= test_simulator.main()
    return flask.render_template('simulation.html')

@app.route("/test", methods=('GET', 'POST'))
def test():
    return flask.render_template('test.html')

if __name__ == "__main__":
    url = "http://127.0.0.1:5000/"
    webbrowser.open(url)
    app.run(debug=True)