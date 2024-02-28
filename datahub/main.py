"""CLI interface """
from datahub import *
import argparse
import logging
import json
import inspect

logger = logging.getLogger(__name__)

def run_json(task):
    try:
        if type(task) == str:
            task = json.loads(task)
        file = task.get("file", None)
        format = task.get("format", "h5")
        prnt = task.get("print", False)
        start = task.get("start", None)
        end = task.get("end", None)
        path = task.get("path", None)
        decompress = task.get("decompress", False)
        compression = task.get("compression", Compression.GZIP)
        parallel = task.get("parallel", None)
        search = task.get("search", None)
        verbose  = task.get("verbose", None)
        query_id = task.get("id", False)
        time_type = task.get("time", "nano")
        if compression == "lz4":
            compression = Compression.BITSHUFFLE_LZ4
        elif compression.lower() in ["null", "none"]:
            compression = None

        empty_sources = []
        empty_source = {}
        for name in KNOWN_SOURCES.keys():
            _name = name
            exec(name + ' = task.get("' + name + '", None)')
            exec(f"if {name} == empty_source: empty_sources.append('{_name}')")

        consumers = []
        if file is not None:
            if format.lower() in ["h5", "hdf5"]:
                consumers.append(HDF5Writer(file, default_compression=compression, path=path))
            elif format.lower() in ["txt", "text"]:
                consumers.append(TextWriter(file))
            else:
                raise Exception ("Invalid format: " + format)
        if prnt:
            consumers.append(StdoutWriter())
        sources = []

        #If does nt have query arg, construct based on channels arg and start/end
        def get_query(source):
            nonlocal start, end
            query = source.get("query", None)
            if query is None:
                channels = source.pop("channels", [])
                if type(channels) == str:
                    channels = channels.split(',')
                    channels = [s.lstrip("'\"").rstrip("'\"") for s in channels]
                query = {"channels": channels}
                query.update(source)
            if "start" not in query:
                query["start"] = start
            if "end" not in query:
                query["end"] = end
            if query_id:
                if query["start"]:
                    query["start"]=int(query["start"])
                if query["end"]:
                    query["end"]=int(query["end"])

            return query

        def add_source(cfg, src):
            src.query = get_query(cfg)
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

        for name, source in KNOWN_SOURCES.items():
            constructor = eval("get_source_constructor(" + source.__name__ + ", '" + name + "')")
            exec('if ' + name + ' is not None: add_source(' + name + ', ' + constructor + ')')
        for source in sources:
            if verbose is not None:
                source.verbose = verbose
            if parallel is not None:
                source.parallel = parallel

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
                    if source.type in empty_sources:
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
    parser.add_argument("-m", "--format", help="File format: h5 (default) or txt", required=False)
    parser.add_argument("-p", "--print", action='store_true', help="Print data to stdout", required=False)
    parser.add_argument("-t", "--time", help="Time type: nano/int (default), sec/float or str", required=False)
    parser.add_argument("-s", "--start", help="Relative or absolute start time or ID", required=False)
    parser.add_argument("-e", "--end", help="Relative or absolute end time or ID", required=False)
    parser.add_argument("-i", "--id", action='store_true', help="Query by id, and not time", required=False)
    parser.add_argument("-c", "--compression", help="Compression: gzip (default), szip, lzf, lz4 or none", required=False)
    parser.add_argument("-d", "--decompress", action='store_true', help="Auto-decompress compressed images", required=False)
    parser.add_argument("-a", "--parallel", action='store_true', help="Parallelize query if possible",required=False)
    parser.add_argument("-l", "--path", help="Path to data in the file", required=False)
    parser.add_argument("-r", "--search", help="Search channel names given a pattern (instead of fetching data)", required=False , nargs="*")
    parser.add_argument("-v", "--verbose", action='store_true', help="Displays complete search results, not just channels names", required=False)

    for name, source in KNOWN_SOURCES.items():
        meta = eval("Source.get_source_meta(" + source.__name__ + ")")
        eval('parser.add_argument("--' + name + '", metavar="' + meta + '", help="' + name + ' query arguments", required=False, nargs="*")')

    args = parser.parse_args()
    return args


def main():
    """Main function"""
    args = parse_args()
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
                        task[source] = {}
                        for arg, val in zip(source_str[::2], source_str[1::2]):
                            try:
                                task[source][arg] = json.loads(val)
                            except:
                                task[source][arg] = val
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

