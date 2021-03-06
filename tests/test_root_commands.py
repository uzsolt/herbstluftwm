import pytest
import re

# example values for the respective types
ATTRIBUTE_TYPE_EXAMPLE_VALUES = \
    {
        'int': [23, 42, -8],
        'bool': ['true', 'false'],
        'string': ['foo', 'baz', 'bar'],
        'color': ['#ff00ff', '#9fbc00'],  # FIXME: include named colors
        'uint': [23, 42]
    }
ATTRIBUTE_TYPES = list(ATTRIBUTE_TYPE_EXAMPLE_VALUES.keys())


def test_attr_cmd(hlwm):
    assert hlwm.get_attr('monitors.focus.name') == ''
    hlwm.call('attr')
    hlwm.call('attr tags')
    hlwm.call('attr tags.')
    hlwm.call('attr tags.count')
    assert hlwm.call('attr tags.count').stdout == hlwm.get_attr('tags.count')
    hlwm.call_xfail('attr tags.co')


@pytest.mark.parametrize('object_path', ['', 'clients', 'theme', 'monitors'])
def test_object_completion(hlwm, object_path):
    assert hlwm.list_children(object_path) \
        == hlwm.list_children_via_attr(object_path)


def test_object_tree(hlwm):
    t1 = hlwm.call('object_tree').stdout.splitlines()
    t2 = hlwm.call('object_tree theme.').stdout.splitlines()
    t3 = hlwm.call('object_tree theme.tiling.').stdout.splitlines()
    assert len(t1) > len(t2)
    assert len(t2) > len(t3)


def test_substitute(hlwm):
    expected_output = hlwm.get_attr('tags.count') + '\n'

    call = hlwm.call('substitute X tags.count echo X')

    assert call.stdout == expected_output


@pytest.mark.parametrize('prefix', ['set_attr settings.',
                                    'attr settings.',
                                    'cycle_value ',
                                    'set '])
def test_set_attr_completion(hlwm, prefix):
    assert hlwm.complete(prefix + "swap_monitors_to_get_tag") \
        == 'false off on toggle true'.split(' ')


def test_set_attr_only_writable(hlwm):
    # attr completes read-only attributes
    assert hlwm.complete('attr monitors.c', position=1, partial=True) \
        == ['monitors.count ']
    # but set_attr does not
    assert hlwm.complete('set_attr monitors.c', position=1, partial=True) \
        == []


def test_attr_only_second_argument_if_writable(hlwm):
    # attr does not complete values for read-only attributes
    assert hlwm.call_xfail_no_output('complete 2 attr monitors.count') \
        .returncode == 7


def test_set_attr_can_not_set_writable(hlwm):
    assert hlwm.call_xfail('set_attr tags.count 5') \
        .returncode == 3


def test_substitute_missing_attribute__command_treated_as_attribute(hlwm):
    call = hlwm.call_xfail('substitute X echo X')

    assert call.stderr == 'The root object has no attribute "echo"\n'


def test_substitute_command_missing(hlwm):
    call = hlwm.call_xfail('substitute X tags.count')

    assert call.stderr == 'substitute: not enough arguments\n'


def test_sprintf(hlwm):
    expected_count = hlwm.get_attr('tags.count')
    expected_wmname = hlwm.get_attr('settings.wmname')
    expected_output = expected_count + '/' + expected_wmname + '\n'

    call = hlwm.call('sprintf X %s/%s tags.count settings.wmname echo X')

    assert call.stdout == expected_output


def test_sprintf_too_few_attributes__command_treated_as_attribute(hlwm):
    call = hlwm.call_xfail('sprintf X %s/%s tags.count echo X')

    assert call.stderr == 'The root object has no attribute "echo"\n'


def test_sprintf_too_few_attributes_in_total(hlwm):
    call = hlwm.call_xfail('sprintf X %s/%s tags.count')

    assert call.stderr == 'sprintf: not enough arguments\n'


def test_sprintf_command_missing(hlwm):
    call = hlwm.call_xfail('sprintf X %s tags.count')

    assert call.stderr == 'sprintf: not enough arguments\n'


def test_sprintf_double_percentage_escapes(hlwm):
    call = hlwm.call('sprintf X %% echo X')

    assert call.stdout == '%\n'


