import pytest


@pytest.mark.parametrize("invalid_layout,error_pos", [
    ('(', 1),
    ('()', 1),
    ('foo baar', 0),
    ('(foo baar', 1),
    ('((clients max:0 ))', 1),
    ('(clients)', 8),
    ('(clients )', 9),
    ('(split max:0.5:1)', 7),
    ('(split horizontal:0.05:1)', 7),
    ('(split horizontal:0.95:1)', 7),
    ('(split horizontal:x:1)', 7),
    ('(split horizontal:0.5:x)', 7),
    ('(split horizontal:0.5:-1)', 7),
    ('(split horizontal:0.5:2)', 7),
    ('(split horizontal:0.3)', 7),
    ('(split horizontal:0.3:0:0)', 7),
    ('(split  horizonta:0.5:0 )', 8),
    ('(clients max )', 9),
    ('(clients max:0:0 )', 9),
    ('(clients ma:0 )', 9),
    ('(clients max:-1 )', 9),
    ('(clients grid:0 asdf )', 16),
    ('(clients grid:0 0xx0)', 16),
    ('(clients grid:0 09)', 16),
    ('(clients grid:0 0x)', 16),
    ('(clients grid:0 x)', 16),
    ('(split horizontal:0.5:0 x)', 24),
    ('(split horizontal:0.5:0 (split horizontal:0.5:1', 47),
    ('(split horizontal:0.5:0 (split horizontal:0.5:1 ', 48),
    ('(split horizontal:0.5:0 (split horizontal:0.5:1 )', 49),
    ('(split horizontal:0.5:0 (split horizontal:0.5:1 )))', 50),
    ('(split horizontal:0.5:0 (clients max:1', 38),
])
def test_syntax_errors_position(hlwm, invalid_layout, error_pos):
    c = hlwm.call_xfail(['load', invalid_layout])
    c.expect_stderr(r'^load: Syntax error at {}: '.format(error_pos))


def is_subseq(x, y):
    """Checks if x is a subsequence (not substring) of y."""
    # from https://stackoverflow.com/a/24017747/4400896
    it = iter(y)
    return all(c in it for c in x)


@pytest.mark.parametrize("layout", [
    "(clients max:0)",
    "(clients grid:0)",
    " (  clients   vertical:0  )",
    "(split horizontal:0.3:0)",
    "(split vertical:0.3:0 (clients horizontal:0))",
    "(split vertical:0.3:0 (split vertical:0.4:1))",
])
@pytest.mark.parametrize('num_splits_before', [0, 1, 2])
def test_valid_layout_syntax_partial_layouts(hlwm, layout, num_splits_before):
    for i in range(0, num_splits_before):
        hlwm.call('split explode')

    # load the layout that defines the layout tree only partially
    hlwm.call(['load', layout])

    # The new layout is the old layout with some '(clients …)' (and theoretically
    # even '(split…)') subtrees inserted.
    assert is_subseq(layout.replace(' ', ''), hlwm.call('dump').stdout)


@pytest.mark.parametrize(
    "layout", [
        # with window ID placeholders 'W'
        "(clients max:0 W)",
        "(clients max:1 W W)",
        "(split horizontal:0.9:0 (split vertical:0.5:1 (clients max:0) (clients grid:0)) (clients horizontal:0))",
        "(split vertical:0.4:1 (clients max:2 W W W) (clients grid:0 W))",
    ])
def test_full_layouts(hlwm, layout):
    clients = [hlwm.create_client() for k in range(0, layout.count('W'))]
    for winid, _ in clients:
        # replace the next W by the window ID
        layout = layout.replace('W', winid, 1)

    p = hlwm.call(['load', layout])

    assert p.stdout == ''
    assert layout == hlwm.call('dump').stdout


@pytest.mark.parametrize("layout", [
    "(clients horizontal:0 0234)",
    "(clients vertical:0 0x2343)",
    "(clients vertical:0 1713)",
])
def test_load_invalid_winids(hlwm, layout):
    p = hlwm.call(['load', layout])

    assert p.stdout.startswith("Warning: Unknown window IDs")


@pytest.mark.parametrize(
    "running_clients_num,focus",
    [(n, f) for n in [1, 3] for f in range(0, n)])
def test_focus_client_via_load(hlwm, running_clients, running_clients_num, focus):
    layout = '(clients horizontal:{} {})'.format(
        focus, ' '.join(running_clients))

    hlwm.call(['load', layout])

    assert hlwm.call('dump').stdout == layout
    assert hlwm.get_attr('clients.focus.winid') == running_clients[focus]


@pytest.mark.parametrize(
    "running_clients_num,num_bring",
    [(n, f) for n in [1, 3] for f in range(0, n + 1)])
def test_load_brings_windows(hlwm, running_clients, running_clients_num, num_bring):
    hlwm.call('add other')
    layout = '(clients horizontal:0{}{})'.format(
        (' ' if num_bring > 0 else ''),
        ' '.join(running_clients[0:num_bring]))
    assert int(hlwm.get_attr('tags.0.client_count')) \
        == len(running_clients)
    assert int(hlwm.get_attr('tags.1.client_count')) == 0

    hlwm.call(['load', 'other', layout])

    assert int(hlwm.get_attr('tags.0.client_count')) == \
        len(running_clients) - num_bring
    assert int(hlwm.get_attr('tags.1.client_count')) == num_bring
    assert hlwm.call('dump other').stdout == layout
