import dataclasses
import functools
import inspect
import warnings
from collections.abc import MutableMapping
from contextlib import suppress
from copy import deepcopy
from dataclasses import dataclass
from inspect import isclass, isfunction
from pathlib import Path
from pprint import pprint
from pydoc import locate
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple, Type

from hydra.core.config_store import ConfigStore
from omegaconf import MISSING, OmegaConf
from typing_extensions import Literal

from hydra_zen import (
    builds,
    instantiate,
    load_from_yaml,
    make_config,
    make_custom_builds_fn,
    save_as_yaml,
    to_yaml,
)
from hydra_zen.typing import SupportedPrimitive, ZenWrappers
from hydra_zen.typing._implementations import DataClass_

def get_zen_meta_defaults(zen_meta=None):
    """> It returns a dictionary of default values for the `zen_meta` dictionary.

    Args:
        zen_meta (dict): a dictionary of zen_meta parameters

    Returns:
        A dictionary with the keys: name_, group_, package_, provider_, defaults.
    """
    _zen_meta_defaults = dict(
        name_=None,
        group_=None,
        package_="_group_",
        provider_=None,
        defaults=["_self_"],
    )
    if zen_meta is None:
        return _zen_meta_defaults
    else:
        _zen_meta_defaults.update(zen_meta)
        return _zen_meta_defaults


def merge_zen_meta_defaults(name_, group_, package_, provider_, defaults):
    """It merges the zen_meta dictionary with the defaults dictionary.

    Args:
        name_: The name of the resource.
        group_: The group of the resource.
        package_: The name of the package that the resource belongs to.
        provider_: The name of the provider.
        defaults: The default values for the parameters.

    Returns:
        The zen_meta dictionary is being returned.
    """
    zen_meta = get_zen_meta_defaults()
    zen_meta["name_"] = zen_meta.get("name") or name_
    zen_meta["group_"] = zen_meta.get("group") or group_
    zen_meta["package_"] = zen_meta.get("package") or package_
    zen_meta["provider_"] = zen_meta.get("provider") or provider_
    zen_meta["defaults"] = zen_meta.get("defaults") if defaults is None else defaults
    return zen_meta

# commenting these out for now since builds_bases is deprecated starting from hydra-zen 0.8
# unclear if we need the functionality we were using it for
zen_meta_defaults = get_zen_meta_defaults()
# configures = make_custom_builds_fn(populate_full_signature=True, builds_bases=(ZenExtras,), zen_meta=zen_meta_defaults)

#configures = make_custom_builds_fn(populate_full_signature=True)


def add_conf(*args, **kwargs):
    if kwargs or len(args) != 1:
        return _add_custom_conf(**kwargs)
    cls = args[0]
    return _add_conf(cls, **kwargs)


def _add_custom_conf(
    name_: Optional[str] = None,
    group_: Optional[str] = None,
    package_: Optional[str] = "_group_",
    provider_: Optional[str] = None,
    defaults: Optional[list] = None,
    **kwargs,
):
    """Returns add_conf decorator but with different default arguments to be applied to the class
    level conf.

    Args:
        name_ (Optional[str], optional): _description_. Defaults to None.
        group_ (Optional[str], optional): _description_. Defaults to None.
        package_ (Optional[str], optional): _description_. Defaults to "_group_".
        provider_ (Optional[str], optional): _description_. Defaults to None.
        defaults (Optional[list], optional): _description_. Defaults to None.

    Returns:
        _type_: _description_
    """
    zen_meta = merge_zen_meta_defaults(name_, group_, package_, provider_, defaults)
    return functools.partial(_add_conf, zen_meta=zen_meta, **kwargs)


