import re


def digits(value):
    return re.sub(r"\D", "", str(value))


def valid_cpf(value):
    n = digits(value)
    if len(n) != 11 or len(set(n)) == 1:
        return False
    for length in (9, 10):
        check = (sum(int(n[i]) * (length + 1 - i) for i in range(length)) * 10) % 11
        if int(n[length]) != (0 if check == 10 else check):
            return False
    return True


def valid_cnpj(value):
    n = digits(value)
    if len(n) != 14 or len(set(n)) == 1:
        return False
    for length, weights in ((12, [5,4,3,2,9,8,7,6,5,4,3,2]), (13, [6,5,4,3,2,9,8,7,6,5,4,3,2])):
        remainder = sum(int(n[i]) * weights[i] for i in range(length)) % 11
        if int(n[length]) != (0 if remainder < 2 else 11 - remainder):
            return False
    return True
