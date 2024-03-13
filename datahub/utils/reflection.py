import inspect

def get_meta(cls, separator=" "):
    signature = inspect.signature(cls)
    pars = signature.parameters
    ret = ""
    for name, par in pars.items():
        if par.kind != inspect.Parameter.VAR_KEYWORD:
            if par.default == inspect.Parameter.empty:
                ret = ret + name + " "
            else:
                if type(par.default) == str:
                    dflt = "'" + par.default + "'"
                else:
                    dflt = str(par.default)
                ret = ret + name + "=" + dflt + separator
    return ret