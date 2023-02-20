"""Entry point for application"""

import os
import webbrowser
import flask
from flask_socketio import SocketIO, emit
from models import model


app = flask.Flask(__name__)
app.secret_key = 'dev' # default value during development
socketio = SocketIO(app)
mdl = model.Model(socketio)

@app.route('/')
def index():
    """Home Page"""
    if ("user_in_session" not in flask.session) and ('deployed' in os.environ):
        flask.session["user_in_session"] = True
        model.copy_default_values()
    return flask.render_template('index.html')

# @socketio.on('connect', namespace='/test')
# def test_connect():
#     print('Client connected')
#     #randomNumberGenerator()
    # thread = socketio.start_background_task(randomNumberGenerator)


@app.route("/parameters", methods=('GET', 'POST'))
def parameters():
    """Paramter Page"""
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
    """Simulation Page"""
    import simulator # pylint: disable=import-outside-toplevel # lazy import
    context = {'results':False} # avoid loading the result image before a simulation has been run
    if flask.request.method == 'POST':
        context['results'] = True
        simulator.DEBUG_LVL = 1
        sim_results = simulator.test_unit(units=simulator.MONTE_CARLO_RUNS).main()
        context.update(sim_results) # add s_rate, returns, and img_data
            # change s_rate to string with correct formatting
        context['s_rate'] = f"Success Rate: {context['s_rate']*100:.2f}%"
    return flask.render_template('simulation.html', **context)

@app.route('/optimizer', methods=('GET', 'POST'))
def optimizer():
    """Optimizer Page"""
    #import genetic
    from data import constants as const # pylint: disable=import-outside-toplevel # lazy import
    if flask.request.method == 'POST':
        # if flask.request.form['submit_button'] == 'Start Optimizing!':
        #     genetic.Algorithm().main()
        if flask.request.form['submit_button'] == 'Stop Optimizing':
            # Create a file called cancel.quit that's then captured
            # by the running simulator.main() and causes genetic.main() to stop
            with open(const.QUIT_LOC, 'w', encoding="utf-8"):
                pass # close file
    return flask.render_template('optimizer.html')

@socketio.on('start_optimizer', namespace='/optimize')
def start_optimizer():
    """Optimizer algorithm starter"""
    emit('new_log', {'log': 'Loading Optimizer'}, namespace='/optimize')
    import genetic # pylint: disable=import-outside-toplevel # lazy import
    emit('new_log', {'log': 'Starting Optimizer'}, namespace='/optimize')
    socketio.start_background_task(genetic.Algorithm(mdl).main)

@app.route("/test", methods=('GET', 'POST'))
def test():
    """Test Page"""
    return flask.render_template('test.html')

if __name__ == "__main__":
    URL = "http://127.0.0.1:5000/"
    webbrowser.open(URL)
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)
