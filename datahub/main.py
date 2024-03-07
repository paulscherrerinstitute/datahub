"""CLI interface """
from datahub import *
import argparse
import logging
import json
import inspect

logger = logging.getLogger(__name__)

SOURCE_SEPARATOR = "/"
CHANNEL_SEPARATOR = ","
EMPTY_SOURCE = [{}]

def run_json(task):
    try:
        if type(task) == str:
            task = json.loads(task)
        file = task.get("file", None)
        format = task.get("format", "h5")
        prnt = task.get("print", False)
        plot = task.get("plot", None)
        pshell = task.get("pshell", None)
        start = task.get("start", None)
        end = task.get("end", None)
        path = task.get("path", None)
        decompress = task.get("decompress", False)
        compression = task.get("compression", Compression.GZIP)
        parallel = task.get("parallel", None)
        interval = task.get("interval", None)
        modulo = task.get("modulo", None)
        search = task.get("search", None)
        verbose  = task.get("verbose", None)
        query_id = task.get("id", False)
        time_type = task.get("time", "nano")
        if compression == "lz4":
            compression = Compression.BITSHUFFLE_LZ4
        elif compression.lower() in ["null", "none"]:
            compression = None

        valid_sources = {}
        for name in KNOWN_SOURCES.keys():
            _name = name
            exec(f"{name} = task.get('{name}', None)")
            exec(f"no = 0 if {name} is None else len({name})")
            exec(f"for i in range(no): \n   if {name}[i] is not None: valid_sources['{name}_'+str(i)] = ({name}[i], KNOWN_SOURCES['{name}'])")

        consumers = []
        if file is not None:
            if format.lower() in ["h5", "hdf5"]:
                consumers.append(HDF5Writer(file, default_compression=compression))
            elif format.lower() in ["txt", "text"]:
                consumers.append(TextWriter(file))
            else:
                raise Exception ("Invalid format: " + format)
        if prnt:
            consumers.append(Stdout())
        try:
            if pshell is not None:
                args = {}
                for arg, val in zip(pshell[::2], pshell[1::2]):
                    try:
                        args[arg] = json.loads(val)
                    except:
                        args[arg] = val
                consumers.append(PShell(**args))
        except Exception as ex:
            logger.exception(ex)
        if plot is not None:
            consumers.append(Plot(channels=[] if len(plot) < 1 else plot[0]))
        sources = []

        #If does nt have query arg, construct based on channels arg and start/end
        def get_query(source):
            nonlocal start, end, interval, modulo
            query = source.get("query", None)
            if query is None:
                channels = source.pop("channels", [])
                if type(channels) == str:
                    channels = channels.split(CHANNEL_SEPARATOR)
                    channels = [s.lstrip("'\"").rstrip("'\"") for s in channels]
                query = {"channels": channels}
                query.update(source)
            if "start" not in query:
                query["start"] = start
            if "end" not in query:
                query["end"] = end
            if "interval" not in query:
                if interval:
                    query["interval"] = interval
            if "modulo" not in query:
                if modulo:
                    query["modulo"] = modulo
            query_by_id = query_id
            if "id" in query:
                query_by_id = str_to_bool(str(query["id"]))
            if query_by_id:
                if not is_null_str(query["start"]):
                    query["start"]=int(query["start"])
                if not is_null_str(query["end"]):
                    query["end"]=int(query["end"])

            return query

        def add_source(cfg, src, empty):
            src.query = None if empty else get_query(cfg)
            sources.append(src)

        #Create source removing constructor parameters from the query dictionary
        def get_source_constructor(cls, typ):
            signature = inspect.signature(cls)
            pars = signature.parameters
            ret = cls.__name__+"("
            index = 0
            for name, par in pars.items():
                if par.kind != inspect.Parameter.VAR_KEYWORD:
                    if index > 0:
                        ret = ret + ", "
                    if par.default == inspect.Parameter.empty:
                        ret = ret + name + "=" + typ + ".pop('" + name + "')"
                    else:
                        if type (par.default) == str:
                            dflt = "'" + par.default + "'"
                        else:
                            dflt = str(par.default)
                        ret = ret + name + "=" + typ + ".pop('" + name + "', " + dflt + ")"
                    index = index + 1
            if index > 0:
                ret = ret + ", "
            ret = ret + f"auto_decompress={str(decompress)}, time_type='{str(time_type)}'"
            ret = ret + ")"
            return ret

        for name, (cfg,source) in valid_sources.items():
            empty = cfg =={}
            exec(f"{name} = cfg")
            constructor = eval("get_source_constructor(" + source.__name__ + ", '" + name + "')")
            exec('if ' + name + ' is not None: add_source(' + name + ', ' + constructor + ', ' + str(empty) +')')
        for source in sources:
            if verbose is not None:
                source.verbose = verbose
            if parallel is not None:
                source.parallel = parallel
            if path is not None:
                if source.path is None:
                    source.path = path

        if search is not None:
            if search == []:
                search = [""]
            for source in sources:
                try:
                    for regex in search:
                        source.print_search(regex)
                except:
                    logger.exception(f"Error searching source: {str(source)}")
        else:
            for source in sources:
                for consumer in consumers:
                    source.add_listener(consumer)

            for source in sources:
                if source is not None:
                    if source.query is None:
                        source.print_help()
                    else:
                        source.request(source.query, background=True)

            for source in sources:
                source.join()

    finally:
        cleanup()


def get_source_meta(cls):
    signature = inspect.signature(cls)
    pars = signature.parameters
    ret = "channels "
    for name, par in pars.items():
        if par.kind != inspect.Parameter.VAR_KEYWORD:
            if par.default == inspect.Parameter.empty:
                ret = ret + name + " "
            else:
                if type(par.default) == str:
                    dflt = "'" + par.default + "'"
                else:
                    dflt = str(par.default)
                ret = ret + name + "=" + dflt + " "
    ret = ret + ("start=None end=None")
    return ret


