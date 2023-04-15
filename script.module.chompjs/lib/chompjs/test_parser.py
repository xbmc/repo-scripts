# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import functools
import math
import unittest

from chompjs import parse_js_object


def parametrize_test(*arguments_list):
    def decorate(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            for arguments in arguments_list:
                func(self, *arguments)
        return wrapper
    return decorate


class TestParser(unittest.TestCase):
    @parametrize_test(
        ("{'hello': 'world'}", {'hello': 'world'}),
        ("{'hello': 'world', 'my': 'master'}", {'hello': 'world', 'my': 'master'}),
        (
            "{'hello': 'world', 'my': {'master': 'of Orion'}, 'test': 'xx'}",
            {'hello': 'world', 'my': {'master': 'of Orion'}, 'test': 'xx'},
        ),
        ("{}", {}),
    )
    def test_parse_object(self, in_data, expected_data):
        result = parse_js_object(in_data)
        self.assertEqual(result, expected_data)

    @parametrize_test(
        ("[]", []),
        ("[[[]]]", [[[]]]),
        ("[[[1]]]", [[[1]]]),
        ("[1]", [1]),
        ("[1, 2, 3, 4]", [1, 2, 3, 4]),
        ("['h', 'e', 'l', 'l', 'o']",  ['h', 'e', 'l', 'l', 'o']),
        ("[[[[[[[[[[[[[[[1]]]]]]]]]]]]]]]", [[[[[[[[[[[[[[[1]]]]]]]]]]]]]]]),
    )
    def test_parse_list(self, in_data, expected_data):
        result = parse_js_object(in_data)
        self.assertEqual(result, expected_data)

    @parametrize_test(
        ("{'hello': [], 'world': [0]}", {'hello': [], 'world': [0]}),
        ("{'hello': [1, 2, 3, 4]}", {'hello': [1, 2, 3, 4]}),
        ("[{'a':12}, {'b':33}]", [{'a': 12}, {'b': 33}]),
        (
            "[false, {'true': true, `pies`: \"kot\"}, false,]",
            [False, {"true": True, 'pies': 'kot'}, False],
        ),
        (
            "{a:1,b:1,c:1,d:1,e:1,f:1,g:1,h:1,i:1,j:1}",
            {k: 1 for k in 'abcdefghij'},
        ),
        (
            "{'a':[{'b':1},{'c':[{'d':{'f':{'g':[1,2]}}},{'e':1}]}]}",
            {'a': [{'b': 1}, {'c': [{'d': {'f': {'g': [1, 2]}}}, {'e': 1}]}]},
        ),
    )
    def test_parse_mixed(self, in_data, expected_data):
        result = parse_js_object(in_data)
        self.assertEqual(result, expected_data)

    @parametrize_test(
        ("{'hello': 12, 'world': 10002.21}", {'hello': 12, 'world': 10002.21}),
        ("[12, -323, 0.32, -32.22, .2, - 4]", [12, -323, 0.32, -32.22, 0.2, -4]),
        ('{"a": -12, "b": - 5}', {'a': -12, 'b': -5}),
        ("{'a': true, 'b': false, 'c': null}", {'a': True, 'b': False, 'c': None}),
        ("[\"\\uD834\\uDD1E\"]", [u'𝄞']),
        ("{'a': '123\\'456\\n'}", {'a': "123'456\n"}),
        ("['\u00E9']", ['é']),
        ('{"cache":{"\u002Ftest\u002F": 0}}', {'cache': {'/test/': 0}}),
        ('{"a": 12_12}', {'a': 1212}),
        ('{"a": 3.125e7}', {'a': 3.125e7}),
        ('''{"a": "b\\'"}''', {'a': "b'"}),
        ('{"a": .99, "b": -.1}', {"a": 0.99, "b": -.1}),
        ('["/* ... */", "// ..."]', ["/* ... */", "// ..."]),
        ('{"inclusions":["/*","/"]}', {'inclusions': ['/*', '/']}),
    )
    def test_parse_standard_values(self, in_data, expected_data):
        result = parse_js_object(in_data)
        self.assertEqual(result, expected_data)

    def test_parse_nan(self):
        in_data = '{"A": NaN}'
        result = parse_js_object(in_data)
        assert math.isnan(result["A"])

    @parametrize_test(
        ("{abc: 100, dev: 200}", {'abc': 100, 'dev': 200}),
        ("{abcdefghijklmnopqrstuvwxyz: 12}", {"abcdefghijklmnopqrstuvwxyz": 12}),
        (
            "{age: function(yearBorn,thisYear) {return thisYear - yearBorn;}}",
            {"age": "function(yearBorn,thisYear) {return thisYear - yearBorn;}"}
        ),
        (
            "{\"abc\": function() {return '])))))))))))))))';}}",
            {"abc": "function() {return '])))))))))))))))';}"},
        ),
        ('{"a": undefined}', {"a": "undefined"}),
        ('[undefined, undefined]', ["undefined", "undefined"]),
        ("{_a: 1, $b: 2}", {"_a": 1, "$b": 2}),
        ("[0x12, 0xAB, 051, 0o51, 0b111]", ["0x12", "0xab", "051", "0o51", "0b111"]),
        ("{regex: /a[^d]{1,12}/i}", {'regex': '/a[^d]{1,12}/i'}),
        ("{'a': function(){return '\"'}}", {'a': 'function(){return \'"\'}'}),
        ("{1: 1, 2: 2, 3: 3, 4: 4}", {'1': 1, '2': 2, '3': 3, '4': 4}),
        ("{'a': 121.}", {'a': 121.0})
    )
    def test_parse_strange_values(self, in_data, expected_data):
        result = parse_js_object(in_data)
        self.assertEqual(result, expected_data)

    @parametrize_test(
        ('{"a": {"b": [12, 13, 14]}}text text', {"a": {"b": [12, 13, 14]}}),
        ('var test = {"a": {"b": [12, 13, 14]}}', {"a": {"b": [12, 13, 14]}}),
        ('{"a":\r\n10}', {'a': 10}),
        ("{'foo': 0,\r\n}", {'foo': 0}),
        ("{truefalse: 0, falsefalse: 1, nullnull: 2}", {'truefalse': 0, 'falsefalse': 1, 'nullnull': 2}),
    )
    def test_strange_input(self, in_data, expected_data):
        result = parse_js_object(in_data)
        self.assertEqual(result, expected_data)

    @parametrize_test(
        (
            """
                var obj = {
                    // Comment
                    x: "X", // Comment
                };
            """,
            {"x": "X"},
        ),
        (
            """
                var /* Comment */ obj = /* Comment */ {
                    /* Comment */
                    x: /* Comment */ "X", /* Comment */
                };
            """,
            {"x": "X"},
        ),
        (
            """[/*...*/1,2,3,/*...*/4,5,6]""",
            [1, 2, 3, 4, 5, 6],
        ),
    )
    def test_comments(self, in_data, expected_data):
        result = parse_js_object(in_data)
        self.assertEqual(result, expected_data)

    @parametrize_test(
        ('["Test\\nDrive"]\n{"Test": "Drive"}', [['Test\nDrive'], {'Test': 'Drive'}]),
    )
    def test_jsonlines(self, in_data, expected_data):
        result = parse_js_object(in_data, jsonlines=True)
        self.assertEqual(result, expected_data)


class TestParserExceptions(unittest.TestCase):
    @parametrize_test(
        ('}{', ValueError),
        ('', ValueError),
        (None, ValueError),
    )
    def test_exceptions(self, in_data, expected_exception):
        with self.assertRaises(expected_exception):
            parse_js_object(in_data)

    @parametrize_test(
        ("{whose: 's's', category_name: '>'}", ValueError),
    )
    def test_malformed_input(self, in_data, expected_exception):
        with self.assertRaises(expected_exception):
            parse_js_object(in_data)

    @parametrize_test(
        (
            '{"test": """}',
            ValueError,
            'Error parsing input near character 13',
        ),
    )
    def test_error_messages(self, in_data, expected_exception, expected_exception_text):
        with self.assertRaisesRegex(expected_exception, expected_exception_text):
            parse_js_object(in_data)


class TestOptions(unittest.TestCase):
    @parametrize_test(
        ('{\\\"a\\\": 12}', {'a': 12}),
    )
    def test_unicode_escape(self, in_data, expected_data):
        result = parse_js_object(in_data, unicode_escape=True)
        self.assertEqual(result, expected_data)

    @parametrize_test(
        ('["\n"]', ["\n"]),
        ("{'a': '\"\"', 'b': '\\\\', 'c': '\t\n'}", {'a': '""', 'b': '\\', 'c': '\t\n'}),
        (
            """var myObj = {
                myMethod: function(params) {
                    // ...
                },
                myValue: 100
            }""",
            {'myMethod': 'function(params) {\n                    // ...\n                }', 'myValue': 100},
        ),
    )
    def test_json_non_strict(self, in_data, expected_data):
        result = parse_js_object(in_data, json_params={'strict': False})
        self.assertEqual(result, expected_data)


if __name__ == '__main__':
    unittest.main()
