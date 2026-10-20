import importlib.util as _mini_iu
import os as _mini_os
import sys as _mini_sys


def _mini_load(name):
    """同じフォルダの部品を1回だけ読む。"""
    try:
        folder = _mini_os.path.dirname(_mini_os.path.abspath(__file__))
    except NameError:
        raise ImportError("部品の場所が分かりません（__file__ がありません）")
    key = "yomiyasu_mini_fixture_" + name
    module = _mini_sys.modules.get(key)
    if module is None:
        spec = _mini_iu.spec_from_file_location(key, _mini_os.path.join(folder, name + ".py"))
        if spec is None:
            raise ImportError("部品 {} を読めません".format(name))
        module = _mini_iu.module_from_spec(spec)
        _mini_sys.modules[key] = module
        try:
            spec.loader.exec_module(module)
        except BaseException:
            del _mini_sys.modules[key]
            raise
    return module