def _add_conf(
    cls,
    **kwargs,
):
    """Decorator that adds an attribute called `conf` which holds the configuration object for that
    class.

    Args:
        cls: the class that is being decorated

    Returns:
        The class itself.

    Examples:

        ### decorate a class definition ###
        @add_conf
        class MyClass:
            def __init__(
                self,
                a:str='dog',
                b:int=3,
                ):
                self.a = a
                self.b = b

            def __repr__(self):
                return f'MyClass({self.a}, {self.b})'

        # config class is now available as attribute on MyClass
        MyClassConfig = MyClass.conf
        MyClassConfig
        >>> types.Builds_MyClass

        # create instance of config class by calling .conf
        my_class_config_instance = MyClass.conf(a='Lily', b=117)
        my_class_config_instance
        >>> Builds_MyClass(_target_='hydra_zen.funcs.zen_processing', _zen_target='__main__.MyClass', _zen_exclude=('name_', 'group_', 'package_', 'provider_', 'defaults'), a='Lily', b=117, name_=None, group_=None, package_='_group_', provider_=None, defaults=['_self_'])

        # create instance of object via hydra instantiate
        my_class_instance = MyClass.conf(a='Lily', b=117).instantiate()
        my_class_instance
        >>> MyClass('Lily', 117)

        # fields of .conf track the arguments used to construct the parent object
        my_class = MyClass(a='Lily', b=117)
        my_class.conf
        >>> Builds_MyClass(_target_='hydra_zen.funcs.zen_processing', _zen_target='__main__.MyClass', _zen_exclude=('name_', 'group_', 'package_', 'provider_', 'defaults'), a='Lily', b=117, name_=None, group_=None, package_='_group_', provider_=None, defaults=['_self_'])

        ### decorate an imported class ###
        from sklearn.linear_model import LogisticRegression
        WrappedLogisticRegression = add_conf(LogisticRegression)
        LogisticRegressionConfig = WrappedLogisticRegression.conf
    """
    wrapped_cls = deepcopy(cls)
    # validate signature of wrapped class
    check_class_signature_does_not_include_reserved_keywords(wrapped_cls)
    check_signature_has_defaults_for_all_parameters(wrapped_cls)
    #conf = configures(wrapped_cls, **kwargs)  # creates conf dataclass for wrapped_cls
    conf = builds(wrapped_cls, populate_full_signature=True, builds_bases=(ZenExtras,), zen_meta=zen_meta_defaults, **kwargs)
    setattr(wrapped_cls, "Conf", conf)  # adds conf dataclass as Conf
    wrapped_cls = override_constructor(wrapped_cls)
    # wrapped_cls = override_mro(wrapped_cls,mro=cls.__mor__) # let's leave this as a reminder
    wrapped_cls = make_get_state_ignore_conf(wrapped_cls)

    return wrapped_cls


def override_constructor(cls):
    @functools.wraps(cls, updated=())
    class WrappedClass(cls):
        def __new__(
            cls,
            *args,
            name_: Optional[str] = None,
            group_: Optional[str] = None,
            package_: Optional[str] = "_group_",
            provider_: Optional[str] = None,
            defaults: Optional[list] = None,
            **kwargs,
        ):
            zen_meta = merge_zen_meta_defaults(
                name_, group_, package_, provider_, defaults
            )

            global _configuring
            if _configuring:
                return cls.Conf(*args, **zen_meta, **kwargs)
            else:
                return super(WrappedClass, cls).__new__(cls)

        def __init__(
            self,
            *args,
            name_: Optional[str] = None,
            group_: Optional[str] = None,
            package_: Optional[str] = "_group_",
            provider_: Optional[str] = None,
            defaults: Optional[list] = None,
            **kwargs,
        ):
            zen_meta = merge_zen_meta_defaults(
                name_, group_, package_, provider_, defaults
            )
            if not hasattr(self, "conf"):
                conf = self.Conf(*args, **zen_meta, **kwargs)
                setattr(self, "conf", conf)
            super().__init__(*args, **kwargs)

    # functools.update_wrapper(WrappedClass,cls,updated=())
    return WrappedClass


global _configuring
_configuring = False


class ConfMode(object):
    def __enter__(self):
        global _configuring
        _configuring = True

    def __exit__(self, exc_type, exc_value, traceback):
        global _configuring
        _configuring = False


def make_get_state_ignore_conf(cls):
    """It takes a class and returns a new class that has a new __getstate__ method.

    this is to avoid errors from trying to pickle objects that have conf attribute
    since pickle struggles with dynamically generated classes

    Args:
        cls: the class to be modified

    Returns:
        A new class with a new __getstate__ method
    """

    def new__getstate__(self):
        state = self.__dict__.copy()
        conf = state.get("conf")
        del conf
        Conf = state.get("Conf")
        del Conf
        return state

    setattr(cls, "__getstate__", new__getstate__)
    return cls


def check_class_signature_does_not_include_reserved_keywords(cls):
    """It checks that the constructor of a class does not use any of the reserved keywords.

    Args:
        cls: the class to be checked
    """

    for k in inspect.signature(cls).parameters.keys():
        try:
            assert k not in [
                "name_",
                "group_",
                "package_",
                "provider_",
            ]
        except AssertionError:
            print(
                f"Warning: {cls.__name__} constructor uses a reserved keyword argument: {k}"
            )


def check_signature_has_defaults_for_all_parameters(cls_or_func):
    """It checks that the constructor of a class does not use any of the reserved keywords.

    Args:
        cls_or_func: the class or function to be checked
    """
    defaultless_params = []
    for k, param in inspect.signature(cls_or_func).parameters.items():
        if k not in [
            "kwargs",
            "name_",
            "group_",
            "package_",
            "provider_",
        ]:
            if param.default is not inspect._empty:
                defaultless_params.append(k)


global cs
cs = ConfigStore.instance()