def parse_args():
    """Parse cli arguments with argparse"""
    parser = argparse.ArgumentParser(description='Command line interface for DataHub  ' + datahub.version(), prefix_chars='--')
    parser.add_argument("-j", "--json", help="Complete query defined as JSON", required=False)
    parser.add_argument("-f", "--file", help="Save data to file", required=False)
    parser.add_argument("-fmt", "--format", help="File format: h5 (default) or txt", required=False)
    parser.add_argument("-p", "--print", action='store_true', help="Print data to stdout", required=False)
    parser.add_argument("-m", "--plot", help="Create plots with matplotlib. ",required=False, nargs="*")
    parser.add_argument("-ps", "--pshell", help="Create plots in a PShell plot server on given port (default=7777). ", required=False, nargs="*")
    parser.add_argument("-t", "--time", help="Time type: nano/int (default), sec/float or str", required=False)
    parser.add_argument("-s", "--start", help="Relative or absolute start time or ID", required=False)
    parser.add_argument("-e", "--end", help="Relative or absolute end time or ID", required=False)
    parser.add_argument("-i", "--id", action='store_true', help="Query by id, and not time", required=False)
    parser.add_argument("-c", "--compression", help="Compression: gzip (default), szip, lzf, lz4 or none", required=False)
    parser.add_argument("-d", "--decompress", action='store_true', help="Auto-decompress compressed images", required=False)
    parser.add_argument("-pl", "--parallel", action='store_true', help="Parallelize query if possible",required=False)
    parser.add_argument("-pt", "--path", help="Path to data in the file", required=False)
    parser.add_argument("-sr", "--search", help="Search channel names given a pattern (instead of fetching data)", required=False , nargs="*")
    parser.add_argument("-di", "--interval", help="Downsampling interval between samples in seconds", required=False)
    parser.add_argument("-dm", "--modulo", help="Downsampling modulo of the samples", required=False)
    parser.add_argument("-v", "--verbose", action='store_true', help="Displays complete search results, not just channels names", required=False)

    for name, source in KNOWN_SOURCES.items():
        meta = eval("Source.get_source_meta(" + source.__name__ + ")")
        eval('parser.add_argument("--' + name + '", metavar="' + meta + '", help="' + name + ' query arguments", required=False, nargs="*")')

    args = parser.parse_args()
    return parser, args

def get_full_argument_name(parser, abbr):
    for action in parser._actions:
        if '-' + abbr in action.option_strings:
            return action.dest
    return None

def _split_list(list, separator):
    result = []
    sublist = []
    for item in list:
        if item == separator:
            if sublist:
                result.append(sublist)
                sublist = []
        else:
            sublist.append(item)
    if sublist:
        result.append(sublist)
    return result

def main():
    """Main function"""
    parser, args = parse_args()
    try:
        #if args.action == 'search':
        #    return search(args)
        if args.json:
            run_json(args.json)
        else:
            task={}
            if args.file:
                task["file"] = args.file
            if args.format:
                task["format"] = args.format
            if args.print:
                task["print"] = bool(args.print)
            task["plot"] = args.plot
            task["pshell"] = args.pshell
            if args.start:
                task["start"] = args.start
            if args.end:
                task["end"] = args.end
            if args.id:
                task["id"] = bool(args.id)
            if args.time:
                task["time"] = args.time
            if args.path:
                task["path"] = args.path
            if args.decompress:
                task["decompress"] = bool(args.decompress)
            if args.compression:
                task["compression"] = args.compression
            if args.parallel:
                task["parallel"] = args.parallel
            if args.interval:
                task["interval"] = args.interval
            if args.modulo:
                task["modulo"] = args.modulo
            if args.search is not None:
                task["search"] = args.search
            if args.verbose is not None:
                task["verbose"] = args.verbose

            for source in KNOWN_SOURCES.keys():
                source_str = eval("args." + source)
                if type(source_str) == list:
                    if len(source_str) == 1:
                        task[source] = json.loads(source_str[0])
                    else:
                        task[source] = []
                        sources = _split_list(source_str, SOURCE_SEPARATOR)
                        if sources == []:
                            task[source] = EMPTY_SOURCE #if source is entered with no arguments, print help for it
                        for src in sources:
                            index = len( task[source] )
                            task[source].append({})
                            for arg, val in zip(src[::2], src[1::2]):
                                full_name = get_full_argument_name(parser, arg)
                                if full_name:
                                    arg = full_name
                                try:
                                    task[source][index][arg] = json.loads(val)
                                except:
                                    task[source][index][arg] = val
            run_json(task)

    except RuntimeError as e:
        logger.error(e)
    return 0
if __name__ == '__main__':
    """
    json_str = '{' \
               '"file": "/Users/gobbo_a/dev/back/json.h5", ' \
               '"print": true, ' \
               '"epics": {"url": null, "query":{"start":null, "end":3.0, "channels": ["TESTIOC:TESTCALCOUT:Input", "TESTIOC:TESTSINUS:SinCalc", "TESTIOC:TESTWF2:MyWF"]}},' \
               '"bsread": {"url": "tcp://localhost:9999", "mode":"PULL", "query":{"start":null, "end":3.0, "channels":  ["UInt8Scalar", "Float32Scalar"]}}' \
               '}'
    args = ["--json", json_str]
    sys.argv=sys.argv + args
    """
    """
    args = ["--search", "SARFE10-PSSS059:SPECTRUM_X", "--databuffer"]
    sys.argv = sys.argv + args
    """
    main()

