import json

from jinja2 import StrictUndefined, ChainableUndefined, ChoiceLoader

from .jinja2_utils import MyEnvironment, extract_template_error, RootTemplateLoader, SearchPathAbsLoader, \
    MyFileSystemLoader


class NullUndefined(ChainableUndefined):
    def _return_self(self, other):
        return self

    __add__ = __radd__ = __sub__ = __rsub__ = _return_self
    __mul__ = __rmul__ = __div__ = __rdiv__ = _return_self
    __truediv__ = __rtruediv__ = _return_self
    __floordiv__ = __rfloordiv__ = _return_self
    __mod__ = __rmod__ = _return_self
    __pos__ = __neg__ = _return_self
    __call__ = __getitem__ = _return_self
    __lt__ = __le__ = __gt__ = __ge__ = _return_self
    __int__ = __float__ = __complex__ = _return_self
    __pow__ = __rpow__ = _return_self


class Jinja2Renderer:
    def __init__(self, opts):
        self.opts = opts

    def build_env(self):
        debug_enabled = self.opts.get("debugTrace", False)
        root_loader = RootTemplateLoader()
        loader = ChoiceLoader([
            root_loader,
            SearchPathAbsLoader(self.opts.get("searchDirs", [])),
            MyFileSystemLoader(self.opts.get("searchDirs", [])),
        ])
        environment = MyEnvironment(debug_enabled=debug_enabled,
                                    loader=loader,
                                    undefined=NullUndefined if self.opts.get("nonStrict", False) else StrictUndefined,
                                    cache_size=10000,
                                    auto_reload=False,
                                    trim_blocks=self.opts.get("trimBlocks", False),
                                    lstrip_blocks=self.opts.get("lstripBlocks", False))
        environment.globals.update(self.opts.get("globals", {}))

        for e in self.opts.get("extensions", []):
            environment.add_extension(e)

        for name, code in self.opts.get("filters", {}).items():
            track = {}
            exec(code, track)
            i = name.find(":")
            if i != -1:
                funcname = name[i + 1:]
                name = name[:i]
            else:
                funcname = name

            f = track.get(funcname)

            if f is None or not callable(f):
                raise AttributeError(f"function {funcname} is not found in filter code")

            environment.filters[name] = f

        return environment, root_loader

    def render_helper(self, templates, cmd):
        env, root_loader = self.build_env()

        result = []

        for i, t in enumerate(templates):
            try:
                if cmd == "render_strings":
                    t = env.from_string(t).render()
                elif cmd == "render_files":
                    root_loader.root_template = t
                    t = env.get_template(t).render()
                elif cmd == "find_variables":
                    from jinja2 import Environment, meta
                    ast = Environment().parse(t)
                    t = json.dumps(list(meta.find_undeclared_variables(ast)))
                result.append({
                    "result": t
                })
            except Exception as e:
                result.append({
                    "error": extract_template_error(e),
                })

        return result

    def RenderStrings(self, templates):
        try:
            return self.render_helper(templates, "render_strings")
        except Exception as e:
            return [{
                "error": str(e)
            }] * len(templates)

    def RenderFiles(self, templates):
        try:
            return self.render_helper(templates, "render_files")
        except Exception as e:
            return [{
                "error": str(e)
            }] * len(templates)

    def FindVariables(self, templates):
        try:
            return self.render_helper(templates, "find_variables")
        except Exception as e:
            return [{
                "error": str(e)
            }] * len(templates)