def test_sprintf_completion_1_placeholder(hlwm):
    assert hlwm.complete('sprintf T %s', partial=True) \
        == sorted(['T '] + hlwm.complete('get_attr', partial=True))


def test_sprintf_completion_0_placeholders(hlwm):
    assert hlwm.complete('sprintf T %%') \
        == sorted(['T'] + hlwm.call('list_commands').stdout.splitlines())


def test_disjoin_rects(hlwm):
    # test the example from the manpage
    expected = '\n'.join((
        '300x150+300+250',
        '600x250+0+0',
        '300x150+0+250',
        '300x150+600+250',
        '600x250+300+400',
        ''))  # trailing newline
    response = hlwm.call('disjoin_rects 600x400+0+0 600x400+300+250').stdout
    assert response == expected


def test_attribute_completion(hlwm):
    def complete(partialPath):
        return hlwm.complete('get_attr ' + partialPath,
                             partial=True, position=1)

    assert complete('monitors.') == ['monitors.0.',
                                     'monitors.by-name.',
                                     'monitors.count ',
                                     'monitors.focus.']
    assert complete('monitors.fo') == ['monitors.focus.']
    assert complete('monitors.count') == ['monitors.count ']
    assert complete('monitors.focus') == ['monitors.focus.']
    assert complete('monitors.fooob') == []
    assert complete('monitors.fooo.bar') == []
    assert len(complete('monitors.focus.')) >= 8
    assert complete('t') == ['tags.', 'theme.', 'tmp.']
    assert complete('') == [l + '.' for l in hlwm.list_children_via_attr('')]


@pytest.mark.parametrize('attrtype', ATTRIBUTE_TYPES)
@pytest.mark.parametrize('name', ['my_test', 'my_foo'])
@pytest.mark.parametrize('object_path', ['', 'clients', 'theme.tiling.active'])
def test_new_attr_without_removal(hlwm, attrtype, name, object_path):
    path = (object_path + '.' + name).lstrip('.')

    hlwm.call(['new_attr', attrtype, path])

    hlwm.get_attr(path)


@pytest.mark.parametrize('attrtype', ATTRIBUTE_TYPES)
def test_new_attr_existing_builtin_attribute(hlwm, attrtype):
    hlwm.get_attr('monitors.count')
    hlwm.call_xfail(['new_attr', attrtype, 'monitors.count']) \
        .expect_stderr('attribute name must start with "my_"')


@pytest.mark.parametrize('attrtype', ATTRIBUTE_TYPES)
def test_new_attr_existing_user_attribute(hlwm, attrtype):
    path = 'theme.my_user_attr'
    hlwm.call(['new_attr', attrtype, path])
    hlwm.get_attr(path)

    hlwm.call_xfail(['new_attr', attrtype, path]) \
        .expect_stderr('already has an attribute')


@pytest.mark.parametrize('attrtype', ATTRIBUTE_TYPES)
@pytest.mark.parametrize('path', ['foo', 'monitors.bar'])
def test_new_attr_missing_prefix(hlwm, attrtype, path):
    hlwm.call_xfail(['new_attr', attrtype, path]) \
        .expect_stderr('must start with "my_"')


@pytest.mark.parametrize('attrtypevalues', ATTRIBUTE_TYPE_EXAMPLE_VALUES.items())
@pytest.mark.parametrize('path', ['my_foo', 'monitors.my_bar'])
def test_new_attr_is_writable(hlwm, attrtypevalues, path):
    (attrtype, values) = attrtypevalues
    hlwm.call(['new_attr', attrtype, path])
    for v in values:
        hlwm.call(['set_attr', path, v])
        assert hlwm.get_attr(path) == str(v)


@pytest.mark.parametrize('attrtype', ATTRIBUTE_TYPES)
def test_new_attr_has_right_type(hlwm, attrtype):
    path = 'my_user_attr'
    hlwm.call(['new_attr', attrtype, path])

    m = re.search('(.) . . ' + path, hlwm.call(['attr', '']).stdout)

    assert m.group(1)[0] == attrtype[0]


def test_new_attr_complete(hlwm):
    assert 'bool' in hlwm.complete('new_attr')
    assert 'my_' in hlwm.complete('new_attr int', partial=True)
    assert 'tags.my_' in hlwm.complete('new_attr int tags.', partial=True, position=2)
    assert 'tags.my_' in hlwm.complete('new_attr int tags.m', partial=True, position=2)
    assert 'settings.my_' in hlwm.complete('new_attr int settings.m', partial=True, position=2)


