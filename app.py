import flask
import webbrowser
import simulator, genetic
from models import model
from data import constants as const
from matplotlib.figure import Figure


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
    context = {'results':False}
    if flask.request.method == 'POST':
        context['results'] = True
        test_simulator = simulator.test_unit(units=simulator.MONTE_CARLO_RUNS)
        s_rate, _, context['img_data'] = test_simulator.main()
        context['s_rate'] = f"Success Rate: {s_rate*100:.2f}%"
    return flask.render_template('simulation.html', **context)

@app.route('/optimizer', methods=('GET', 'POST'))
def optimizer():
    if flask.request.method == 'POST':
        if flask.request.form['submit_button'] == 'Start Optimizing!':
            genetic.Algorithm().main()
        elif flask.request.form['submit_button'] == 'Stop Optimizing':
            with open(const.QUIT_LOC, 'w') as file:
                pass # close
    return flask.render_template('optimizer.html')

@app.route("/test", methods=('GET', 'POST'))
def test():
    return flask.render_template('test.html')

if __name__ == "__main__":
    url = "http://127.0.0.1:5000/"
    webbrowser.open(url)
    app.run(debug=True)