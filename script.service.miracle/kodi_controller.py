from intent_handlers import dispatch_handler
from utils import debug, error


def execute_intent_req(miracle_msg):
    debug('Executing intent: %s' % miracle_msg['intent_request']['intent']['name'])
    try:
        dispatch_handler(miracle_msg['intent_request'])
    except Exception as e:
        error('Failed executing intent: %s' % e)

action_map = {
    'execute_intent': execute_intent_req
}
