from behave import *
from sismic.io import import_from_yaml
from sismic.interpreter import Interpreter
from sismic.model import Event


# #################### GENERAL PURPOSE
@given('I do nothing')
@when('I do nothing')
def do_nothing(context):
    pass


@given('I reproduce "{scenario}"')
@when('I reproduce "{scenario}"')
def reproduce_scenario(context, scenario):
    current_feature = context.feature
    for included_scenario in current_feature.scenarios:
        if included_scenario.name == scenario:
            steps = ['{} {}'.format(s.step_type, s.name) for s in included_scenario.steps]
            context.execute_steps('\n'.join(steps))
            return
    assert False, 'Unknown scenario {}.'.format(scenario)


@given('I repeat step "{step}" {repeat:d} times')
@when('I repeat step "{step}" {repeat:d} times')
def repeat_step(context, step, repeat):
    keyword = step.split(' ', 1)[0].lower()
    assert keyword in ['given', 'when', 'and', 'but', 'then'], 'Step {} should start with a supported keyword'.format(step)

    for x in range(repeat):
        context.execute_steps(step)


# #################### CONFIGURATION
def _execute_statechart(context, force_execution=False):
    if context._automatic_execution or force_execution:
        context._events = []
        steps = context._interpreter.execute()
        context._steps.append(steps)


@given('I disable automatic execution')
def disable_automatic_execution(context):
    context._automatic_execution = False


@given('I enable automatic execution')
def enable_automatic_execution(context):
    context._automatic_execution = True


@given('I import a statechart from {path}')
@when('I import a statechart from {path}')
def load_statechart(context, path):
    with open(path) as f:
        context._statechart = import_from_yaml(f)
    context._interpreter = Interpreter(context._statechart)
    context._steps = []
    context._events = []
    context._automatic_execution = True
    context._interpreter.bind(lambda e: context._events.append(e))


@given('I execute the statechart')
@when('I execute the statechart')
def execute_statechart(context):
    steps = context._interpreter.execute()
    context._steps.append(steps)


@given('I execute once the statechart')
@when('I execute once the statechart')
def execute_once_statechart(context):
    step = context._interpreter.execute_once()
    context._steps.append([step])


# #################### STATECHART
@given('I send event {event_name}')
@given('I send event {event_name} with {parameter}={value}')
@when('I send event {event_name}')
@when('I send event {event_name} with {parameter}={value}')
def send_event(context, event_name, parameter=None, value=None):
    parameters = {}
    if context.table:
        for row in context.table:
            parameters[row['parameter']] = eval(row['value'], {}, {})

    if parameter and value:
        parameters[parameter] = eval(value)

    event = Event(event_name, **parameters)
    context._interpreter.queue(event)
    _execute_statechart(context)


@given('I wait {seconds:g} seconds')
@given('I wait {seconds:g} second')
@when('I wait {seconds:g} seconds')
@when('I wait {seconds:g} second')
def wait_seconds(context, seconds):
    context._interpreter.time += seconds
    _execute_statechart(context)


@given('I wait {seconds:g} seconds {repeat:d} times')
@given('I wait {seconds:g} second {repeat:d} times')
@when('I wait {seconds:g} seconds {repeat:d} times')
@when('I wait {seconds:g} second {repeat:d} times')
def wait_seconds(context, seconds, repeat):
    for i in range(repeat):
        context._interpreter.time += seconds
        _execute_statechart(context)


@given('I set variable {variable} to {value}')
def set_variable(context, variable, value):
    context._interpreter.context[variable] = eval(value, {}, {})


@then('state {state} should be active')
def state_is_active(context, state):
    assert state in context._statechart.states, 'Unknown state {}'.format(state)
    assert state in context._interpreter.configuration, 'State {} is not active'.format(state)


@then('state {state} should not be active')
def state_is_not_active(context, state):
    assert state in context._statechart.states, 'Unknown state {}'.format(state)
    assert state not in context._interpreter.configuration, 'State {} is active'.format(state)


@then('event {event_name} should be fired')
@then('event {event_name} should be fired with {parameter}={value}')
def event_is_received(context, event_name, parameter=None, value=None):
    parameters = {}
    if context.table:
        for row in context.table:
            parameters[row['parameter']] = eval(row['value'], {}, {})

    if parameter and value:
        parameters[parameter] = eval(value)

    for event in context._events:
        if event.name == event_name:
            matching_parameters = True
            for key, value in parameters.items():
                if getattr(event, key, None) != value:
                    matching_parameters = False
                    break
            if matching_parameters:
                return

    assert False, 'No matching event fired for {} with {} in {}'.format(event_name, parameters, context._events)


@then('no event should be fired')
def no_event_received(context):
    assert len(context._events) == 0, 'Sent events: {}'.format(context._events)


@then('variable {variable} should be defined')
def variable_is_defined(context, variable):
    assert variable in context._interpreter.context, '{} is not defined'.format(variable)


@then('the value of {variable} should be {value}')
def variable_equals_value(context, variable, value):
    variable_is_defined(context, variable)
    value = eval(value, {}, {})
    context_value = context._interpreter.context[variable]
    assert context_value == value, 'Variable {} equals {} != {}'.format(variable, context_value, value)


@then('expression {expression} should hold')
def expression_holds(context, expression):
    assert context._interpreter._evaluator._evaluate_code(expression), '{} does not hold'.format(expression)


@then('the statechart is in a final configuration')
def final_configuration(context):
    assert context._interpreter.final, 'The statechart is not in a final configuration: {}'.format(context._interpreter.configuration)