@dataclass
class ZenExtras:
    """Mixin that adds convenience methods to hydra_zen dataclasses."""

    def __post_init__(self):
        if getattr(self, "name_", None) is not None:
            self.store()

    def to_yaml(self, *, resolve=False, sort_keys=False):
        """It converts the data into a YAML format.

        Args:
            resolve: If True, resolve any references in the object. Defaults to False
            sort_keys: If True, the output will be sorted by key. Defaults to False

        Returns:
            The return value is a string.
        """
        return to_yaml(self, resolve=resolve, sort_keys=sort_keys)

    def save_as_yaml(self, f, resolve=False):
        """It takes a file object and a boolean value as arguments, and then it saves the file as a
        YAML file.

        Args:
            f: the file to save to.
            resolve: If True, resolve the object to a dictionary before saving. Defaults to False
        """
        save_as_yaml(self, f, resolve=resolve)

    def load_from_yaml(self, file_):
        """`load_from_yaml` loads a yaml file into a python object.

        Args:
            file_: The file to load the parameters from.

        Returns:
            The load_from_yaml function is being returned.
        """
        return load_from_yaml(file_)

    def to_omegaconf(self):
        """It converts a PyTorch model to an OmegaConf object.

        Returns:
            OmegaConf.structured(self)
        """
        return OmegaConf.structured(self)

    def to_dict(self):
        """`OmegaConf.to_container(self.to_omegaconf())`

        The `to_omegaconf()` function returns a dictionary of the class attributes. The `to_container()`
        function converts the dictionary to a container

        Returns:
            A dictionary
        """
        return OmegaConf.to_container(self.to_omegaconf())

    def instantiate(self):
        """It returns the instantiate function.

        Returns:
            The instantiate method is being returned.
        """
        return instantiate(self)

    def unpack(self):
        """Alias for instantiate."""
        return self.instantiate()

    def store(self):
        """Stores object in the config store.

        Returns:
            The object itself (for chaining)
        """
        global cs
        cs.store(
            name=self.name_,
            node=self,
            group=self.group_,
            package=self.package_,
            provider=self.provider_,
        )
        return self

    def save(self, config_root, subdir=None, filename=None, resolve=False):
        """`save` takes a `config_root` (a path to a directory), a `subdir` (a path to a
        subdirectory), a `filename` (a path to a file), and a `resolve` (a boolean) and saves the
        configuration as a yaml file in the `config_root` directory.

        Args:
            config_root: The root directory where the config file will be saved.
            subdir: The subdirectory to save the config file in.
            filename: The name of the file to save the configuration to.
            resolve: If True, resolve the config to a dict and save that. Defaults to False
        """
        config_root = Path(config_root)
        subdir = Path(subdir or self.group_)
        subdir = config_root.joinpath(self.group_)
        subdir.mkdir(parents=True, exist_ok=True)
        filename = Path(filename or self.name_)
        self.save_as_yaml(
            subdir.joinpath(filename).with_suffix(".yaml"), resolve=resolve
        )

    def show(self, verbosity: str = "compact", exclude_keys=None, *args, **kwargs):
        """It shows the object in a human readable format.

        Returns:
            The return value is a string.
        """
        exclude_keys = (
            [
                "package_",
                "provider_",
                "_zen_exclude",
                "zen_partial",
                "_target_",
                "_recursive_",
            ]
            if exclude_keys is None
            else exclude_keys
        )

        if verbosity == "all":
            output = self.to_yaml(*args, **kwargs)
        elif verbosity == "compact":
            d = self.to_dict()
            delete_keys_from_dict(d, exclude_keys)
            delete_null_cs_keys(d)
            delete_null_vals_from_dict(d)
            output = to_yaml(OmegaConf.create(d), *args, **kwargs)
        elif verbosity == "standard":
            d = self.to_dict()
            delete_keys_from_dict(d, exclude_keys)
            output = to_yaml(OmegaConf.create(d), *args, **kwargs)
        return print(output)

    def __call__(self, **kwargs):
        """`__call__` takes a dictionary of keyword arguments, merges them with the current
        instance of the class, and returns a new instance of the class with the updated config.

        Returns:
            A new instance of the class, with the new values set.
        """
        # //TODO https://github.com/Cellular-Longevity/newtricks/issues/491 Fix support for hydra-zen types when using __call__ on instantiated conf
        # current_instance_omegaconf = self.to_omegaconf()

        # # current_instance_omegaconf.merge_with(newly_called_omegaconf)
        # current_instance_omegaconf.merge_with(OmegaConf.create(dict(**kwargs)))

        # # OmegaConf.to_object(current_instance_omegaconf)
        # # it should be possible to do this ^ but it hits an error
        # # https://github.com/mit-ll-responsible-ai/hydra-zen/issues/242
        # # looks like it has maybe been patched in recent PR to omegaconf https://github.com/omry/omegaconf/pull/879

        # return _to_object_workaround(current_instance_omegaconf)

        new_instance = deepcopy(self)
        for key, value in kwargs.items():
            setattr(new_instance, key, value)

        try:
            new_instance.store()
        except:
            pass
        return new_instance
