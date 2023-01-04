from dataclasses import is_dataclass  # FrozenInstanceError,; dataclass,

import pytest

from hydra_zen import (  # builds,; load_from_yaml,; make_config,; make_custom_builds_fn,; save_as_yaml,; to_yaml,
    instantiate,
)
from hydra_zen.structured_configs._add_conf import add_batteries, add_conf

# from functools import partial
# from inspect import isclass
# from typing import Any, Callable, Dict, List, Optional


class SimpleClassToBeWrapped:
    def __init__(self, string_field: str = "a", int_field: int = 3):
        self.string_field = string_field
        self.int_field = int_field


@pytest.fixture
def simple_wrapped_class():
    return add_conf(
        zen_dataclass={
            "module": "tests.test_add_conf",
            "cls_name": "SimpleClassToBeWrapped",
        },
    )(SimpleClassToBeWrapped)


@add_conf
class SimpleDecoratedClass:
    def __init__(self, string_field: str = "b", int_field: int = 4):
        self.string_field = string_field
        self.int_field = int_field


@add_batteries
class SimpleBatteriesDecoratedClass:
    def __init__(self, string_field: str = "c", int_field: int = 5):
        self.string_field = string_field
        self.int_field = int_field


list_of_wrapped_classes = [
    simple_wrapped_class,
    SimpleDecoratedClass,
]


@pytest.mark.parametrize(
    "wrapped_class",
    [
        simple_wrapped_class,
        SimpleDecoratedClass,
        SimpleBatteriesDecoratedClass,
    ],
)
def test_add_conf_decorator_adds_dataclass_as_Conf_attr(wrapped_class):
    assert hasattr(wrapped_class, "Conf")
    assert is_dataclass(wrapped_class.Conf)


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


def test_class_to_config_roundtrip(simple_wrapped_class):
    simple_class_instance = simple_wrapped_class()
    simple_config = simple_class_instance.conf
    simple_class_instance_2 = instantiate(simple_config)
    assert isinstance(simple_class_instance_2, SimpleClassToBeWrapped)
    assert simple_class_instance_2.string_field == simple_class_instance.string_field
    assert simple_class_instance_2.int_field == simple_class_instance.int_field


@pytest.mark.parametrize(
    "wrapped_class",
    [
        # simple_wrapped_class,
        # SimpleDecoratedClass,
        SimpleBatteriesDecoratedClass,
    ],
)
def test_add_batteries_adds_conf_with_extra_methods(wrapped_class):
    assert hasattr(wrapped_class.Conf, "instantiate")
    assert hasattr(wrapped_class.Conf, "store")
    assert hasattr(wrapped_class.Conf, "to_yaml")
