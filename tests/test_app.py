def test_do_something_one():
    from app import do_something

    assert do_something() == 1


def test_do_something_two():
    from app import do_something

    assert do_something() != 0


def test_do_something_three():
    assert True
