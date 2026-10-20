import hashlib as _mini_hashlib
import os as _mini_os
import sys as _mini_sys
import types as _mini_types


def _mini_load(name):
    """同じフォルダの name.py を読む。鍵に版と、フォルダの場所と中身の sha256 の頭を入れ、ほかの写しと混ぜない。
    __pycache__ は作らない。"""
    try:
        here = __file__
    except NameError:
        raise ImportError("部品の場所が分かりません（__file__ がありません）") from None
    folder = _mini_os.path.dirname(_mini_os.path.realpath(here))
    path = _mini_os.path.join(folder, name + ".py")
    with open(path, "rb") as handle:
        data = handle.read()
    digest = _mini_hashlib.sha256(folder.encode("utf-8", "surrogatepass") + b"\0" + data).hexdigest()
    key = "yomiyasu_mini_{}_{}_{}".format(__version__.replace(".", "_").replace("-", "_"), name, digest[:16])
    module = _mini_sys.modules.get(key)
    if module is None:
        module = _mini_types.ModuleType(key)
        module.__file__ = path
        code = compile(data, path, "exec", dont_inherit=True)
        _mini_sys.modules[key] = module
        try:
            exec(code, module.__dict__)
        except BaseException:
            del _mini_sys.modules[key]
            raise
    return module


def _mini_bind(name, names):
    try:
        module = _mini_load(name)
        space = globals()
        for key in names.split():
            space[key] = getattr(module, key)
    except Exception as error:
        _mini_on_error(name, error)
