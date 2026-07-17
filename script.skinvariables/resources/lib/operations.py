import re
import xbmc


def check_condition(condition):
    if not condition:
        return True  # No condition set so we treat as True
    if '||' in condition:
        return check_or_conditions(condition.split('||'))
    if '==' in condition:
        a, b = condition.split('==')
        return True if a == b else False
    if '!=' in condition:
        a, b = condition.split('!=')
        return True if a != b else False
    if '>>' in condition:
        a, b = condition.split('>>')
        return True if a in b else False
    if '<<' in condition:
        a, b = condition.split('<<')
        return True if b in a else False
    if '!>' in condition:
        a, b = condition.split('!>')
        return True if a not in b else False
    if '!<' in condition:
        a, b = condition.split('!<')
        return True if b not in a else False
    if xbmc.getCondVisibility(condition):
        return True
    return False


def check_or_conditions(conditions):
    for condition in conditions:
        if condition and check_condition(condition):
            return True
    return False


def check_and_conditions(conditions):
    for condition in conditions:
        if condition and not check_condition(condition):
            return False
    return True


class FormatDict(dict):
    def __missing__(self, key):
        return ''


class RuleOperations():
    def __init__(self, meta, **params):
        self.meta = meta
        self.params = FormatDict(params)
        self.run_operations()

    def run_operations(self):
        for i in self.operations:
            for k, v in i.items():
                self.routes[k](v)

    @property
    def operations(self):
        return [{i: self.meta[i]} for i in self.routes if i in self.meta] + self.meta.get('operations', [])

    @property
    def routes(self):
        try:
            return self._routes
        except AttributeError:
            self._routes = {
                'capitalize': self.set_capitalize,
                'infolabels': self.set_infolabels,
                'regex': self.set_regex,
                'values': self.set_values,
                'sums': self.set_sums,
                'decode': self.set_decode,
                'encode': self.set_encode,
                'escape': self.set_escape,
                'lower': self.set_lower,
                'upper': self.set_upper,
            }
            return self._routes

    def set_infolabels(self, d):
        for k, v in d.items():
            k = k.format_map(self.params)
            v = v.format_map(self.params)
            self.params[k] = xbmc.getInfoLabel(v)

    def set_regex(self, d):
        for k, v in d.items():
            k = k.format_map(self.params)
            self.params[k] = re.sub(v['regex'].format_map(self.params), v['value'].format_map(self.params), v['input'].format_map(self.params))

    def set_values(self, d):
        for k, v in d.items():
            k = k.format_map(self.params)
            self.params[k] = self.get_actions_list(v)[0]

    def set_sums(self, d):
        for k, v in d.items():
            k = k.format_map(self.params)
            self.params[k] = sum([int(i.format_map(self.params)) for i in v])

    def set_decode(self, d):
        from urllib.parse import unquote_plus
        for k, v in d.items():
            k = k.format_map(self.params)
            v = v.format_map(self.params)
            self.params[k] = unquote_plus(v)

    def set_encode(self, d):
        from urllib.parse import quote_plus
        for k, v in d.items():
            k = k.format_map(self.params)
            v = v.format_map(self.params)
            self.params[k] = quote_plus(v)

    def set_escape(self, d):
        from xml.sax.saxutils import escape
        for k, v in d.items():
            k = k.format_map(self.params)
            v = v.format_map(self.params)
            self.params[k] = escape(v)

    def set_lower(self, d):
        for k, v in d.items():
            k = k.format_map(self.params)
            self.params[k] = v.format_map(self.params).lower()

    def set_upper(self, d):
        for k, v in d.items():
            k = k.format_map(self.params)
            self.params[k] = v.format_map(self.params).upper()

    def set_capitalize(self, d):
        for k, v in d.items():
            k = k.format_map(self.params)
            self.params[k] = v.format_map(self.params).capitalize()

    def check_rules(self, rules):
        for rule in rules:
            rule = rule.format_map(self.params)
            if not check_condition(rule):  # If one rule of many is false then rule is false overall so exit early
                return False
        return True  # If all rules are successful then rule is true

    def get_actions_list(self, rule_actions):
        actions_list = []

        if not isinstance(rule_actions, list):
            rule_actions = [rule_actions]

        for action in rule_actions:

            # Parts are prefixed with percent % so needs to be replaced
            if isinstance(action, str) and action.startswith('%'):
                action = action.format_map(self.params)
                action = self.meta['parts'][action[1:]]

            # Standard actions are strings - add formatted action to list and continue
            if isinstance(action, str):
                actions_list.append(action.format_map(self.params))
                continue

            # Sublists of actions are lists - recursively add sublists and continue
            if isinstance(action, list):
                actions_list += self.get_actions_list(action)
                continue

            # Rules are dictionaries - successful rules add their actions and stop iterating (like a skin variable)
            if self.check_rules(action['rules']):
                actions_list += self.get_actions_list(action['value'])
                break

        return actions_list