def test_remove_attr_invalid_attribute(hlwm):
    hlwm.call_xfail('remove_attr tags.invalid') \
        .expect_stderr('Object "tags" has no attribute "invalid".')


def test_remove_attr_invalid_child(hlwm):
    hlwm.call_xfail('remove_attr clients.foo.bar') \
        .expect_stderr('Object "clients." has no child named "foo"')


def test_remove_attr_non_user_path(hlwm):
    hlwm.call_xfail('remove_attr monitors.count') \
        .expect_stderr('Cannot remove built-in attribute "monitors.count"')


def test_remove_attr_user_attribute(hlwm):
    path = 'my_user_attr'
    hlwm.call(['new_attr', 'string', path])

    hlwm.call(['remove_attr', path])

    hlwm.call_xfail(['get_attr', path]).expect_stderr('has no attribute')  # attribute does not exist
    hlwm.call(['new_attr', 'string', path])  # and is free again


def test_getenv_completion(hlwm):
    prefix = 'some_uniq_prefix_'
    name = prefix + 'envname'
    hlwm.call(['setenv', name, 'myvalue'])

    assert [name] == hlwm.complete('getenv ' + prefix, position=1)


def test_export_completion(hlwm):
    prefix = 'some_uniq_prefix_'
    name = prefix + 'envname'
    hlwm.call(['setenv', name, 'myvalue'])

    assert [name + '='] == hlwm.complete('export ' + prefix, position=1, partial=True)


def test_compare_invalid_operator(hlwm):
    hlwm.call_xfail('compare monitors.count -= 1') \
        .expect_stderr('unknown operator')


def test_try_command(hlwm):
    proc = hlwm.unchecked_call('try chain , echo foo , false')

    assert proc.returncode == 0
    assert proc.stdout == 'foo\n'


def test_silent_command(hlwm):
    proc = hlwm.unchecked_call('silent chain , echo foo , false')

    assert proc.returncode == 1
    assert proc.stdout == ''


def test_chain_command(hlwm):
    assert hlwm.call('chain , echo foo').stdout == 'foo\n'
    assert hlwm.call('chain , false , echo f').stdout == 'f\n'
    assert hlwm.call('chain : echo g : echo f').stdout == 'g\nf\n'


def test_chain_command_empty(hlwm):
    assert hlwm.call('chain / / echo g / echo f').stdout == 'g\nf\n'
    assert hlwm.call('chain / echo g / echo f / ').stdout == 'g\nf\n'
    assert hlwm.call('chain / / echo g / / echo f / ').stdout == 'g\nf\n'
    assert hlwm.call('chain /').stdout == ''
    assert hlwm.call('chain / /').stdout == ''
    assert hlwm.call('chain / / /').stdout == ''


def test_chain_return_code(hlwm):
    p1 = hlwm.unchecked_call('get_attr')
    p2 = hlwm.unchecked_call('chain X echo line X get_attr')

    assert p1.returncode > 1
    assert p1.returncode == p2.returncode
    assert p2.stderr[0:5] == 'line\n'


def test_chain_nested(hlwm):
    assert hlwm.call('chain X chain Y echo a Y echo b X echo c').stdout \
        == 'a\nb\nc\n'
    # the inner 'chain Y' must not see the other Y
    assert hlwm.call('chain X chain Y echo a X echo b Y echo c').stdout \
        == 'a\nb Y echo c\n'


def test_chain_and_1(hlwm):
    proc = hlwm.unchecked_call('and , echo foo , false , echo bar')
    assert proc.returncode == 1
    assert proc.stderr == 'foo\n'


def test_chain_and_2(hlwm):
    proc = hlwm.unchecked_call('and , echo foo , true , echo bar , false , echo baz')
    assert proc.returncode == 1
    assert proc.stderr == 'foo\nbar\n'


def test_chain_or(hlwm):
    proc = hlwm.unchecked_call(
        'or , chain : echo a : false , \
            , chain : echo b : false , \
            , chain : echo c : true  , \
            , chain : echo d : false , \
        ')
    assert proc.returncode == 0
    assert proc.stdout == 'a\nb\nc\n'
    assert proc.stderr == ''


