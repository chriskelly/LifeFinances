import flask
import webbrowser

app = flask.Flask(__name__)

@app.route('/')
def index():
    return flask.render_template('index.html')

@app.route("/parameters", methods=('GET', 'POST'))
def parameters():
    from models import model
    mdl = model.Model()
    if flask.request.method == 'POST':
        mdl.save_from_flask(flask.request.form)
        if 'remove_row' in flask.request.form:
            mdl.remove_from_special_tables(flask.request.form['remove_row'])
        elif 'add_row' in flask.request.form:
            mdl.add_to_special_tables(flask.request.form['add_row'])
    context = {
        "param_vals": mdl.param_vals,
        "param_details":mdl.param_details
    }
    return flask.render_template("parameters.html", **context)

@app.route('/simulation', methods=('GET', 'POST'))
def simulation():
    import simulator
    context = {'results':False} # used to avoid loading the result image before a simulation has been run
    if flask.request.method == 'POST':
        context['results'] = True
        simulator.DEBUG_LVL = 1
        sim_results = simulator.test_unit(units=simulator.MONTE_CARLO_RUNS).main()
        context.update(sim_results) # add s_rate, returns, and img_data
        context['s_rate'] = f"Success Rate: {context['s_rate']*100:.2f}%" # change s_rate to string with correct formatting
    return flask.render_template('simulation.html', **context)

@app.route('/optimizer', methods=('GET', 'POST'))
def optimizer():
    import genetic
    from data import constants as const
    if flask.request.method == 'POST':
        if flask.request.form['submit_button'] == 'Start Optimizing!':
            genetic.Algorithm().main()
        elif flask.request.form['submit_button'] == 'Stop Optimizing':
            # Create a file called cancel.quit that's then captured by the running simulator.main() and causes genetic.main() to stop
            with open(const.QUIT_LOC, 'w') as file:
                pass # close file
    return flask.render_template('optimizer.html')

@app.route("/test", methods=('GET', 'POST'))
def test():
    return flask.render_template('test.html')

if __name__ == "__main__":
    url = "http://127.0.0.1:5000/"
    webbrowser.open(url)
    app.run(debug=True)