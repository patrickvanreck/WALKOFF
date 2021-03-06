import unittest
from core.filter import Filter
import core.config.config
from tests.config import function_api_path
from core.helpers import import_all_filters, import_all_flags, UnknownFilter, InvalidInput, InvalidElementConstructed
import uuid


class TestFilter(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        core.config.config.filters = import_all_filters('tests.util.flagsfilters')
        core.config.config.flags = import_all_flags('tests.util.flagsfilters')
        core.config.config.load_flagfilter_apis(path=function_api_path)

    def __compare_init(self, elem, action, args=None, uid=None):
        args = args if args is not None else {}
        self.assertEqual(elem.action, action)
        self.assertDictEqual(elem.args, args)
        self.assertEqual(elem.name, elem.action)
        if uid is None:
            self.assertIsNotNone(elem.uid)
        else:
            self.assertEqual(elem.uid, uid)

    def test_init_action_only(self):
        filter_elem = Filter(action='Top Filter')
        self.__compare_init(filter_elem, 'Top Filter')

    def test_init_invalid_action(self):
        with self.assertRaises(UnknownFilter):
            Filter(action='Invalid')

    def test_init_with_uid(self):
        uid = uuid.uuid4().hex
        filter_elem = Filter(action='Top Filter', uid=uid)
        self.__compare_init(filter_elem, 'Top Filter', uid=uid)

    def test_init_with_args(self):
        filter_elem = Filter(action='mod1_filter2', args={'arg1': '5.4'})
        self.__compare_init(filter_elem, 'mod1_filter2', args={'arg1': 5.4})

    def test_init_with_args_with_routing(self):
        filter_elem = Filter(action='mod1_filter2', args={'arg1': '@step1'})
        self.__compare_init(filter_elem, 'mod1_filter2', args={'arg1': '@step1'})

    def test_init_with_invalid_arg_name(self):
        with self.assertRaises(InvalidInput):
            Filter(action='mod1_filter2', args={'invalid': '5.4'})

    def test_init_with_invalid_arg_type(self):
        with self.assertRaises(InvalidInput):
            Filter(action='mod1_filter2', args={'arg1': 'invalid'})

    def test_init_with_no_action_or_xml(self):
        with self.assertRaises(InvalidElementConstructed):
            Filter()

    def test_as_json_no_args(self):
        uid = uuid.uuid4().hex
        filter_elem = Filter(action='Top Filter', uid=uid)
        expected = {'action': 'Top Filter', 'args': [], 'uid': uid}
        self.assertDictEqual(filter_elem.as_json(), expected)

    def test_as_json_with_args(self):
        uid = uuid.uuid4().hex
        filter_elem = Filter(action='mod1_filter2', args={'arg1': '-5.4'}, uid=uid)
        expected = {'action': 'mod1_filter2', 'args':  [{'name': 'arg1', 'value': -5.4}], 'uid': uid}
        self.assertDictEqual(filter_elem.as_json(), expected)

    def test_as_json_with_args_with_routing(self):
        uid = uuid.uuid4().hex
        filter_elem = Filter(action='mod1_filter2', args={'arg1': '@step1'}, uid=uid)
        expected = {'action': 'mod1_filter2', 'args': [{'name': 'arg1', 'value': '@step1'}], 'uid': uid}
        self.assertDictEqual(filter_elem.as_json(), expected)

    def test_from_json_no_args(self):
        json_in = {'action': 'Top Filter', 'args': []}
        filter_elem = Filter.from_json(json_in)
        self.__compare_init(filter_elem, 'Top Filter')

    def test_from_json_with_uid(self):
        uid = uuid.uuid4().hex
        json_in = {'action': 'Top Filter', 'args': [], 'uid': uid}
        filter_elem = Filter.from_json(json_in)
        self.__compare_init(filter_elem, 'Top Filter', uid=uid)

    def test_from_json_with_args(self):
        json_in = {'action': 'mod1_filter2', 'args': [{'name': 'arg1', 'value': 5.4}]}
        filter_elem = Filter.from_json(json_in)
        self.__compare_init(filter_elem, 'mod1_filter2', args={'arg1': 5.4})

    def test_from_json_with_args_with_routing(self):
        json_in = {'action': 'mod1_filter2', 'args': [{'name': 'arg1', 'value': '@step1'}]}
        filter_elem = Filter.from_json(json_in)
        self.__compare_init(filter_elem, 'mod1_filter2', args={'arg1': '@step1'})

    def test_call_with_no_args_no_conversion(self):
        self.assertAlmostEqual(Filter(action='Top Filter')(5.4, {}), 5.4)

    def test_call_with_no_args_with_conversion(self):
        self.assertAlmostEqual(Filter(action='Top Filter')('-10.437', {}), -10.437)

    def test_call_with_invalid_input(self):
        self.assertEqual(Filter(action='Top Filter')('invalid', {}), 'invalid')

    def test_call_with_filter_which_raises_exception(self):
        self.assertEqual(Filter(action='sub1_filter3')('anything', {}), 'anything')

    def test_call_with_args_no_conversion(self):
        self.assertAlmostEqual(Filter(action='mod1_filter2', args={'arg1': '10.3'})('5.4', {}), 15.7)

    def test_call_with_args_with_conversion(self):
        self.assertAlmostEqual(Filter(action='mod1_filter2', args={'arg1': '10.3'})(5.4, {}), 15.7)

    def test_call_with_args_with_routing(self):
        self.assertAlmostEqual(Filter(action='mod1_filter2', args={'arg1': '@step1'})(5.4, {'step1': 10.3}), 15.7)

    def test_call_with_complex_args(self):
        original_filter = Filter(action='sub1_filter1', args={'arg1': {'a': '5.4', 'b': 'string_in'}})
        self.assertEqual(original_filter(3, {}), '3.0 5.4 string_in')

    def test_call_with_nested_complex_args(self):
        args = {'arg': {'a': '4', 'b': 6, 'c': [1, 2, 3]}}
        original_filter = Filter(action='complex', args=args)
        self.assertAlmostEqual(original_filter(3, {}), 19.0)

    def test_call_with_args_invalid_input(self):
        self.assertEqual(Filter(action='mod1_filter2', args={'arg1': '10.3'})('invalid', {}), 'invalid')
