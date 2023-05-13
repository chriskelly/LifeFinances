"""Flask Routes"""

import os
import webbrowser
import flask
from flask_socketio import emit
from models import model, user
from app import socketio, app
import data.constants as const

mdl = model.Model(socketio)

@app.route('/')
def index():
    """Home Page"""
    if ("user_in_session" not in flask.session) and ('deployed' in os.environ):
        flask.session["user_in_session"] = True
        if os.path.exists(const.DB_LOC):
            os.remove(const.DB_LOC)
        model.initialize_db()
    return flask.render_template('index.html')

@app.route("/parameters", methods=('GET', 'POST'))
def parameters():
    """Parameter Page"""
    form = user.UserForm(obj=mdl.user)
    if flask.request.method == 'POST' and form.validate():
        if 'add_field' in flask.request.form:
            user.append_field(form, field=flask.request.form['add_field'])
            form.populate_obj(mdl.user)
        elif 'remove_field' in flask.request.form:
            # Confirm which field to remove, find the index,
            # and remove the corresponding item from the user
            field_id = flask.request.form['remove_field']
            table, _ = field_id.split('-')
            fields = form.__dict__[table]
            for i, field in enumerate(fields):
                if field.id == field_id:
                    form.populate_obj(mdl.user) # save any changes made prior to call
                    # if needed, database record would be = fields.object_data[i]
                    transient_record = mdl.user.__dict__[table][i]
                    mdl.user.__dict__[table].remove(transient_record) # delete from user object
                    break
        elif 'submit' in flask.request.form:
            form.populate_obj(mdl.user)
        mdl.save_user()
        form.process(obj=mdl.user) # reload form with updated user
        flask.flash('User updated successfully')
    return flask.render_template("parameters.html", form=form)

@app.route('/simulation', methods=('GET', 'POST'))
def simulation():
    """Simulation Page"""
    import simulator # pylint: disable=import-outside-toplevel # lazy import
    context = {'results':False} # avoid loading the result image before a simulation has been run
    if flask.request.method == 'POST':
        context['results'] = True
        simulator.DEBUG_LVL = 1
        sim_results = simulator.test_unit(units=simulator.MONTE_CARLO_RUNS).run()
        context.update(sim_results) # add s_rate, returns, and img_data
            # change s_rate to string with correct formatting
        context['s_rate'] = f"Success Rate: {context['s_rate']*100:.2f}%"
    return flask.render_template('simulation.html', **context)

@app.route('/optimization', methods=('GET', 'POST'))
def optimization():
    """Optimization Page"""
    if flask.request.method == 'POST':
        if flask.request.form['submit_button'] == 'Stop Optimizing':
            # Create a file called cancel.quit that's then captured
            # by the running simulator.main() and causes genetic.main() to stop
            with open(const.QUIT_LOC, 'w', encoding="utf-8"):
                pass # close file
    return flask.render_template('optimization.html')

@socketio.on('start_optimizer', namespace='/optimize')
def start_optimizer():
    """Optimizer algorithm starter"""
    emit('new_log', {'log': 'Loading Optimizer'}, namespace='/optimize')
    import optimizer # pylint: disable=import-outside-toplevel # lazy import
    emit('new_log', {'log': 'Starting Optimizer'}, namespace='/optimize')
    socketio.start_background_task(optimizer.Algorithm(mdl).main)

if __name__ == "__main__":
    URL = "http://127.0.0.1:5000/"
    webbrowser.open(URL)
    socketio.run(app, debug=True)