def test_chain_complete_cmd(hlwm):
    assert hlwm.complete('chain X true X false X') == \
        sorted(hlwm.call('list_commands').stdout.splitlines())


def test_chain_complete_sep_only(hlwm):
    assert hlwm.complete('chain X true') == ['X']


def test_chain_complete_sep_and_args(hlwm):
    res = hlwm.complete('chain X focus')
    assert 'X' in res
    assert 'left' in res


def test_chain_complete_cmd_arg(hlwm):
    assert hlwm.complete('chain X chain Y true Y false X false X !') == \
        sorted(['X'] + hlwm.call('list_commands').stdout.splitlines())


@pytest.mark.parametrize('args', [[], ['abc'], ['foo', 'bar']])
def test_echo_command(hlwm, args):
    assert hlwm.call(['echo'] + args).stdout == ' '.join(args) + '\n'


def test_echo_completion(hlwm):
    # check that the exit code is right
    assert hlwm.complete('echo foo') == []


@pytest.mark.parametrize('value', ['', 'bar'])
def test_setenv_command(hlwm, value):
    hlwm.call(['setenv', 'FOO', value])

    assert hlwm.call('getenv FOO').stdout == value + '\n'


@pytest.mark.parametrize('value', ['', 'bar'])
def test_export_command(hlwm, value):
    hlwm.call(['export', 'FOO=' + value])

    assert hlwm.call('getenv FOO').stdout == value + '\n'


def test_setenv_and_spawn(hlwm, hlwm_process):
    hlwm.call(['setenv', 'FOO', 'bar'])

    hlwm_process.read_and_echo_output()
    hlwm.unchecked_call(['spawn', 'sh', '-c', 'echo FOO is $FOO .'],
                        read_hlwm_output=False)
    hlwm_process.read_and_echo_output(until_stdout='FOO is bar .')


def test_setenv_completion_existing_var(hlwm):
    hlwm.call('setenv FOO bar')

    assert 'FOO' in hlwm.complete('setenv')


def test_setenv_completion_unset_var(hlwm):
    hlwm.call('unsetenv FOO')

    assert 'FOO' not in hlwm.complete('setenv')


def test_unsetenv_command(hlwm):
    hlwm.call('setenv FOO bar')
    hlwm.call('unsetenv FOO')

    proc = hlwm.unchecked_call('getenv foo')

    assert proc.returncode == 8


def test_mktemp_distinct(hlwm):
    lines = hlwm.call('mktemp int X mktemp int Y \
        chain , echo X , echo Y').stdout.splitlines()

    assert lines[0][0:4] == 'tmp.'
    assert lines[1][0:4] == 'tmp.'
    assert lines[0] != lines[1]


def test_mktemp_right_type(hlwm):
    hlwm.call('mktemp int X set_attr X 23')
    hlwm.call_xfail('mktemp int X set_attr X sdflkj') \
        .expect_stderr('not a valid value')


def test_mktemp_complete(hlwm):
    assert 'int' in hlwm.complete('mktemp')
    assert 'X' in hlwm.complete('mktemp string X echo')
    completions = hlwm.complete('mktemp string X mktemp string Y echo')
    assert 'X' in completions and 'Y' in completions
    compl2 = hlwm.complete('mktemp string X')
    assert 'X' in compl2 and 'echo' in compl2


def test_negate_command(hlwm):
    assert hlwm.call('! false').stdout == ''
    assert hlwm.call('! ! echo f').stdout == 'f\n'
    hlwm.call_xfail('! echo test') \
        .expect_stderr('test')


def test_negate_complete_cmd(hlwm):
    assert hlwm.complete('!') \
        == sorted(hlwm.call('list_commands').stdout.splitlines())


def test_negate_complete_arg(hlwm):
    assert 'left' in hlwm.complete('! focus')
    assert [] == hlwm.complete('! true')


def test_integer_out_of_range(hlwm):
    type2outOfRange = {
        'uint': ['-18446744073709551616', '-1', '18446744073709551616'],
        'int': ['-18446744073709551616', '18446744073709551616'],
    }
    for typeName, values in type2outOfRange.items():
        attribute = 'my_' + typeName + '_attr'
        hlwm.call(f'new_attr {typeName} {attribute}')
        for v in values:
            hlwm.call_xfail(['set_attr', attribute, v]) \
                .expect_stderr('out of range')
