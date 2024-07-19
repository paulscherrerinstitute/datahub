import re

CHANNEL_NAME_ALLOWED_SYMBOLS =  ":-"
CHANNEL_NAME_PATTERN = "[\w" + CHANNEL_NAME_ALLOWED_SYMBOLS + "]"

def check_msg_single_statement(msg, statement):
    pattern = r"^(?P<name>" + CHANNEL_NAME_PATTERN + "+)(?P<op>==|!=|<=|>=|>|<)(?P<value>.+)$"
    match = re.match(pattern, statement)
    if not match:
        raise ValueError(f"Invalid statement: {statement}")
    name = match.group("name")
    op = match.group("op")
    value_str = match.group("value")

    if name not in msg:
        return False
    actual_value = msg[name]

    #Convert the value to the appropriate type (int, float, bool, or str)
    try:
        if value_str.lower() == 'true':
            value = True
        elif value_str.lower() == 'false':
            value = False
        elif value_str.isdigit():
            value = int(value_str)
        else:
            try:
                value = float(value_str)
            except ValueError:
                value = value_str.strip('"\'')  # Remove surrounding quotes for string
    except ValueError:
        raise ValueError(f"Invalid value: {value}")

    # Try using eval to perform the comparison
    #try:
    #    return eval(f"{repr(actual_value)} {op} {repr(value)}")
    #except Exception:
    #    return False
    # Perform the comparison with no eval to improve performance
    if op == "==":
        return actual_value == value
    elif op == "!=":
        return actual_value != value
    elif op == "<=":
        return actual_value <= value
    elif op == ">=":
        return actual_value >= value
    elif op == "<":
        return actual_value < value
    elif op == ">":
        return actual_value > value
    else:
        raise ValueError(f"Invalid operator: {op}")


def check_msg(msg, statement):
    def tokenize(expression):
        #token_pattern = re.compile(r'\s*(AND|OR|\(|\)|True|False|\w+(<|>|[!=<>]=)[^\s()]+)\s*')
        token_pattern = re.compile(r'\s*(AND|OR|\(|\)|True|False|' + CHANNEL_NAME_PATTERN + '+(<|>|[!=<>]=)[^\s()]+)\s*')
        tokens = token_pattern.findall(expression)
        # Extract the first element from each tuple in tokens, which contains the actual token.
        tokens = [token[0] for token in tokens]
        return tokens

    def eval_expr(entry, tokens):
        def parse_value():
            token = tokens.pop(0)
            if token == '(':
                val = eval_expr(entry, tokens)
                if tokens and tokens[0] == ')':
                    tokens.pop(0)  # Remove ')'
                return val
            elif token == 'True':
                return True
            elif token == 'False':
                return False
            elif re.match(r"^" + CHANNEL_NAME_PATTERN + "+([!=<>]=|>|<).+$", token):
                return check_msg_single_statement(entry, token)
            else:
                raise ValueError(f"Unexpected token: {token}")

        values = [parse_value()]

        while tokens:
            if not tokens:
                break
            op = tokens.pop(0)
            if op == ')':
                break
            next_value = parse_value()
            if op == 'AND':
                values[-1] = values[-1] and next_value
            elif op == 'OR':
                values[-1] = values[-1] or next_value
            else:
                raise ValueError(f"Unexpected operator: {op}")

        return values[0]

    tokens = tokenize(statement)

    # Add a check for balanced parentheses
    if tokens.count('(') != tokens.count(')'):
        raise ValueError("Unbalanced parentheses in the statement")

    if len(tokens) == 1: #Speed up normal case (1 simple statement)
        return check_msg_single_statement(msg, tokens[0])
    return eval_expr(msg, tokens)