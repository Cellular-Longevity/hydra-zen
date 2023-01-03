from dataclasses import FrozenInstanceError, dataclass, is_dataclass
from functools import partial
from inspect import isclass
from typing import Any, Callable, Dict, List, Optional

import pytest

from hydra_zen import (
    builds,
    instantiate,
    load_from_yaml,
    make_config,
    make_custom_builds_fn,
    save_as_yaml,
    to_yaml,
)
from hydra_zen.structured_configs._conf import add_conf


class SimpleClassToBeWrapped:
    def __init__(self, string_field: str = "a", int_field: int = 3):
        self.string_field = string_field
        self.int_field = int_field


@pytest.fixture
def simple_wrapped_class():
    return add_conf(SimpleClassToBeWrapped)


def test_add_conf_decorator_adds_dataclass_as_Conf_attr(simple_wrapped_class):
    assert hasattr(simple_wrapped_class, "Conf")
    assert is_dataclass(simple_wrapped_class.Conf)


def test_Conf_constructs_dataclass_instance(simple_wrapped_class):
    simple_config = simple_wrapped_class.Conf()
    assert isinstance(simple_config, simple_wrapped_class.Conf)


def test_instantiation_from_Conf_instance(simple_wrapped_class):
    simple_config = simple_wrapped_class.Conf()
    simple_class_instance = instantiate(simple_config)
    assert isinstance(simple_class_instance, SimpleClassToBeWrapped)


def test_normal_construction_of_wrapped_class(simple_wrapped_class):
    simple_class_instance = simple_wrapped_class()
    assert isinstance(simple_class_instance, SimpleClassToBeWrapped)


def test_class_instance_has_conf_attr(simple_wrapped_class):
    simple_class_instance = simple_wrapped_class()
    assert hasattr(simple_class_instance, "conf")
